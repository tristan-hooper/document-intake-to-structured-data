# Real scanned reports in the test

I used actual scanned PDFs from the U.S. Census Bureau. I chose them online because I wanted to test real differences in print and page layout, not errors made by artificial blur. OCR (optical character recognition) is software that reads text from page images. I compared three OCR pipelines on the selected pages and tested text already stored in two PDFs as a separate baseline. I downloaded and inspected the files on October 5, 2026. The four PDFs include 16 selected pages: 12 for testing and four for development.

Page numbers below are positions in each PDF. A printed page label may be different. The URLs link to the original reports.

| ID | Report | PDF pages | Test pages | Development pages | What I saw |
|---|---|---:|---|---|---|
| S1 | [School Enrollment in the United States: 1970, P20-215](https://www.census.gov/content/dam/Census/library/publications/1970/demo/p20-215.pdf) | 2 | 1, 2 | None | Clear scans, two columns, ruled tables, and small numbers. The report is about 1970 but was issued in 1971. |
| S2 | [Mobility of the Population of the United States: March 1960 to March 1961, P20-118](https://www.census.gov/content/dam/Census/library/publications/1962/demo/p20-118.pdf) | 11 | 1, 4, 5 | 2 | Uneven print, small text, and a mix of paragraphs and ruled tables. |
| S3 | [Mortality Statistics: 1911, Bulletin 112](https://www2.census.gov/library/publications/decennial/1910/bulletins/demographics/112-mortality-statistics.pdf) | 140 | 5, 8, 10, 12 | 6, 11 | Speckled pages, variable print, two columns, and dense tables. The report covers 1911 and was published in 1913. |
| S4 | [Estimates of Population of the United States, 1910–1916, Bulletin 133](https://www2.census.gov/library/publications/decennial/1910/bulletins/demographics/133-estimates-of-population-of-us-1910-1916.pdf) | 42 | 4, 10, 11 | 6 | Light or uneven print, speckles, and full-page tables with several header levels. |

These are 12 pages from four reports, not 12 separate reports. I chose the pages before comparing the OCR tools. I did not create balanced “good,” “medium,” and “poor” groups. Page layout and print quality often change together, so this test cannot show which one caused an OCR error.

## What I checked

- I checked that each download was a PDF and saved its file size and SHA-256 hash, a digital fingerprint, in the [source manifest](../data/manifest.json).
- I looked at the selected pages and development-page previews. I also checked some pages at higher resolution.
- The selected pages in S1 and S2 have no useful text layer. Pages in S3 and S4 contain older OCR text. I measured that text separately; I did not use it as the answer key.
- Every OCR tool read the same rendered page image. I added no blur or other artificial image changes.
- The data is historical public statistics. I did not use patient records or extract names and signatures as targets.

Codex helped transcribe the answers, and the same annotator checked them a second time. No independent person checked the answers. This limits what the scores can prove.

## Source use

I keep the full PDFs local and out of Git. The project records links, file hashes, page choices, answer references, and results instead of copying the full reports into the repository.

The Census Bureau's [public access policy](https://www2.census.gov/foia/ds_policies/ds027.pdf) says that work made by Bureau employees is generally not under U.S. copyright, but it also lists exceptions and rules for other countries. I have not treated that general policy as a reuse license for each report. Before public release, I still need to check the terms for the reports, software, and model files.

The [annotation notes](../data/annotations/README.md) explain the answer references and how I scored text and values. The [case study](CASE_STUDY.md) explains the test and its results.
