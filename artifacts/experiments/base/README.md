# Base experiment

Canonical completed rerun on the original frozen data, grouped split, and saved similarity matrices. Promoted on 2026-10-02 after the researcher reviewed the differences and judged them immaterial to the research questions.

- Coarse development: 157 configurations, each on 432 questions.
- Adaptive fine development: 4,227 configurations, each on 432 questions.
- Development summary: 12 representation/selector winners; five validation candidates.
- Validation: five candidates, each on 144 questions.
- Test: one validation-frozen winner, on 144 questions.
- Winner: E5, top_k_threshold, k=1, threshold=0.84.

Question F1: development 0.6473765432, validation 0.6041666667, test 0.4837962963. Exact matches: 275/432, 85/144, 69/144.

## Provenance

Formerly `artifacts/experiments/original_frozen_new_pipeline/`. Output data and scores were not rerun or altered during promotion. References in configs, manifests, and candidate/winner metadata were relocated; their original versions are preserved under `../archive/migration_provenance/`. Original run_name strings remain as historical launch identifiers.

The first run is at `../archive/first_run/`. Its E5 threshold was 0.83959, with validation/test F1 0.6111111111/0.4907407407. The base threshold 0.84 changes Q0417 on validation and Q0534/Q0547 on test to abstention. The researcher's assessment concerns the conclusions, not numerical equivalence. This rerun reuses previously evaluated data and is not a new independent held-out sample.

The test error reconciliation is in `outputs/test/winner/error_analysis/`. Shared data and similarity matrices and the separate manual_review_v1 experiment were not changed.
