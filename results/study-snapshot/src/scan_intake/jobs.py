"""Windows job ownership: descendants cannot outlive the adapter job."""
import os
import uuid


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
