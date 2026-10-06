import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
import queue
import time

import pytest

from scan_intake.process import AdapterProcess
from scan_intake.jobs import attach_job, resume_process, CREATE_SUSPENDED
from scan_intake.storage import Store, export_run
from scan_intake.evaluation import edit_distance


def test_edit_distance_has_independent_expected_results():
    assert edit_distance("kitten","sitting") == 3
    assert edit_distance("ABC","abc") == 3
    assert edit_distance(["a","b"],["a","c","b"]) == 1
    assert edit_distance("abc","") == 3


def test_page_commit_and_alias_resume(tmp_path):
    source = {"sha256":"abc","title":"Report","local_file":"report.pdf"}
    result = {"pdf_page":1,"status":"completed","value":"0"}
    store = Store(tmp_path/"state.sqlite")
    store.commit_page("key",source,"A",result)
    store.close()
    resumed = Store(tmp_path/"state.sqlite")
    assert resumed.lookup("key") == result
    resumed.observe_alias({**source,"local_file":"renamed.pdf"})
    assert resumed.connection.execute("SELECT count(*) FROM pages").fetchone()[0] == 1
    assert resumed.connection.execute("SELECT count(*) FROM observations").fetchone()[0] == 2
    resumed.commit_page("failed",source,"A",{"pdf_page":2,"status":"timeout"})
    assert resumed.lookup("failed") is None
    resumed.close()


def test_failed_page_transaction_does_not_leave_source(tmp_path):
    store = Store(tmp_path/"state.sqlite")
    source = {"sha256":"abc","title":"Report","local_file":"report.pdf"}
    with pytest.raises(sqlite3.IntegrityError):
        store.commit_page("key",source,"A",{"pdf_page":None,"status":"completed"})
    assert store.connection.execute("SELECT count(*) FROM sources").fetchone()[0] == 0
    store.close()


def test_interrupted_export_does_not_publish_partial_run(tmp_path,monkeypatch):
    first = export_run(tmp_path,"first",[],{"status":"completed"})
    pointer = (tmp_path/"current.json").read_bytes()
    real_replace = os.replace
    def fail_publication(source,destination):
        if Path(destination).name == "second":
            raise OSError("simulated interrupted rename")
        return real_replace(source,destination)
    monkeypatch.setattr(os,"replace",fail_publication)
    with pytest.raises(OSError):
        export_run(tmp_path,"second",[],{"status":"completed"})
    assert (tmp_path/"current.json").read_bytes() == pointer
    assert not (tmp_path/"second").exists()
    assert json.loads((first/"run.json").read_text())["artifact_sha256"]


def test_timeout_terminates_owned_process_tree(tmp_path):
    import psutil
    child_script = "import time; time.sleep(60)"
    pid_file = tmp_path/"child-pid.txt"
    host_file = tmp_path/"host-pid.txt"
    script = tmp_path/"hang.py"
    script.write_text("import os,subprocess,sys,time\nfrom pathlib import Path\n"
        f"Path({str(host_file)!r}).write_text(str(os.getpid()))\n"
        "sys.stdin.readline()\n"
        f"child=subprocess.Popen([sys.executable,'-c',{child_script!r}])\n"
        f"Path({str(pid_file)!r}).write_text(str(child.pid))\n"
        "time.sleep(60)\n",encoding="utf-8")
    worker = AdapterProcess.__new__(AdapterProcess)
    worker.messages = queue.Queue()
    worker.log = (tmp_path/"worker.log").open("w")
    worker.process = subprocess.Popen([sys.executable,str(script)],stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,stderr=worker.log,text=True,encoding="utf-8",
        start_new_session=os.name != "nt",
        creationflags=(subprocess.CREATE_NO_WINDOW | CREATE_SUSPENDED) if os.name == "nt" else 0)
    try:
        if os.name == "nt":
            # Deliberately delay attachment: even the virtualenv host must not boot yet.
            time.sleep(.1)
            assert not host_file.exists()
            assert psutil.Process(worker.process.pid).children() == []
        worker.job = attach_job(worker.process)
        resume_process(worker.process)
        worker.process.stdin.write("start\n")
        worker.process.stdin.flush()
        deadline = time.monotonic()+5
        while not pid_file.exists() and time.monotonic() < deadline:
            time.sleep(.01)
        assert pid_file.exists()
        child_pid = int(pid_file.read_text())
        child_process = psutil.Process(child_pid)
        with pytest.raises(TimeoutError):
            worker.receive(.05)
        assert worker.process.poll() is not None
        child_process.wait(timeout=5)
        assert not child_process.is_running()
    finally:
        worker.close()
