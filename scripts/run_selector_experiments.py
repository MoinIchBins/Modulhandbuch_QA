import json
from pathlib import Path

import numpy as np

from chunk_selector import ChunkSelector
from mapping_evaluator import QAMappingEvaluator


GOLD_PATH = Path("data/produced_v2/frozen/qa_mapping_merged.jsonl")
DEVELOPMENT_IDS_PATH = Path("data/produced_v2/frozen/split/development_question_ids.json")
OUTPUT_DIR = Path("data/produced_v2/selector_experiments/dev_relative_margin_temp")

REPRESENTATIONS = {
    "e5": {
        "matrix": Path(
            "data/produced_v2/similarity_matrices/"
            "retrieval_bi_encoder/cosine_similarity_matrix.npy"
        ),
        "question_ids": Path(
            "data/produced_v2/similarity_matrices/retrieval_bi_encoder/question_ids.json"
        ),
        "chunk_ids": Path(
            "data/produced_v2/similarity_matrices/retrieval_bi_encoder/chunk_ids.json"
        ),
    },
    "tfidf": {
        "matrix": Path(
            "data/produced_v2/similarity_matrices/tf_idf/cosine_similarity_matrix.npy"
        ),
        "question_ids": Path(
            "data/produced_v2/similarity_matrices/tf_idf/question_ids.json"
        ),
        "chunk_ids": Path("data/produced_v2/similarity_matrices/tf_idf/chunk_ids.json"),
    },
    "sentence_bert": {
        "matrix": Path(
            "data/produced_v2/similarity_matrices/"
            "sentence_bert/cosine_similarity_matrix.npy"
        ),
        "question_ids": Path(
            "data/produced_v2/similarity_matrices/sentence_bert/question_ids.json"
        ),
        "chunk_ids": Path(
            "data/produced_v2/similarity_matrices/sentence_bert/chunk_ids.json"
        ),
    },
}

TOP_K_VALUES = [1]
N_MARGINS = 17
MARGIN_REGIONS = {
    "tfidf": (0.0, 0.4),
}

EXPERIMENTS = [
    {
        "representation": representation,
        "method": "relative_margin",
        "top_k": top_k,
        "margin": float(margin),
    }
    for representation, (lower, upper) in MARGIN_REGIONS.items()
    for top_k in TOP_K_VALUES
    for margin in np.linspace(lower, upper, N_MARGINS)
]


def experiment_name(config):
    parts = [config["representation"], config["method"]]
    for key in ("top_k", "threshold", "margin"):
        if config.get(key) is not None:
            parts.append(str(config[key]))
    return "_".join(parts)


def main():
    with DEVELOPMENT_IDS_PATH.open("r", encoding="utf-8") as file:
        development_ids = json.load(file)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)

    evaluator = QAMappingEvaluator(GOLD_PATH)
    summaries = []

    for representation, files in REPRESENTATIONS.items():
        configs = [
            config for config in EXPERIMENTS
            if config["representation"] == representation
        ]
        if not configs:
            continue

        with files["question_ids"].open("r", encoding="utf-8") as file:
            matrix_question_ids = json.load(file)
        with files["chunk_ids"].open("r", encoding="utf-8") as file:
            chunk_ids = json.load(file)

        row_by_question_id = {
            question_id: row
            for row, question_id in enumerate(matrix_question_ids)
        }
        development_rows = [
            row_by_question_id[question_id]
            for question_id in development_ids
        ]
        development_scores = np.load(files["matrix"], mmap_mode="r")[development_rows]

        for config in configs:
            selector = ChunkSelector(
                method=config["method"],
                top_k=config.get("top_k"),
                threshold=config.get("threshold"),
                margin=config.get("margin"),
            )
            selections = selector.select(development_scores, chunk_ids)

            predictions = [
                {
                    "question_id": question_id,
                    "chunk_ids": selection["chunk_ids"],
                    "scores": selection["scores"],
                }
                for question_id, selection in zip(development_ids, selections)
            ]

            result = evaluator.eval(
                [
                    {
                        "question_id": row["question_id"],
                        "chunk_ids": row["chunk_ids"],
                    }
                    for row in predictions
                ],
                question_ids=development_ids,
            )

            name = experiment_name(config)

            with (OUTPUT_DIR / f"{name}_predictions.jsonl").open(
                "w",
                encoding="utf-8",
            ) as file:
                for row in predictions:
                    file.write(json.dumps(row, ensure_ascii=False) + "\n")

            with (OUTPUT_DIR / f"{name}_evaluation.json").open(
                "w",
                encoding="utf-8",
            ) as file:
                json.dump(
                    {
                        "experiment": config,
                        **result,
                    },
                    file,
                    ensure_ascii=False,
                    indent=2,
                )

            summary = {
                "experiment": name,
                **config,
                **result["summary"],
            }
            summaries.append(summary)

            print(
                f"{name}: "
                f"F1={summary['mean_question_f1']:.4f}, "
                f"exact={summary['exact_match_rate']:.4f}, "
                f"avg_chunks={summary['average_selected_chunks']:.2f}"
            )

    with (OUTPUT_DIR / "summary.jsonl").open("w", encoding="utf-8") as file:
        for row in summaries:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
