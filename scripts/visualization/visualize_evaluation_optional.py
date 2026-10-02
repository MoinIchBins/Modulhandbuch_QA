import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


# ============================================================
# Configuration
# ============================================================

# ------------------------------------------------------------
# Recommended settings: dev_top_k_v1
# ------------------------------------------------------------
#
# RESULTS_DIR = Path(
#     "artifacts/experiments/archive/first_run/outputs/development/dev_top_k_v1"
# )
# METHOD = "top_k"
# X_PARAMETER = "top_k"
# GROUP_PARAMETER = None
#
# TABLE_METRICS = [
#     "overall_f1",
#     "answerable_precision",
#     "answerable_recall",
#     "answerable_f1",
#     "micro_f1",
# ]
#
# PLOT_METRICS = [
#     "answerable_precision",
#     "answerable_recall",
#     "answerable_f1",
# ]


# ------------------------------------------------------------
# Recommended settings: dev_threshold_v1
# / dev_threshold_refined_v1
# ------------------------------------------------------------
#
# RESULTS_DIR = Path(
#     "artifacts/experiments/archive/first_run/outputs/development/dev_threshold_v1"
# )
# METHOD = "threshold"
# X_PARAMETER = "threshold"
# GROUP_PARAMETER = None
#
# TABLE_METRICS = [
#     "overall_f1",
#     "answerable_precision",
#     "answerable_recall",
#     "answerable_f1",
#     "zero_gold_abstention_rate",
#     "empty_selection_rate",
#     "average_selected_chunks",
# ]
#
# PLOT_METRICS = [
#     "overall_f1",
#     "zero_gold_abstention_rate",
#     "answerable_recall",
# ]


# ------------------------------------------------------------
# Active settings: base validation relative-margin candidates
# ------------------------------------------------------------
RESULTS_DIR = Path(
    "artifacts/experiments/base/outputs/validation/finalists"
)

OUTPUT_DIR = RESULTS_DIR / "comparison"

METHOD = "relative_margin"
X_PARAMETER = "margin"
GROUP_PARAMETER = "top_k"

TABLE_METRICS = [
    "overall_f1",
    "overall_precision",
    "answerable_precision",
    "answerable_recall",
    "answerable_f1",
    "zero_gold_abstention_rate",
    "exact_match",
    "empty_selection_rate",
    "average_selected_chunks",
]

PLOT_METRICS = [
    "overall_f1",
]

BEST_CONFIG_SORT = [
    "overall_f1",
    "exact_match",
    "overall_precision",
    "average_selected_chunks",
]

BEST_CONFIG_ASCENDING = [
    False,
    False,
    False,
    True,
]

# Combined representation plot?
PLOT_ALL_REPRESENTATIONS = True

COMBINED_PLOT_METRIC = "overall_f1"
COMBINED_X_MODE = "raw"         # raw or normalized


# ------------------------------------------------------------
# Best-config selection
# ------------------------------------------------------------

BEST_CONFIG_SORT = [
    "overall_f1",
    "exact_match",
    "overall_precision",
    "average_selected_chunks",
]

BEST_CONFIG_ASCENDING = [
    False,
    False,
    False,
    True,
]


# ============================================================
# Helpers
# ============================================================

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

        if GROUP_PARAMETER is not None and GROUP_PARAMETER not in experiment:
            continue

        summary = result["summary"]
        per_question = result["per_question"]

        answerable = [
            row
            for row in per_question
            if len(row["gold_chunk_ids"]) > 0
        ]

        result_row = {
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

        if GROUP_PARAMETER is not None:
            result_row[GROUP_PARAMETER] = experiment[GROUP_PARAMETER]

        rows.append(result_row)

    return pd.DataFrame(rows)


def parameter_columns():
    columns = ["representation", X_PARAMETER]

    if GROUP_PARAMETER is not None:
        columns.append(GROUP_PARAMETER)

    return columns


def save_full_table(df):
    columns = [
        *parameter_columns(),
        *TABLE_METRICS,
    ]

    sort_columns = ["representation"]

    if GROUP_PARAMETER is not None:
        sort_columns.append(GROUP_PARAMETER)

    sort_columns.append(X_PARAMETER)

    table = (
        df[columns]
        .sort_values(sort_columns)
        .reset_index(drop=True)
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
        best = (
            group
            .sort_values(
                BEST_CONFIG_SORT,
                ascending=BEST_CONFIG_ASCENDING,
            )
            .iloc[0]
        )

        best_rows.append(best)

    best_df = pd.DataFrame(best_rows)

    columns = [
        *parameter_columns(),
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
    print(
        "(overall F1 -> exact match -> precision "
        "-> fewer selected chunks)\n"
    )
    print(best_df.round(4).to_string(index=False))

    return best_df


def plot_metrics_by_representation(df):
    if not PLOT_METRICS:
        return

    for representation, representation_df in df.groupby("representation"):
        fig, ax = plt.subplots(figsize=(8, 5))

        if GROUP_PARAMETER is None:
            group = representation_df.sort_values(X_PARAMETER)

            for metric in PLOT_METRICS:
                ax.plot(
                    group[X_PARAMETER],
                    group[metric],
                    marker="o",
                    label=metric,
                )

        else:
            for group_value, group in representation_df.groupby(
                GROUP_PARAMETER
            ):
                group = group.sort_values(X_PARAMETER)

                for metric in PLOT_METRICS:
                    if len(PLOT_METRICS) == 1:
                        label = f"{GROUP_PARAMETER}={group_value}"
                    else:
                        label = (
                            f"{GROUP_PARAMETER}={group_value} - {metric}"
                        )

                    ax.plot(
                        group[X_PARAMETER],
                        group[metric],
                        marker="o",
                        label=label,
                    )

        ax.set_xlabel(
            X_PARAMETER.replace("_", " ").title()
        )
        ax.set_ylabel("Score")
        ax.set_title(
            f"{representation}: "
            f"{METHOD.replace('_', ' ')} comparison"
        )
        ax.legend()
        ax.grid(alpha=0.25)

        fig.tight_layout()

        fig.savefig(
            OUTPUT_DIR
            / f"{representation}_{METHOD}_metrics.png",
            dpi=300,
        )

        plt.close(fig)


def plot_all_representations(df):
    if not PLOT_ALL_REPRESENTATIONS:
        return

    # The combined plot is intended for the current top-1-only search.
    # For older runs with several top-k values, skip it rather than
    # producing an ambiguous figure.
    if GROUP_PARAMETER is not None:
        group_values = df[GROUP_PARAMETER].dropna().unique()

        if len(group_values) > 1:
            print(
                "\nSkipping combined representation plot: "
                f"multiple {GROUP_PARAMETER} values are present."
            )
            return

    fig, ax = plt.subplots(figsize=(8, 5))

    for representation, group in df.groupby("representation"):
        group = group.sort_values(X_PARAMETER)

        if COMBINED_X_MODE == "normalized":
            minimum = group[X_PARAMETER].min()
            maximum = group[X_PARAMETER].max()

            if maximum == minimum:
                x_values = [0.0] * len(group)
            else:
                x_values = (
                    group[X_PARAMETER] - minimum
                ) / (maximum - minimum)

        elif COMBINED_X_MODE == "raw":
            x_values = group[X_PARAMETER]

        else:
            raise ValueError(
                "COMBINED_X_MODE must be 'normalized' or 'raw'."
            )

        ax.plot(
            x_values,
            group[COMBINED_PLOT_METRIC],
            marker="o",
            label=representation,
        )

    if COMBINED_X_MODE == "normalized":
        ax.set_xlabel("Relative Threshold Position")
    else:
        ax.set_xlabel(
            X_PARAMETER.replace("_", " ").title()
        )

    ax.set_ylabel(
        COMBINED_PLOT_METRIC.replace("_", " ").title()
    )
    ax.set_title(
        f"{METHOD.replace('_', ' ').title()}: "
        "representation comparison"
    )
    ax.legend()
    ax.grid(alpha=0.25)

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / f"{METHOD}_{COMBINED_PLOT_METRIC}_all_representations.png",
        dpi=300,
    )

    plt.close(fig)


def plot_best_f1_comparison(best_df):
    fig, ax = plt.subplots(figsize=(7, 5))

    ax.bar(
        best_df["representation"],
        best_df["overall_f1"],
    )

    ax.set_xlabel("Representation")
    ax.set_ylabel("Mean F1")
    ax.set_title(
        f"Best {METHOD.replace('_', ' ')} configuration by representation"
    )
    ax.grid(axis="y", alpha=0.25)

    fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR / f"{METHOD}_best_f1_comparison.png",
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
        + BEST_CONFIG_SORT
        + [COMBINED_PLOT_METRIC]
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

    best_df = save_best_configs(df)

    plot_metrics_by_representation(df)
    plot_all_representations(df)
    plot_best_f1_comparison(best_df)

    print(f"\nResults saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
