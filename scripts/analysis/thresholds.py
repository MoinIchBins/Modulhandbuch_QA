import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def score_summary(values):
    values = np.asarray(values, dtype=float)
    if len(values) == 0:
        return {
            "count": 0,
            "min": None,
            "p10": None,
            "p25": None,
            "median": None,
            "p75": None,
            "p90": None,
            "max": None,
        }

    return {
        "count": len(values),
        "min": float(np.min(values)),
        "p10": float(np.quantile(values, 0.10)),
        "p25": float(np.quantile(values, 0.25)),
        "median": float(np.median(values)),
        "p75": float(np.quantile(values, 0.75)),
        "p90": float(np.quantile(values, 0.90)),
        "max": float(np.max(values)),
    }


def question_scores(name, question_id, scores, gold_chunks, chunk_ids, column_by_chunk):
    sorted_scores = np.sort(scores)[::-1]

    row = {
        "representation": name,
        "question_id": question_id,
        "gold_size": len(gold_chunks),
        "top_score": float(sorted_scores[0]),
        "second_score": float(sorted_scores[1]),
        "top1_top2_gap": float(sorted_scores[0] - sorted_scores[1]),
        "best_gold_score": None,
        "worst_gold_score": None,
        "best_non_gold_score": None,
        "best_gold_margin": None,
        "worst_gold_margin": None,
    }

    if gold_chunks:
        gold_indices = [column_by_chunk[chunk_id] for chunk_id in gold_chunks]
        gold_scores = scores[gold_indices]

        non_gold_mask = np.ones(len(chunk_ids), dtype=bool)
        non_gold_mask[gold_indices] = False
        best_non_gold = float(np.max(scores[non_gold_mask]))
        best_gold = float(np.max(gold_scores))
        worst_gold = float(np.min(gold_scores))

        row.update(
            {
                "best_gold_score": best_gold,
                "worst_gold_score": worst_gold,
                "best_non_gold_score": best_non_gold,
                "best_gold_margin": best_gold - best_non_gold,
                "worst_gold_margin": worst_gold - best_non_gold,
            }
        )

    return row


def plot_representation(name, answerable, zero_gold, output_dir):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(
        answerable["worst_gold_score"].dropna(),
        bins=25,
        alpha=0.6,
        label="Worst required gold score",
    )
    ax.hist(
        answerable["best_non_gold_score"].dropna(),
        bins=25,
        alpha=0.6,
        label="Best non-gold score",
    )
    if not zero_gold.empty:
        ax.hist(
            zero_gold["top_score"].dropna(),
            bins=25,
            alpha=0.6,
            label="Zero-gold top score",
        )
    ax.set_xlabel("Similarity score")
    ax.set_ylabel("Questions")
    ax.set_title(f"{name}: threshold-relevant score distributions")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / f"{name}_threshold_distributions.png", dpi=300)
    plt.close(fig)


