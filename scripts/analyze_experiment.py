"""Gold, similarity and threshold diagnostics for an experiment split."""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from .analysis.gold import analyze_gold_sets
from .analysis.similarity import analyze_matrix, jsonable, make_matrix_plots
from .analysis.thresholds import (
    question_scores,
    score_summary,
    plot_representation,
)
from .core.config import load_config, read_json, read_jsonl, write_json
from .core.pipeline import initialize_run, load_scores, preflight


def main():
    """Run the selected diagnostic; threshold advice uses development data."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument(
        "--kind", choices=("gold", "matrices", "thresholds"), required=True
    )
    parser.add_argument(
        "--split",
        choices=("development", "validation", "test"),
        default="development",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    if args.kind == "thresholds" and args.split != "development":
        parser.error("Threshold search advice is restricted to development")

    preflight(config)
    initialize_run(config)

    root = Path(config["output_dir"]) / "diagnostics" / args.split / args.kind
    root.mkdir(parents=True, exist_ok=True)

    ids = read_json(config["splits"][args.split])
    gold = {row["question_id"]: row for row in read_jsonl(config["gold_path"])}

    if args.kind == "gold":
        from .core.config import write_jsonl

        path = root / "gold_subset.jsonl"
        write_jsonl(path, [gold[q] for q in ids])
        analyze_gold_sets(path)
        return

    for name, files in config["representations"].items():
        if not files["higher_is_better"]:
            raise ValueError(
                (
                    "These optional score-separation diagnostics require higher-is-better scores"
                )
            )

        matrix, chunks = load_scores(files, ids)
        folder = root / name
        folder.mkdir(exist_ok=True)
        
        if args.kind == "matrices":
            result, questions, chunk_stats = analyze_matrix(
                matrix, ids, chunks, gold
            )
            questions.to_csv(folder / "per_question.csv", index=False)
            chunk_stats.to_csv(folder / "per_chunk.csv", index=False)
            write_json(folder / "analysis.json", jsonable(result))
            make_matrix_plots(result, questions, chunk_stats, folder)
        else:
            column = {chunk: index for index, chunk in enumerate(chunks)}
            frame = pd.DataFrame(
                [
                    question_scores(
                        name,
                        q,
                        matrix[i],
                        set(gold[q]["all_required_chunk_ids"]),
                        chunks,
                        column,
                    )
                    for i, q in enumerate(ids)
                ]
            )

            frame.to_csv(folder / "threshold_scores.csv", index=False)
            answerable = frame[frame["gold_size"] > 0]
            zero_gold = frame[frame["gold_size"] == 0]
            unwanted = pd.concat(
                [answerable["best_non_gold_score"], zero_gold["top_score"]]
            ).dropna()

            if answerable.empty or unwanted.empty:
                raise ValueError(
                    (
                        "Threshold advice requires answerable questions and unwanted scores"
                    )
                )

            boundaries = [
                float(answerable["worst_gold_score"].quantile(0.1)),
                float(unwanted.quantile(0.9)),
            ]

            write_json(
                folder / "threshold_advice.json",
                {
                    "split": "development",
                    "suggested_grid": np.linspace(
                        min(boundaries), max(boundaries), 7
                    ).tolist(),
                    "worst_gold_score": score_summary(
                        answerable["worst_gold_score"].dropna()
                    ),
                },
            )
            plot_representation(name, answerable, zero_gold, folder)

    print(f"Diagnostics saved to {root}")


if __name__ == "__main__":
    main()
