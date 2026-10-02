# QA Retrieval Codebase Guide

This is the recommended entry point for understanding and operating the repository.

The repository implements an **offline evidence-retrieval experiment for question answering over a German examination regulation**. It does **not** implement end-to-end answer generation. Its core task is to predict which document chunk or chunks provide the evidence required for a question, including the option to return no chunk for questions that are not answerable from the corpus.

The experimental workflow compares:

- **representations:** TF-IDF, Sentence-BERT, and E5-style retrieval embeddings;
- **selection strategies:** `top_k`, `threshold`, `top_k_threshold`, and `relative_margin`;
- **development configurations:** parameter sweeps over representations and selectors;
- **validation finalists:** a frozen set selected after development;
- **one frozen final system:** evaluated once on the held-out test split;
- **baselines and error analyses:** used to contextualize and interpret retrieval quality.

The main numerical pipeline is:

```text
questions + chunks + gold mappings
        │
        ▼
    embeddings
        │
        ▼
 similarity matrices
        │
        ▼
 selector experiments
        │
        ▼
 development analysis
        │
        ▼
 frozen validation finalists
        │
        ▼
 validation
        │
        ▼
 frozen final configuration
        │
        ▼
 held-out test evaluation
```

---



## 1. Project scope and mental model

The central unit of prediction is a mapping:

```text
question_id -> selected chunk_id(s)
```

The gold data stores the evidence chunks required for each question. A question can require one chunk, multiple chunks, or no chunk at all. The retrieval system therefore has to solve two related problems:

1. rank semantically or lexically relevant chunks;
2. decide whether a chunk should be returned at all.

This second point is why the project contains threshold- and margin-based selectors in addition to ordinary top-k retrieval.

The repository should be understood as an **experimental research codebase with fixed local paths and preserved experiment history**, not as a reusable retrieval library or production service.

---



## 2. Dataset and annotation provenance

The processed dataset was created specifically for this project.

The methodological provenance is:


| Stage                    | Provenance               |
| ------------------------ | ------------------------ |
| Document chunking        | Manual                   |
| Question creation        | Language-model supported |
| Gold evidence assignment | Language-model supported |
| Quality control          | Manual                   |


The resulting experiment works with **720 questions** and **201 chunks**.

The project uses a **development / validation / test** protocol. Development data is used for selector/configuration exploration; validation is used to compare a frozen finalist set; test is reserved for the final frozen configuration.

Questions sharing the same **non-empty required gold-chunk set** are kept together during splitting. This reduces leakage caused by placing closely related questions with identical evidence targets into different experimental splits.

Canonical split artifacts are stored under:

```text
data/frozen/split/
```

with:

```text
development_question_ids.json
validation_question_ids.json
test_question_ids.json
gold_with_split.jsonl
split_groups.json
```

A second split directory also exists under `data/split/`, but the active later-stage experiment scripts use the frozen artifacts. Do not regenerate or replace the frozen split unless the experimental protocol is intentionally being changed.

---



## 3. Repository layout

A useful condensed view of the repository is:

```text
.
├── README.md
├── requirements.txt
├── python_version.txt
├── data/
│   ├── raw/                         # source documents
│   ├── processed/                   # prepared questions and chunks
│   ├── split/                       # retained preparation-era split copy
│   └── frozen/                      # exact reported inputs and splits
├── artifacts/
│   ├── embeddings/
│   ├── similarity_matrices/
│   ├── similarity_analysis/
│   ├── experiments/
│   │   ├── development/             # dev_* rounds and threshold_analysis
│   │   ├── validation/              # validation_finalists
│   │   ├── test/                    # test_winner
│   │   └── single_gold_only_evaluations/ # shared validation/test diagnostics
│   └── baselines/                   # definitions, frozen reference, outputs
├── results/                         # compact reported summaries
├── scripts/
│   ├── baselines/                   # baseline programs
│   └── visualization/               # auxiliary plotting programs
├── tools/
│   └── chunk_browser/               # app, README, local chunks.jsonl
├── literature/
└── metadata/                        # includes report/paper
```



### `data/raw/`

Original or source-level project material, including the regulation PDF and supporting documents.

This directory is upstream of the retrieval experiment and should not normally be touched when rerunning the numerical pipeline.

### `data/processed/`

Prepared project data.

Important files include:

```text
data/processed/PO_25_CL_chunks.jsonl
data/processed/qSet_PO.jsonl
```

The prepared `qamappings/` directory is absent in this checkout. The surviving experiment gold is `data/frozen/qa_mapping_merged.jsonl`; no missing annotation files were reconstructed.

### `data/frozen/`

The canonical frozen experiment inputs used by later-stage runs:

```text
PO_25_CL_chunks.jsonl
qSet_PO.jsonl
qa_mapping_merged.jsonl
split/
```

Treat this directory as the stable experimental snapshot.

### `artifacts/embeddings/`

Precomputed vector representations for:

```text
tf_idf/
sentence_bert/
retrieval_bi_encoder/
```

`retrieval_bi_encoder` is the directory/backend name used for the **E5-style representation**. In experiment filenames and discussion, the same representation is referred to simply as **E5**.

Each representation directory contains question and chunk embeddings plus aligned ID files. TF-IDF additionally stores its fitted vectorizer.

### `artifacts/similarity_matrices/`

Precomputed question-by-chunk score matrices for each representation.

For each representation the project stores:

```text
cosine_similarity_matrix.npy
dot_similarity_matrix.npy
euclidean_similarity_matrix.npy
question_ids.json
chunk_ids.json
metadata.json
```

Most later retrieval experiments use **cosine similarity**.

### `artifacts/similarity_analysis/`

Diagnostics on the raw similarity spaces before selector tuning.

This contains per-question/per-chunk analyses and plots for rank behavior, MRR, recall/hit/all-gold-at-k, score separation, gold-rank distributions, and frequent top-ranked chunks.

### `artifacts/experiments/`

The main experiment-history directory.

It contains:

- multiple versioned development sweeps;
- consolidated development rankings;
- threshold-region diagnostics;
- validation finalists;
- the final test winner;
- single-gold evaluation slices;
- validation and test error-analysis artifacts.

This directory is intentionally historical. A single current runner configuration does **not** regenerate every versioned directory that is preserved here.

### `artifacts/baselines/`

Baseline definitions, the frozen development reference, and validation/test baseline outputs.

The preserved baselines include:

- always abstain;
- most-frequent development answer;
- random top-1.

The executable baseline, comparison, and plotting programs live in `scripts/baselines/`. See [baseline instructions](artifacts/baselines/README.md).

### `scripts/visualization/`

Auxiliary visualization programs. The canonical sweep analyzer is `scripts/analyze_selector_experiments.py`; it retains metric validation and optional plot suppression from the former auxiliary copy.

Run the auxiliary programs from the repository root:

```bash
python scripts/visualization/visualize_validation_results.py
python scripts/visualization/visualize_evaluation_optional.py
```

These write plots beside the configured preserved evaluations, so redirect their output constants before generating new plots.

The chunk browser lives at:

```text
tools/chunk_browser/
```



### `scripts/`

The active Python code for embeddings, similarity computation, selector logic, evaluation, experiment running, diagnostics, and error analysis.

### `results/`

A compact results handoff layer:

```text
baseline_summary.jsonl
dev_ranking.csv
validation_summary.jsonl
winner_summary.jsonl
```

Use this directory when you need a concise view of the authoritative experiment outputs rather than the full historical artifact tree.

### `literature/`

Literature PDFs, structured reading notes, citation material, and the audited project handover.

This is documentation/research support rather than executable pipeline code.

### `metadata/`

Project decisions, limitations, prompts, method notes, and the paper workspace.

The current ACL paper files are under:

```text
metadata/report/paper/
```

This directory is separate from the retrieval runtime pipeline.

---




### Snapshot provenance and limitations

The prepared question/chunk files and all five files under `data/split/` were byte-identical to their frozen counterparts when this layout was changed. Both copies remain intact. Embedding generation now reads frozen questions/chunks; the integrity and similarity-analysis scripts read frozen gold, consistent with the experiment runners. The missing prepared gold cannot be compared with frozen gold, so its historical equivalence is not asserted.

`scripts/data_splitter.py` is an earlier preparation utility: it still references the absent prepared gold and writes to `data/trash/`. It is not part of reported-run reproduction and was not repointed to or used to regenerate frozen splits.

Historical output files retain embedded source paths exactly as recorded. Resolve those provenance strings using this relocation table; they are not active script paths:

| Historical prefix | Current location |
| --- | --- |
| `data/produced_v2/frozen/` | `data/frozen/` |
| `data/produced_v2/embeddings/` | `artifacts/embeddings/` |
| `data/produced_v2/similarity_matrices/` | `artifacts/similarity_matrices/` |
| `data/produced_v2/similarity_analysis/` | `artifacts/similarity_analysis/` |
| `data/produced_v2/selector_experiments/dev_*/` | `artifacts/experiments/development/dev_*/` |
| `data/produced_v2/selector_experiments/threshold_analysis/` | `artifacts/experiments/development/threshold_analysis/` |
| `data/produced_v2/selector_experiments/validation_finalists/` | `artifacts/experiments/validation/validation_finalists/` |
| `data/produced_v2/selector_experiments/test_winner/` | `artifacts/experiments/test/test_winner/` |
| `data/produced_v2/selector_experiments/single_gold_only_evaluations/` | `artifacts/experiments/single_gold_only_evaluations/` |
| `data/produced_v2/baselines/` | `artifacts/baselines/` (programs: `scripts/baselines/`) |

Mixed validation/test single-gold diagnostics remain together to preserve the historical directory. Actual run names such as `dev_threshold_v1` are unchanged. `results/` remains an unchanged compact handoff, not an automatic export destination for every runner.

## 4. Core implementation modules

Four modules contain most of the reusable experiment logic.

### `scripts/text_embedder.py`

Abstraction over the three representation families:

```text
TF_IDF
SENTENCE_BERT
RETRIEVAL_BI_ENCODER
```

For the retrieval bi-encoder / E5 representation, the implementation uses the expected retrieval-style prefixes:

```text
query:   <question>
passage: <chunk>
```

Used by:

```text
scripts/compute_embeddings.py
```



### `scripts/similarity_calculator.py`

Computes pairwise question/chunk similarity or distance matrices.

Implemented methods:

```text
cosine
dot
euclidean
```

Used by:

```text
scripts/compute_similarity_matrices.py
```



### `scripts/chunk_selector.py`

Converts a row of similarity scores into predicted chunk IDs.

Implemented selector families:

```text
top_k
threshold
top_k_threshold
relative_margin
```

Conceptually:

- `top_k`: always choose the highest-ranked k chunks;
- `threshold`: return chunks whose score exceeds a threshold;
- `top_k_threshold`: apply both a score threshold and a maximum k;
- `relative_margin`: decide using the score difference/margin around the best candidates.

Used by development, validation, and final-test runners.

### `scripts/mapping_evaluator.py`

The common scoring authority for predicted question-to-chunk mappings.

It compares predicted `chunk_ids` against gold `all_required_chunk_ids` and emits aggregate plus per-question metrics.

Important metrics include:

```text
mean_question_precision
mean_question_recall
mean_question_f1
exact_match_rate
micro_f1
zero_gold_abstention_rate
empty_selection_rate
average_selected_chunks
```

Because downstream scripts expect these fields, changes to evaluator output names can break analysis code.

---



## 5. Main executable scripts


| Script                                     | Role                                                    | Typical use                            |
| ------------------------------------------ | ------------------------------------------------------- | -------------------------------------- |
| `compute_embeddings.py`                    | Generate TF-IDF, Sentence-BERT, and E5-style embeddings | Run when embeddings need to be rebuilt |
| `compute_similarity_matrices.py`           | Convert embeddings into cosine/dot/euclidean matrices   | Run after embeddings                   |
| `embeddings_similarity_integrity_check.py` | Check shapes, IDs, mappings, and cosine spot checks     | Sanity check before experiments        |
| `analyze_similarity_matrices.py`           | Diagnose raw retrieval/ranking behavior                 | Representation analysis                |
| `analyze_threshold_regions.py`             | Suggest plausible threshold ranges from dev scores      | Threshold exploration                  |
| `run_selector_experiments.py`              | Execute configurable selector sweeps on development     | Parameter exploration                  |
| `analyze_selector_experiments.py`          | Analyze one selector sweep family                       | Local experiment comparison            |
| `dev_summary_script.py`                    | Consolidate selected dev experiment directories         | Global development ranking             |
| `run_validation_finalists.py`              | Evaluate the frozen finalist set on validation          | Model/config selection stage           |
| `evaluate_single_gold_only.py`             | Re-evaluate a result on one-gold questions only         | Diagnostic slice                       |
| `prefilter_errors.py`                      | Group obvious retrieval-error types                     | Error-analysis preparation             |
| `manual_error_review_all_groups.py`        | Human review of grouped errors                          | Manual qualitative audit               |
| `run_test_winner.py`                       | Run the one frozen final system on test                 | Final held-out evaluation              |
| `check_empty_jsonl_in_predictions.py`      | Narrow debugging utility for test predictions           | One-off debugging                      |
| `analyze_gold.py`                          | Inspect gold mapping files                              | Data diagnostics                       |
| `data_splitter.py`                         | Split/preparation utility                               | Not part of normal frozen reruns       |


---



## 6. End-to-end operating procedure

Most scripts use fixed repository-relative paths and hard-coded configuration constants. Run them from the **repository root**.

**Preservation first:** the commands below describe the workflow, not a safe batch rerun into the checked-in history. Before executing any generation, analysis, or review command, set its output constants to a new, empty directory and point downstream inputs at that new output. Keep model, selector, seed, split, and metric settings unchanged. Several scripts overwrite files by default; baseline runners instead refuse existing run directories. Do not delete preserved directories to bypass that protection. The read-only integrity check in section 6.5 can run directly against stored artifacts.

`tree.txt` is a tracked layout snapshot, refreshed for this reorganization. Regenerate it from the root with `tree -I '__pycache__' > tree.txt` (hidden files and the local environment are omitted by default).

### 6.1 Environment setup

Create/activate the intended Python environment and install the project dependencies:

```bash
python --version
pip install -r requirements.txt
```

The intended Python version is recorded in:

```text
python_version.txt
```

Before reproducing an old experiment, check that model/library versions still match the environment in which the stored artifacts were created.

### 6.2 Confirm the frozen data snapshot

Before recomputing anything, verify the presence of:

```text
data/frozen/PO_25_CL_chunks.jsonl
data/frozen/qSet_PO.jsonl
data/frozen/qa_mapping_merged.jsonl
data/frozen/split/development_question_ids.json
data/frozen/split/validation_question_ids.json
data/frozen/split/test_question_ids.json
```

For ordinary experiment reproduction, these should be treated as immutable.

### 6.3 Generate embeddings

```bash
python scripts/compute_embeddings.py
```

Expected outputs are written below:

```text
artifacts/embeddings/
```

with one directory per representation.

### 6.4 Generate similarity matrices

```bash
python scripts/compute_similarity_matrices.py
```

Expected outputs are written below:

```text
artifacts/similarity_matrices/
```



### 6.5 Run integrity checks

Before tuning selectors:

```bash
python scripts/embeddings_similarity_integrity_check.py
```

This is the fastest way to detect ID-order mismatches, unexpected array shapes, missing gold IDs, or matrix inconsistencies.

For deeper diagnostics:

```bash
python scripts/analyze_similarity_matrices.py
```

and, when exploring abstention thresholds:

```bash
python scripts/analyze_threshold_regions.py
```



### 6.6 Run development selector experiments

The development runner is:

```bash
python scripts/run_selector_experiments.py
```

Important: **inspect its constants before running it**.

The repository preserves many development experiment rounds, for example:

```text
dev_top_k_v1/
dev_threshold_v1/
dev_threshold_v2/
dev_top_k_threshold_v1/
...
dev_top_k_threshold_v6/
dev_relative_margin_v1/
dev_relative_margin_v2/
```

These directories reflect multiple historical configurations and refinement rounds.

The current `run_selector_experiments.py` configuration should therefore be interpreted as **the sweep the script is configured to run now**, not as a complete executable reconstruction of all preserved development experiments.

A typical development run writes:

```text
*_predictions.jsonl
*_evaluation.json
summary.jsonl
```

into the configured experiment directory.

### 6.7 Analyze development results

For a sweep-specific analysis:

```bash
python scripts/analyze_selector_experiments.py
```

Check its configured:

```text
RESULTS_DIR
METHOD
X_PARAMETER
TABLE_METRICS
PLOT_METRICS
```

before use.

For the consolidated development comparison:

```bash
python scripts/dev_summary_script.py
```

This script reads selected versioned development directories and produces combined rankings/plots. The repository already contains consolidated artifacts under:

```text
artifacts/experiments/development/dev_consolidated/
```

including:

```text
best_configs.csv
overall_ranking.csv
selector_winners.csv
dev_f1_overview.png
dev_full_ranking.png
dev_winners.png
```

The compact exported ranking is also available at:

```text
results/dev_ranking.csv
```



### 6.8 Freeze and evaluate validation finalists

The validation stage is intentionally narrower than development.

The finalist configurations are hard-coded in:

```text
scripts/run_validation_finalists.py
```

Before running, inspect the `FINALISTS` list. Then execute:

```bash
python scripts/run_validation_finalists.py
```

Outputs are written under:

```text
artifacts/experiments/validation/validation_finalists/
```

The preserved finalist directory contains E5 and TF-IDF configurations, including the configuration that became the final winner.

It also contains:

```text
validation_ranking.csv
validation_ranking.png
summary.jsonl
```

A compact validation result handoff is stored in:

```text
results/validation_summary.jsonl
```



### 6.9 Perform validation error analysis

The automatic prefilter is:

```bash
python scripts/prefilter_errors.py
```

For the selected validation result it groups errors such as:

```text
multi-gold / single prediction
answerable but abstained
zero-gold but retrieved
manual-review remainder
```

The validation error artifacts are stored under:

```text
artifacts/experiments/validation/validation_finalists/error_analysis_of_best/
```

For manual inspection:

```bash
python scripts/manual_error_review_all_groups.py
```

This workflow uses the local browser under:

```text
tools/chunk_browser/
```

The manually reviewed combined CSV is:

```text
manual_review_all_error_groups.csv
```

The completed validation audit contains **58 non-exact cases**.

### 6.10 Freeze the final system

After validation, the final configuration must be fixed before looking at test performance.

The frozen final configuration is:

```text
representation = E5
selector       = top_k_threshold
top_k          = 1
threshold      = 0.83959
```

In the embedding/similarity directories, E5 corresponds to:

```text
retrieval_bi_encoder
```

Do not retune the threshold or selector after observing test results if the goal is to preserve the reported held-out evaluation.

### 6.11 Run the final test evaluation

The final-test runner is:

```bash
python scripts/run_test_winner.py
```

It writes to:

```text
artifacts/experiments/test/test_winner/
```

The principal files are:

```text
e5_top_k_threshold_top_k_1_threshold_0.83959_predictions.jsonl
e5_top_k_threshold_top_k_1_threshold_0.83959_evaluation.json
summary.jsonl
```

Test error-analysis artifacts are also preserved under:

```text
artifacts/experiments/test/test_winner/error_analysis/
```

The completed test audit contains **74 non-exact cases**.

### 6.12 Run or inspect baselines

Baseline utilities live under:

```text
scripts/baselines/
```

The directory contains:

```text
run_baselines.py
freeze_dev_reference.py
compare_with_system.py
plot_baselines.py
```

Definitions remain in `artifacts/baselines/baseline_definitions.json`. Validation and test outputs are already preserved under:

```text
artifacts/baselines/validation_v1/
artifacts/baselines/test_v1/
```

When rerunning them from the repository root, the expected entry point is:

```bash
python scripts/baselines/run_baselines.py validation
```

Check `artifacts/baselines/README.md` and the hard-coded paths/constants before changing or reproducing baseline runs.

The compact baseline result summary is available at:

```text
results/baseline_summary.jsonl
```

---



## 7. Current authoritative experiment endpoint

The final reported system is the E5 `top_k_threshold` configuration with:

```text
top_k = 1
threshold = 0.83959
```

Official question-level F1:

```text
validation F1 = 0.6111
test F1       = 0.4907
difference    = -0.1204
```

These are the official experimental results.

Manual error review is used to **interpret** these scores; it must not be used to replace them with retrospectively "corrected" evaluation scores.

The compact final result export is:

```text
results/winner_summary.jsonl
```

---



## 8. Generated artifact flow



### Embeddings

```text
scripts/compute_embeddings.py
    │
    └──> artifacts/embeddings/
          ├── tf_idf/
          ├── sentence_bert/
          └── retrieval_bi_encoder/
```



### Similarities

```text
scripts/compute_similarity_matrices.py
    │
    └──> artifacts/similarity_matrices/
```



### Development

```text
similarity matrices
    │
    ▼
scripts/run_selector_experiments.py
    │
    ▼
artifacts/experiments/development/dev_*/
    │
    ├──> scripts/analyze_selector_experiments.py
    └──> scripts/dev_summary_script.py
              │
              ▼
       dev_consolidated/
```



### Validation

```text
frozen development finalists
    │
    ▼
scripts/run_validation_finalists.py
    │
    ▼
validation_finalists/
    │
    ├──> ranking/summary
    ├──> scripts/evaluate_single_gold_only.py
    └──> scripts/prefilter_errors.py
              │
              ▼
       scripts/manual_error_review_all_groups.py
```



### Test

```text
frozen validation winner
    │
    ▼
scripts/run_test_winner.py
    │
    ▼
test_winner/
    ├── predictions
    ├── evaluation
    ├── summary
    └── error_analysis/
```

---



## 9. Development experiment history versus current script state

This distinction is important when working with the repository.

The directory tree contains many historical development rounds with increasingly refined search regions. For example, several versions of threshold and top-k+threshold sweeps are preserved.

By contrast, `scripts/run_selector_experiments.py` contains one **current set of constants** defining what it would run today.

Therefore:

```text
preserved experiment directory != automatically reproducible from current constants
```

To reproduce a particular historical sweep exactly, recover its parameter grid from its outputs, comparison files, metadata, project notes, or version history before changing the runner.

Do not infer that missing current constants mean those historical experiments did not occur.

---



## 10. Selector configuration guide



### Change a representation

Core implementation:

```text
scripts/text_embedder.py
```

Pipeline registration and downstream hard-coded representation lists may also need changes in:

```text
scripts/compute_embeddings.py
scripts/compute_similarity_matrices.py
scripts/run_selector_experiments.py
scripts/run_validation_finalists.py
scripts/analyze_threshold_regions.py
scripts/analyze_similarity_matrices.py
scripts/embeddings_similarity_integrity_check.py
```



### Change or add a selector

Implement selector behavior in:

```text
scripts/chunk_selector.py
```

Then add the configuration to the relevant runner:

```text
scripts/run_selector_experiments.py
scripts/run_validation_finalists.py
scripts/run_test_winner.py
```



### Change a development sweep

Inspect/edit the constants in:

```text
scripts/run_selector_experiments.py
```

Typical configuration items include output directory, selector family, `top_k`, threshold grids, and margin ranges.

Always write a new versioned experiment directory rather than silently overwriting an earlier reported run.

### Change evaluation metrics

Edit:

```text
scripts/mapping_evaluator.py
```

Be aware that many analysis scripts expect the existing field names.

---



## 11. Diagnostics: where to look when something is wrong



### Embeddings or matrices look suspicious

Start with:

```bash
python scripts/embeddings_similarity_integrity_check.py
```

Then inspect:

```bash
python scripts/analyze_similarity_matrices.py
```



### Threshold behavior looks strange

Use:

```bash
python scripts/analyze_threshold_regions.py
```

and inspect:

```text
artifacts/experiments/development/threshold_analysis/
```



### Development ranking looks inconsistent

Inspect:

```text
artifacts/experiments/development/dev_consolidated/
results/dev_ranking.csv
```

and verify which historical experiment directories `dev_summary_script.py` is configured to consume.

### Validation performance needs qualitative explanation

Inspect:

```text
artifacts/experiments/validation/validation_finalists/error_analysis_of_best/
```

and use the manual-review script/browser.

### Test performance needs qualitative explanation

Inspect:

```text
artifacts/experiments/test/test_winner/error_analysis/
```

The test error audit is post-hoc analysis only; it must not feed back into threshold selection for the reported experiment.

---



## 12. Files that are not normal pipeline stages

Several scripts are useful but should not be mistaken for required steps in every reproduction.

### `data_splitter.py`

The repository already contains canonical frozen split artifacts. The split script is therefore a preparation/legacy utility, not something that should be rerun casually.

### `check_empty_jsonl_in_predictions.py`

A narrow debugging script for final-test prediction IDs. It is not part of the core evaluation procedure.

### `evaluate_single_gold_only.py`

A diagnostic evaluation slice. It supplements rather than replaces the main evaluator result.

### Manual error review

The review CSVs explain failure modes. They are not alternative gold labels for recomputing the official headline score.

---



## 13. Research and paper support files

The executable retrieval pipeline and the paper-support material intentionally live side by side.

Useful research documentation includes:

```text
literature/Hausarbeit_QA_Model_Agent_Handover_V2_Audited.md
literature/literature_matrix.csv
literature/notes/
metadata/decisions.md
metadata/limitations.md
metadata/report/retrieval_model_comparison_report.md
metadata/report/threshold_region_method.md
metadata/report/top_k_threshold_method.md
```

The ACL paper workspace is:

```text
metadata/report/paper/
```

These files describe, interpret, or report the experiments. They should not be confused with code that generates the primary retrieval predictions.

---



## 14. Recommended reading order for a new contributor

If you are new to the repository, read the code in this order:

```text
1. scripts/chunk_selector.py
2. scripts/mapping_evaluator.py
3. scripts/run_selector_experiments.py
4. scripts/text_embedder.py
5. scripts/compute_embeddings.py
6. scripts/similarity_calculator.py
7. scripts/compute_similarity_matrices.py
8. scripts/run_validation_finalists.py
9. scripts/run_test_winner.py
10. scripts/analyze_similarity_matrices.py
```

Then inspect:

```text
results/
artifacts/experiments/development/dev_consolidated/
artifacts/experiments/validation/validation_finalists/
artifacts/experiments/test/test_winner/
```

This gives the shortest path from implementation to the reported experiment.

---



## 15. Rules for preserving experimental validity

When extending or reproducing the project, follow these rules:

1. Treat the frozen dataset and split as immutable for reproduction.
2. Use development for parameter exploration.
3. Select/freeze a small finalist set before validation.
4. Use validation to choose the final configuration.
5. Freeze that configuration before test.
6. Do not tune on test results.
7. Keep new experiment outputs in new versioned directories.
8. Preserve old prediction/evaluation files instead of overwriting them.
9. Keep manual error analysis separate from headline metric computation.
10. Record any changed representation, selector, threshold, split, or evaluator behavior in project metadata.

---



## 16. Minimal reproduction checklist

For a clean numerical rerun using the existing frozen data:

```bash
pip install -r requirements.txt

python scripts/compute_embeddings.py
python scripts/compute_similarity_matrices.py
python scripts/embeddings_similarity_integrity_check.py

# Development: inspect/configure runner before executing.
python scripts/run_selector_experiments.py
python scripts/dev_summary_script.py

# Validation: inspect frozen FINALISTS before executing.
python scripts/run_validation_finalists.py

# Final test: only after the winner is frozen.
python scripts/run_test_winner.py
```

For result interpretation, additionally inspect or run:

```bash
python scripts/analyze_similarity_matrices.py
python scripts/analyze_threshold_regions.py
python scripts/prefilter_errors.py
python scripts/manual_error_review_all_groups.py
```

Do not assume the minimal command sequence reconstructs every historical development sweep. The repository preserves experiment history that was produced over multiple rounds and parameter-grid refinements.

---



## 17. One-sentence summary

**This repository evaluates how well TF-IDF, Sentence-BERT, and E5-style representations combined with different chunk-selection/abstention rules can recover gold evidence chunks for QA, using a leakage-aware development/validation/test workflow with preserved experiment artifacts, baselines, diagnostics, and manual error audits.**