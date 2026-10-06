"""Engine adapters. These receive page images only, never reference answers."""
from pathlib import Path
from time import perf_counter
import os

from PIL import Image


def unit(text, bounds, scope, confidence=None, confidence_scope=None):
    return dict(text=text, bounds=bounds, scope=scope, confidence=confidence,
                confidence_scope=confidence_scope)


def rectangle(points, width, height):
    return [float(min(p[0] for p in points))/width, float(min(p[1] for p in points))/height,
            float(max(p[0] for p in points))/width, float(max(p[1] for p in points))/height]


def rapid_params(root, threads=4):
    from rapidocr import LangRec
    models = root / "models/rapidocr"
    return {
        "Det.model_path": str(models/"ch_PP-OCRv4_det_infer.onnx"),
        "Cls.model_path": str(models/"ch_ppocr_mobile_v2.0_cls_infer.onnx"),
        "Rec.model_path": str(models/"en_PP-OCRv4_rec_infer.onnx"),
        "Rec.lang_type": LangRec.EN, "Rec.rec_keys_path": None,
        "Global.font_path": str(Path(os.environ.get("WINDIR", "C:/Windows"))/"Fonts/arial.ttf"),
        "Global.max_side_len": 2000, "Global.text_score": 0.5,
        "EngineConfig.onnxruntime.use_cuda": False,
        "EngineConfig.onnxruntime.use_dml": False,
        "EngineConfig.onnxruntime.intra_op_num_threads": threads,
        "EngineConfig.onnxruntime.inter_op_num_threads": 1,
    }


class TesseractAdapter:
    def __init__(self, root, threads=4):
        import pytesseract
        self.library = pytesseract
        executable = os.environ.get("TESSERACT_CMD") or str(root/"tools/vendor/tesseract/tesseract.exe")
        self.library.pytesseract.tesseract_cmd = executable
        tessdata = os.environ.get("TESSDATA_PREFIX") or str(root/"tools/vendor/tesseract/tessdata")
        os.environ["TESSDATA_PREFIX"] = tessdata
        self.config = "--oem 1 --psm 3"
        if not Path(executable).is_file() or not (Path(tessdata)/"eng.traineddata").is_file():
            raise FileNotFoundError("Tesseract executable or English model is missing")
        self.version = str(self.library.get_tesseract_version())

    def extract(self, path):
        started = perf_counter()
        with Image.open(path) as image:
            width,height = image.size
            data = self.library.image_to_data(image,lang="eng",config=self.config,
                    output_type=self.library.Output.DICT,timeout=115)
        units = []
        for i,text in enumerate(data["text"]):
            if not text.strip():
                continue
            left,top,w,h = (data[k][i] for k in ("left","top","width","height"))
            score = float(data["conf"][i])
            units.append(unit(text,[left/width,top/height,(left+w)/width,(top+h)/height],
                              "word",score if score >= 0 else None,"tesseract_word_0_100"))
        return dict(units=units,field_units=units,processing_seconds=perf_counter()-started,
                    engine="Tesseract",engine_version=self.version)


class RapidAdapter:
    def __init__(self, root, threads=4):
        from .rapid_geometry import corrected_rapidocr_class
        self.engine = corrected_rapidocr_class()(params=rapid_params(root,threads))

    def extract(self, path):
        started = perf_counter()
        result = self.engine(str(path),return_word_box=True)
        with Image.open(path) as image:
            width,height = image.size
        units,words = [],[]
        if result.boxes is not None:
            for box,text,score in zip(result.boxes,result.txts,result.scores):
                units.append(unit(text,rectangle(box,width,height),"line",float(score),"rapidocr_line_0_1"))
            for line in result.word_results:
                for text,score,box in line:
                    if box is not None:
                        words.append(unit(text,rectangle(box,width,height),"native_word_alignment",
                                          float(score),"rapidocr_word_0_1"))
        return dict(units=units,field_units=words or units,processing_seconds=perf_counter()-started,
                    engine="RapidOCR",geometry_note="Word alignment comes from RapidOCR's recognition alignment; no adapter-generated word boxes.")


class DoclingAdapter:
    def __init__(self, root, threads=4):
        from docling.datamodel.accelerator_options import AcceleratorOptions, AcceleratorDevice
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions
        from docling.document_converter import DocumentConverter, ImageFormatOption
        params = rapid_params(root,threads)
        options = PdfPipelineOptions(artifacts_path=root/"models/docling",
            accelerator_options=AcceleratorOptions(device=AcceleratorDevice.CPU,num_threads=threads),
            do_ocr=True,do_table_structure=True,generate_parsed_pages=True,do_picture_classification=False,
            do_picture_description=False,do_code_enrichment=False,do_formula_enrichment=False,
            ocr_options=RapidOcrOptions(backend="onnxruntime",lang=["english"],
                force_full_page_ocr=True,det_model_path=params["Det.model_path"],
                cls_model_path=params["Cls.model_path"],rec_model_path=params["Rec.model_path"],
                font_path=params["Global.font_path"],rapidocr_params=params))
        self.converter = DocumentConverter(allowed_formats=[InputFormat.IMAGE],
            format_options={InputFormat.IMAGE:ImageFormatOption(pipeline_options=options)})
        self.converter.initialize_pipeline(InputFormat.IMAGE)

    def extract(self, path):
        from docling_core.types.doc import TableItem, TextItem
        started = perf_counter()
        result = self.converter.convert(path,raises_on_error=True)
        document = result.document
        page = document.pages[1]
        width,height = page.size.width,page.size.height
        units,fields,reading_regions = [],[],[]
        for item,_ in document.iterate_items():
            if isinstance(item,TableItem):
                for cell in item.data.table_cells:
                    if cell.bbox is None or not cell.text.strip():
                        continue
                    bbox = cell.bbox.to_top_left_origin(height)
                    fields.append(unit(cell.text,[bbox.l/width,bbox.t/height,bbox.r/width,bbox.b/height],"table_cell"))
                    reading_regions.append(fields[-1])
            elif isinstance(item,TextItem):
                for prov in item.prov:
                    bbox = prov.bbox.to_top_left_origin(height)
                    units.append(unit(item.text,[bbox.l/width,bbox.t/height,bbox.r/width,bbox.b/height],"block"))
                    reading_regions.append(units[-1])
        # Retain engine-provided OCR lines for bounded text/field alignment outside tables.
        ocr_lines = []
        for cell in result.pages[0].cells:
            bbox = cell.rect.to_bounding_box().to_top_left_origin(height)
            ocr_lines.append(unit(cell.text,[bbox.l/width,bbox.t/height,bbox.r/width,bbox.b/height],
                                  "line",float(cell.confidence),"rapidocr_line_0_1"))
        ordered,used = [],set()
        for region in reading_regions:
            left,top,right,bottom = region["bounds"]
            inside = [(i,line) for i,line in enumerate(ocr_lines)
                      if i not in used and left <= (line["bounds"][0]+line["bounds"][2])/2 <= right
                      and top <= (line["bounds"][1]+line["bounds"][3])/2 <= bottom]
            if region["scope"] == "table_cell":
                ordered.append(region)
                used.update(i for i,_ in inside)
            else:
                ordered.extend(line for _,line in inside)
                used.update(i for i,_ in inside)
        ordered.extend(line for i,line in enumerate(ocr_lines) if i not in used)
        return dict(units=ordered or units,field_units=fields+ocr_lines,
                    document_units=units,table_cells=fields,processing_seconds=perf_counter()-started,
                    engine="Docling + RapidOCR",conversion_status=str(result.status),
                    geometry_note="Table cells are native Docling structure; other fields use OCR lines. No word coordinates are fabricated.")


def make_adapter(pipeline,root,threads=4):
    return {"A":TesseractAdapter,"B":RapidAdapter,"C":DoclingAdapter}[pipeline](root,threads)
