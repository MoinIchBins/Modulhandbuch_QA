# QA Evidence Retrieval Experiments

Retrieve evidence passages for questions about a German examination regulation, with an option to return no evidence. The project compares TF-IDF, multilingual Sentence-BERT and multilingual E5 using four chunk-selection rules. It evaluates evidence sets; it does not generate answers.

The primary evaluation uses **`configs/base.json`** and the frozen dataset: **720 questions** (600 answerable, 120 zero-gold), **201 chunks**, and grouped development/validation/test partitions of **432/144/144**. Its frozen winner is **E5 top-1 with absolute threshold `0.84`**. These results are produced by the current configuration-driven pipeline.

| Dataset / protocol | Validation-selected winner | Validation Q-F1 | Test Q-F1 | Test exact match | Test micro-F1 |
| --- | --- | ---: | ---: | ---: | ---: |
| Frozen, 720 questions (`base`) | E5 top-1, threshold `0.84` | 0.604167 | 0.483796 | 0.479167 | 0.500000 |
| Reviewed follow-up, 710 questions (`manual_review_v1`) | E5 top-1, relative margin `0.003025` | 0.546948 | 0.650235 | 0.640845 | 0.703390 |

The frozen winner achieves development Q-F1 **0.647377** and 69 exact matches among 144 test questions. Its saved results are under [`artifacts/experiments/base/`](artifacts/experiments/base/); selection is recorded in [`validation/frozen_winner.json`](artifacts/experiments/base/validation/frozen_winner.json) and test metrics in [`test/summary.jsonl`](artifacts/experiments/base/test/summary.jsonl).

The follow-up excludes ten questions and uses a question-level split of 426/142/142. Dataset membership and splitting differ, so its higher test score is not a controlled improvement over the frozen evaluation. The paper reports both protocols separately.

The full guide is [pipeline.md](pipeline.md), including configuration, staged execution, dataset replay, model preparation and provenance.

## Setup

Use **Python 3.11** and run commands from the repository root:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install --requirement requirements.txt
.venv/bin/python -m scripts.run_experiment --config configs/base.json --stage check
```

The single requirements file includes experiment, model-preparation and style-check dependencies. Installing the packages does not download model weights; model preparation may download weights if the requested snapshot is not cached. Experiments use the retained cosine matrices.

## Reproduce the paper's pipeline

Published outputs already exist. Copy the config to a new run before executing it:

```bash
.venv/bin/python -m scripts.copy_experiment --config configs/base.json --destination configs/base_rerun.json --name base_rerun --output-dir artifacts/experiments/base_rerun
.venv/bin/python -m scripts.run_experiment --config configs/base_rerun.json --confirm-test
```

Choose another name and directory if those paths exist. A complete run performs development search, validation selection, test evaluation, baselines and report generation. For the frozen protocol, expected counts are 157 coarse settings, 4,227 fine settings, twelve development family winners, five validation candidates and one test winner. Retaining every setting's predictions can require gigabytes of disk space.

Completed stages cannot be overwritten. Changed configuration or environment requires a new output directory. Use a new run when changing source code or input data; their contents are no longer tracked by the experiment manifest. Existing questions have already been evaluated; reproducing their results is not a new independent test sample.

To reproduce the separate follow-up, copy `configs/manual_review_v1.json` into its own new configuration and output directory. Both protocols use the same coarse grids, local fine search with 201 points, and five validation candidates. Each evaluates 4,227 fine settings on these datasets.

## Files

```text
README.md                         # setup and main reproduction command
pipeline.md                       # complete pipeline and preparation guide
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
paper/                            # LaTeX source, bibliography and ACL style
literature/                       # reference papers and reading notes
```

The scripts use Python namespace packages, so empty `__init__.py` files are not needed. Use the module commands above rather than executing nested script files directly.

## Tests and code style

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m black --check --line-length 79 scripts tests
.venv/bin/python -m pycodestyle scripts tests
```

The twelve tests cover the core workflow, scoring, ranking, refinement, input validation and dataset membership. Browser simulation and peripheral utility tests are outside this suite.

## Paper and provenance

Build the multi-file LaTeX project with `latexmk` from `paper/`:

```bash
cd paper
latexmk -pdf -outdir=build paper.tex
```

The PDF is `paper/build/paper.pdf`. LaTeX tooling is separate from the Python requirements.

Questions and gold evidence sets were created with GPT-5.5 Sol support and manually reviewed by the author; no independent second annotation was conducted. The optional chunk browser was AI-generated. It supports manual passage inspection and is separate from the Python retrieval implementation; it does not calculate rankings or experiment scores.

