# Project One release

This release package contains a local Windows prototype, a guided comparison on real scanned Census reports, and a case study. It is a portfolio experiment, not a production document-processing system.

Start with the [README](../README.md). The [case study](CASE_STUDY.md) explains the problem, method, results, and limits. The [current results](../results/final/comparison.csv) support choosing RapidOCR for this small table-focused demo. Every extracted value still requires human review.

The original project code and documentation use the [MIT license](../LICENSE). See the [third-party notices](../THIRD_PARTY_NOTICES.md) for source, package, model, and font distinctions. Full PDFs, downloaded weights, runtime binaries, local databases, and execution logs are excluded from the release.

The supplied references have not been independently adjudicated. The comparison is exploratory and does not estimate performance on unseen reports. No staff-time savings or automatic-approval safety was measured.

The historical benchmark files preserve the environment and paths used during execution. Those paths describe the original local run; they are not required locations for a new checkout. Follow the README to create a new freeze and output folder when running a fresh comparison.
