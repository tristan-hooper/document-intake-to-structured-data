"""Record an auditable pre-evaluation snapshot; refuse to overwrite a freeze."""
from datetime import datetime,timezone
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

import psutil

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('data/evaluation-freeze.json'))
    args=parser.parse_args()
    destination=args.output if args.output.is_absolute() else ROOT/args.output
    if destination.exists():
        raise RuntimeError('Evaluation freeze already exists; revision requires an explicit record')
    label=destination.stem.replace('evaluation-freeze-','')
    evidence=ROOT/'results/verification'/label
    evidence.mkdir(parents=True,exist_ok=True)
    temporary=ROOT/'.cache/test-tmp'
    temporary.mkdir(parents=True,exist_ok=True)
    environment={**os.environ,'TEMP':str(temporary),'TMP':str(temporary)}
    checks={
        'sources':[sys.executable,'-m','scan_intake.cli','verify-sources'],
        'annotations':[sys.executable,'tools/validate_annotations.py'],
        'tests':[sys.executable,'-m','pytest','-q','--basetemp','.cache/pytest-freeze'],
    }
    outcomes={}
    for name,command in checks.items():
        result=subprocess.run(command,cwd=ROOT,env=environment,capture_output=True,text=True,encoding='utf-8')
        log=evidence/(name+'.txt')
        log.write_text(result.stdout+result.stderr,encoding='utf-8')
        outcomes[name]={'exit_code':result.returncode,'log':log.relative_to(ROOT).as_posix(),
                        'sha256':hashlib.sha256(log.read_bytes()).hexdigest()}
        if result.returncode:
            raise RuntimeError(f'Pre-freeze check failed: {name}; see {log}')
    environment_record={'python':platform.python_version(),'platform':platform.platform(),
        'processor_identifier':os.environ.get('PROCESSOR_IDENTIFIER'),
        'logical_cpus':psutil.cpu_count(),'physical_cpus':psutil.cpu_count(logical=False),
        'physical_memory_bytes':psutil.virtual_memory().total,'device':'CPU','adapter_threads':4,
        'execution_note':'Sequential local runs; other desktop activity is uncontrolled. No GPU inference.'}
    paths=[ROOT/'pyproject.toml',ROOT/'requirements-benchmark.lock',ROOT/'config/benchmark.json',
           ROOT/'data/manifest.json',ROOT/'data/model-manifest.json',
           ROOT/'data/annotations/targets.json',ROOT/'data/annotations/references.json',
           ROOT/'data/annotations/README.md',*sorted((ROOT/'src/scan_intake').glob('*.py')),
           *sorted((ROOT/'tests').glob('*.py')),ROOT/'tools/fetch_sources.py',ROOT/'tools/fetch_models.py',
           ROOT/'tools/run_benchmark.py',ROOT/'tools/summarize_benchmark.py',
           ROOT/'tools/finalize_benchmark_integrity.py',ROOT/'tools/validate_annotations.py',
           ROOT/'tools/freeze_evaluation.py']
    freeze={'version':1,'frozen_at_utc':datetime.now(timezone.utc).isoformat(),
        'scoring_rule':'Table cells are atomic; target assignment uses the cell center. Crossing line/block bounds remain unresolved.',
        'evaluation_started':False,'checks':outcomes,'environment':environment_record,
        'artifact_sha256':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        'policy':'No evaluation outputs used for configuration, target selection, or rule selection after freeze.',
        'annotation_limit':'Codex visual transcription, checked twice by the same annotator; no independent human adjudication.',
        'development_evidence':['20261006T014317Z-A-8e50ae3c','20261006T014806Z-B-0fb61c4f','20261006T014515Z-C-55b0788e'],
        'development_note':'Earlier development artifacts may have prior implementation fingerprints. Geometry repair, scoped model verification and cold-render support are covered by current tests; cold rendering/resume additionally checked through CLI.'}
    destination.write_text(json.dumps(freeze,indent=2)+'\n',encoding='utf-8')
    print('Frozen',len(paths),'artifacts',flush=True)


if __name__=='__main__':
    main()
