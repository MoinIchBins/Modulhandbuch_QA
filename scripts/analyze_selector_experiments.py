import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


# ----------------------------
# Configuration
# ----------------------------

RESULTS_DIR = Path(
    "artifacts/experiments/development/dev_threshold_v1"
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

# Keep this short to avoid graph spam.
PLOT_METRICS = [
    "overall_f1",
    "zero_gold_abstention_rate",
    "answerable_recall",
]


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

        row = {
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

        rows.append(row)

    return pd.DataFrame(rows)


def save_table(df):
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


def print_best_configs(df):
    print("\nBest configuration per representation")
    print("(selected by overall_f1)\n")

    for representation, group in df.groupby("representation"):
        best = group.loc[group["overall_f1"].idxmax()]

        print(
            f"{representation:15} "
            f"{X_PARAMETER}={best[X_PARAMETER]:.4f}  "
            f"F1={best['overall_f1']:.4f}  "
            f"answerable_recall={best['answerable_recall']:.4f}  "
            f"abstention={best['zero_gold_abstention_rate']:.4f}"
        )


def plot_metrics(df):
    if not PLOT_METRICS:
        return

    fig, ax = plt.subplots(figsize=(9, 5))

    line_styles = ["-", "--", ":", "-."]

    for representation, group in df.groupby("representation"):
        group = group.sort_values(X_PARAMETER)

        for index, metric in enumerate(PLOT_METRICS):
            ax.plot(
                group[X_PARAMETER],
                group[metric],
                marker="o",
                linestyle=line_styles[index % len(line_styles)],
                label=f"{representation} — {metric}",
            )

    ax.set_xlabel(X_PARAMETER.replace("_", " ").title())
    ax.set_ylabel("Score")
    ax.set_title(
        f"{METHOD.replace('_', ' ').title()} development comparison"
    )
    ax.legend()
    ax.grid(alpha=0.25)

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR / f"{METHOD}_metrics.png",
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

    missing_metrics = [
        metric
        for metric in set(TABLE_METRICS + PLOT_METRICS)
        if metric not in df.columns
    ]

    if missing_metrics:
        raise ValueError(
            f"Unknown metrics: {missing_metrics}"
        )

    save_table(df)
    print_best_configs(df)
    plot_metrics(df)

    print(f"\nResults saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
