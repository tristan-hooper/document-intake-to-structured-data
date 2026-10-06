"""Own adapter process lifetime and terminate its descendants on timeout."""
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import signal
from .jobs import attach_job, terminate_job


class AdapterProcess:
    def __init__(self,root,pipeline,log_path,threads=4,initialization_timeout=120):
        self.messages = queue.Queue()
        self.log = Path(log_path).open("a",encoding="utf-8")
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(root/"src")
        environment["PYTHONUTF8"] = "1"
        environment["PYTHONIOENCODING"] = "utf-8"
        self.job = None
        try:
            self.process = subprocess.Popen([sys.executable,"-m","scan_intake.worker","--root",str(root),
                "--pipeline",pipeline,"--threads",str(threads)],cwd=root,env=environment,
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,text=True,encoding="utf-8",
                start_new_session=os.name != "nt",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            self.job = attach_job(self.process)
            self.process.stdin.write("start\n")
            self.process.stdin.flush()
            threading.Thread(target=self._read,daemon=True).start()
            response = self.receive(initialization_timeout)
            if response.get("status") != "ready":
                raise RuntimeError(response.get("error","Adapter initialization failed"))
            self.initialization_seconds = response["initialization_seconds"]
        except BaseException:
            self.close()
            raise

    def _read(self):
        try:
            for line in self.process.stdout:
                try:
                    self.messages.put(json.loads(line))
                except json.JSONDecodeError:
                    self.messages.put({"status":"protocol_error","error":"Non-JSON adapter output"})
        except (UnicodeError,OSError,ValueError):
            self.messages.put({"status":"protocol_error","error":"Adapter output decoding failed"})
        finally:
            self.messages.put({"status":"process_exited","error":"Adapter process exited"})

    def receive(self,timeout):
        try:
            response = self.messages.get(timeout=timeout)
        except queue.Empty:
            self.close()
            raise TimeoutError("Adapter wall-clock timeout; owned process tree terminated")
        if response.get("status") in {"process_exited","protocol_error"}:
            self.close()
            raise RuntimeError(response["error"])
        return response

    def extract(self,path,repetitions=0,timeout=120):
        from .contracts import fingerprint
        def once():
            if self.process.poll() is not None:
                raise RuntimeError("Adapter process is not running")
            self.process.stdin.write(json.dumps({"image":str(path)})+"\n")
            self.process.stdin.flush()
            return self.receive(timeout)
        response = once()
        timings,hashes = [],[]
        if response["status"] == "completed":
            output = response["output"]
            initial = fingerprint({"units":output["units"],"fields":output["field_units"]})
            for _ in range(repetitions):
                measured = once()
                if measured["status"] != "completed":
                    return measured
                result = measured["output"]
                timings.append(result["processing_seconds"])
                hashes.append(fingerprint({"units":result["units"],"fields":result["field_units"]}))
            output["repeat_outputs_identical"] = all(h == initial for h in hashes) if hashes else None
        return {**response,"warmed_processing_seconds":timings}

    def close(self):
        process = getattr(self,"process",None)
        if process is not None:
            if getattr(self,"job",None) is not None:
                terminate_job(self.job)
                self.job = None
            elif process.poll() is None and os.name != "nt":
                os.killpg(process.pid,signal.SIGKILL)
            elif process.poll() is None:
                process.kill()
            if process.poll() is None:
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
            for handle in (process.stdin,process.stdout):
                if handle:
                    handle.close()
        if getattr(self,"log",None):
            self.log.close()

    def __enter__(self):
        return self

    def __exit__(self,*_):
        self.close()
