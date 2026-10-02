import json
from pathlib import Path

import numpy as np

from chunk_selector import ChunkSelector
from mapping_evaluator import QAMappingEvaluator


GOLD_PATH = Path("data/frozen/qa_mapping_merged.jsonl")
VALIDATION_IDS_PATH = Path(
    "data/frozen/split/validation_question_ids.json"
)
OUTPUT_DIR = Path(
    "artifacts/experiments/validation/validation_finalists"
)

REPRESENTATIONS = {
    "e5": {
        "matrix": Path(
            "artifacts/similarity_matrices/"
            "retrieval_bi_encoder/cosine_similarity_matrix.npy"
        ),
        "question_ids": Path(
            "artifacts/similarity_matrices/"
            "retrieval_bi_encoder/question_ids.json"
        ),
        "chunk_ids": Path(
            "artifacts/similarity_matrices/retrieval_bi_encoder/chunk_ids.json"
        ),
    },
    "tfidf": {
        "matrix": Path(
            "artifacts/similarity_matrices/tf_idf/cosine_similarity_matrix.npy"
        ),
        "question_ids": Path(
            "artifacts/similarity_matrices/tf_idf/question_ids.json"
        ),
        "chunk_ids": Path("artifacts/similarity_matrices/tf_idf/chunk_ids.json"),
    },
}

FINALISTS = [
    ("e5", "top_k_threshold", {"top_k": 1, "threshold": 0.83959}),
    ("e5", "relative_margin", {"top_k": 1, "margin": 0.0025}),
    ("e5", "top_k", {"top_k": 1}),
    ("tfidf", "relative_margin", {"top_k": 1, "margin": 0.235}),
    ("tfidf", "top_k_threshold", {"top_k": 1, "threshold": 0.0999}),
]


def experiment_name(representation, method, parameters):
    parts = [representation, method]
    for key in ("top_k", "threshold", "margin"):
        if key in parameters:
            parts.append(f"{key}_{parameters[key]}")
    return "_".join(parts)


def main():
    with VALIDATION_IDS_PATH.open("r", encoding="utf-8") as file:
        validation_ids = json.load(file)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
    evaluator = QAMappingEvaluator(GOLD_PATH)
    summaries = []

    cache = {}
    for representation, method, parameters in FINALISTS:
        if representation not in cache:
            files = REPRESENTATIONS[representation]

            with files["question_ids"].open("r", encoding="utf-8") as file:
                matrix_question_ids = json.load(file)
            with files["chunk_ids"].open("r", encoding="utf-8") as file:
                chunk_ids = json.load(file)

            row_by_question_id = {
                question_id: row
                for row, question_id in enumerate(matrix_question_ids)
            }
            validation_rows = [
                row_by_question_id[question_id]
                for question_id in validation_ids
            ]
            cache[representation] = (
                np.load(files["matrix"], mmap_mode="r")[validation_rows],
                chunk_ids,
            )

        validation_scores, chunk_ids = cache[representation]

        selector = ChunkSelector(
            method=method,
            top_k=parameters.get("top_k"),
            threshold=parameters.get("threshold"),
            margin=parameters.get("margin"),
        )
        selections = selector.select(validation_scores, chunk_ids)

        predictions = [
            {
                "question_id": question_id,
                "chunk_ids": selection["chunk_ids"],
                "scores": selection["scores"],
            }
            for question_id, selection in zip(validation_ids, selections)
        ]

        result = evaluator.eval(
            [
                {
                    "question_id": row["question_id"],
                    "chunk_ids": row["chunk_ids"],
                }
                for row in predictions
            ],
            question_ids=validation_ids,
        )

        name = experiment_name(representation, method, parameters)

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
                    "representation": representation,
                    "method": method,
                    **parameters,
                    **result,
                },
                file,
                ensure_ascii=False,
                indent=2,
            )

        summary = {
            "experiment": name,
            "representation": representation,
            "method": method,
            **parameters,
            **result["summary"],
        }
        summaries.append(summary)

        print(
            f"{name}: "
            f"F1={summary['mean_question_f1']:.4f}, "
            f"exact={summary['exact_match_rate']:.4f}, "
            f"precision={summary['mean_question_precision']:.4f}, "
            f"avg_chunks={summary['average_selected_chunks']:.2f}"
        )

    with (OUTPUT_DIR / "summary.jsonl").open("w", encoding="utf-8") as file:
        for row in summaries:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
