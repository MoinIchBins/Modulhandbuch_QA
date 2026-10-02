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

Before generating anything, inspect the JSON configuration and output path. Experiment runners refuse to use an existing output directory; pass `--output-dir` to choose another location.

For the `manual_review_v1` runs below, skip steps 1–3: the reviewed questions are an unchanged subset of the questions already embedded, and the chunks are unchanged. The experiment runners align matrix rows by question ID. The embedding and matrix generation scripts use the frozen input paths and rewrite shared artifact folders.

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
4. Compare every representation (`tfidf`, `e5`, `sentence_bert`) with all four selectors on development. The coarse grid uses representation-specific threshold and margin values because score scales differ. The fine run narrows each continuous search around its best coarse configuration; `top_k` uses the discrete coarse values directly.
  ```bash
   .venv/bin/python scripts/run_selector_experiments.py --config configs/manual_review_v1_coarse.json
   .venv/bin/python scripts/analyze_selector_experiments.py artifacts/experiments/manual_review_v1/outputs/development/coarse_all_v2
   .venv/bin/python scripts/run_selector_experiments.py --config configs/manual_review_v1_fine.json --coarse-run artifacts/experiments/manual_review_v1/outputs/development/coarse_all_v2
   .venv/bin/python scripts/dev_summary_script.py --run-set configs/manual_review_v1_dev_round_1.json
  ```
   The coarse config lists every representation, selector, and parameter grid. The fine config explicitly lists each representation/selector region and its point count; edit those intervals and densities after reviewing the coarse analysis if needed. The fine runner retains each discrete `top_k` winner and checks that its config matches the coarse run. The development summary ranks the fine results within each representation and selector and writes those 12 candidates to `validation_candidates.json`.
5. Compare the development-selected candidates on validation:
  ```bash
   .venv/bin/python scripts/run_validation_finalists.py --config configs/manual_review_v1_validation.json
  ```
   Validation ranks all candidates by question-level F1, exact match, precision, then fewer selected chunks. It writes a single `frozen_winner.json` from the top validation result. The test runner accepts that validation output directory and evaluates only that winner:
  ```bash
   .venv/bin/python scripts/run_test_winner.py --validation-dir artifacts/experiments/manual_review_v1/outputs/validation/finalists_full_search_v2
  ```
   Do not tune on test results. Use `--output-dir` on a runner to choose another new run directory.

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
