"""Independent coordinate oracle: a 2x resize must be reversed exactly once."""
from types import SimpleNamespace
import numpy as np
from rapidocr.ch_ppocr_det import TextDetOutput
from rapidocr.ch_ppocr_rec import TextRecOutput
from rapidocr import LangRec
from scan_intake.rapid_geometry import corrected_rapidocr_class


def test_word_geometry_is_mapped_once():
    engine = corrected_rapidocr_class().__new__(corrected_rapidocr_class())
    engine.return_word_box = True
    engine.return_single_char_box = False
    engine.cfg = SimpleNamespace(Global=SimpleNamespace(text_score=.5,font_path='C:/Windows/Fonts/arial.ttf'),
                                 Rec=SimpleNamespace(lang_type=LangRec.EN))
    engine.filter_by_text_score = lambda result: result
    original = np.array([[[100.,200.],[200.,200.],[200.,220.],[100.,220.]]])
    def native_alignment(crops,boxes,result,single_char):
        # The recognition aligner receives preprocessing geometry, not page geometry.
        np.testing.assert_array_equal(boxes,original)
        result.word_results = ((('42',.99,boxes[0].tolist()),),)
        return result
    engine.cal_rec_boxes = native_alignment
    detection = TextDetOutput(boxes=original.copy(),scores=[.99])
    recognition = TextRecOutput(txts=('42',),scores=[.99],word_results=[object()])
    result = engine.build_final_output(np.zeros((1000,1000,3),dtype=np.uint8),
        detection,SimpleNamespace(elapse=0),recognition,[np.zeros((20,100,3),dtype=np.uint8)],
        {'preprocess':{'ratio_h':2.,'ratio_w':2.}})
    expected = [[200,400],[400,400],[400,440],[200,440]]
    assert result.word_results[0][0][2] == expected
    np.testing.assert_array_equal(result.boxes[0],expected)
