import json
from pathlib import Path

import numpy as np

from chunk_selector import ChunkSelector
from mapping_evaluator import QAMappingEvaluator


# Change these paths to match your project.
GOLD_PATH = Path("data/produced_v2/frozen/qa_mapping_merged.jsonl")
DEVELOPMENT_IDS_PATH = Path("data/produced_v2/frozen/split/development_question_ids.json")

REPRESENTATIONS = {
    "e5": {
        "matrix": Path("data/produced_v2/similarity_matrices/retrieval_bi_encoder/cosine_similarity_matrix.npy"),
        "question_ids": Path("data/produced_v2/similarity_matrices/retrieval_bi_encoder/question_ids.json"),
        "chunk_ids": Path("data/produced_v2/similarity_matrices/retrieval_bi_encoder/chunk_ids.json"),
    },
    "tfidf": {
        "matrix": Path("data/produced_v2/similarity_matrices/tf_idf/cosine_similarity_matrix.npy"),
        "question_ids": Path("data/produced_v2/similarity_matrices/tf_idf/question_ids.json"),
        "chunk_ids": Path("data/produced_v2/similarity_matrices/tf_idf/chunk_ids.json"),
    },
    "sentence_bert": {
        "matrix": Path("data/produced_v2/similarity_matrices/sentence_bert/cosine_similarity_matrix.npy"),
        "question_ids": Path("data/produced_v2/similarity_matrices/sentence_bert/question_ids.json"),
        "chunk_ids": Path("data/produced_v2/similarity_matrices/sentence_bert/chunk_ids.json"),
    }
}


OUTPUT_DIR = Path(
    "data/produced_v2/selector_experiments/dev_threshold"
)



first_experiment = [
    {
        "representation": representation,
        "method": "top_k",
        "top_k": top_k,
    }
    for representation in ("e5", "tfidf", "sentence_bert")
    for top_k in range(1, 10)
]


THRESHOLD_REGIONS = {
    "e5": (0.8331, 0.8865),
    "tfidf": (0.0591, 0.5162),
    "sentence_bert": (0.4740, 0.7595),
}

EXPERIMENTS = [
    {
        "representation": representation,
        "method": "threshold",
        "threshold": float(threshold),
    }
    for representation, (lower, upper) in THRESHOLD_REGIONS.items()
    for threshold in np.linspace(lower, upper, 9)
]


def load_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_jsonl(path, records):
    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def experiment_name(config):
    parts = [config["representation"], config["method"]]

    if config.get("top_k") is not None:
        parts.append(str(config["top_k"]))
    if config.get("threshold") is not None:
        parts.append(str(config["threshold"]))
    if config.get("temperature") is not None:
        parts.append(str(config["temperature"]))

    return "_".join(parts)


def main():
    development_ids = load_json(DEVELOPMENT_IDS_PATH)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)

    evaluator = QAMappingEvaluator(GOLD_PATH)
    summaries = []

    for representation, files in REPRESENTATIONS.items():
        configs = [
            config
            for config in EXPERIMENTS
            if config["representation"] == representation
        ]

        if not configs:
            continue

        matrix_question_ids = load_json(files["question_ids"])
        chunk_ids = load_json(files["chunk_ids"])

        if len(matrix_question_ids) != len(set(matrix_question_ids)):
            raise ValueError(
                f"{representation}: question IDs contain duplicates."
            )

        if len(chunk_ids) != len(set(chunk_ids)):
            raise ValueError(
                f"{representation}: chunk IDs contain duplicates."
            )

        row_by_question_id = {
            question_id: row
            for row, question_id in enumerate(matrix_question_ids)
        }

        missing_ids = [
            question_id
            for question_id in development_ids
            if question_id not in row_by_question_id
        ]

        if missing_ids:
            raise ValueError(
                f"{representation}: development questions missing "
                f"from similarity matrix: {missing_ids}"
            )

        development_rows = [
            row_by_question_id[question_id]
            for question_id in development_ids
        ]

        matrix = np.load(files["matrix"], mmap_mode="r")

        expected_shape = (
            len(matrix_question_ids),
            len(chunk_ids),
        )

        if matrix.shape != expected_shape:
            raise ValueError(
                f"Unexpected shape for {representation}: "
                f"{matrix.shape}. Expected {expected_shape}."
            )

        development_scores = matrix[development_rows]

        for config in configs:
            selector = ChunkSelector(
                method=config["method"],
                top_k=config.get("top_k"),
                threshold=config.get("threshold"),
                temperature=config.get("temperature", 0.05),
            )

            selections = selector.select(
                development_scores,
                chunk_ids,
            )

            predictions = [
                {
                    "question_id": question_id,
                    "chunk_ids": selection["chunk_ids"],
                    "scores": selection["scores"],
                    **(
                        {"weights": selection["weights"]}
                        if "weights" in selection
                        else {}
                    ),
                }
                for question_id, selection
                in zip(development_ids, selections)
            ]

            evaluation_input = [
                {
                    "question_id": prediction["question_id"],
                    "chunk_ids": prediction["chunk_ids"],
                }
                for prediction in predictions
            ]

            result = evaluator.eval(
                evaluation_input,
                question_ids=development_ids,
            )

            name = experiment_name(config)

            save_jsonl(
                OUTPUT_DIR / f"{name}_predictions.jsonl",
                predictions,
            )

            with (
                OUTPUT_DIR / f"{name}_evaluation.json"
            ).open("w", encoding="utf-8") as file:
                json.dump(
                    {
                        "experiment": config,
                        **result,
                    },
                    file,
                    ensure_ascii=False,
                    indent=2,
                )

            summaries.append(
                {
                    "experiment": name,
                    **config,
                    **result["summary"],
                }
            )

            print(
                f"{name}: "
                f"F1={result['summary']['mean_question_f1']:.4f}, "
                f"exact={result['summary']['exact_match_rate']:.4f}, "
                f"avg_chunks="
                f"{result['summary']['average_selected_chunks']:.2f}"
            )

    save_jsonl(
        OUTPUT_DIR / "summary.jsonl",
        summaries,
    )


if __name__ == "__main__":
    main()
