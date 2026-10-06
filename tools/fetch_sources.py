"""Download unchanged public PDFs from the pinned source manifest."""
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def main():
    manifest = json.loads((ROOT/"data/manifest.json").read_text(encoding="utf-8"))
    folder = ROOT/"data/raw"
    folder.mkdir(parents=True,exist_ok=True)
    for source in manifest["sources"]:
        destination = folder/source["local_file"]
        if destination.exists():
            data = destination.read_bytes()
        else:
            with urlopen(source["url"],timeout=120) as response:
                data = response.read(20*1024*1024+1)
        if len(data) != source["bytes"] or hashlib.sha256(data).hexdigest() != source["sha256"]:
            raise ValueError(f"Source size/hash mismatch: {source['source_id']}")
        if not destination.exists():
            temporary = destination.with_suffix(".pdf.partial")
            temporary.write_bytes(data)
            temporary.replace(destination)
        print(source["source_id"],"verified",flush=True)


if __name__ == "__main__":
    main()
