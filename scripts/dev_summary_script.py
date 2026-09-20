from pathlib import Path
import json

import matplotlib.pyplot as plt
import pandas as pd


RESULTS_DIR = Path("data/produced_v2/selector_experiments")
EXPERIMENT_DIRS = {
    "top_k": RESULTS_DIR / "dev_top_k_v1",
    "threshold": RESULTS_DIR / "dev_threshold_v2",
    "top_k_threshold": RESULTS_DIR / "dev_top_k_threshold_v6",
    "relative_margin": RESULTS_DIR / "dev_relative_margin_v2",
}
OUTPUT_DIR = RESULTS_DIR / "dev_consolidated"


def rank_results(df):
    return df.sort_values(
        by=[
            "mean_question_f1",
            "exact_match_rate",
            "mean_question_precision",
            "average_selected_chunks",
        ],
        ascending=[False, False, False, True],
    )


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = []
    for selector, folder in EXPERIMENT_DIRS.items():
        summary_file = list(folder.glob("*summary*.jsonl"))[0]
        with summary_file.open("r", encoding="utf-8") as file:
            for line in file:
                row = json.loads(line)
                row["selector"] = selector
                rows.append(row)

    results = pd.DataFrame(rows)
    best_configs = (
        rank_results(results)
        .groupby(["representation", "selector"], as_index=False, sort=False)
        .first()
    )
    selector_winners = (
        rank_results(best_configs)
        .groupby("selector", as_index=False, sort=False)
        .first()
    )
    overall_ranking = rank_results(best_configs)

    best_configs.to_csv(OUTPUT_DIR / "best_configs.csv", index=False)
    selector_winners.to_csv(OUTPUT_DIR / "selector_winners.csv", index=False)
    overall_ranking.to_csv(OUTPUT_DIR / "overall_ranking.csv", index=False)

    table = best_configs.pivot(
        index="selector",
        columns="representation",
        values="mean_question_f1",
    )
    ax = table.plot(kind="bar", figsize=(9, 5))
    ax.set_title("Development Performance")
    ax.set_xlabel("")
    ax.set_ylabel("Overall Question-Level F1")
    ax.set_ylim(0, 0.7)
    ax.legend(title="Representation")
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "dev_f1_overview.png", dpi=200)
    plt.close()

    winners = rank_results(selector_winners)
    labels = [
        f"{row.selector}\n{row.representation}"
        for row in winners.itertuples()
    ]
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(labels, winners["mean_question_f1"])
    ax.bar_label(
        bars,
        labels=[f"{value:.3f}" for value in winners["mean_question_f1"]],
        padding=3,
    )
    ax.set_title("Best Development Configuration per Selector")
    ax.set_ylabel("Overall Question-Level F1")
    ax.set_ylim(0, 0.7)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "dev_winners.png", dpi=200)
    plt.close()

    labels = [
        f"{row.representation} + {row.selector}"
        for row in overall_ranking.itertuples()
    ]
    fig, ax = plt.subplots(figsize=(9, 6))
    bars = ax.barh(labels, overall_ranking["mean_question_f1"])
    ax.bar_label(
        bars,
        labels=[f"{value:.3f}" for value in overall_ranking["mean_question_f1"]],
        padding=3,
    )
    ax.invert_yaxis()
    ax.set_title("Development Ranking")
    ax.set_xlabel("Overall Question-Level F1")
    ax.set_xlim(0, 0.7)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "dev_full_ranking.png", dpi=200)
    plt.close()

    columns = [
        "representation",
        "selector",
        "top_k",
        "threshold",
        "margin",
        "mean_question_f1",
        "exact_match_rate",
        "mean_question_precision",
        "zero_gold_abstention_rate",
        "average_selected_chunks",
    ]
    columns = [column for column in columns if column in overall_ranking.columns]

    print("\nBest development configurations:\n")
    print(overall_ranking[columns].to_string(index=False))


if __name__ == "__main__":
    main()
