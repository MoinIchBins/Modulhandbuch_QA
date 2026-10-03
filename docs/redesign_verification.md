# Redesign verification — 3 October 2026

The new pipeline was exercised in temporary output directories. Existing experiment outputs were not overwritten.

## Full experiment regression

All configured settings were compared by representation, selector and parameters. Every prediction row (including scores), per-question evaluation and aggregate summary matched the saved experiment. File names, manifests and report layouts intentionally use the new interface.

- base development/coarse: 157 settings, all predictions, evaluation details and summaries exactly equal to saved run
- base development/fine: 4227 settings, all predictions, evaluation details and summaries exactly equal to saved run
- base validation: 5 settings, all predictions, evaluation details and summaries exactly equal to saved run
- base test: 1 settings, all predictions, evaluation details and summaries exactly equal to saved run
- manual_review_v1 development/coarse: 157 settings, all predictions, evaluation details and summaries exactly equal to saved run
- manual_review_v1 development/fine: 2129 settings, all predictions, evaluation details and summaries exactly equal to saved run
- manual_review_v1 validation: 12 settings, all predictions, evaluation details and summaries exactly equal to saved run
- manual_review_v1 test: 1 settings, all predictions, evaluation details and summaries exactly equal to saved run

The revised historical fine grid covers the full configured ranges. The current pre-redesign runner uses local intervals and did not regenerate that historical grid. The new `fine_search_mode` makes this protocol distinction explicit: `base=local`, `manual_review_v1=full_range`. The final planner was checked directly against both historical manifests. The first local-grid revised trial was discarded from the regression comparison; its temporary results were never installed.

## Baselines

- base validation: baseline outputs exactly match the pre-redesign runner on the same inputs/runtime
- base test: baseline outputs exactly match the pre-redesign runner on the same inputs/runtime
- manual_review_v1 validation: baseline outputs exactly match the pre-redesign runner on the same inputs/runtime
- manual_review_v1 test: baseline outputs exactly match the pre-redesign runner on the same inputs/runtime

Baseline checks covered every seeded random-run summary, aggregate/sample deviation, deterministic prediction, and deterministic evaluation. Some older saved baseline values differ from the current evaluator at the last floating-point bit (for example a micro-F1 difference of about 1e-18). The redesign preserves the current evaluator arithmetic and matches the pre-redesign runner exactly on the same runtime.

## Focused tests and command checks

- 17 focused tests passed: complete pipeline, split leakage and labels, matrix alignment/non-finite scores, duplicate IDs/parameters, distance direction, changed-input rejection, winner tampering, stage order, empty review groups, missing predictions versus abstention, complete-row/tie behavior, local interval edges, fine-bound validation, test confirmation, baseline-reference protection, and manual-review saving/cleanup.
- Command checks passed for preflight, complete execution with baselines and reports, report regeneration, manual-review prefiltering, gold/matrix/threshold diagnostics, and TF-IDF representation preparation.
- Repeating a completed experiment correctly failed rather than overwriting it.
- Manual-review interaction used simulated input and mocked browser/server operations, including startup interruption. A live browser review was not conducted.
- Neural embedding models were not downloaded or recomputed. The experiment regressions used the saved matrices. The separate preparation command was executed with TF-IDF.
- Source syntax and installed entry-point/preflight checks were included in installation verification.

The minimal experiment requirements record the package versions used. No claim is made that different model weights, numerical libraries, hardware, or data files reproduce bitwise-identical results. Run manifests identify the exact cached inputs and source/environment used.
