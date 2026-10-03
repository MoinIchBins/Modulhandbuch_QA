"""Filter question records and apply saved split assignments."""

import argparse
from pathlib import Path

from ..core.config import (
    SPLITS,
    file_hash,
    read_json,
    read_jsonl,
    unique_ids,
    write_json,
    write_jsonl,
)

REVIEW_EXCLUSIONS = (
    "Q0485",
    "Q0488",
    "Q0491",
    "Q0494",
    "Q0497",
    "Q0503",
    "Q0515",
    "Q0521",
    "Q0527",
    "Q0529",
)


def rebuild_dataset(questions_path, gold_path, splits_dir, output, revised):
    """Filter the excluded questions and apply the supplied split IDs."""
    questions = read_jsonl(questions_path)
    gold_rows = read_jsonl(gold_path)
    unique_ids([row["question_id"] for row in questions], "questions")
    unique_ids([row["question_id"] for row in gold_rows], "gold")
    excluded = set(REVIEW_EXCLUSIONS) if revised else set()
    questions = [r for r in questions if r["question_id"] not in excluded]
    gold = {
        r["question_id"]: r
        for r in gold_rows
        if r["question_id"] not in excluded
    }
    expected = {r["question_id"] for r in questions}
    if set(gold) != expected:
        raise ValueError("Questions and annotations must cover the same IDs")
    split_paths = {
        s: Path(splits_dir) / f"{s}_question_ids.json" for s in SPLITS
    }
    splits = {s: read_json(p) for s, p in split_paths.items()}
    assignments = {}
    for split, ids in splits.items():
        unique_ids(ids, split)
        if set(ids) - expected or set(ids).intersection(assignments):
            raise ValueError(
                "Split IDs must be disjoint and reference retained questions"
            )
        assignments.update(dict.fromkeys(ids, split))
    if set(assignments) != expected:
        raise ValueError("Split IDs must cover every retained question")
    rows = []
    order = [q for s in SPLITS for q in splits[s]] if revised else list(gold)
    for question_id in order:
        row = dict(gold[question_id])
        if revised:
            row.pop("split_group_id", None)
        row["split"] = assignments[question_id]
        rows.append(row)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    write_jsonl(output / "qSet_PO.jsonl", questions)
    write_jsonl(output / "gold_with_split.jsonl", rows)
    for split, ids in splits.items():
        write_json(output / f"{split}_question_ids.json", ids)
    inputs = [Path(questions_path), Path(gold_path), *split_paths.values()]
    write_json(
        output / "preparation.json",
        {
            "mode": "replay_explicit_frozen_assignments",
            "excluded_question_ids": sorted(excluded),
            "input_sha256": {str(p.resolve()): file_hash(p) for p in inputs},
        },
    )


def main():
    """Export the selected dataset and split files."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", required=True)
    parser.add_argument("--gold", required=True)
    parser.add_argument("--splits-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--revised", action="store_true")
    args = parser.parse_args()
    rebuild_dataset(
        args.questions,
        args.gold,
        args.splits_dir,
        args.output_dir,
        args.revised,
    )
    print(f"Dataset exported: {args.output_dir}")


if __name__ == "__main__":
    main()
