import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


SUMMARY_PATH = Path(
    "artifacts/experiments/validation/validation_finalists/summary.jsonl"
)

OUTPUT_DIR = SUMMARY_PATH.parent


SORT_COLUMNS = [
    "mean_question_f1",
    "exact_match_rate",
    "mean_question_precision",
    "average_selected_chunks",
]

SORT_ASCENDING = [
    False,
    False,
    False,
    True,
]


def load_results():
    rows = []

    with SUMMARY_PATH.open("r", encoding="utf-8") as file:
        for line in file:
            rows.append(json.loads(line))

    return pd.DataFrame(rows)


def rank_results(results):
    return results.sort_values(
        SORT_COLUMNS,
        ascending=SORT_ASCENDING,
    ).reset_index(drop=True)


def make_label(row):
    parts = [
        row["representation"],
        row["method"],
    ]

    if pd.notna(row.get("top_k")):
        parts.append(f"k={int(row['top_k'])}")

    if pd.notna(row.get("threshold")):
        parts.append(f"t={row['threshold']:.4f}")

    if pd.notna(row.get("margin")):
        parts.append(f"m={row['margin']:.4f}")

    return " + ".join(parts)


def plot_ranking(results):
    labels = [
        make_label(row)
        for _, row in results.iterrows()
    ]

    fig, ax = plt.subplots(figsize=(9, 5))

    bars = ax.barh(
        labels,
        results["mean_question_f1"],
    )

    ax.bar_label(
        bars,
        labels=[
            f"{value:.3f}"
            for value in results["mean_question_f1"]
        ],
        padding=3,
    )

    ax.invert_yaxis()

    ax.set_title("Validation Ranking of Frozen Finalists")
    ax.set_xlabel("Overall Question-Level F1")
    ax.set_xlim(0, 0.7)

    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR / "validation_ranking.png",
        dpi=200,
    )

    plt.close()


def main():
    results = load_results()
    ranking = rank_results(results)

    ranking.insert(
        0,
        "rank",
        range(1, len(ranking) + 1),
    )

    ranking.to_csv(
        OUTPUT_DIR / "validation_ranking.csv",
        index=False,
    )

    plot_ranking(ranking)

    columns = [
        "rank",
        "representation",
        "method",
        "top_k",
        "threshold",
        "margin",
        "mean_question_f1",
        "exact_match_rate",
        "mean_question_precision",
        "mean_question_recall",
        "zero_gold_abstention_rate",
        "average_selected_chunks",
    ]

    columns = [
        column
        for column in columns
        if column in ranking.columns
    ]

    print("\nValidation ranking:\n")
    print(
        ranking[columns]
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()