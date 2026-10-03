import argparse
import csv
import json
import random
import statistics
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.mapping_evaluator import QAMappingEvaluator


GOLD_PATH = PROJECT_ROOT / "data/frozen/qa_mapping_merged.jsonl"
CHUNK_IDS_PATH = (
    PROJECT_ROOT
    / "artifacts/similarity_matrices/retrieval_bi_encoder/chunk_ids.json"
)
SPLIT_DIR = PROJECT_ROOT / "data/frozen/split"

BASELINE_DIR = Path(__file__).resolve().parents[2] / "artifacts/baselines"
DEFINITIONS_PATH = BASELINE_DIR / "baseline_definitions.json"
FREQUENT_ANSWER_PATH = BASELINE_DIR / "dev_reference/most_frequent_answer.json"

REPORT_METRICS = [
    "mean_question_f1",
    "exact_match_rate",
    "mean_question_precision",
    "mean_question_recall",
    "micro_f1",
    "average_selected_chunks",
    "empty_selection_rate",
    "zero_gold_abstention_rate",
]


def load_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_json(path, data):
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def save_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def make_predictions(question_ids, chunk_ids):
    return [
        {"question_id": question_id, "chunk_ids": list(chunk_ids)}
        for question_id in question_ids
    ]


def make_random_predictions(question_ids, chunk_ids, seed):
    rng = random.Random(seed)

    return [
        {
            "question_id": question_id,
            "chunk_ids": [rng.choice(chunk_ids)],
        }
        for question_id in question_ids
    ]


def aggregate_random_runs(run_summaries):
    result = {
        "baseline": "random_top1",
        "run_count": len(run_summaries),
    }

    for metric in REPORT_METRICS:
        values = [row[metric] for row in run_summaries]
        result[metric] = statistics.mean(values)
        result[f"{metric}_std"] = (
            statistics.stdev(values) if len(values) > 1 else 0.0
        )

    return result


def compact_summary(name, summary):
    row = {"baseline": name}

    for metric in REPORT_METRICS:
        row[metric] = summary[metric]
        row[f"{metric}_std"] = 0.0

    return row


def save_summary_csv(path, rows):
    fieldnames = ["baseline", "run_count"]

    for metric in REPORT_METRICS:
        fieldnames.extend([metric, f"{metric}_std"])

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run_deterministic_baseline(
    name,
    predicted_chunks,
    question_ids,
    evaluator,
    output_dir,
):
    predictions = make_predictions(question_ids, predicted_chunks)
    result = evaluator.eval(predictions, question_ids=question_ids)

    save_jsonl(
        output_dir / f"{name}_predictions.jsonl",
        predictions,
    )
    save_json(
        output_dir / f"{name}_evaluation.json",
        result,
    )

    return result["summary"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "split",
        choices=["validation", "test"],
        help="Evaluate baselines on validation or test only.",
    )
    parser.add_argument(
        "--confirm-test",
        action="store_true",
        help="Required before evaluating the untouched test split.",
    )
    args = parser.parse_args()

    if args.split == "test" and not args.confirm_test:
        raise SystemExit(
            "Test evaluation is intentionally protected. "
            "Re-run with --confirm-test only after the final system is frozen."
        )

    if not FREQUENT_ANSWER_PATH.exists():
        raise FileNotFoundError(
            "Freeze the development-derived baseline first:\n"
            "python scripts/baselines/freeze_dev_reference.py"
        )

    print(f"\nRunning baselines on {args.split} split")

    split_ids = load_json(SPLIT_DIR / f"{args.split}_question_ids.json")
    chunk_ids = load_json(CHUNK_IDS_PATH)
    definitions = load_json(DEFINITIONS_PATH)
    frequent_answer = load_json(FREQUENT_ANSWER_PATH)["chunk_ids"]

    print(f"Loaded {len(split_ids)} {args.split} questions")
    print(f"Loaded {len(chunk_ids)} retrieval chunks")
    print(
        "Most-frequent dev answer contains "
        f"{len(frequent_answer)} chunk(s)"
    )

    version = "validation_v1" if args.split == "validation" else "test_v1"
    output_dir = BASELINE_DIR / version
    output_dir.mkdir(parents=True, exist_ok=False)

    print(f"Writing results to {output_dir}")

    evaluator = QAMappingEvaluator(GOLD_PATH)

    # 1. Random top-1: evaluate the same fixed set of seeds every time.
    seeds = definitions["random_top1"]["seeds"]
    random_runs = []

    print(f"\n[1/3] Random top-1 ({len(seeds)} runs)")

    for run_number, seed in enumerate(seeds, start=1):
        predictions = make_random_predictions(split_ids, chunk_ids, seed)
        result = evaluator.eval(predictions, question_ids=split_ids)

        random_runs.append(
            {
                "baseline": "random_top1",
                "seed": seed,
                **result["summary"],
            }
        )

        if run_number == 1 or run_number % 10 == 0 or run_number == len(seeds):
            print(f"  completed {run_number}/{len(seeds)} runs")

    random_summary = aggregate_random_runs(random_runs)
    print(
        "  random top-1 mean F1: "
        f"{random_summary['mean_question_f1']:.4f} "
        f"± {random_summary['mean_question_f1_std']:.4f}"
    )

    save_jsonl(
        output_dir / "random_top1_runs.jsonl",
        random_runs,
    )
    save_json(
        output_dir / "random_top1_summary.json",
        random_summary,
    )

    # 2. Always return the frozen most-frequent non-empty dev answer set.
    print("\n[2/3] Most-frequent development answer")

    frequent_summary = run_deterministic_baseline(
        "most_frequent_dev_answer",
        frequent_answer,
        split_ids,
        evaluator,
        output_dir,
    )

    print(f"  F1: {frequent_summary['mean_question_f1']:.4f}")

    # 3. Always abstain.
    print("\n[3/3] Always abstain")

    abstain_summary = run_deterministic_baseline(
        "always_abstain",
        [],
        split_ids,
        evaluator,
        output_dir,
    )

    print(f"  F1: {abstain_summary['mean_question_f1']:.4f}")

    summary_rows = [
        random_summary,
        compact_summary(
            "most_frequent_dev_answer",
            frequent_summary,
        ),
        compact_summary(
            "always_abstain",
            abstain_summary,
        ),
    ]

    save_summary_csv(
        output_dir / "summary.csv",
        summary_rows,
    )
    save_jsonl(
        output_dir / "summary.jsonl",
        summary_rows,
    )

    print(f"\nFinished. Baseline results on {args.split}:\n")

    for row in summary_rows:
        std = row.get("mean_question_f1_std", 0.0)
        print(
            f"{row['baseline']:28} "
            f"F1={row['mean_question_f1']:.4f} "
            f"± {std:.4f}"
        )


if __name__ == "__main__":
    main()
