import json
from pathlib import Path

import numpy as np

from chunk_selector import ChunkSelector
from mapping_evaluator import QAMappingEvaluator


GOLD_PATH = Path("data/produced_v2/frozen/qa_mapping_merged.jsonl")
TEST_IDS_PATH = Path("data/produced_v2/frozen/split/test_question_ids.json")
OUTPUT_DIR = Path("data/produced_v2/selector_experiments/test_winner")

MATRIX_PATH = Path(
    "data/produced_v2/similarity_matrices/"
    "retrieval_bi_encoder/cosine_similarity_matrix.npy"
)
QUESTION_IDS_PATH = Path(
    "data/produced_v2/similarity_matrices/retrieval_bi_encoder/question_ids.json"
)
CHUNK_IDS_PATH = Path(
    "data/produced_v2/similarity_matrices/retrieval_bi_encoder/chunk_ids.json"
)

REPRESENTATION = "e5"
METHOD = "top_k_threshold"
PARAMETERS = {
    "top_k": 1,
    "threshold": 0.83959,
}


def main():
    with TEST_IDS_PATH.open("r", encoding="utf-8") as file:
        test_ids = json.load(file)

    with QUESTION_IDS_PATH.open("r", encoding="utf-8") as file:
        matrix_question_ids = json.load(file)

    with CHUNK_IDS_PATH.open("r", encoding="utf-8") as file:
        chunk_ids = json.load(file)

    row_by_question_id = {
        question_id: row
        for row, question_id in enumerate(matrix_question_ids)
    }
    test_rows = [row_by_question_id[question_id] for question_id in test_ids]
    test_scores = np.load(MATRIX_PATH, mmap_mode="r")[test_rows]

    selector = ChunkSelector(
        method=METHOD,
        top_k=PARAMETERS["top_k"],
        threshold=PARAMETERS["threshold"],
    )
    selections = selector.select(test_scores, chunk_ids)

    predictions = [
        {
            "question_id": question_id,
            "chunk_ids": selection["chunk_ids"],
            "scores": selection["scores"],
        }
        for question_id, selection in zip(test_ids, selections)
    ]

    evaluator = QAMappingEvaluator(GOLD_PATH)
    result = evaluator.eval(
        [
            {
                "question_id": row["question_id"],
                "chunk_ids": row["chunk_ids"],
            }
            for row in predictions
        ],
        question_ids=test_ids,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
    name = "e5_top_k_threshold_top_k_1_threshold_0.83959"

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
                "representation": REPRESENTATION,
                "method": METHOD,
                **PARAMETERS,
                **result,
            },
            file,
            ensure_ascii=False,
            indent=2,
        )

    summary = {
        "experiment": name,
        "representation": REPRESENTATION,
        "method": METHOD,
        **PARAMETERS,
        **result["summary"],
    }

    with (OUTPUT_DIR / "summary.jsonl").open("w", encoding="utf-8") as file:
        file.write(json.dumps(summary, ensure_ascii=False) + "\n")

    print(
        f"{name}: "
        f"F1={summary['mean_question_f1']:.4f}, "
        f"exact={summary['exact_match_rate']:.4f}, "
        f"precision={summary['mean_question_precision']:.4f}, "
        f"avg_chunks={summary['average_selected_chunks']:.2f}"
    )


if __name__ == "__main__":
    main()
