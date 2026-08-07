import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


RESULTS_DIR = Path(
    "data/produced_v2/selector_experiments/dev_top_k_v1"
)

OUTPUT_DIR = RESULTS_DIR / "comparison"


def load_evaluations():
    rows = []

    for path in RESULTS_DIR.glob("*_evaluation.json"):
        with path.open("r", encoding="utf-8") as file:
            result = json.load(file)

        experiment = result["experiment"]

        if experiment["method"] != "top_k":
            continue

        per_question = result["per_question"]
        summary = result["summary"]

        answerable = [
            row
            for row in per_question
            if len(row["gold_chunk_ids"]) > 0
        ]

        one_chunk = [
            row
            for row in answerable
            if len(row["gold_chunk_ids"]) == 1
        ]

        two_chunk = [
            row
            for row in answerable
            if len(row["gold_chunk_ids"]) == 2
        ]

        rows.append(
            {
                "representation": experiment["representation"],
                "top_k": experiment["top_k"],

                # Complete selector performance
                "overall_f1": summary["mean_question_f1"],
                "micro_f1": summary["micro_f1"],

                # Retrieval quality on answerable questions
                "answerable_precision": mean_metric(
                    answerable, "precision"
                ),
                "answerable_recall": mean_metric(
                    answerable, "recall"
                ),
                "answerable_f1": mean_metric(
                    answerable, "f1"
                ),

                # Performance by required gold-set size
                "one_chunk_f1": mean_metric(
                    one_chunk, "f1"
                ),
                "two_chunk_f1": mean_metric(
                    two_chunk, "f1"
                ),
                "two_chunk_recall": mean_metric(
                    two_chunk, "recall"
                ),
            }
        )

    return pd.DataFrame(rows)


def mean_metric(rows, metric):
    if not rows:
        return None

    return sum(row[metric] for row in rows) / len(rows)


def save_table(df):
    table = df.sort_values(
        ["representation", "top_k"]
    )

    table.to_csv(
        OUTPUT_DIR / "top_k_comparison.csv",
        index=False,
    )

    print("\nTop-k comparison\n")

    print(
        table[
            [
                "representation",
                "top_k",
                "overall_f1",
                "answerable_precision",
                "answerable_recall",
                "answerable_f1",
                "one_chunk_f1",
                "two_chunk_f1",
            ]
        ].round(4).to_string(index=False)
    )


def plot_f1_by_k(df):
    fig, ax = plt.subplots(figsize=(8, 5))

    for representation, group in df.groupby("representation"):
        group = group.sort_values("top_k")

        ax.plot(
            group["top_k"],
            group["answerable_f1"],
            marker="o",
            label=representation,
        )

    ax.set_xlabel("Top-k")
    ax.set_ylabel("Mean F1")
    ax.set_title("Answerable-question F1 by top-k")
    ax.set_xticks(sorted(df["top_k"].unique()))
    ax.legend()
    ax.grid(alpha=0.25)

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR / "f1_by_top_k.png",
        dpi=300,
    )

    plt.close(fig)


def plot_best_k_by_gold_size(df):
    best_rows = (
        df.sort_values("answerable_f1", ascending=False)
        .groupby("representation", as_index=False)
        .first()
    )

    plot_data = best_rows[
        [
            "representation",
            "top_k",
            "one_chunk_f1",
            "two_chunk_f1",
        ]
    ].copy()

    labels = [
        f"{row.representation}\nk={row.top_k}"
        for row in plot_data.itertuples()
    ]

    x = range(len(plot_data))
    width = 0.35

    fig, ax = plt.subplots(figsize=(8, 5))

    ax.bar(
        [value - width / 2 for value in x],
        plot_data["one_chunk_f1"],
        width=width,
        label="1 required chunk",
    )

    ax.bar(
        [value + width / 2 for value in x],
        plot_data["two_chunk_f1"],
        width=width,
        label="2 required chunks",
    )

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)

    ax.set_ylabel("Mean F1")
    ax.set_title(
        "Best top-k result by gold-set size"
    )

    ax.legend()
    ax.grid(axis="y", alpha=0.25)

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR / "best_k_by_gold_size.png",
        dpi=300,
    )

    plt.close(fig)


def print_best_configs(df):
    print("\nBest top-k per representation\n")

    for representation, group in df.groupby("representation"):
        best = group.loc[
            group["answerable_f1"].idxmax()
        ]

        print(
            f"{representation:15} "
            f"k={int(best['top_k'])}  "
            f"F1={best['answerable_f1']:.4f}  "
            f"precision={best['answerable_precision']:.4f}  "
            f"recall={best['answerable_recall']:.4f}"
        )


def main():
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    df = load_evaluations()

    if df.empty:
        raise ValueError(
            f"No top-k evaluation files found in {RESULTS_DIR}"
        )

    save_table(df)
    print_best_configs(df)

    plot_f1_by_k(df)
    plot_best_k_by_gold_size(df)

    print(
        f"\nResults saved to: {OUTPUT_DIR}"
    )


if __name__ == "__main__":
    main()