# Source and software notices

The [MIT license](LICENSE) applies to this project's original code and documentation. It does not change the terms for Census publications, dependencies, model weights, or Windows fonts. This repository does not bundle PDFs, model weights, installed packages, Tesseract binaries, or fonts. Setup downloads the pinned inputs separately.

## Census sources

The four reports are U.S. Census Bureau publications. Their titles, dates, download links, selected pages, and file hashes are in the [dataset record](docs/DATASET.md) and [source manifest](data/manifest.json). The Census Bureau's [public access policy](https://www2.census.gov/foia/ds_policies/ds027.pdf) says employee-created works generally lack U.S. copyright protection, with exceptions. This is not a blanket license for third-party material or use outside the United States.

This repository includes short reference passages and selected aggregate values to explain and score the experiment. It does not reproduce whole reports or imply Census Bureau endorsement. Source material retains its own status; the project MIT license does not relicense it.

## Main software and models

| Component | Recorded terms | Source |
|---|---|---|
| Docling 2.67.0 code | MIT | Installed wheel license; [upstream](https://github.com/docling-project/docling) |
| RapidOCR 3.4.2 code | Apache-2.0 | [Versioned license](https://github.com/RapidAI/RapidOCR/blob/v3.4.2/LICENSE) |
| ONNX Runtime 1.23.2 | MIT plus included third-party notices | Installed package `LICENSE` and `ThirdPartyNotices.txt`; [upstream](https://github.com/microsoft/onnxruntime) |
| Tesseract 5.5.3 | Apache-2.0; Windows distribution includes additional libraries | [Versioned license](https://github.com/tesseract-ocr/tesseract/blob/5.5.3/LICENSE) |
| Tesseract English fast model | Apache-2.0 | [Model repository license](https://github.com/tesseract-ocr/tessdata_fast/blob/main/LICENSE) |
| pytesseract 0.3.13 | Apache-2.0 | Installed package license; [upstream](https://github.com/madmaze/pytesseract) |
| pypdfium2 4.30.0 | Apache-2.0 OR BSD-3-Clause, plus PDFium third-party terms | Installed package `LicenseRef-PdfiumThirdParty.txt`; [upstream](https://github.com/pypdfium2-team/pypdfium2) |
| Docling Heron weights | Apache-2.0 | [Pinned model card](https://huggingface.co/docling-project/docling-layout-heron/blob/8f39ad3c0b4c58e9c2d2c84a38465abf757272d8/README.md) |
| Docling TableFormer weights | Pinned model card declares CDLA-Permissive-2.0 | [Pinned model card](https://huggingface.co/docling-project/docling-models/blob/fc0f2d45e2218ea24bce5045f58a389aed16dc23/README.md) |
| PP-OCR recognition/detection and classifier weights | Separate model artifacts; do not infer their terms from the RapidOCR code license | [Pinned download inventory](data/model-manifest.json), [PaddleOCR upstream](https://github.com/PaddlePaddle/PaddleOCR), [RapidOCR model distribution](https://www.modelscope.cn/models/RapidAI/RapidOCR) |
| Arial font used locally | Supplied by Windows; not redistributed | Local Windows installation |

The [dependency inventory](docs/DEPENDENCY_LICENSES.csv) records license declarations from the installed distributions matching the benchmark lock. A declaration is not a substitute for a package's full license or its bundled notices. Dependencies are installed by the user, not copied into this repository. Anyone distributing a packaged application, container, binaries, or weights must review those components and preserve their required notices separately. This source-only publication does not claim that every dependency or weight can be redistributed under MIT.
