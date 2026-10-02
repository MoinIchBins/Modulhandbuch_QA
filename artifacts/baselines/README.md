# Baselines

This folder contains three fixed reference baselines for the retrieval evaluation.

They are **not selector candidates** and must not be tuned on validation or test.

All commands below assume they are run from the project root.

## Baselines

1. **Random top-1**

   * Selects exactly one retrieval chunk uniformly at random for every question.
   * Uses 100 fixed seeds (`0` to `99`).
   * Reports the mean and standard deviation across the 100 runs.

2. **Most-frequent development answer**

   * Finds the most frequent **non-empty exact gold chunk set** in the development split.
   * The selected set is frozen once in `dev_reference/most_frequent_answer.json`.
   * The same frozen set is then returned for every validation or test question.
   * It is never recomputed from validation or test.

3. **Always abstain**

   * Returns an empty chunk set for every question.

## Project paths used by the scripts

The baseline scripts use the following existing project files:

```text
data/frozen/qa_mapping_merged.jsonl
data/frozen/split/development_question_ids.json
data/frozen/split/validation_question_ids.json
data/frozen/split/test_question_ids.json
artifacts/similarity_matrices/retrieval_bi_encoder/chunk_ids.json
```

The scripts also reuse the existing evaluator:

```python
from scripts.mapping_evaluator import QAMappingEvaluator
```

The baseline folder is:

```text
artifacts/baselines/
```

Programs live in `scripts/baselines/`. Definitions and generated outputs remain here. Both `validation_v1/` and `test_v1/` are already preserved.

Artifact structure (validation expanded):

```text
artifacts/baselines/
├── README.md
├── baseline_definitions.json
├── dev_reference/
│   └── most_frequent_answer.json
├── test_v1/
└── validation_v1/
    ├── always_abstain_evaluation.json
    ├── always_abstain_predictions.jsonl
    ├── baseline_f1_comparison.png
    ├── most_frequent_dev_answer_evaluation.json
    ├── most_frequent_dev_answer_predictions.jsonl
    ├── random_top1_runs.jsonl
    ├── random_top1_summary.json
    ├── summary.csv
    └── summary.jsonl
```

---

## 1. Freeze the development-derived baseline

This step derives the most-frequent non-empty answer set from the **development split only**.

Run:

```bash
python scripts/baselines/freeze_dev_reference.py
```

It creates:

```text
artifacts/baselines/dev_reference/most_frequent_answer.json
```

The script intentionally refuses to overwrite an existing frozen reference.

If this file already exists, as it currently does, **do not rerun this step** unless you intentionally want to rebuild the complete experiment from scratch.

---

## 2. Evaluate the baselines on validation

Run:

```bash
python scripts/baselines/run_baselines.py validation
```

This evaluates all three baselines only against:

```text
data/frozen/split/validation_question_ids.json
```

and writes the results to:

```text
artifacts/baselines/validation_v1/
```

Expected outputs:

```text
artifacts/baselines/validation_v1/
├── random_top1_runs.jsonl
├── random_top1_summary.json
├── most_frequent_dev_answer_predictions.jsonl
├── most_frequent_dev_answer_evaluation.json
├── always_abstain_predictions.jsonl
├── always_abstain_evaluation.json
├── summary.csv
└── summary.jsonl
```

### Preserving existing runs

Both run directories contain research evidence. Do not delete them to rerun commands. For a new reproduction, redirect the output directory in `scripts/baselines/run_baselines.py` to a new location and update the plotting/comparison input paths accordingly. Preserve definitions, seeds, and the frozen development reference.

---

## 3. Plot the validation baselines

After the validation baseline run has completed, create the baseline-only F1 plot:

```bash
python scripts/baselines/plot_baselines.py validation
```

This reads:

```text
artifacts/baselines/validation_v1/summary.csv
```

and creates:

```text
artifacts/baselines/validation_v1/baseline_f1_comparison.png
```

---

## 4. Compare the validation winner with the baselines

The winner selected from the frozen validation finalists is:

```text
E5 + top_k_threshold
top_k = 1
threshold = 0.84
```

Its validation evaluation file is:

```text
artifacts/experiments/base/outputs/validation/finalists/e5_top_k_threshold_top_k_1_threshold_0.84_evaluation.json
```

Run exactly:

```bash
python scripts/baselines/compare_with_system.py \
    validation \
    artifacts/experiments/base/outputs/validation/finalists/e5_top_k_threshold_top_k_1_threshold_0.84_evaluation.json
```

Do **not** pass the finalist summary file:

```text
artifacts/experiments/base/outputs/validation/finalists/summary.jsonl
```

`compare_with_system.py` expects the evaluation JSON of the **single frozen system**, not the combined finalist summary.

The comparison command creates:

```text
artifacts/baselines/validation_v1/system_vs_baselines.csv
artifacts/baselines/validation_v1/system_vs_baselines.png
```

The validation baselines are contextual references only. They do not participate in model selection and must not be used to retune the winner.

---

## 5. Final system before test evaluation

After validation, the frozen final retrieval configuration is:

```text
representation: e5
selector:       top_k_threshold
top_k:          1
threshold:      0.84
```

These values must remain unchanged for the test evaluation.

Validation has already been used to select this system. The test split must therefore be used only for final generalization measurement, not for further selection or tuning.

---

## 6. Evaluate the baselines on test

Only run this after the final E5 configuration above has been frozen and the test stage is ready.

Run:

```bash
python scripts/baselines/run_baselines.py test --confirm-test
```

The explicit `--confirm-test` flag is intentional. It prevents accidental test evaluation.

This evaluates the baselines only against:

```text
data/frozen/split/test_question_ids.json
```

and creates:

```text
artifacts/baselines/test_v1/
```

with the same output structure as `validation_v1`.

---

## 7. Plot the test baselines

After the test baseline evaluation:

```bash
python scripts/baselines/plot_baselines.py test
```

This creates:

```text
artifacts/baselines/test_v1/baseline_f1_comparison.png
```

---

## 8. Compare the final test system with the baselines

First run the **single frozen final retrieval configuration** on the test split and save its evaluation JSON.

The final test evaluation is already preserved in `artifacts/experiments/base/outputs/test/winner/`.

For a new comparison output (redirect output paths first), run:

```bash
python scripts/baselines/compare_with_system.py \
    test \
    artifacts/experiments/base/outputs/test/winner/e5_top_k_threshold_top_k_1_threshold_0.84_evaluation.json
```

The second argument must be the `_evaluation.json` for:

```text
E5 + top_k_threshold + top_k=1 + threshold=0.84
```

The command will create:

```text
artifacts/baselines/test_v1/system_vs_baselines.csv
artifacts/baselines/test_v1/system_vs_baselines.png
```

The path above identifies the existing frozen test evaluation.

---

## Reporting protocol

The baselines have a different role from the selector experiments.

### Development

Use development to tune representations and selectors and to freeze finalist hyperparameters.

Do not add the three baselines to the development hyperparameter-sweep plots. The baselines are not candidate selectors.

### Validation

Use validation to choose among the already frozen finalists.

The baseline comparison may be reported as contextual evidence, but it must not influence hyperparameter tuning.

Current validation retrieval winner:

```text
E5 + top_k_threshold + top_k=1 + threshold=0.84
```

### Test

Evaluate only the single frozen winner on the test split reserved within the selection workflow.

The main final comparison should contain:

```text
Final E5 retrieval system
Random top-1
Most-frequent development answer
Always abstain
```

The test comparison is the most important place to report the baselines because it shows whether the final question-dependent retrieval system outperforms trivial or dataset-frequency-based strategies on unseen data.

---

## Recommended paper usage

Use the baseline results in three places:

1. **Methodology**

   * Define all three baselines.
   * State that the most-frequent answer is derived from development only.
   * State that random top-1 uses 100 fixed random seeds.

2. **Validation / model selection**

   * Optionally report the validation baseline comparison as contextual reference.
   * Make clear that the baselines did not participate in tuning or finalist selection.

3. **Final test evaluation**

   * Prominently compare the frozen final E5 system with all three baselines.
   * Report random top-1 as mean ± standard deviation.
   * Use the same evaluation metrics as for the retrieval system.

Do not mix the baseline results into the selector hyperparameter-search plots.

---

## Short command reference

### Development reference

Already frozen if this file exists:

```text
artifacts/baselines/dev_reference/most_frequent_answer.json
```

To create it from scratch:

```bash
python scripts/baselines/freeze_dev_reference.py
```

### Validation

```bash
python scripts/baselines/run_baselines.py validation

python scripts/baselines/plot_baselines.py validation

python scripts/baselines/compare_with_system.py \
    validation \
    artifacts/experiments/base/outputs/validation/finalists/e5_top_k_threshold_top_k_1_threshold_0.84_evaluation.json
```

### Test

```bash
python scripts/baselines/run_baselines.py test --confirm-test

python scripts/baselines/plot_baselines.py test
```

Then compare the preserved final test evaluation, with outputs redirected:

```bash
python scripts/baselines/compare_with_system.py \
    test \
    artifacts/experiments/base/outputs/test/winner/e5_top_k_threshold_top_k_1_threshold_0.84_evaluation.json
```

## Current system comparison

`system_vs_baselines.csv` and its plot use the promoted base winner (threshold 0.84). Reference baseline predictions and scores are unchanged. Prior comparison files are retained in the first-run archive.
