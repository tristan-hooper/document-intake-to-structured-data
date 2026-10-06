"""Development-only feasibility probe. No evaluation references or pages are read."""
import argparse
import json
import os
from pathlib import Path
from time import perf_counter
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/"src"))
os.environ["HF_HOME"] = str(root/".cache/huggingface")
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["OMP_NUM_THREADS"] = "4"
from scan_intake.adapters import make_adapter

parser = argparse.ArgumentParser()
parser.add_argument("pipeline",choices=["A","B","C"])
args = parser.parse_args()
start = perf_counter()
adapter = make_adapter(args.pipeline,root)
initialization = perf_counter()-start
outputs = {}
for page_id in ["S2-p002","S3-p006","S3-p011","S4-p006"]:
    result = adapter.extract(root/"data/rendered"/(page_id+".png"))
    outputs[page_id] = result
    print(page_id,len(result["units"]),len(result["field_units"]),round(result["processing_seconds"],3),flush=True)
destination = root/"runs/development-probes"
destination.mkdir(parents=True,exist_ok=True)
(destination/(args.pipeline+".json")).write_text(json.dumps({"pipeline":args.pipeline,"initialization_seconds":initialization,"pages":outputs},indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
print("Saved development probe",args.pipeline,"initialization",round(initialization,3),flush=True)
