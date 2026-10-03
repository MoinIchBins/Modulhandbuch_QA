# QA Evidence Retrieval Experiments

Retrieve evidence passages for questions about a German examination regulation, with an option to return no evidence. The project compares TF-IDF, multilingual Sentence-BERT and multilingual E5 using four chunk-selection rules. It evaluates evidence sets; it does not generate answers.

The primary evaluation uses **`configs/base.json`** and the frozen dataset: **720 questions** (600 answerable, 120 zero-gold), **201 chunks**, and grouped development/validation/test partitions of **432/144/144**. Its frozen winner is **E5 top-1 with absolute threshold `0.84`**.

| Dataset / protocol | Validation-selected winner | Validation Q-F1 | Test Q-F1 | Test exact match | Test micro-F1 |
| --- | --- | ---: | ---: | ---: | ---: |
| Frozen, 720 questions (`base`) | E5 top-1, threshold `0.84` | 0.604167 | 0.483796 | 0.479167 | 0.500000 |
| Reviewed follow-up, 710 questions (`manual_review_v1`) | E5 top-1, relative margin `0.003025` | 0.546948 | 0.650235 | 0.640845 | 0.703390 |

The frozen winner achieves development Q-F1 **0.647377** and 69 exact matches among 144 test questions. Its saved results are under [`artifacts/experiments/base/`](artifacts/experiments/base/); selection is recorded in [`validation/frozen_winner.json`](artifacts/experiments/base/validation/frozen_winner.json) and test metrics in [`test/summary.jsonl`](artifacts/experiments/base/test/summary.jsonl).

The follow-up excludes ten questions and uses a question-level split of 426/142/142. Dataset membership and splitting differ, so its higher test score is not a controlled improvement over the frozen evaluation. The paper reports both protocols separately. The finished paper is [paper/build/paper.pdf](paper/build/paper.pdf).

## Contents

- [Setup](#setup)
- [Reproduce the paper's pipeline](#reproduce-the-papers-pipeline)
- [Start-to-end check on a new machine](#start-to-end-check-on-a-new-machine)
- [Inputs and outputs](#inputs-and-outputs)
- [Configuration](#configuration)
- [Run the stages](#run-the-stages)
- [Describe the saved test result](#describe-the-saved-test-result)
- [Replay dataset membership](#replay-dataset-membership)
- [Diagnostics](#diagnostics)
- [Manual review](#manual-review)
- [Prepare new representations](#prepare-new-representations)
- [Data and model sources](#data-and-model-sources)
- [Files](#files)
- [Tests](#tests)

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

Install dependencies and check the frozen inputs:

```bash
python -m pip install --requirement requirements.txt
python -m scripts.run_experiment --config configs/base.json --stage check
```

The single requirements file includes experiment and model-preparation dependencies. Installing the packages does not download model weights; model preparation may download weights if the requested snapshot is not cached. Experiments use the retained cosine matrices.

## Reproduce the paper's pipeline

Published outputs already exist. Copy the config to a new run before executing it:

```bash
python -m scripts.copy_experiment --config configs/base.json --destination configs/base_rerun.json --name base_rerun --output-dir artifacts/experiments/base_rerun
python -m scripts.run_experiment --config configs/base_rerun.json --confirm-test
```

Choose another name and directory if those paths exist. A complete run performs development search, validation selection, test evaluation, baselines and report generation. For the frozen protocol, expected counts are 157 coarse settings, 4,227 fine settings, twelve development family winners, five validation candidates and one test winner. Retaining every setting's predictions can require gigabytes of disk space.

Both protocols use the same coarse grids, local fine search with 201 points, and five validation candidates. These counts are fixed in the scripts. The detailed staged examples below use a separate follow-up copy named `manual_review_v1_rerun`.

## What the three commands do

Run these commands from the project root with the environment activated.

1. `run_experiment --config configs/base.json --stage check` reads and validates the frozen inputs and parameter grids: IDs, split overlap, gold evidence, matrix dimensions and finite scores. It does not create or change results.
2. `copy_experiment ... --destination configs/base_rerun.json ... --output-dir artifacts/experiments/base_rerun` writes a new config with the same inputs and search settings, a new run name and a separate output path. It does not copy results or run the experiment. It refuses existing destination configs or output directories.
3. `run_experiment --config configs/base_rerun.json --confirm-test` defaults to `--stage all`. It creates the output directory, searches development, compares the five validation candidates, evaluates the winner on test, and creates baselines and reports. `--confirm-test` permits the test stage; it does not change the split or tune on test.

The published `artifacts/experiments/base/` results remain untouched. Repeating the complete command after it finishes fails because stage directories already exist. For another run, choose a new config, name and directory, for example `base_rerun_2` in all three places. An interrupted, partially written stage cannot be resumed; use a new run directory. If development completed successfully, you can continue with `--stage validation`, then `--stage test --confirm-test`, as described below.

## Start-to-end check on a new machine

### 1. Bring the project files

Copy the current project, including `scripts/`, `tests/`, `configs/`, `requirements.txt`, `data/frozen/`, `data/manual_review_v1/`, and `artifacts/similarity_matrices/`. Keep the published `artifacts/experiments/base/` and `artifacts/experiments/manual_review_v1/` directories for the comparison below. Published results are not needed to compute a fresh run, but are needed for that comparison. Copying the whole project is the simplest way to include everything.

Create a new virtual environment; do not transfer `.venv/`. Use the portable source configs `configs/base.json` and `configs/manual_review_v1.json`. Generate rerun configs **on the new machine**: the copy command records its absolute project/output paths, so transferring a previously generated rerun config can leave it pointing to the wrong location.

This walkthrough reproduces retrieval from the frozen datasets and cached matrices. It does not recreate annotations, rechunk the PDF or regenerate representations. Encoder weights and a GPU are not needed for this run. Representation preparation is a separate optional workflow later in this guide.

### 2. Install dependencies and run the small tests

From the copied project's root, create and activate a fresh environment using [the setup above](#setup). Then install dependencies and run these checks; the commands are the same on Windows and macOS/Linux:

```bash
python -m pip install --requirement requirements.txt
python -m unittest discover -s tests -v
python -m scripts.run_experiment --config configs/base.json --stage check
python -m scripts.run_experiment --config configs/manual_review_v1.json --stage check
```

Expected: twelve passing tests and `Input and configuration checks passed.` for each dataset. Tests use temporary fixtures and do not change published results. Allow several gigabytes of disk space for dependencies and rerun outputs.

### 3. Create and run your own experiments

Choose unused names. These commands create **two new config files automatically** and write results to separate new directories:

```bash
python -m scripts.copy_experiment --config configs/base.json --destination configs/base_rerun.json --name base_rerun --output-dir artifacts/experiments/base_rerun
python -m scripts.run_experiment --config configs/base_rerun.json --confirm-test

python -m scripts.copy_experiment --config configs/manual_review_v1.json --destination configs/manual_review_v1_rerun.json --name manual_review_v1_rerun --output-dir artifacts/experiments/manual_review_v1_rerun
python -m scripts.run_experiment --config configs/manual_review_v1_rerun.json --confirm-test
```

No hand-written config is needed. Each run should evaluate **157 coarse settings, 4,227 fine settings, five validation settings and one test winner**. Development also retains twelve family winners. You can run the experiments one after another.

### 4. Inspect and compare your results

Inside each new output directory, inspect:

- `development/summary.jsonl`: twelve family winners.
- `development/validation_candidates.json`: the five selected candidates.
- `validation/frozen_winner.json`: the winner and parameters.
- `test/summary.jsonl`: the final test scores.
- `reports/development/ranking.csv` and `reports/validation/ranking.csv`: readable rankings and corresponding PNG plots.
- `reports/test/system_vs_baselines.csv`: the winner and comparison methods.

Expected winners and scores are listed in [the results table at the top](#qa-evidence-retrieval-experiments).

For an automatic comparison, run this after **both** reruns finish. Change the rerun names if you chose different ones. It checks all saved setting summaries in all five stages and the winners against the published runs, allowing `1e-12` absolute rounding differences in floating-point metrics.

Save the following code as `compare_results.py` in the project root:

```python
import json
import math
from pathlib import Path

root = Path("artifacts/experiments")
counts = {"development/coarse": 157, "development/fine": 4227,
          "development": 12, "validation": 5, "test": 1}

def summaries(name, stage):
    path = root / name / stage / "summary.jsonl"
    return {row["experiment"]: row
            for row in map(json.loads, path.read_text().splitlines())}

for original, rerun in (("base", "base_rerun"),
                        ("manual_review_v1", "manual_review_v1_rerun")):
    for stage, count in counts.items():
        expected = summaries(original, stage)
        actual = summaries(rerun, stage)
        assert len(actual) == count, (rerun, stage, "count")
        assert actual.keys() == expected.keys(), (rerun, stage, "settings")
        for name, row in expected.items():
            assert actual[name].keys() == row.keys(), (rerun, stage, name)
            for key, value in row.items():
                result = actual[name][key]
                matches = (math.isclose(result, value, rel_tol=0, abs_tol=1e-12)
                           if isinstance(value, float) else result == value)
                assert matches, (rerun, stage, name, key, result, value)
    winners = []
    for name in (original, rerun):
        path = root / name / "validation/frozen_winner.json"
        winners.append(json.loads(path.read_text())["winner"])
    assert winners[0] == winners[1], (rerun, "winner")
    print(f"{rerun}: stage counts, summary values and winner match.")
```

Run it with the activated environment on any operating system:

```bash
python compare_results.py
```

`experiment.json` naturally differs between machines: it records paths, run names and the environment. PNG rendering may also differ. Compare numerical results rather than requiring those files to be byte-identical. If a comparison fails, its error identifies the stage, setting and metric; check that input data, matrices, configurations and installed dependency versions match the reference. Passing this check reproduces the reported experiment, rather than measuring performance on new questions.

### 5. Recompute test metrics from predictions

For a further check against the saved gold evidence, run:

```bash
python -m scripts.analysis.assessment --config configs/base_rerun.json --output-dir artifacts/assessment/base_rerun --confirm-test
python -m scripts.analysis.assessment --config configs/manual_review_v1_rerun.json --output-dir artifacts/assessment/manual_review_v1_rerun --confirm-test
```

These commands recompute test metrics from your predictions, check them against the saved evaluation, and export subgroup scores and descriptive bootstrap intervals into **new** directories. Choose unused output directories for repeat exports. Model preparation, interactive review and the paper build are optional and are not required to reproduce retrieval scores.

## Inputs and outputs

The primary frozen dataset has 720 questions: 600 answerable and 120 with empty gold evidence sets. The 201 indexed chunks are shared across all partitions. Split sizes are 432 development, 144 validation and 144 test questions. Identical non-empty gold evidence sets remain in the same partition. The separate reviewed follow-up has 710 questions and a question-level random split of 426/142/142 (seed 42). Both protocols run through the current scripts.

Follow-up inputs are:

- Questions, annotations and split IDs: `data/manual_review_v1/`.
- Retrieval chunks: `data/frozen/PO_25_CL_chunks.jsonl`.
- Retained cosine matrices and ordered ID arrays: `artifacts/similarity_matrices/`.
- Complete experiment definition: `configs/manual_review_v1.json`.

The matrices contain all frozen source-question rows; the runner selects the retained rows by question ID. Extra matrix rows are allowed.

```text
artifacts/experiments/<name>/
  experiment.json                 # resolved config and environment
  development/
    coarse/                       # 157 settings
    fine/                         # 4,227 settings for either dataset
    summary.jsonl                 # twelve representation/selector winners
    validation_candidates.json
  validation/
    summary.jsonl                 # five frozen candidates
    frozen_winner.json
  test/
    summary.jsonl                 # one frozen winner
  baselines/                      # validation/test reference scores
  reports/                        # CSV tables and PNG plots
  manual_review/                  # optional review CSVs and browser copy
  diagnostics/                    # optional descriptive analysis
```

Stage directories also contain prediction JSONL, evaluation JSON and a `run_manifest.json`. Their `complete.json` receipts record checksums for the downstream-consumed artifacts. The experiment manifest records the resolved configuration and package versions. It does not fingerprint input files or source code.

## Configuration

`project_root` resolves relative to the config file; input/output paths resolve relative to that root. Run module commands from the repository root.

| Field | Meaning |
| --- | --- |
| `name`, `output_dir` | Run name and output directory |
| `gold_path`, `chunks_path` | Gold JSONL and retrieval-chunk JSONL |
| `splits` | Development, validation and test ID files |
| `representations` | Matrix paths, ordered question/chunk IDs and score direction |
| `development` | Coarse sweeps or explicit settings, local fine-search bounds |
| `baselines` | Enabled flag, reference chunk order and distinct random seeds |
| `reports` | Generate reports after stages |
| `manual_review` | Default review split, optional previous-review CSV and browser port |

Cosine and dot scores use `higher_is_better: true`; Euclidean distances use `false`. Matrices must have finite entries and match the supplied ID arrays. Splits must be disjoint, and gold IDs must reference indexed chunks.

The follow-up configuration searches `top_k`, `threshold`, `top_k_threshold` and `relative_margin`. Applicable `top_k` values are 1, 2 and 3. Coarse search evaluates 157 settings. Local refinement brackets each coarse winner with its neighboring coarse points and evaluates 201 evenly spaced values within the configured bounds. It retains the best coarse points, removes duplicates and yields 4,227 fine settings for either dataset. The twelve family winners are ranked, and only the top five proceed to validation.

Ranking uses mean question-wise F1, exact match, mean precision and then fewer selected chunks. Complete ties retain input order. Empty prediction against empty gold receives perfect scores; missing prediction records are counted separately.

`configs/base.json` defines the retained grouped protocol with 720 questions, local refinement using 201 points, 4,227 fine settings and five validation finalists. It is the paper's primary evaluation, with the reviewed protocol reported separately. Both definitions use the same entry points and cached chunks/matrices.

## Run the stages

Create a new configuration and output directory:

```bash
python -m scripts.copy_experiment --config configs/manual_review_v1.json --destination configs/manual_review_v1_rerun.json --name manual_review_v1_rerun --output-dir artifacts/experiments/manual_review_v1_rerun
```

The copy command retains input/search settings and refuses existing destination/output paths. Then use **either** the complete commands above **or** these staged commands:

```bash
python -m scripts.run_experiment --config configs/manual_review_v1_rerun.json --stage development
python -m scripts.run_experiment --config configs/manual_review_v1_rerun.json --stage validation
python -m scripts.run_experiment --config configs/manual_review_v1_rerun.json --stage test --confirm-test
```

1. Preflight checks IDs, split overlap, matrix alignment and selector settings.
2. Development searches parameters and saves validation candidates.
3. Validation compares those candidates and writes `validation/frozen_winner.json`.
4. Test checks that the saved winner matches validation and scores that configuration.
5. Enabled baselines and reports are generated after validation/test; development also gets its ranking report.

To regenerate reports for a run produced by the current code/environment:

```bash
python -m scripts.report_experiment --config configs/manual_review_v1_rerun.json
```

Completed stages cannot be overwritten. A continued run must retain the same configuration and recorded environment. Use a new output directory for an interrupted stage or changes to source code or input data; the experiment manifest records file paths, not their contents.

## Describe the saved test result

```bash
python -m scripts.analysis.assessment --config configs/manual_review_v1.json --output-dir artifacts/assessment/current_description --confirm-test
```

Choose a new output directory if that path exists. The exporter recomputes scores from saved predictions and gold, then writes subgroup metrics and a gold-set cluster-bootstrap interval. It reads existing results rather than selecting another model. The interval conditions on the fixed winner and annotated test collection; it does not include annotation uncertainty, parameter-selection uncertainty or repeated-split variation.

## Replay dataset membership

```bash
python -m scripts.preparation.dataset --questions data/frozen/qSet_PO.jsonl --gold data/frozen/split/gold_with_split.jsonl --splits-dir data/manual_review_v1 --output-dir artifacts/dataset_replay/manual_review_v1 --revised
```

The exporter removes the ten documented exclusions, applies the supplied split IDs, checks complete/disjoint membership and records input hashes. The output directory must be new. The exclusion rationale is in [the dataset README](data/manual_review_v1/README.md).

To replay the retained grouped dataset, use `--splits-dir data/frozen/split`, choose another output directory and omit `--revised`. This reproduces saved assignments; it does not regenerate questions or recover the unavailable split-generation code.

## Diagnostics

```bash
python -m scripts.analyze_experiment --config configs/manual_review_v1_rerun.json --kind gold
python -m scripts.analyze_experiment --config configs/manual_review_v1_rerun.json --kind matrices
python -m scripts.analyze_experiment --config configs/manual_review_v1_rerun.json --kind thresholds
```

Diagnostics default to development and write to `diagnostics/<split>/<kind>/`. Gold/matrix inspection can select another split with `--split`; threshold advice is restricted to development. Matrix and threshold diagnostics require higher-is-better scores. These exports do not automatically change the search config.

## Manual review

```bash
python -m scripts.manual_review.prefilter --config configs/manual_review_v1_rerun.json --split validation
python -m scripts.manual_review.review --config configs/manual_review_v1_rerun.json --split validation
```

Prefiltering writes four category CSVs under `manual_review/<split>/`, including headers for empty categories. Groups are based on predicted/gold set relationships; they are not semantic explanations by themselves. Interactive review opens source passages, resumes earlier labels and saves decisions atomically. It stops the local browser server on exit. Review annotations do not modify the experiment gold or winner.

The optional browser in `tools/chunk_browser/` was AI-generated. It displays evidence passages during manual review; retrieval and scoring are performed by the Python scripts.

## Prepare new representations

```bash
python -m scripts.preparation.representations --config configs/prepare_representations.example.json
```

The TF-IDF example creates new embeddings and a cosine matrix in `artifacts/representations/new_tfidf/`. It refuses an existing output directory. Its `representations.json` contains paths for a new experiment config. Available methods are `TF_IDF`, `SENTENCE_BERT` and `RETRIEVAL_BI_ENCODER`; similarities are `cosine`, `dot` and `euclidean`.

The pinned neural example is:

```bash
python -m scripts.preparation.representations --config configs/prepare_neural.example.json
```

Both examples encode the frozen source questions. Experiments select their own question rows by ID. Neural preparation may download weights when they are absent locally. A model entry can supply `model_name_or_path` and an immutable `revision`; a preserved local snapshot directory is also supported. Metadata records the requested model/revision, sequence limit, E5 prefixes and normalization setting.

Changing chunks, questions, annotations or representations requires a new config and output directory. Such a change is a new experiment, not reproduction of the reported result.

## Data and model sources

The reproducible experiment inputs are the three retained cosine matrices and their explicit question/chunk ID arrays. Experiment manifests record their paths. Regenerating neural representations is a separate operation and may not reproduce them bit for bit.

| Encoder | Local snapshot available on 3 October 2026 | Snapshot sequence limit |
| --- | --- | ---: |
| `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | `e8f8c211226b894fcb81acc59f3b34ba3efd5f42` | 128 tokens |
| `intfloat/multilingual-e5-base` | `d128750597153bb5987e10b1c3493a34e5a4502a` | 512 tokens |

These identifiers and limits were read from locally cached model snapshots. Their presence now does not prove that the historical cached matrices were created from these exact snapshots. The retained historical artifacts do not record immutable model revisions or per-text truncation logs. The reconstruction below checks whether these snapshots reproduce the retained matrices.

The preparation code fits TF-IDF only on the chunk collection, using lowercase word unigrams, bigrams and trigrams with no sublinear term-frequency scaling. Questions are transformed using that fitted vocabulary. E5 prefixes question text with `query: ` and evidence text with `passage: `. Neural embeddings are not normalized in advance; cosine similarity handles vector norms.

For future neural preparation, provide `model_name_or_path` and an immutable `revision` in the model config. New preparation outputs record the requested revision and effective maximum sequence length. Passing a preserved local snapshot directory is also supported. Archive the model files and preparation outputs if future regeneration must be independent of model-host changes.

Questions and gold evidence sets were created with GPT-5.5 Sol support and manually reviewed by the author; no independent second annotation was conducted. Frozen questions, annotations and split IDs can be replayed, but a complete generation-prompt log, independently documented review protocol and original revised random-split source are not retained. Dataset replay uses the saved records and split assignments.

### Verified reconstruction

The local snapshots above were used offline to encode all 720 questions and 201 chunks. TF-IDF reproduced its cached cosine matrix exactly. Sentence-BERT differed by at most 6.855e-7 and E5 by at most 1.312e-6 in absolute cosine similarity. The selected-setting summaries checked during that separate reconstruction remained unchanged. These snapshots provide a verified reconstruction; the original preparation record remains unavailable.

The current token audit includes special tokens and E5 prefixes. All questions fit the respective limits (maximum 38 tokens for Sentence-BERT and 41 for E5). Sentence-BERT truncates 35 of 201 chunks (maximum untruncated length 347 tokens); E5 truncates none (maximum 349 tokens). This is a plausible influence on model comparison, not an isolated causal explanation.

`configs/prepare_neural.example.json` specifies the verified public model IDs and immutable revisions for new preparation. The verification used the already-cached local snapshot directories and made no model downloads.

## Files

```text
README.md                         # setup, experiments and preparation guide
requirements.txt                  # all Python dependencies
configs/                          # experiment and preparation configurations
scripts/core/                     # selection, scoring, search and execution
scripts/analysis/                 # descriptive diagnostics and uncertainty
scripts/preparation/              # dataset replay and representation preparation
scripts/manual_review/            # error groups and interactive review
data/                            # source documents, chunks, questions and splits
artifacts/                        # cached matrices, runs and assessment exports
tests/                            # twelve focused unittest checks
tools/chunk_browser/               # optional AI-generated inspection tool
paper/                            # submitted PDF and accompanying LaTeX source
literature/                       # reference papers and reading notes
```

## Tests

```bash
python -m unittest discover -s tests -v
```

The twelve tests use small synthetic datasets in temporary directories. They check:

- Development, validation and test execution, the fixed five validation candidates, expected scores and overwrite protection.
- Rejection of overlapping splits, inconsistent split labels, duplicate IDs, invalid parameters, incorrectly shaped matrices and non-finite scores.
- Consistent run configuration, unchanged validation-winner files, completed validation before test, and explicit test confirmation.
- The distinction between an empty prediction and a missing prediction, ranking ties and fine-search interval boundaries.
- Rejection of overlapping dataset-replay assignments before writing output.

The tests do not modify published results or run the full parameter search. They check implementation behavior; use the reproduction walkthrough to compare complete experiment results.
