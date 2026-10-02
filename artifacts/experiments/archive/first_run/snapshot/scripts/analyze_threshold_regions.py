import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


GOLD_PATH = Path("data/frozen/qa_mapping_merged.jsonl")
DEVELOPMENT_IDS_PATH = Path(
    "data/frozen/split/development_question_ids.json"
)

REPRESENTATIONS = {
    "e5": {
        "matrix": Path(
            "artifacts/similarity_matrices/retrieval_bi_encoder/"
            "cosine_similarity_matrix.npy"
        ),
        "question_ids": Path(
            "artifacts/similarity_matrices/retrieval_bi_encoder/"
            "question_ids.json"
        ),
        "chunk_ids": Path(
            "artifacts/similarity_matrices/retrieval_bi_encoder/"
            "chunk_ids.json"
        ),
    },
    "tfidf": {
        "matrix": Path(
            "artifacts/similarity_matrices/tf_idf/"
            "cosine_similarity_matrix.npy"
        ),
        "question_ids": Path(
            "artifacts/similarity_matrices/tf_idf/question_ids.json"
        ),
        "chunk_ids": Path(
            "artifacts/similarity_matrices/tf_idf/chunk_ids.json"
        ),
    },
    "sentence_bert": {
        "matrix": Path(
            "artifacts/similarity_matrices/sentence_bert/"
            "cosine_similarity_matrix.npy"
        ),
        "question_ids": Path(
            "artifacts/similarity_matrices/sentence_bert/question_ids.json"
        ),
        "chunk_ids": Path(
            "artifacts/similarity_matrices/sentence_bert/chunk_ids.json"
        ),
    },
}

OUTPUT_DIR = Path(
    "artifacts/experiments/development/threshold_analysis"
)


def read_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


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


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    development_ids = read_json(DEVELOPMENT_IDS_PATH)
    gold = {}
    with GOLD_PATH.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                row = json.loads(line)
                gold[row["question_id"]] = set(row["all_required_chunk_ids"])

    all_question_rows = []
    all_summary_rows = []
    threshold_suggestions = {}

    for name, files in REPRESENTATIONS.items():
        matrix_question_ids = read_json(files["question_ids"])
        chunk_ids = read_json(files["chunk_ids"])
        matrix = np.load(files["matrix"], mmap_mode="r")

        row_by_question = {
            question_id: index
            for index, question_id in enumerate(matrix_question_ids)
        }
        column_by_chunk = {
            chunk_id: index
            for index, chunk_id in enumerate(chunk_ids)
        }

        rows = []
        for question_id in development_ids:
            scores = matrix[row_by_question[question_id]]
            gold_chunks = gold[question_id]
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

            rows.append(row)

        df = pd.DataFrame(rows)
        df.to_csv(OUTPUT_DIR / f"{name}_threshold_scores.csv", index=False)
        all_question_rows.append(df)

        answerable = df[df["gold_size"] > 0]
        zero_gold = df[df["gold_size"] == 0]
        summary = pd.DataFrame(
            [
                {
                    "representation": name,
                    "metric": metric,
                    **score_summary(values.dropna()),
                }
                for metric, values in {
                    "worst_gold_score": answerable["worst_gold_score"],
                    "best_non_gold_score": answerable["best_non_gold_score"],
                    "zero_gold_top_score": zero_gold["top_score"],
                    "worst_gold_margin": answerable["worst_gold_margin"],
                }.items()
            ]
        )
        all_summary_rows.append(summary)

        unwanted_scores = pd.concat(
            [
                answerable["best_non_gold_score"],
                zero_gold["top_score"],
            ],
            ignore_index=True,
        ).dropna()

        gold_boundary = float(answerable["worst_gold_score"].quantile(0.10))
        unwanted_boundary = float(unwanted_scores.quantile(0.90))
        lower = min(gold_boundary, unwanted_boundary)
        upper = max(gold_boundary, unwanted_boundary)
        threshold_suggestions[name] = np.linspace(lower, upper, 7).tolist()

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
        fig.savefig(OUTPUT_DIR / f"{name}_threshold_distributions.png", dpi=300)
        plt.close(fig)

    combined_questions = pd.concat(all_question_rows, ignore_index=True)
    combined_summary = pd.concat(all_summary_rows, ignore_index=True)

    combined_questions.to_csv(OUTPUT_DIR / "all_threshold_scores.csv", index=False)
    combined_summary.to_csv(OUTPUT_DIR / "threshold_summary.csv", index=False)

    print("\nThreshold-relevant score summary\n")
    print(combined_summary.round(4).to_string(index=False))

    print("\nSuggested coarse threshold grids\n")
    for representation, thresholds in threshold_suggestions.items():
        print(f"{representation:15} {[round(value, 4) for value in thresholds]}")

    print(f"\nResults saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
