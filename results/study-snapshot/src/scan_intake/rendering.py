"""Render verified byte snapshots; retain cache evidence and close PDF resources."""
import hashlib
import json
import math
import os
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import pypdfium2 as pdfium
from PIL import Image

from .contracts import ContractError, read_json, fingerprint

RENDER_SETTINGS = {"dpi":300,"color":"RGB","format":"PNG","pypdfium2":"4.30.0",
                   "preprocessing":"none","max_pixels":25_000_000}


def open_document(snapshot,source):
    try:
        document = pdfium.PdfDocument(snapshot)
    except Exception as error:
        raise ContractError("Malformed, encrypted or unsupported PDF") from error
    if len(document) != source["total_pdf_pages"] or len(document) > 150:
        document.close()
        raise ContractError("PDF page count mismatch or limit exceeded")
    return document


def render_page(snapshot,source,number,cache):
    started = perf_counter()
    key = fingerprint({"source":source["sha256"],"page":number,"settings":RENDER_SETTINGS})
    directory = Path(cache)/key
    path,meta_path = directory/"page.png",directory/"render.json"
    if path.is_file() and meta_path.is_file():
        metadata = read_json(meta_path)
        if metadata["image_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest():
            with Image.open(path) as image:
                if image.mode == "RGB" and list(image.size) == metadata["dimensions"]:
                    return path,{**metadata,"cache_hit":True,"lookup_seconds":perf_counter()-started}
    document = open_document(snapshot,source)
    try:
        page = document[number-1]
        try:
            width,height = page.get_size()
            if math.ceil(width*300/72)*math.ceil(height*300/72) > RENDER_SETTINGS["max_pixels"]:
                raise ContractError("Rendered page exceeds pixel limit")
            bitmap = page.render(scale=300/72)
            try:
                image = bitmap.to_pil().convert("RGB")
                directory.mkdir(parents=True,exist_ok=True)
                temporary = directory/(uuid4().hex+".png")
                try:
                    image.save(temporary,format="PNG")
                    image_hash = hashlib.sha256(temporary.read_bytes()).hexdigest()
                    os.replace(temporary,path)
                finally:
                    temporary.unlink(missing_ok=True)
                metadata = dict(render_key=key,image_sha256=image_hash,dimensions=list(image.size),
                                settings=RENDER_SETTINGS,render_seconds=perf_counter()-started,cache_hit=False)
                temporary = directory/(uuid4().hex+".json")
                try:
                    temporary.write_text(json.dumps(metadata,indent=2)+"\n",encoding="utf-8")
                    os.replace(temporary,meta_path)
                finally:
                    temporary.unlink(missing_ok=True)
                return path,metadata
            finally:
                bitmap.close()
        finally:
            page.close()
    finally:
        document.close()


def native_regions(snapshot,source,page_spec):
    document = open_document(snapshot,source)
    try:
        page = document[page_spec["pdf_page"]-1]
        try:
            width,height = page.get_size()
            textpage = page.get_textpage()
            try:
                regions = {}
                for region in [page_spec["text_region"],*page_spec["targets"]]:
                    left,top,right,bottom = region["bounds"]
                    text = textpage.get_text_bounded(left*width,(1-bottom)*height,
                                                    right*width,(1-top)*height)
                    regions[region.get("target_id",region.get("region_id"))] = text
                return dict(native_regions=regions,engine="Existing PDF text",
                            existing_text_characters=textpage.count_chars())
            finally:
                textpage.close()
        finally:
            page.close()
    finally:
        document.close()
