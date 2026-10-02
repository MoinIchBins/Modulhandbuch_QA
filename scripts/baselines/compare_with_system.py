import argparse
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt


BASELINE_DIR = Path(__file__).resolve().parents[2] / "artifacts/baselines"


def load_baselines(path):
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def load_system_summary(path):
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if "summary" in data:
        return data["summary"]

    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "split",
        choices=["validation", "test"],
    )
    parser.add_argument(
        "system_evaluation",
        type=Path,
        help="Evaluation JSON for the frozen retrieval system.",
    )
    args = parser.parse_args()

    version = "validation_v1" if args.split == "validation" else "test_v1"
    output_dir = BASELINE_DIR / version
    baseline_path = output_dir / "summary.csv"

    print(f"\nComparing frozen system with {args.split} baselines")
    print(f"Reading baselines from {baseline_path}")
    print(f"Reading system evaluation from {args.system_evaluation}")

    baseline_rows = load_baselines(baseline_path)
    system = load_system_summary(args.system_evaluation)

    print(f"Loaded {len(baseline_rows)} baselines")

    rows = [
        {
            "system": "final_retrieval_system",
            "mean_question_f1": float(system["mean_question_f1"]),
            "mean_question_f1_std": 0.0,
            "exact_match_rate": float(system["exact_match_rate"]),
            "mean_question_precision": float(system["mean_question_precision"]),
            "mean_question_recall": float(system["mean_question_recall"]),
            "zero_gold_abstention_rate": float(
                system["zero_gold_abstention_rate"]
            ),
            "average_selected_chunks": float(system["average_selected_chunks"]),
        }
    ]

    for row in baseline_rows:
        rows.append(
            {
                "system": row["baseline"],
                "mean_question_f1": float(row["mean_question_f1"]),
                "mean_question_f1_std": float(
                    row["mean_question_f1_std"]
                ),
                "exact_match_rate": float(row["exact_match_rate"]),
                "mean_question_precision": float(
                    row["mean_question_precision"]
                ),
                "mean_question_recall": float(row["mean_question_recall"]),
                "zero_gold_abstention_rate": float(
                    row["zero_gold_abstention_rate"]
                ),
                "average_selected_chunks": float(
                    row["average_selected_chunks"]
                ),
            }
        )

    rows.sort(
        key=lambda row: row["mean_question_f1"],
        reverse=True,
    )

    csv_path = output_dir / "system_vs_baselines.csv"

    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    labels = [row["system"] for row in rows]
    values = [row["mean_question_f1"] for row in rows]
    errors = [row["mean_question_f1_std"] for row in rows]

    fig, ax = plt.subplots(figsize=(9, 5))

    bars = ax.barh(
        labels,
        values,
        xerr=errors,
        capsize=4,
    )

    ax.bar_label(
        bars,
        labels=[f"{value:.3f}" for value in values],
        padding=3,
    )

    ax.invert_yaxis()
    ax.set_title(f"Frozen System vs {args.split.title()} Baselines")
    ax.set_xlabel("Overall Question-Level F1")
    ax.set_xlim(0, max(0.7, max(values) + 0.05))

    fig.tight_layout()
    fig.savefig(
        output_dir / "system_vs_baselines.png",
        dpi=200,
    )
    plt.close(fig)

    print(f"Saved comparison table to {csv_path}")
    print(f"Saved comparison plot to {output_dir / 'system_vs_baselines.png'}")


if __name__ == "__main__":
    main()
