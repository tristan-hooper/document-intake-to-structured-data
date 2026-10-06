"""Reproduce model/runtime files from the checked-in URL and SHA-256 inventory."""
import hashlib
import argparse
import json
from pathlib import Path
import subprocess
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def verified(path, spec):
    return path.is_file() and path.stat().st_size == spec.get("bytes",path.stat().st_size) and hashlib.sha256(path.read_bytes()).hexdigest() == spec["sha256"]


def download(path,spec):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+".partial")
    try:
        with urlopen(spec["url"],timeout=120) as response, temporary.open("wb") as output:
            while chunk:=response.read(1024*1024):
                output.write(chunk)
        if not verified(temporary,spec):
            raise ValueError(f"Downloaded artifact hash/size mismatch: {path.name}")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--pipeline',choices=['A','B','C','all'],default='all')
    args=parser.parse_args()
    manifest=json.loads((ROOT/"data/model-manifest.json").read_text(encoding="utf-8"))
    prefixes={'A':('tools/vendor/',),'B':('models/rapidocr/',),
              'C':('models/rapidocr/','models/docling/'),'all':('',)}
    manifest['files']=[item for item in manifest['files'] if item['path'].startswith(prefixes[args.pipeline])]
    vendor=[item for item in manifest["files"] if item["path"].startswith("tools/vendor/") and "url" not in item]
    if any(not verified(ROOT/item["path"],item) for item in vendor):
        archive=ROOT/"tools/vendor/tesseract-5.5.3-installer.exe"
        distribution=manifest["tesseract_distribution"]
        if not verified(archive,distribution):
            download(archive,distribution)
        seven_zip=Path("C:/Program Files/7-Zip/7z.exe")
        if not seven_zip.is_file():
            raise FileNotFoundError("7-Zip is required to extract the pinned Windows Tesseract distribution locally")
        subprocess.run([str(seven_zip),"x",str(archive),"-o"+str(ROOT/"tools/vendor/tesseract"),"-y"],check=True,stdout=subprocess.DEVNULL)
    for item in manifest["files"]:
        path=(ROOT/item["path"]).resolve()
        if not path.is_relative_to(ROOT):
            raise ValueError("Artifact path escapes project")
        if not verified(path,item):
            if "url" not in item:
                raise ValueError(f"Extracted runtime artifact mismatch: {item['path']}")
            download(path,item)
        print("Verified",item["path"],flush=True)
    print("All pinned models/runtime files verified",flush=True)


if __name__ == "__main__":
    main()
