"""Render selected pages for manual annotation. Never reads existing OCR text."""
import hashlib
import io
import json
import math
from pathlib import Path

import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[1]
MAX_PIXELS = 25_000_000
manifest = json.loads((ROOT / "data/manifest.json").read_text(encoding="utf-8"))
for source in manifest["sources"]:
    snapshot = (ROOT / "data/raw" / source["local_file"]).read_bytes()
    if hashlib.sha256(snapshot).hexdigest() != source["sha256"]:
        raise ValueError(f"Source hash mismatch: {source['source_id']}")
    document = pdfium.PdfDocument(snapshot)
    try:
        for split in ("development", "evaluation"):
            for number in source[f"{split}_pdf_pages"]:
                page = document[number - 1]
                try:
                    scale = 300 / 72
                    width_points, height_points = page.get_size()
                    width_pixels = math.ceil(width_points * scale)
                    height_pixels = math.ceil(height_points * scale)
                    if width_pixels * height_pixels > MAX_PIXELS:
                        raise ValueError(f"Rendered page exceeds pixel limit: {source['source_id']}-p{number:03}")
                    bitmap = page.render(scale=scale)
                    try:
                        image = bitmap.to_pil().convert("RGB")
                        if image.width * image.height > MAX_PIXELS:
                            raise ValueError(f"Rendered page exceeds pixel limit: {source['source_id']}-p{number:03}")
                        name = f'{source["source_id"]}-p{number:03}'
                        target = ROOT / "data/rendered" / f"{name}.png"
                        target.parent.mkdir(parents=True, exist_ok=True)
                        image.save(target)
                        preview = image.copy()
                        preview.thumbnail((1400, 1800))
                        target = ROOT / "data/previews" / f"{name}.png"
                        target.parent.mkdir(parents=True, exist_ok=True)
                        preview.save(target)
                        print(name, split, image.size)
                    finally:
                        bitmap.close()
                finally:
                    page.close()
    finally:
        document.close()
