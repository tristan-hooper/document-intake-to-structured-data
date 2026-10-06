"""Run the frozen comparison sequentially, retaining logs, failures and exports."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]


def main():
    sys.path.insert(0,str(ROOT/'src'))
    from scan_intake.cli import verify_freeze
    verify_freeze(ROOT)
    results=ROOT/'results'
    index_path=results/'benchmark-index.json'
    if index_path.exists():
        raise RuntimeError('Benchmark index exists; do not silently rerun or replace frozen evidence')
    index={'started_at_utc':datetime.now(timezone.utc).isoformat(),'status':'running','pipelines':{},
        'timing_protocol':'Each OCR pipeline renders all selected pages into a new cache, performs one initial extraction and three warmed repeats per page. CLI workload timing includes repetitions; warmed medians isolate processing. External wall timing also includes final export.',
        'order':['A','B','C','N']}
    def save():
        temporary=index_path.with_suffix('.partial')
        temporary.write_text(json.dumps(index,indent=2)+'\n',encoding='utf-8')
        temporary.replace(index_path)
    save()
    for pipeline in index['order']:
        folder=results/pipeline
        folder.mkdir(exist_ok=True)
        command=[sys.executable,'-m','scan_intake.cli','extract','--pipeline',pipeline,
                 '--split','evaluation','--fresh']
        if pipeline!='N':
            command+=['--repetitions','3','--cold-render']
        started=perf_counter()
        entry={'status':'running','command':command[2:],'started_at_utc':datetime.now(timezone.utc).isoformat()}
        index['pipelines'][pipeline]=entry
        save()
        with (folder/'execution.log').open('w',encoding='utf-8') as log:
            process=subprocess.Popen(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                                     text=True,encoding='utf-8')
            entry['process_pid']=process.pid
            save()
            run=None
            for line in process.stdout:
                log.write(line)
                log.flush()
                print(pipeline,line.strip(),flush=True)
                try:
                    message=json.loads(line)
                    if 'run' in message:
                        run=Path(message['run'])
                except (ValueError,TypeError):
                    pass
            code=process.wait()
        entry.update(exit_code=code,external_wall_seconds=perf_counter()-started,
                     status='completed' if code==0 else 'failed')
        if run is not None:
            entry['run_id']=run.name
            entry['artifact_sha256']={}
            for filename in ['run.json','pages.json','candidates.csv','review.csv']:
                destination=folder/filename
                shutil.copyfile(run/filename,destination)
                entry['artifact_sha256'][filename]=hashlib.sha256(destination.read_bytes()).hexdigest()
            scoring=subprocess.run([sys.executable,'-m','scan_intake.cli','evaluate',str(run),
                '--output',str(folder/'evaluation.json')],cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
            (folder/'scoring.log').write_text(scoring.stdout+scoring.stderr,encoding='utf-8')
            entry['scoring_exit_code']=scoring.returncode
            if scoring.returncode:
                entry['status']='scoring_failed'
        else:
            entry['status']='no_export'
        save()
    index['status']='completed' if all(p['status']=='completed' for p in index['pipelines'].values()) else 'completed_with_failures'
    index['finished_at_utc']=datetime.now(timezone.utc).isoformat()
    save()
    print('Benchmark',index['status'],flush=True)
    return 0 if index['status']=='completed' else 1


if __name__=='__main__':
    raise SystemExit(main())
