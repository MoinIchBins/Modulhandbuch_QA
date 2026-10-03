# Experiment pipeline

## Frozen 720-question evaluation

The paper's primary protocol is `configs/base.json`. Saved outputs are in `artifacts/experiments/base/`. Its winner is E5 top-1 with threshold `0.84`: development Q-F1 `0.647377`, validation Q-F1 `0.604167`, test Q-F1 `0.483796`, test exact match `0.479167` and test micro-F1 `0.500000`.

```bash
.venv/bin/python -m scripts.run_experiment --config configs/base.json --stage check
.venv/bin/python -m scripts.copy_experiment --config configs/base.json --destination configs/base_rerun.json --name base_rerun --output-dir artifacts/experiments/base_rerun
.venv/bin/python -m scripts.run_experiment --config configs/base_rerun.json --confirm-test
```

Both protocols use the same coarse grids, local refinement with 201 points, 4,227 fine settings on these datasets, and five validation finalists. The point count and validation-candidate count are fixed in the scripts. Neither protocol uses the removed implementation. The detailed paths and commands below describe the follow-up; substitute the base config and its output directory when working with the primary frozen evaluation.


This guide describes the current Python entry points and configurations. The paper reports `configs/base.json` as its primary frozen evaluation and `configs/manual_review_v1.json` as a separate follow-up; the detailed examples below use a new follow-up copy named `manual_review_v1_rerun`. Start with the setup in [README.md](README.md). All Python dependencies are in `requirements.txt`.

## What the three commands do

Run these commands from the project root after setting up the environment.

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

Use Python 3.11 and change into the project root. For macOS/Linux:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install --requirement requirements.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m scripts.run_experiment --config configs/base.json --stage check
.venv/bin/python -m scripts.run_experiment --config configs/manual_review_v1.json --stage check
```

Expected: twelve passing tests and `Input and configuration checks passed.` for each dataset. Tests use temporary fixtures and do not change published results. Allow several gigabytes of disk space for dependencies and rerun outputs.

On Windows, create the environment with `py -3.11 -m venv .venv` and replace `.venv/bin/python` with `.venv/Scripts/python.exe`. Put the optional comparison code below in a Python file and execute it rather than using shell heredoc syntax.

### 3. Create and run your own experiments

Choose unused names. These commands create **two new config files automatically** and write results to separate new directories:

```bash
.venv/bin/python -m scripts.copy_experiment --config configs/base.json --destination configs/base_rerun.json --name base_rerun --output-dir artifacts/experiments/base_rerun
.venv/bin/python -m scripts.run_experiment --config configs/base_rerun.json --confirm-test

.venv/bin/python -m scripts.copy_experiment --config configs/manual_review_v1.json --destination configs/manual_review_v1_rerun.json --name manual_review_v1_rerun --output-dir artifacts/experiments/manual_review_v1_rerun
.venv/bin/python -m scripts.run_experiment --config configs/manual_review_v1_rerun.json --confirm-test
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

Expected scores using the retained matrices and settings:

| Dataset | Winner | Validation Q-F1 | Test Q-F1 | Test exact match | Test micro-F1 |
| --- | --- | ---: | ---: | ---: | ---: |
| Frozen, 720 questions | E5 top-1, threshold `0.84` | 0.604167 | 0.483796 | 0.479167 | 0.500000 |
| Reviewed, 710 questions | E5 top-1, relative margin `0.003025` | 0.546948 | 0.650235 | 0.640845 | 0.703390 |

For an automatic comparison, run this after **both** reruns finish. Change the rerun names if you chose different ones. It checks all saved setting summaries in all five stages and the winners against the published runs, allowing `1e-12` absolute rounding differences in floating-point metrics.

```bash
.venv/bin/python - <<'PY'
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
PY
```

`experiment.json` naturally differs between machines: it records paths, run names and the environment. PNG rendering may also differ. Compare numerical results rather than requiring those files to be byte-identical. If a comparison fails, its error identifies the stage, setting and metric; check that input data, matrices, configurations and installed dependency versions match the reference. Passing this check reproduces the reported experiment, rather than measuring performance on new questions.

### 5. Recompute test metrics from predictions

For a further check against the saved gold evidence, run:

```bash
.venv/bin/python -m scripts.analysis.assessment --config configs/base_rerun.json --output-dir artifacts/assessment/base_rerun --confirm-test
.venv/bin/python -m scripts.analysis.assessment --config configs/manual_review_v1_rerun.json --output-dir artifacts/assessment/manual_review_v1_rerun --confirm-test
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
.venv/bin/python -m scripts.copy_experiment --config configs/manual_review_v1.json --destination configs/manual_review_v1_rerun.json --name manual_review_v1_rerun --output-dir artifacts/experiments/manual_review_v1_rerun
```

The copy command retains input/search settings and refuses existing destination/output paths. Then use **either** the complete command in the README **or** these staged commands:

```bash
.venv/bin/python -m scripts.run_experiment --config configs/manual_review_v1_rerun.json --stage development
.venv/bin/python -m scripts.run_experiment --config configs/manual_review_v1_rerun.json --stage validation
.venv/bin/python -m scripts.run_experiment --config configs/manual_review_v1_rerun.json --stage test --confirm-test
```

1. Preflight checks IDs, split overlap, matrix alignment and selector settings.
2. Development searches parameters and saves validation candidates.
3. Validation compares those candidates and writes `validation/frozen_winner.json`.
4. Test checks that the saved winner matches validation and scores that configuration.
5. Enabled baselines and reports are generated after validation/test; development also gets its ranking report.

The current winner is E5 relative margin with `top_k=1`, `margin=0.003025`: validation Q-F1 0.546948 and test Q-F1 0.650235. Test EM is 0.640845 and micro-F1 is 0.703390.

To regenerate reports for a run produced by the current code/environment:

```bash
.venv/bin/python -m scripts.report_experiment --config configs/manual_review_v1_rerun.json
```

Completed stages cannot be overwritten. A continued run must retain the same configuration and recorded environment. Use a new output directory for an interrupted stage or changes to source code or input data; the experiment manifest no longer detects content changes to those files.

## Describe the saved test result

```bash
.venv/bin/python -m scripts.analysis.assessment --config configs/manual_review_v1.json --output-dir artifacts/assessment/current_description --confirm-test
```

Choose a new output directory if that path exists. The exporter recomputes scores from saved predictions and gold, then writes subgroup metrics and a gold-set cluster-bootstrap interval. It reads existing results rather than selecting another model. The interval conditions on the fixed winner and annotated test collection; it does not include annotation uncertainty, parameter-selection uncertainty or repeated-split variation.

## Replay dataset membership

```bash
.venv/bin/python -m scripts.preparation.dataset --questions data/frozen/qSet_PO.jsonl --gold data/frozen/split/gold_with_split.jsonl --splits-dir data/manual_review_v1 --output-dir artifacts/dataset_replay/manual_review_v1 --revised
```

The exporter removes the ten documented exclusions, applies the supplied split IDs, checks complete/disjoint membership and records input hashes. The output directory must be new. The exclusion rationale is in [the dataset README](data/manual_review_v1/README.md).

To replay the retained grouped dataset, use `--splits-dir data/frozen/split`, choose another output directory and omit `--revised`. This reproduces saved assignments; it does not regenerate questions or recover the unavailable split-generation code.

## Diagnostics

```bash
.venv/bin/python -m scripts.analyze_experiment --config configs/manual_review_v1_rerun.json --kind gold
.venv/bin/python -m scripts.analyze_experiment --config configs/manual_review_v1_rerun.json --kind matrices
.venv/bin/python -m scripts.analyze_experiment --config configs/manual_review_v1_rerun.json --kind thresholds
```

Diagnostics default to development and write to `diagnostics/<split>/<kind>/`. Gold/matrix inspection can select another split with `--split`; threshold advice is restricted to development. Matrix and threshold diagnostics require higher-is-better scores. These exports do not automatically change the search config.

## Manual review

```bash
.venv/bin/python -m scripts.manual_review.prefilter --config configs/manual_review_v1_rerun.json --split validation
.venv/bin/python -m scripts.manual_review.review --config configs/manual_review_v1_rerun.json --split validation
```

Prefiltering writes four category CSVs under `manual_review/<split>/`, including headers for empty categories. Groups are based on predicted/gold set relationships; they are not semantic explanations by themselves. Interactive review opens source passages, resumes earlier labels and saves decisions atomically. It stops the local browser server on exit. Review annotations do not modify the experiment gold or winner.

The browser in `tools/chunk_browser/` is an AI-generated auxiliary tool, excluded from assessment of the Python code's authorship style. It supports inspection, not numerical retrieval or evaluation.

## Prepare new representations

```bash
.venv/bin/python -m scripts.preparation.representations --config configs/prepare_representations.example.json
```

The TF-IDF example creates new embeddings and a cosine matrix in `artifacts/representations/new_tfidf/`. It refuses an existing output directory. Its `representations.json` contains paths for a new experiment config. Available methods are `TF_IDF`, `SENTENCE_BERT` and `RETRIEVAL_BI_ENCODER`; similarities are `cosine`, `dot` and `euclidean`.

The pinned neural example is:

```bash
.venv/bin/python -m scripts.preparation.representations --config configs/prepare_neural.example.json
```

Both examples encode the frozen source questions. Experiments select their own question rows by ID. Neural preparation may download weights when they are absent locally. A model entry can supply `model_name_or_path` and an immutable `revision`; a preserved local snapshot directory is also supported. Metadata records the requested model/revision, sequence limit, E5 prefixes and normalization setting.

Changing chunks, questions, annotations or representations requires a new config and output directory. Such a change is a new experiment, not reproduction of the reported result.

## Representation and data provenance

The reproducible experiment inputs are the three retained cosine matrices and their explicit question/chunk ID arrays. Experiment manifests record their paths. Regenerating neural representations is a separate operation and may not reproduce them bit for bit.

| Encoder | Local snapshot available on 3 October 2026 | Snapshot sequence limit |
| --- | --- | ---: |
| `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | `e8f8c211226b894fcb81acc59f3b34ba3efd5f42` | 128 tokens |
| `intfloat/multilingual-e5-base` | `d128750597153bb5987e10b1c3493a34e5a4502a` | 512 tokens |

These identifiers and limits were read from locally cached model snapshots. Their presence now does not prove that the historical cached matrices were created from these exact snapshots. The retained historical artifacts do not record immutable model revisions or per-text truncation logs. Do not label these values as established retrospective provenance without additional records or vector regeneration and comparison.

The preparation code fits TF-IDF only on the chunk collection, using lowercase word unigrams, bigrams and trigrams with no sublinear term-frequency scaling. Questions are transformed using that fitted vocabulary. E5 prefixes question text with `query: ` and evidence text with `passage: `. Neural embeddings are not normalized in advance; cosine similarity handles vector norms.

For future neural preparation, provide `model_name_or_path` and an immutable `revision` in the model config. New preparation outputs record the requested revision and effective maximum sequence length. Passing a preserved local snapshot directory is also supported. Archive the model files and preparation outputs if future regeneration must be independent of model-host changes.

Question generation used GPT-5.5 Sol support and author review according to the project README. Frozen questions, annotations and split IDs can be replayed, but a complete generation-prompt log, independently documented review protocol and original revised random-split source are not retained. The new replay utility makes no claim to recreate those missing steps.

### Verified reconstruction

The local snapshots above were used offline to encode all 720 questions and 201 chunks. TF-IDF reproduced its cached cosine matrix exactly. Sentence-BERT differed by at most 6.855e-7 and E5 by at most 1.312e-6 in absolute cosine similarity. The selected-setting summaries checked during that separate reconstruction remained unchanged. This demonstrates a usable pinned reconstruction, while preserving the distinction from an unavailable historical preparation log.

The current token audit includes special tokens and E5 prefixes. All questions fit the respective limits (maximum 38 tokens for Sentence-BERT and 41 for E5). Sentence-BERT truncates 35 of 201 chunks (maximum untruncated length 347 tokens); E5 truncates none (maximum 349 tokens). This is a plausible influence on model comparison, not an isolated causal explanation.

`configs/prepare_neural.example.json` specifies the verified public model IDs and immutable revisions for new preparation. The verification used the already-cached local snapshot directories and made no model downloads.
