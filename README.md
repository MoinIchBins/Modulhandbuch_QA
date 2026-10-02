# QA Evidence Retrieval Experiments

This project compares TF-IDF, Sentence-BERT, and E5 with four chunk-selection rules for questions about a German examination regulation. It retrieves evidence chunks and can abstain; it does not generate answers.

## Base experiment

The canonical experiment is `artifacts/experiments/base/`. It uses 720 questions, 201 chunks, and the original frozen grouped split (432 development, 144 validation, 144 test). Its validation-selected winner is **E5, top_k_threshold, top_k=1, threshold=0.84**.

| Split | Mean question F1 | Exact matches |
| --- | ---: | ---: |
| Development | 0.647377 | 275/432 |
| Validation | 0.604167 | 85/144 |
| Test | 0.483796 | 69/144 |

The completed rerun is now the base experiment. The historical first run is archived. The researcher reviewed the differences and judged them immaterial to the research questions; the reported numbers nevertheless use the actual rerun results. See `artifacts/experiments/base/README.md` for provenance.

## Layout

```text
artifacts/experiments/
  base/
    configs/                 # coarse, fine, development summary, validation
    outputs/
      development/           # coarse_all, fine_all, fine_summary
      validation/finalists/  # five candidates and frozen_winner.json
      test/winner/           # held-out winner and reconciled error analysis
  manual_review_v1/          # separate revised-dataset experiment
  archive/
    first_run/               # historical outputs, documentation, snapshots
    migration_provenance/    # original rerun path metadata
results/                     # compact canonical exports
metadata/report/paper/       # current paper.tex
```

Frozen inputs are in `data/frozen/`; shared embeddings and similarity matrices remain under `artifacts/`. Do not regenerate these inputs for this recreation. `data/split/` is the preparation-era reference. `data/manual_review_v1/` belongs to the separate follow-up. Scripts are under `scripts/`, literature under `literature/`, and the chunk browser under `tools/chunk_browser/`.

## Pipeline

From the repository root, with dependencies from `requirements.txt` installed:

```bash
.venv/bin/python scripts/run_selector_experiments.py --config artifacts/experiments/base/configs/coarse.json
.venv/bin/python scripts/run_selector_experiments.py --config artifacts/experiments/base/configs/fine.json --coarse-run artifacts/experiments/base/outputs/development/coarse_all
.venv/bin/python scripts/dev_summary_script.py --run-set artifacts/experiments/base/configs/dev_summary.json
.venv/bin/python scripts/run_validation_finalists.py --config artifacts/experiments/base/configs/validation.json
.venv/bin/python scripts/run_test_winner.py --validation-dir artifacts/experiments/base/outputs/validation/finalists
```

These commands document the completed run. Its output folders already exist, and runners refuse to overwrite them. For another experiment, copy the configs, choose fresh output directories, and update downstream references together; do not clear the canonical outputs.

The coarse stage evaluates 157 settings. The fine stage automatically brackets each best coarse parameter by its neighboring values, evaluates 201 points per interval, retains the best coarse point, and deduplicates settings (4,227 configurations). At grid edges it extends one neighboring step within the configured bounds. Development ranks the best setting for each of 12 representation/selector pairs and forwards the top five. Ranking uses question F1, exact match, precision, then fewer selected chunks. Validation freezes the winner, and test evaluates only that configuration.

## Results and interpretation

`results/` exports the base development ranking, all five validation results, and test winner. `artifacts/baselines/` preserves unchanged reference baseline predictions; its system comparisons use the base winner. `metadata/report/paper/paper.tex` is the current paper source. Earlier drafts and the old handover belong to the first-run archive.

The base test has 75 non-exact predictions. Its error analysis retains historical human labels for 73 unchanged cases and reclassifies two changed predictions as false abstentions. The reconciliation and provenance are saved with the test winner; it is not represented as a new manual audit.

## Separate follow-up

`manual_review_v1` removes ten reviewed items and uses a different split. Its configs remain under `configs/manual_review_v1_*.json`, with outputs under `artifacts/experiments/manual_review_v1/`. Its metrics must not be mixed with the base experiment.

Use development for search, validation for selection, and test for the frozen winner. Neither the archived test result nor the rerun test result is a reason to retune the selected configuration. Historical launch configs were not retained; the old outputs remain the evidence for that first run.
