# QA Evidence Retrieval Experiments

Retrieve evidence passages for questions about a German examination regulation, with an option to return no evidence. The project compares TF-IDF, multilingual Sentence-BERT and multilingual E5 using four chunk-selection rules. It evaluates evidence sets; it does not generate answers.

The primary evaluation uses `configs/base.json` and the frozen dataset: **720 questions** (600 answerable, 120 zero-gold), **201 chunks**, and grouped development/validation/test partitions of **432/144/144**. Its frozen winner is **E5 top-1 with absolute threshold** `0.84`.


| Dataset / protocol                                     | Validation-selected winner           | Validation Q-F1 | Test Q-F1 | Test exact match | Test micro-F1 |
| ------------------------------------------------------ | ------------------------------------ | --------------- | --------- | ---------------- | ------------- |
| Frozen, 720 questions (`base`)                         | E5 top-1, threshold `0.84`           | 0.604167        | 0.483796  | 0.479167         | 0.500000      |
| Reviewed follow-up, 710 questions (`manual_review_v1`) | E5 top-1, relative margin `0.003025` | 0.546948        | 0.650235  | 0.640845         | 0.703390      |


The frozen winner achieves development Q-F1 **0.647377** and 69 exact matches among 144 test questions. Its saved results are under `[artifacts/experiments/base/](artifacts/experiments/base/)`; selection is recorded in `[validation/frozen_winner.json](artifacts/experiments/base/validation/frozen_winner.json)` and test metrics in `[test/summary.jsonl](artifacts/experiments/base/test/summary.jsonl)`.

The follow-up excludes ten questions and uses a question-level split of 426/142/142. Dataset membership and splitting differ, so its higher test score is not a controlled improvement over the frozen evaluation. The paper reports both protocols separately. The compiled paper is [paper/build/paper.pdf](paper/build/paper.pdf).

## Contents

- [Setup](#setup)
- [Reproduce and verify the experiments](#reproduce-and-verify-the-experiments)
- [Configuration and outputs](#configuration-and-outputs)
- [Optional workflows](#optional-workflows)
- [Data and model sources](#data-and-model-sources)
- [Project files and tests](#project-files-and-tests)



## Setup

Use **Python 3.11** and open a terminal in the repository root. Create the environment once; skip creation if `.venv` already exists.

On Windows (PowerShell):

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation because scripts are disabled, allow scripts for this terminal session and try again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

On macOS/Linux:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

Check that Python points to the environment's executable:

```bash
python -c "import sys; print(sys.executable)"
```

The printed path should be inside this project's `.venv`. **All commands below assume the environment is activated** and run from the repository root unless stated otherwise. Activation lasts for the current terminal session; activate it again in a new terminal. Run `deactivate` to leave it.

Install dependencies:

```bash
python -m pip install --requirement requirements.txt
```



## Reproduce and verify the experiments

On a new machine, copy the project **without** `.venv/`, then follow [Setup](#setup). Include both datasets in `data/`, the prepared `artifacts/representations/full_text/`, and the published `artifacts/experiments/base/` and `artifacts/experiments/manual_review_v1/` results for comparison. Cached-matrix runs need no model weights or GPU. Allow several gigabytes for dependencies and outputs.

### 1. Check the installation and inputs

```bash
python -m unittest discover -s tests -v
python -m scripts.run_experiment --config configs/base.json --stage check
python -m scripts.run_experiment --config configs/manual_review_v1.json --stage check
```

Expect twelve passing tests and `Input and configuration checks passed.` for each dataset. Input checks validate IDs, disjoint splits, gold evidence, matrix alignment, finite scores and parameter grids without writing results.

### 2. Create and run separate copies

Generate rerun configs on the machine you want to run the experiment because they contain absolute project/output paths. The copy command writes a new config with the existing inputs and settings; it neither copies results nor runs the experiment.

```bash
python -m scripts.copy_experiment --config configs/base.json --destination configs/base_rerun.json --name base_rerun --output-dir artifacts/experiments/base_rerun
python -m scripts.run_experiment --config configs/base_rerun.json --confirm-test

python -m scripts.copy_experiment --config configs/manual_review_v1.json --destination configs/manual_review_v1_rerun.json --name manual_review_v1_rerun --output-dir artifacts/experiments/manual_review_v1_rerun
python -m scripts.run_experiment --config configs/manual_review_v1_rerun.json --confirm-test
```

No hand-written config is needed. Choose unused config names and output directories; existing paths are refused. The complete run searches development, compares **five** candidates on validation, freezes one winner, then evaluates test and generates baselines and reports. `--confirm-test` permits test evaluation.

Each protocol evaluates **157 coarse settings**, retaining twelve development family winners, five validation candidates and one test winner. The base run has **4,227 unique fine settings**; the reviewed run has **4,228**. Both use fixed 201-point refinement; the difference comes from retaining a coarse point not identical to a fine-grid value.

Completed stages cannot be overwritten. For an interrupted stage or changed code, inputs, configuration or environment, create a new run. A successfully completed development stage can continue with validation and test separately:

```bash
python -m scripts.run_experiment --config configs/base_rerun.json --stage validation
python -m scripts.run_experiment --config configs/base_rerun.json --stage test --confirm-test
```

For a fully staged run, start with `--stage development` instead of the complete command. Continuing stages requires the same configuration and recorded environment.

### 3. Compare the results

After both reruns finish:

```bash
python -m scripts.compare_results artifacts/experiments/base artifacts/experiments/base_rerun
python -m scripts.compare_results artifacts/experiments/manual_review_v1 artifacts/experiments/manual_review_v1_rerun
```

Use your chosen directory names if different. The script checks all five summary files, setting counts against the published run, every summary value, and the frozen winner. Floating-point metrics allow `1e-12` absolute differences. Success prints `stage counts, summary values and winner match.`; failure identifies the mismatch and exits with a nonzero status.

Paths, environment records and plot rendering can differ across machines and are not compared. If numerical results differ, check the datasets, matrices, settings and dependency versions. This reproduces the published evaluation on existing questions, not performance on a new sample.

Inspect `test/summary.jsonl` for final scores and `reports/test/system_vs_baselines.csv` for comparisons. Expected scores are in the table above. To independently recompute scores from saved predictions and export subgroup metrics and descriptive bootstrap intervals:

```bash
python -m scripts.analysis.assessment --config configs/base_rerun.json --output-dir artifacts/assessment/base_rerun --confirm-test
python -m scripts.analysis.assessment --config configs/manual_review_v1_rerun.json --output-dir artifacts/assessment/manual_review_v1_rerun --confirm-test
```

Assessment output directories must be new. Intervals condition on the fixed winner and annotated test collection; they exclude annotation, selection and repeated-split uncertainty.

## Configuration and outputs

`configs/base.json` uses the 720-question grouped split; `configs/manual_review_v1.json` uses 710 questions and a question-level random split (seed 42). Identical non-empty gold sets stay together only in the grouped protocol. Both index all 201 chunks; matrix rows are selected by question ID.

`project_root` resolves relative to the config file; other paths resolve relative to that root.


| Fields                                  | Purpose                                         |
| --------------------------------------- | ----------------------------------------------- |
| `name`, `output_dir`                    | Run identity and result directory               |
| `gold_path`, `chunks_path`, `splits`    | Evidence annotations, chunks and partition IDs  |
| `representations`                       | Score matrices, ordered IDs and score direction |
| `development`                           | Coarse grids and fine-search bounds             |
| `baselines`, `reports`, `manual_review` | Baseline, report and review settings            |


The four selectors are `top_k`, `threshold`, `top_k_threshold` and `relative_margin`; applicable `top_k` values are 1–3. Fine search brackets coarse winners with neighboring grid points, retains coarse points and removes duplicates. Ranking prefers mean question F1, exact match, precision, then fewer chunks; complete ties retain input order. Empty prediction against empty gold scores perfectly; missing records are reported separately.

Current experiments use cosine scores (`higher_is_better: true`). Preparation also supports dot scores (`true`) and Euclidean distances (`false`).

```text
artifacts/experiments/<name>/
  experiment.json                   # resolved configuration and environment
  development/coarse/               # 157 settings
  development/fine/                 # 4,227 base / 4,228 reviewed settings
  development/summary.jsonl          # twelve family winners
  development/validation_candidates.json
  validation/summary.jsonl           # five candidates
  validation/frozen_winner.json
  test/summary.jsonl                 # one winner
  baselines/                        # validation/test reference scores
  reports/                          # ranking CSVs, plots, baseline comparisons
  diagnostics/                      # optional analysis
  manual_review/                    # optional review CSVs and browser assets
```

Stages also save predictions, evaluation JSON, `run_manifest.json` and `complete.json` receipts. Receipts verify files consumed downstream. `experiment.json` records configuration and package versions, not input or source-file contents.

## Optional workflows

Examples below use a completed `manual_review_v1_rerun`. They are not required for cached-matrix reproduction.

### Reports and diagnostics

```bash
python -m scripts.report_experiment --config configs/manual_review_v1_rerun.json
python -m scripts.analyze_experiment --config configs/manual_review_v1_rerun.json --kind gold
python -m scripts.analyze_experiment --config configs/manual_review_v1_rerun.json --kind matrices
python -m scripts.analyze_experiment --config configs/manual_review_v1_rerun.json --kind thresholds
```

Reports read completed stages. Diagnostics default to development and write to `diagnostics/<split>/<kind>/`. Gold and matrix inspection accept `--split`; threshold advice is development-only. Matrix and threshold diagnostics require higher-is-better scores and do not change the search settings.

### Manual error review

```bash
python -m scripts.manual_review.prefilter --config configs/manual_review_v1_rerun.json --split validation
python -m scripts.manual_review.review --config configs/manual_review_v1_rerun.json --split validation
```

Prefiltering groups non-exact predictions into four CSVs. Interactive review opens evidence passages, resumes saved labels and saves decisions without changing gold evidence or scores. The optional browser in `tools/chunk_browser/` was AI-generated; Python performs retrieval and scoring.

### Dataset replay

```bash
python -m scripts.preparation.dataset --questions data/frozen/qSet_PO.jsonl --gold data/frozen/split/gold_with_split.jsonl --splits-dir data/manual_review_v1 --output-dir artifacts/dataset_replay/manual_review_v1 --revised
```

This applies the ten documented exclusions and saved split IDs, checks membership and records input hashes in a new output directory. See [the exclusion rationale](data/manual_review_v1/README.md). For the grouped dataset, use `--splits-dir data/frozen/split`, a different output directory and omit `--revised`. Replay does not regenerate annotations or split assignments.

### New representations

```bash
python -m scripts.preparation.representations --config configs/prepare_representations.example.json
python -m scripts.preparation.representations --config configs/prepare_neural.example.json
```

The first example prepares TF-IDF; the second prepares pinned Sentence-BERT and E5 models. Both encode frozen source questions and chunks into new directories and export `representations.json` paths for a new experiment config. Existing output directories are refused. Available methods are `TF_IDF`, `SENTENCE_BERT` and `RETRIEVAL_BI_ENCODER`.

Neural preparation can download missing weights. Supply a model ID and immutable `revision`, or a preserved local snapshot; metadata records model/revision, sequence limit, prefixes and normalization. Changed data or representations require a new experiment config and output directory.

## Data and model sources

Questions and gold evidence used GPT-5.5 Sol support and author review, with no independent second annotator. Complete generation prompts and a detailed review protocol are unavailable. The current preparation scripts reproduce the datasets using saved split assignments; they do not regenerate those assignments. Reproduction uses the saved datasets, assignments and prepared complete-text cosine matrices.

The source document is the [HHU examination regulation dated 20 January 2026](data/raw/PO_25_CL.pdf), including the computational-linguistics appendix and study plan. The [bibliography](paper/references.bib) identifies the cited publications; their PDFs are stored in [literature/papers/](literature/papers/).

All three representation methods are implemented in `[scripts/preparation/text_embedder.py](scripts/preparation/text_embedder.py)`:


| Method                                   | Implementation and source                                                                                                                                                                                                                                                                                        |
| ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TF-IDF (`TF_IDF`)                        | scikit-learn's `TfidfVectorizer`, fitted on chunk texts; no pretrained checkpoint. [Spärck Jones (1972)](https://doi.org/10.1108/eb026526) provides the collection-frequency weighting principle underlying IDF.                                                                                                 |
| Sentence-BERT (`SENTENCE_BERT`)          | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`; [model card](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2), [Sentence-BERT paper](https://aclanthology.org/D19-1410/) and [multilingual distillation paper](https://aclanthology.org/2020.emnlp-main.365/). |
| Multilingual E5 (`RETRIEVAL_BI_ENCODER`) | `intfloat/multilingual-e5-base`; [model card](https://huggingface.co/intfloat/multilingual-e5-base), [E5 paper](https://arxiv.org/abs/2212.03533) and [multilingual E5 report](https://arxiv.org/abs/2402.05672).                                                                                                |


TF-IDF fits lowercase word 1–3 grams on chunks, without sublinear term-frequency scaling, and transforms questions using that vocabulary. Sentence-BERT encodes questions and chunks without task prefixes. E5 uses `query:`  for questions and `passage:`  for chunks. Neural vectors are not normalized before cosine calculation.

The neural checkpoints use the following pinned snapshots and project-configured token limits. TF-IDF has no transformer token limit or pretrained snapshot.


| Model           | Pinned snapshot                            | Input limit | Longest question / chunk |
| --------------- | ------------------------------------------ | ----------- | ------------------------ |
| Sentence-BERT   | `e8f8c211226b894fcb81acc59f3b34ba3efd5f42` | 512         | 38 / 347                 |
| Multilingual E5 | `d128750597153bb5987e10b1c3493a34e5a4502a` | 512         | 41 / 349                 |


All current matrices are generated from complete texts in `artifacts/representations/full_text/`. Neural preparation counts tokens including special tokens and E5 prefixes and rejects inputs exceeding the configured limit. Every question and passage fits, so **nothing is truncated**. Preparation metadata records the model revisions, effective limits and observed token lengths.

To regenerate all three representations:

1. Copy `configs/prepare_full_text.json` to `configs/prepare_full_text_rerun.json`.
2. In the copied file, change `output_dir` to an unused directory, such as `artifacts/representations/full_text_rerun`. Keep the other settings unchanged to reproduce the same preparation.
3. Run:
  ```bash
   python -m scripts.preparation.representations --config configs/prepare_full_text_rerun.json
  ```
4. Point a new experiment configuration at the paths exported in `artifacts/representations/full_text_rerun/representations.json`.

Running the original preparation configuration unchanged is refused because its output directory already exists. Archive weights and preparation outputs for future reproduction.

## Project files and tests


| Directory                | Contents                                                                      |
| ------------------------ | ----------------------------------------------------------------------------- |
| `configs/`               | Experiment and preparation configurations                                     |
| `scripts/core/`          | Search, selection, scoring and execution                                      |
| `scripts/analysis/`      | Diagnostics and test-result assessment                                        |
| `scripts/preparation/`   | Dataset replay; TF-IDF, Sentence-BERT and E5 preparation; similarity matrices |
| `scripts/manual_review/` | Error grouping and review                                                     |
| `data/`, `artifacts/`    | Documents, datasets, matrices and results                                     |
| `tests/`                 | Twelve focused checks on temporary synthetic datasets                         |
| `tools/chunk_browser/`   | Optional AI-generated passage viewer                                          |
| `paper/`, `literature/`  | Finished paper, LaTeX source and references                                   |


The tests check stage execution and order, five validation candidates, scoring, overwrite protection, input validity, configuration consistency, winner-file changes, missing predictions, ranking ties, refinement boundaries and dataset-replay overlap. They do not modify published results or run the full search. Run them with `python -m unittest discover -s tests -v`; compare complete experiment results using the reproduction steps above.