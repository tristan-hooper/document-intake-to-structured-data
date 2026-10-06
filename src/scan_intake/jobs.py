"""Windows job ownership: descendants cannot outlive the adapter job."""
import os
import uuid

# Documented Win32 flag; Python's subprocess does not export this constant.
CREATE_SUSPENDED = 0x00000004


def attach_job(process):
    if os.name != "nt":
        return None
    import win32job
    job = win32job.CreateJobObject(None,"scan-intake-"+uuid.uuid4().hex)
    try:
        information = win32job.QueryInformationJobObject(job,win32job.JobObjectExtendedLimitInformation)
        information["BasicLimitInformation"]["LimitFlags"] = win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        win32job.SetInformationJobObject(job,win32job.JobObjectExtendedLimitInformation,information)
        win32job.AssignProcessToJobObject(job,int(process._handle))
        return job
    except BaseException:
        job.Close()
        raise


def terminate_job(job):
    import win32job
    try:
        win32job.TerminateJobObject(job,1)
    finally:
        job.Close()


def resume_process(process):
    """Resume the sole initial thread after a suspended launcher joins its job."""
    if os.name != "nt":
        return
    import psutil
    import win32api
    import win32con
    import win32process
    threads = psutil.Process(process.pid).threads()
    if len(threads) != 1:
        raise RuntimeError("Unexpected thread state in suspended adapter launcher")
    handle = win32api.OpenThread(win32con.THREAD_SUSPEND_RESUME,False,threads[0].id)
    try:
        if win32process.ResumeThread(handle) != 1:
            raise RuntimeError("Adapter initial thread was not suspended exactly once")
    finally:
        handle.Close()
