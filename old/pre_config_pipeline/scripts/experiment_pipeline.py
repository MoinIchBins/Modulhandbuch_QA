"""Shared input and prediction steps for the three experiment runners."""
import json
from pathlib import Path

import numpy as np

from chunk_selector import ChunkSelector


def read_json(path):
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)


def load_scores(files, question_ids, representation):
    matrix_question_ids = read_json(files["question_ids"])
    chunk_ids = read_json(files["chunk_ids"])
    row_by_question_id = {question_id: row for row, question_id in enumerate(matrix_question_ids)}
    missing = [question_id for question_id in question_ids if question_id not in row_by_question_id]
    if missing:
        raise ValueError(f"Questions missing from {representation} matrix: {missing[:5]}")
    rows = [row_by_question_id[question_id] for question_id in question_ids]
    return np.load(files["matrix"], mmap_mode="r")[rows], chunk_ids


def make_predictions(experiment, scores, chunk_ids, question_ids):
    selector = ChunkSelector(
        method=experiment["method"],
        top_k=experiment.get("top_k"),
        threshold=experiment.get("threshold"),
        margin=experiment.get("margin"),
    )
    selections = selector.select(scores, chunk_ids)
    return [
        {"question_id": question_id, "chunk_ids": selection["chunk_ids"], "scores": selection["scores"]}
        for question_id, selection in zip(question_ids, selections)
    ]


def write_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")
