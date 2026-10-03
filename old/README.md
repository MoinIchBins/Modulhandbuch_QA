# Script cleanup — 3 October 2026

The original active scripts are archived in `old/scripts/`. This archive was made before replacing active files. Historical experiment snapshots and saved experiment outputs were not modified.

## Changes

- Fixed the three moved configuration defaults, blank review evidence text, and cleanup after review-server startup failures.
- Split similarity analysis, threshold analysis, review sessions, evaluation, split generation, integrity checks, development summaries, validation export, and random-baseline execution into focused functions.
- Shared matrix loading, prediction construction and prediction JSONL writing across development, validation and test runners.
- Removed duplicate plotting settings and unused configuration examples; consolidated plotting and threshold selection branches.
- Added `check_prediction_ids.py`; the old filename remains a working compatibility entry point.
- Kept metric arithmetic, ranking, stable ties, seeds, split order, output names, overwrite guards and review precedence.

## Deliberately preserved

The assessment's optional changes to `groupby(...).first()` null handling, reported fine-search edge intervals, and the validation plotting CSV filename were not applied: each changes existing output semantics or naming. The unused selector `temperature` argument remains for caller compatibility. Scripts rated clear were left alone except for the small gold-report and embedding-validation changes.

## Verification

Old and new versions were run against the saved project data, with all generated results redirected to temporary folders. Comparison of runner JSON ignored only the differing temporary destination path. All other checked artifacts matched exactly, except the intended filled evidence-text fields.

- All updated Python files parse
- Selectors match across all methods, both directions, ties and threshold boundaries
- Evaluator matches for complete/missing/unknown predictions and empty scopes
- All three complete similarity analyses match exactly (720 questions each)
- Similarity edge cases match: ties, zero-gold only and no second score
- analyze_threshold_regions: generated artifacts byte-identical
- evaluate_single_gold_only: generated artifacts byte-identical
- data_splitter: generated artifacts byte-identical
- Embedding integrity checks pass with identical diagnostics and random spot checks
- run_selector_experiments.py: full saved-data run matches, including predictions and ranking
- run_validation_finalists.py: full saved-data run matches, including predictions and ranking
- Held-out test runner matches with the same frozen winner (temporary outputs only)
- Fine-search experiments and neighboring intervals match
- Optional visualization tables and PNGs byte-identical with/without grouping
- Prefilter retains all categories/IDs and fills previously blank evidence text
- Review import precedence, commands, autosave and quit match; interrupted startup cleans up server
- Prediction-ID checker preserves CLI output and is safe to import
- dev_summary_script.py: all CSV/JSON/PNG outputs byte-identical
- analyze_selector_experiments.py: all CSV/JSON/PNG outputs byte-identical
- Gold analysis report unchanged
- TF-IDF embeddings identical; invalid method gives ValueError
- Baseline predictions, seeded random runs and sample standard deviations unchanged
- Baseline comparison CSV and PNG byte-identical

Manual review was tested with simulated input and mocked browser/server operations; no live browser session was conducted. Neural embeddings were not recomputed or downloaded; the existing embedding matrices passed the reproducible integrity checks. TF-IDF was compared directly. No new experiment results were installed.

## Updated files

- `scripts/analyze_gold.py`
- `scripts/analyze_selector_experiments.py`
- `scripts/analyze_similarity_matrices.py`
- `scripts/analyze_threshold_regions.py`
- `scripts/baselines/compare_with_system.py`
- `scripts/baselines/run_baselines.py`
- `scripts/check_empty_jsonl_in_predictions.py`
- `scripts/check_prediction_ids.py`
- `scripts/chunk_selector.py`
- `scripts/data_splitter.py`
- `scripts/dev_summary_script.py`
- `scripts/embeddings_similarity_integrity_check.py`
- `scripts/evaluate_single_gold_only.py`
- `scripts/experiment_pipeline.py`
- `scripts/manual_error_review_all_groups.py`
- `scripts/mapping_evaluator.py`
- `scripts/prefilter_errors.py`
- `scripts/run_selector_experiments.py`
- `scripts/run_test_winner.py`
- `scripts/run_validation_finalists.py`
- `scripts/text_embedder.py`
- `scripts/visualization/visualize_evaluation_optional.py`
