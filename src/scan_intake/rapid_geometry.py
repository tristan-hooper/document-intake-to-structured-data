"""Version-specific integration fix: align words before mapping to original pixels.

RapidOCR 3.4.2 build_final_output maps detection boxes before calc_word_boxes.
The latter expects preprocessing coordinates and maps its results again. Retain
the original detection boxes for the native alignment routine; do not estimate
token positions or use reference answers.
"""


def corrected_rapidocr_class():
    from importlib.metadata import version
    from rapidocr import RapidOCR
    if version("rapidocr") != "3.4.2":
        raise RuntimeError("RapidOCR geometry integration requires pinned version 3.4.2")

    class CorrectedRapidOCR(RapidOCR):
        def build_final_output(self,ori_img,det_res,cls_res,rec_res,cropped_img_list,op_record):
            self._alignment_boxes = None
            self._alignment_crops = cropped_img_list
            if det_res.boxes is not None and rec_res.txts is not None:
                keep = [i for i,text in enumerate(rec_res.txts) if text.strip()]
                self._alignment_boxes = det_res.boxes[keep].copy()
                self._alignment_crops = [cropped_img_list[i] for i in keep]
            try:
                return super().build_final_output(ori_img,det_res,cls_res,rec_res,cropped_img_list,op_record)
            finally:
                self._alignment_boxes = None
                self._alignment_crops = None

        def calc_word_boxes(self,img,dt_boxes,rec_res,op_record,raw_h,raw_w):
            if self._alignment_boxes is None:
                raise RuntimeError("Missing native detection geometry for word alignment")
            return super().calc_word_boxes(self._alignment_crops,self._alignment_boxes,
                                          rec_res,op_record,raw_h,raw_w)

    return CorrectedRapidOCR
