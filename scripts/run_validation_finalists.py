import json
from pathlib import Path

import numpy as np

from chunk_selector import ChunkSelector
from mapping_evaluator import QAMappingEvaluator


GOLD_PATH = Path(
    "data/produced_v2/frozen/qa_mapping_merged.jsonl"
)

VALIDATION_IDS_PATH = Path(
    "data/produced_v2/frozen/split/validation_question_ids.json"
)

OUTPUT_DIR = Path(
    "data/produced_v2/selector_experiments/validation_finalists"
)


REPRESENTATIONS = {
    "e5": {
        "matrix": Path(
            "data/produced_v2/similarity_matrices/"
            "retrieval_bi_encoder/cosine_similarity_matrix.npy"
        ),
        "question_ids": Path(
            "data/produced_v2/similarity_matrices/"
            "retrieval_bi_encoder/question_ids.json"
        ),
        "chunk_ids": Path(
            "data/produced_v2/similarity_matrices/"
            "retrieval_bi_encoder/chunk_ids.json"
        ),
    },
    "tfidf": {
        "matrix": Path(
            "data/produced_v2/similarity_matrices/"
            "tf_idf/cosine_similarity_matrix.npy"
        ),
        "question_ids": Path(
            "data/produced_v2/similarity_matrices/"
            "tf_idf/question_ids.json"
        ),
        "chunk_ids": Path(
            "data/produced_v2/similarity_matrices/"
            "tf_idf/chunk_ids.json"
        ),
    },
    "sentence_bert": {
        "matrix": Path(
            "data/produced_v2/similarity_matrices/"
            "sentence_bert/cosine_similarity_matrix.npy"
        ),
        "question_ids": Path(
            "data/produced_v2/similarity_matrices/"
            "sentence_bert/question_ids.json"
        ),
        "chunk_ids": Path(
            "data/produced_v2/similarity_matrices/"
            "sentence_bert/chunk_ids.json"
        ),
    },
}


FINALISTS = [
    (
        "e5",
        "top_k_threshold",
        {
            "top_k": 1,
            "threshold": 0.83959,
        },
    ),
    (
        "e5",
        "relative_margin",
        {
            "top_k": 1,
            "margin": 0.0025,
        },
    ),
    (
        "e5",
        "top_k",
        {
            "top_k": 1,
        },
    ),
    (
        "tfidf",
        "relative_margin",
        {
            "top_k": 1,
            "margin": 0.235,
        },
    ),
    (
        "tfidf",
        "top_k_threshold",
        {
            "top_k": 1,
            "threshold": 0.0999,
        },
    ),
]


def load_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(
                json.dumps(row, ensure_ascii=False) + "\n"
            )


def experiment_name(representation, method, parameters):
    parts = [representation, method]

    for key in ("top_k", "threshold", "margin", "temperature"):
        if key in parameters:
            parts.append(f"{key}_{parameters[key]}")

    return "_".join(parts)


def main():
    validation_ids = load_json(VALIDATION_IDS_PATH)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=False,
    )

    evaluator = QAMappingEvaluator(GOLD_PATH)
    summaries = []

    for representation, method, parameters in FINALISTS:
        files = REPRESENTATIONS[representation]

        matrix_question_ids = load_json(
            files["question_ids"]
        )
        chunk_ids = load_json(
            files["chunk_ids"]
        )

        row_by_question_id = {
            question_id: row
            for row, question_id
            in enumerate(matrix_question_ids)
        }

        missing_ids = [
            question_id
            for question_id in validation_ids
            if question_id not in row_by_question_id
        ]

        if missing_ids:
            raise ValueError(
                f"{representation}: validation questions missing "
                f"from similarity matrix: {missing_ids}"
            )

        validation_rows = [
            row_by_question_id[question_id]
            for question_id in validation_ids
        ]

        matrix = np.load(
            files["matrix"],
            mmap_mode="r",
        )

        validation_scores = matrix[validation_rows]

        selector = ChunkSelector(
            method=method,
            top_k=parameters.get("top_k"),
            threshold=parameters.get("threshold"),
            margin=parameters.get("margin"),
            temperature=parameters.get(
                "temperature",
                0.05,
            ),
        )

        selections = selector.select(
            validation_scores,
            chunk_ids,
        )

        predictions = [
            {
                "question_id": question_id,
                "chunk_ids": selection["chunk_ids"],
                "scores": selection["scores"],
            }
            for question_id, selection
            in zip(validation_ids, selections)
        ]

        evaluation_input = [
            {
                "question_id": row["question_id"],
                "chunk_ids": row["chunk_ids"],
            }
            for row in predictions
        ]

        result = evaluator.eval(
            evaluation_input,
            question_ids=validation_ids,
        )

        name = experiment_name(
            representation,
            method,
            parameters,
        )

        save_jsonl(
            OUTPUT_DIR / f"{name}_predictions.jsonl",
            predictions,
        )

        with (
            OUTPUT_DIR / f"{name}_evaluation.json"
        ).open("w", encoding="utf-8") as file:
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

    save_jsonl(
        OUTPUT_DIR / "summary.jsonl",
        summaries,
    )


if __name__ == "__main__":
    main()