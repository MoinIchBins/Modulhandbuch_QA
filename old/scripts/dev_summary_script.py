import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


DEFAULT_RUN_SET = Path("configs/manual_review_v1_dev_round_1.json")


def rank_results(df):
    return df.sort_values(
        by=["mean_question_f1", "exact_match_rate", "mean_question_precision", "average_selected_chunks"],
        ascending=[False, False, False, True],
    )


def main():
    parser = argparse.ArgumentParser(description="Summarize configured development runs.")
    parser.add_argument("--run-set", type=Path, default=DEFAULT_RUN_SET)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    with args.run_set.open("r", encoding="utf-8") as file:
        run_set = json.load(file)
    output_dir = args.output_dir or Path(run_set["output_dir"])

    rows = []
    for run in run_set["runs"]:
        folder = Path(run["path"])
        summary_file = folder / "summary.jsonl"
        if not summary_file.is_file():
            raise FileNotFoundError(f"No summary.jsonl found in {folder}")
        with summary_file.open("r", encoding="utf-8") as file:
            for line in file:
                row = json.loads(line)
                row["selector"] = run.get("selector", row.get("method"))
                rows.append(row)

    if not rows:
        raise ValueError("The configured development runs contain no summary rows.")
    results = pd.DataFrame(rows)
    best_configs = (
        rank_results(results)
        .groupby(["representation", "selector"], as_index=False, sort=False)
        .first()
    )
    selector_winners = rank_results(best_configs).groupby("selector", as_index=False, sort=False).first()
    overall_ranking = rank_results(best_configs)

    candidate_limit = run_set.get("validation_candidate_limit")
    if candidate_limit is not None and (not isinstance(candidate_limit, int) or candidate_limit < 1):
        raise ValueError("validation_candidate_limit must be a positive integer")
    candidate_rows = rank_results(best_configs)
    if candidate_limit is not None:
        candidate_rows = candidate_rows.head(candidate_limit)

    candidates = []
    for row in candidate_rows.itertuples(index=False):
        parameters = {}
        for key in ("top_k", "threshold", "margin"):
            value = getattr(row, key, None)
            if pd.notna(value):
                parameters[key] = int(value) if key == "top_k" else float(value)
        candidates.append({
            "representation": row.representation,
            "method": row.selector,
            "parameters": parameters,
            "development_metrics": {
                "mean_question_f1": float(row.mean_question_f1),
                "exact_match_rate": float(row.exact_match_rate),
                "mean_question_precision": float(row.mean_question_precision),
                "average_selected_chunks": float(row.average_selected_chunks),
            },
        })

    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "validation_candidates.json").write_text(
        json.dumps({
            "source_runs": [run["path"] for run in run_set["runs"]],
            "ranking": [
                "mean_question_f1 descending",
                "exact_match_rate descending",
                "mean_question_precision descending",
                "average_selected_chunks ascending",
            ],
            "candidates": candidates,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    best_configs.to_csv(output_dir / "best_configs.csv", index=False)
    selector_winners.to_csv(output_dir / "selector_winners.csv", index=False)
    overall_ranking.to_csv(output_dir / "overall_ranking.csv", index=False)

    table = best_configs.pivot(index="selector", columns="representation", values="mean_question_f1")
    ax = table.plot(kind="bar", figsize=(9, 5))
    ax.set_title("Development Performance")
    ax.set_xlabel("")
    ax.set_ylabel("Overall Question-Level F1")
    ax.set_ylim(0, 0.7)
    ax.legend(title="Representation")
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig(output_dir / "dev_f1_overview.png", dpi=200)
    plt.close()

    winners = rank_results(selector_winners)
    labels = [f"{row.selector}\n{row.representation}" for row in winners.itertuples()]
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(labels, winners["mean_question_f1"])
    ax.bar_label(bars, labels=[f"{value:.3f}" for value in winners["mean_question_f1"]], padding=3)
    ax.set_title("Best Development Configuration per Selector")
    ax.set_ylabel("Overall Question-Level F1")
    ax.set_ylim(0, 0.7)
    plt.tight_layout()
    plt.savefig(output_dir / "dev_winners.png", dpi=200)
    plt.close()

    labels = [f"{row.representation} + {row.selector}" for row in overall_ranking.itertuples()]
    fig, ax = plt.subplots(figsize=(9, 6))
    bars = ax.barh(labels, overall_ranking["mean_question_f1"])
    ax.bar_label(bars, labels=[f"{value:.3f}" for value in overall_ranking["mean_question_f1"]], padding=3)
    ax.invert_yaxis()
    ax.set_title("Development Ranking")
    ax.set_xlabel("Overall Question-Level F1")
    ax.set_xlim(0, 0.7)
    plt.tight_layout()
    plt.savefig(output_dir / "dev_full_ranking.png", dpi=200)
    plt.close()

    columns = [
        "representation", "selector", "top_k", "threshold", "margin",
        "mean_question_f1", "exact_match_rate", "mean_question_precision",
        "zero_gold_abstention_rate", "average_selected_chunks",
    ]
    columns = [column for column in columns if column in overall_ranking.columns]
    print("\nBest development configurations:\n")
    print(overall_ranking[columns].to_string(index=False))
    print(f"\nSummary saved to: {output_dir}")


if __name__ == "__main__":
    main()
