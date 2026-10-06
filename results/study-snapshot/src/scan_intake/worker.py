"""Isolated long-lived adapter process; stdout is a JSON-lines protocol."""
import argparse
import json
import os
from pathlib import Path
import sys
from time import perf_counter


def send(value):
    sys.stdout.write(json.dumps(value,ensure_ascii=False,allow_nan=False)+"\n")
    sys.stdout.flush()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root",type=Path,required=True)
    parser.add_argument("--pipeline",choices=["A","B","C"],required=True)
    parser.add_argument("--threads",type=int,default=4)
    args = parser.parse_args()
    os.environ["HF_HOME"] = str(args.root/".cache/huggingface")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["OMP_NUM_THREADS"] = str(args.threads)
    # Parent assigns process ownership before any engine can launch a child.
    if sys.stdin.readline().strip() != "start":
        return 1
    from .adapters import make_adapter
    started = perf_counter()
    try:
        adapter = make_adapter(args.pipeline,args.root,args.threads)
    except Exception as error:
        send(dict(status="initialization_error",error=f"{type(error).__name__}: {error}"))
        return 1
    send(dict(status="ready",initialization_seconds=perf_counter()-started))
    for line in sys.stdin:
        request = json.loads(line)
        try:
            output = adapter.extract(Path(request["image"]))
            send(dict(status="completed",output=output))
        except Exception as error:
            send(dict(status="extraction_error",error=f"{type(error).__name__}: {error}"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
