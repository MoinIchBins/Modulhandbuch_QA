import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


# ----------------------------
# Configuration
# ----------------------------

RESULTS_DIR = Path(
    "data/produced_v2/selector_experiments/dev_threshold_v1"
)

OUTPUT_DIR = RESULTS_DIR / "comparison"

METHOD = "threshold"
X_PARAMETER = "threshold"

# Metrics available:
# overall_f1
# overall_precision
# overall_recall
# exact_match
# micro_f1
# answerable_f1
# answerable_precision
# answerable_recall
# zero_gold_abstention_rate
# empty_selection_rate
# average_selected_chunks

TABLE_METRICS = [
    "overall_f1",
    "answerable_precision",
    "answerable_recall",
    "answerable_f1",
    "zero_gold_abstention_rate",
    "empty_selection_rate",
    "average_selected_chunks",
]

PLOT_METRICS = [
    "overall_f1",
    "zero_gold_abstention_rate",
    "answerable_recall",
]

# Metric used to choose the best configuration
BEST_CONFIG_METRIC = "overall_f1"


# ----------------------------
# Helpers
# ----------------------------

def mean_metric(rows, metric):
    if not rows:
        return None

    return sum(row[metric] for row in rows) / len(rows)


def load_evaluations():
    rows = []

    for path in RESULTS_DIR.glob("*_evaluation.json"):
        with path.open("r", encoding="utf-8") as file:
            result = json.load(file)

        experiment = result["experiment"]

        if experiment["method"] != METHOD:
            continue

        if X_PARAMETER not in experiment:
            continue

        summary = result["summary"]
        per_question = result["per_question"]

        answerable = [
            row
            for row in per_question
            if len(row["gold_chunk_ids"]) > 0
        ]

        rows.append(
            {
                "representation": experiment["representation"],
                X_PARAMETER: experiment[X_PARAMETER],

                "overall_f1": summary["mean_question_f1"],
                "overall_precision": summary["mean_question_precision"],
                "overall_recall": summary["mean_question_recall"],
                "exact_match": summary["exact_match_rate"],
                "micro_f1": summary["micro_f1"],

                "answerable_precision": mean_metric(
                    answerable, "precision"
                ),
                "answerable_recall": mean_metric(
                    answerable, "recall"
                ),
                "answerable_f1": mean_metric(
                    answerable, "f1"
                ),

                "zero_gold_abstention_rate": summary[
                    "zero_gold_abstention_rate"
                ],
                "empty_selection_rate": summary[
                    "empty_selection_rate"
                ],
                "average_selected_chunks": summary[
                    "average_selected_chunks"
                ],
            }
        )

    return pd.DataFrame(rows)


def save_full_table(df):
    columns = [
        "representation",
        X_PARAMETER,
        *TABLE_METRICS,
    ]

    table = (
        df[columns]
        .sort_values(["representation", X_PARAMETER])
    )

    table.to_csv(
        OUTPUT_DIR / f"{METHOD}_comparison.csv",
        index=False,
    )

    print(f"\n{METHOD} comparison\n")
    print(table.round(4).to_string(index=False))


def save_best_configs(df):
    best_rows = []

    for representation, group in df.groupby("representation"):
        best = group.loc[group[BEST_CONFIG_METRIC].idxmax()]
        best_rows.append(best)

    best_df = pd.DataFrame(best_rows)

    columns = [
        "representation",
        X_PARAMETER,
        *TABLE_METRICS,
    ]

    best_df = (
        best_df[columns]
        .sort_values("representation")
        .reset_index(drop=True)
    )

    best_df.to_csv(
        OUTPUT_DIR / f"{METHOD}_best_configs.csv",
        index=False,
    )

    print("\nBest configuration per representation")
    print(f"(selected by {BEST_CONFIG_METRIC})\n")
    print(best_df.round(4).to_string(index=False))


def plot_metrics_by_representation(df):
    if not PLOT_METRICS:
        return

    for representation, group in df.groupby("representation"):
        group = group.sort_values(X_PARAMETER)

        fig, ax = plt.subplots(figsize=(8, 5))

        for metric in PLOT_METRICS:
            ax.plot(
                group[X_PARAMETER],
                group[metric],
                marker="o",
                label=metric,
            )

        ax.set_xlabel(X_PARAMETER.replace("_", " ").title())
        ax.set_ylabel("Score")
        ax.set_title(
            f"{representation}: {METHOD.replace('_', ' ')} comparison"
        )
        ax.legend()
        ax.grid(alpha=0.25)

        fig.tight_layout()

        fig.savefig(
            OUTPUT_DIR / f"{representation}_{METHOD}_metrics.png",
            dpi=300,
        )

        plt.close(fig)

def plot_f1_comparison(df):
    fig, ax = plt.subplots(figsize=(8, 5))

    for representation, group in df.groupby("representation"):
        group = group.sort_values(X_PARAMETER)

        ax.plot(
            group[X_PARAMETER],
            group["overall_f1"],
            marker="o",
            label=representation,
        )

    ax.set_xlabel(X_PARAMETER.replace("_", " ").title())
    ax.set_ylabel("Mean F1")
    ax.set_title(
        f"F1 comparison across representations"
    )
    ax.legend()
    ax.grid(alpha=0.25)

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR / f"{METHOD}_f1_all_representations.png",
        dpi=300,
    )

    plt.close(fig)

def main():
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    df = load_evaluations()

    if df.empty:
        raise ValueError(
            f"No '{METHOD}' evaluation files found in {RESULTS_DIR}"
        )

    requested_metrics = (
        TABLE_METRICS
        + PLOT_METRICS
        + [BEST_CONFIG_METRIC]
    )

    missing_metrics = [
        metric
        for metric in set(requested_metrics)
        if metric not in df.columns
    ]

    if missing_metrics:
        raise ValueError(
            f"Unknown metrics: {missing_metrics}"
        )

    save_full_table(df)
    save_best_configs(df)
    plot_metrics_by_representation(df)
    plot_f1_comparison(df)

    print(f"\nResults saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
