# QA Evidence Retrieval Experiments

This repository evaluates how well different text representations and chunk-selection rules can recover evidence for questions about a German examination regulation. It predicts relevant `chunk_id` values, including an empty selection when the corpus does not answer a question. It does not generate answers.

The dataset contains 720 questions and 201 manually created document chunks. The experiment compares TF-IDF, Sentence-BERT, and E5-style retrieval embeddings with `top_k`, `threshold`, `top_k_threshold`, and `relative_margin` selectors.

## Reported result

The final system uses the E5 representation (`retrieval_bi_encoder`) with `top_k_threshold`, `top_k = 1`, and `threshold = 0.83959`.


| Split      | Question-level F1 |
| ---------- | ----------------- |
| Validation | 0.6111            |
| Test       | 0.4907            |


Development results informed the validation finalists; validation selected the final configuration; the test split was reserved for its final evaluation. 

## Repository layout

```text
.
├── data/
│   ├── raw/                 # source documents
│   ├── processed/           # prepared questions and chunks
│   ├── split/               # retained preparation-era split files
│   └── frozen/              # exact inputs and splits for reported runs
├── artifacts/
│   ├── embeddings/
│   ├── similarity_matrices/
│   ├── similarity_analysis/
│   ├── experiments/
│   │   ├── development/
│   │   ├── validation/
│   │   ├── test/
│   │   └── single_gold_only_evaluations/
│   └── baselines/
├── results/                 # compact result summaries
├── scripts/                 # pipeline, evaluation, and analysis code
│   ├── baselines/
│   └── visualization/
├── tools/chunk_browser/     # local browser for reviewing chunks
├── literature/              # papers and reading notes
└── metadata/                # decisions, methods, limitations, and paper files
```

`data/frozen/` is the authoritative input snapshot for the reported experiments. The active pipeline uses its questions, chunks, gold mappings, and split files. Treat these as immutable when reproducing results. `data/split/` is retained for reference; do not use it to replace the frozen split.

`artifacts/` contains generated representations, diagnostics, and preserved experiment outputs. Development run names retain their experiment-round identifiers. The current runner settings do not recreate every historical run.

`results/` contains concise handoff files: `baseline_summary.jsonl`, `dev_ranking.csv`, `validation_summary.jsonl`, and `winner_summary.jsonl`.

## Reproduction workflow

Use the repository root as the working directory. The project’s Python version is recorded in `python_version.txt`; dependencies are in `requirements.txt`.

Before generating anything, inspect the configured input and output paths in the relevant script. Several scripts can overwrite files. For new runs, direct outputs to a new, empty directory and preserve the checked-in artifacts.

1. Generate embeddings:
  ```bash
   python scripts/compute_embeddings.py
  ```
   Outputs: `artifacts/embeddings/`.
2. Generate similarity matrices:
  ```bash
   python scripts/compute_similarity_matrices.py
  ```
   Outputs: `artifacts/similarity_matrices/`.
3. Check the embedding and matrix IDs, dimensions, and mappings:
  ```bash
   python scripts/embeddings_similarity_integrity_check.py
  ```
4. Explore configurations on development data. Inspect the constants in the runner first:
  ```bash
   python scripts/run_selector_experiments.py
   python scripts/dev_summary_script.py
  ```
   Development outputs belong under `artifacts/experiments/development/`.
5. Evaluate the frozen validation finalists. Inspect `FINALISTS` before running:
  ```bash
   python scripts/run_validation_finalists.py
  ```
   Outputs belong under `artifacts/experiments/validation/`.
6. After selecting and freezing a configuration using validation, evaluate the held-out test split:
  ```bash
   python scripts/run_test_winner.py
  ```
   The preserved final run is under `artifacts/experiments/test/test_winner/`. Do not tune on test results.

The commands show the pipeline order; they are not a batch rerun recipe for the existing output directories. To interpret results, see `scripts/analyze_similarity_matrices.py`, `scripts/analyze_threshold_regions.py`, and the error-analysis scripts. The local chunk browser is documented in `tools/chunk_browser/README.md`.

## Baselines

Baseline programs are in `scripts/baselines/`. Their definitions, frozen development reference, and preserved validation/test outputs are in `artifacts/baselines/`. See `[artifacts/baselines/README.md](artifacts/baselines/README.md)` before running a baseline; the scripts use configured output paths, and preserved runs should not be overwritten.

## Core modules

- `scripts/text_embedder.py` creates TF-IDF, Sentence-BERT, and retrieval bi-encoder representations. E5 uses `query:` and `passage:` prefixes.
- `scripts/similarity_calculator.py` computes cosine, dot-product, and Euclidean scores.
- `scripts/chunk_selector.py` implements the four selection rules.
- `scripts/mapping_evaluator.py` is the shared scoring authority. Analysis scripts depend on its metric field names.



## Experimental safeguards

- Questions with the same non-empty gold-chunk set are kept together when the frozen splits are formed.
- Use development for exploration, validation for finalist selection, and test only for the frozen final evaluation.
- Preserve existing predictions, evaluations, and versioned run directories. Write new experiments to new directories.
- Keep manual error analysis separate from headline metric computation.
- `scripts/data_splitter.py` is a preparation-era utility that refers to unavailable prepared gold data. It is not part of reported-run reproduction; do not use it to regenerate the frozen split.



## Research material

`literature/` contains papers and reading notes. `metadata/` contains decisions, limitations, method notes, reports, and the paper workspace at `metadata/report/paper/`. These materials document and interpret the experiment; they do not generate the primary retrieval predictions.