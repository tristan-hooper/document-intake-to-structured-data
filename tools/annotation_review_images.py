"""Produce inspection crops from draft regions; no recognition is performed."""
import json
from pathlib import Path
from PIL import Image, ImageDraw

root = Path(__file__).resolve().parents[1]
pages = json.loads((root / "data/annotations/targets.json").read_text(encoding="utf-8"))["pages"]
for page in pages:
    with Image.open(root / "data/rendered" / (page["page_id"]+".png")) as image:
        def crop(bounds):
            x0,y0,x1,y1 = bounds
            return image.crop((round(x0*image.width),round(y0*image.height),
                               round(x1*image.width),round(y1*image.height)))
        passage = crop(page["text_region"]["bounds"])
        passage.thumbnail((1450, 1200))
        sheet = Image.new("RGB", (1500, passage.height+330), "#e0e0e0")
        draw = ImageDraw.Draw(sheet)
        draw.text((5,5),page["page_id"]+" text region (no OCR)",fill="black")
        sheet.paste(passage,(15,25))
        for index,target in enumerate(page["targets"]):
            tile = crop(target["bounds"])
            tile = tile.resize((tile.width*3,tile.height*3))
            tile.thumbnail((680,115))
            x,y = 15+(index%2)*745,passage.height+55+(index//2)*140
            draw.text((x,y-20),target["target_id"],fill="black")
            sheet.paste(tile,(x,y))
        destination = root / "data/previews/review" / (page["page_id"]+".png")
        destination.parent.mkdir(parents=True,exist_ok=True)
        sheet.save(destination)
print("Created",len(pages),"review sheets")
