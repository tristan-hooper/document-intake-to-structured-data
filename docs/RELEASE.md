# Project One release

This release package contains a local Windows prototype, a guided comparison on real scanned Census reports, and a case study. It is a portfolio experiment, not a production document-processing system.

Start with the [README](../README.md). The [case study](CASE_STUDY.md) explains the problem, method, results, and limits. The [current results](../results/final/comparison.csv) support choosing RapidOCR for this small table-focused demo. Every extracted value still requires human review.

The original project code and documentation use the [MIT license](../LICENSE). See the [third-party notices](../THIRD_PARTY_NOTICES.md) for source, package, model, and font distinctions. Full PDFs, downloaded weights, runtime binaries, local databases, and execution logs are excluded from the release.

The supplied references have not been independently adjudicated. The comparison is exploratory and does not estimate performance on unseen reports. No staff-time savings or automatic-approval safety was measured.

The historical benchmark files preserve the environment and paths used during execution. Those paths describe the original local run; they are not required locations for a new checkout. Follow the README to create a new freeze and output folder when running a fresh comparison.

## Verification

On October 6, 2026, a clean Windows Git checkout and new Python 3.12 environment downloaded the four pinned PDFs and three RapidOCR models, completed all four development pages, exported 16 candidates and 16 review rows, and passed 36 tests. All values remained review-required. Package installation used an existing local cache. This verifies the selected demo; it does not verify the full A/B/C benchmark on a clean machine.

Git preserves file bytes through `.gitattributes`, and all 24 saved benchmark artifact hashes survived checkout. The source downloader sends a browser-style user-agent because the Census host rejected Python's default request. Every downloaded PDF must still match its recorded size and hash. The used benchmark freeze stays unchanged; a future comparison must make its own freeze.

The detailed [release preparation record](../results/verification/release-preparation-20261006.json) gives the checked scope and the access status at that earlier checkpoint. The source is now [published on GitHub](https://github.com/tristan-hooper/document-intake-to-structured-data). Original preparation and benchmark records remain unchanged.
