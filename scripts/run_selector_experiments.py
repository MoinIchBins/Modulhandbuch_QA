import json
from pathlib import Path

import numpy as np

from chunk_selector import ChunkSelector
from mapping_evaluator import QAMappingEvaluator


# Change these paths to match
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
    },
}


OUTPUT_DIR = Path(
    "data/produced_v2/selector_experiments/dev_top_k_threshold_v3"
)


TOP_K_VALUES = [1, 2, 3]
N_THRESHOLDS = 21


def load_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_zero_gold_development_ids():
    development_ids = set(load_json(DEVELOPMENT_IDS_PATH))
    zero_gold_ids = []

    with GOLD_PATH.open("r", encoding="utf-8") as file:
        for line in file:
            row = json.loads(line)

            if (
                row["question_id"] in development_ids
                and not row["all_required_chunk_ids"]
            ):
                zero_gold_ids.append(row["question_id"])

    return zero_gold_ids


def build_threshold_regions():
    """
    For each representation and top-k value:

        Z_r = score distribution at rank r for zero-gold dev questions

        lower = P10(Z_k)
        upper = P90(Z_1)

    For k=1, threshold mainly controls abstention.
    For k>1, it also controls whether lower-ranked chunks are retained.
    """
    zero_gold_ids = load_zero_gold_development_ids()
    regions = {}

    for representation, files in REPRESENTATIONS.items():
        question_ids = load_json(files["question_ids"])

        row_by_question_id = {
            question_id: row
            for row, question_id in enumerate(question_ids)
        }

        row_indices = [
            row_by_question_id[question_id]
            for question_id in zero_gold_ids
        ]

        matrix = np.load(files["matrix"], mmap_mode="r")
        zero_gold_scores = np.asarray(matrix[row_indices])

        # Get only the three highest scores per question, in descending order.
        top_scores = np.sort(
            zero_gold_scores,
            axis=1,
        )[:, -3:][:, ::-1]

        upper = float(
            np.quantile(top_scores[:, 0], 0.90)
        )

        for top_k in TOP_K_VALUES:
            lower = float(
                np.quantile(
                    top_scores[:, top_k - 1],
                    0.10,
                )
            )

            regions[(representation, top_k)] = (
                lower,
                upper,
            )

    return regions


# ------------------------------------------------------------
# Experiment configuration
# ------------------------------------------------------------
#
# BACKWARD COMPATIBILITY:
#
# You can paste any previous explicit EXPERIMENTS list here and it will
# be used unchanged.
#
# Example:
#
# EXPERIMENTS = [
#     {
#         "representation": "e5",
#         "method": "top_k",
#         "top_k": 1,
#     },
# ]
#
# Leave EXPERIMENTS = None to use the new automatically derived,
# rank-specific top-k + threshold search.

EXPERIMENTS = None


def build_rank_specific_experiments():
    threshold_regions = build_threshold_regions()

    print("\nTop-k + threshold search regions")

    for (representation, top_k), (lower, upper) in threshold_regions.items():
        print(
            f"{representation:15} "
            f"k={top_k}  "
            f"{lower:.6f} -> {upper:.6f}"
        )

    return [
        {
            "representation": representation,
            "method": "top_k_threshold",
            "top_k": top_k,
            "threshold": float(threshold),
        }
        for representation in REPRESENTATIONS
        for top_k in TOP_K_VALUES
        for threshold in np.linspace(
            threshold_regions[(representation, top_k)][0],
            threshold_regions[(representation, top_k)][1],
            N_THRESHOLDS,
        )
    ]

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

    experiments = (
        EXPERIMENTS
        if EXPERIMENTS is not None
        else build_rank_specific_experiments()
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)

    evaluator = QAMappingEvaluator(GOLD_PATH)
    summaries = []

    for representation, files in REPRESENTATIONS.items():
        configs = [
            config
            for config in experiments
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