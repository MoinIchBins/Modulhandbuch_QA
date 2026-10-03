import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt


BASELINE_DIR = Path(__file__).resolve().parents[2] / "artifacts/baselines"


def load_rows(path):
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "split",
        choices=["validation", "test"],
    )
    args = parser.parse_args()

    version = "validation_v1" if args.split == "validation" else "test_v1"
    output_dir = BASELINE_DIR / version
    summary_path = output_dir / "summary.csv"

    print(f"\nPlotting {args.split} baseline results")
    print(f"Reading {summary_path}")

    rows = load_rows(summary_path)
    print(f"Loaded {len(rows)} baseline summaries")

    rows.sort(
        key=lambda row: float(row["mean_question_f1"]),
        reverse=True,
    )

    labels = [row["baseline"] for row in rows]
    values = [float(row["mean_question_f1"]) for row in rows]
    errors = [float(row["mean_question_f1_std"]) for row in rows]

    fig, ax = plt.subplots(figsize=(8, 4))

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
    ax.set_title(f"{args.split.title()} Baselines")
    ax.set_xlabel("Overall Question-Level F1")
    ax.set_xlim(0, max(0.7, max(values) + 0.05))

    fig.tight_layout()
    fig.savefig(
        output_dir / "baseline_f1_comparison.png",
        dpi=200,
    )
    plt.close(fig)

    plot_path = output_dir / "baseline_f1_comparison.png"
    print(f"Saved plot to {plot_path}")


if __name__ == "__main__":
    main()
