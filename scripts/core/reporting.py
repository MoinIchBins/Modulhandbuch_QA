"""Ranking tables, plots and baseline comparisons."""

from pathlib import Path

import matplotlib

import pandas as pd

from .config import read_json, read_jsonl, write_json
from .evaluation import summarize_questions
from .pipeline import experiment_name, require_stage, setting
from .ranking import rank_key


matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot_ranking(rows, path, title, label_field="experiment"):
    """Draw an F1 ranking plot with optional error bars."""
    rows = sorted(rows, key=rank_key, reverse=True)
    values = [row["mean_question_f1"] for row in rows]
    fig, ax = plt.subplots(figsize=(10, max(4, len(rows) * 0.4)))
    bars = ax.barh(
        [row[label_field] for row in rows],
        values,
        xerr=[row.get("mean_question_f1_std", 0.0) for row in rows],
        capsize=3,
    )

    ax.bar_label(bars, labels=[f"{value:.3f}" for value in values], padding=3)
    ax.invert_yaxis()
    ax.set_title(title)
    ax.set_xlabel("Mean question F1")
    ax.set_xlim(0, min(1.1, max(values, default=0) + 0.15))

    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def report_stage(config, stage):
    """Write ranking tables, plots and single-gold statistics."""
    root = Path(config["output_dir"])
    require_stage(root / stage)
    folder = root / "reports" / stage
    folder.mkdir(parents=True, exist_ok=True)

    rows = sorted(
        read_jsonl(root / stage / "summary.jsonl"), key=rank_key, reverse=True
    )
    pd.DataFrame(rows).to_csv(folder / "ranking.csv", index=False)
    plot_ranking(rows, folder / "ranking.png", f"{stage.title()} ranking")

    if stage == "development":
        return

    winner_name = experiment_name(setting(rows[0]))
    result = read_json(root / stage / f"{winner_name}_evaluation.json")
    single = [
        row
        for row in result["per_question"]
        if len(row["gold_chunk_ids"]) == 1
    ]

    ids = {row["question_id"] for row in single}
    summary = summarize_questions(single, ids, ids, [], [])

    write_json(
        folder / "winner_single_gold.json",
        {
            "experiment": result["experiment"],
            "split": stage,
            "filter": {
                "included": "exactly one gold chunk",
                "original_question_count": len(result["per_question"]),
                "included_question_count": len(single),
            },
            "summary": summary,
            "per_question": single,
        },
    )
    
    baseline_path = root / "baselines" / stage / "summary.jsonl"
    if baseline_path.exists():
        baselines = read_jsonl(baseline_path)
        comparison = [
            {
                "baseline": "final_retrieval_system",
                **result["summary"],
                "mean_question_f1_std": 0.0,
            },
            *baselines,
        ]
        pd.DataFrame(baselines).to_csv(folder / "baselines.csv", index=False)
        pd.DataFrame(sorted(comparison, key=rank_key, reverse=True)).to_csv(
            folder / "system_vs_baselines.csv", index=False
        )
        plot_ranking(
            comparison,
            folder / "system_vs_baselines.png",
            f"{stage.title()}: system and baselines",
            "baseline",
        )
