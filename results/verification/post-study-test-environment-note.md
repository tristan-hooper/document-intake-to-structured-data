# Test environment note

An early test run used the default system temporary folder and stopped with 10 setup errors because pytest could not create its temporary test folders. In that run, 22 tests passed; the 10 test bodies with setup errors did not run.

Running the same 32-test suite with a temporary folder inside the project cache passed all 32 tests. This showed that the initial errors came from the temporary-folder setup, not from those test cases. The raw output is kept in the ignored local `.cache/diagnostics` folder.

A later project audit ran the expanded 35-test suite successfully. That later pass supports the tests that ran; it does not rerun the OCR comparison or change its historical results.
