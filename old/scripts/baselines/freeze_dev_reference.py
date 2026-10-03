import json
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

GOLD_PATH = PROJECT_ROOT / "data/frozen/qa_mapping_merged.jsonl"
DEVELOPMENT_IDS_PATH = (
    PROJECT_ROOT
    / "data/frozen/split/development_question_ids.json"
)
OUTPUT_PATH = PROJECT_ROOT / "artifacts/baselines/dev_reference/most_frequent_answer.json"


def load_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_gold(path):
    gold = {}

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue

            row = json.loads(line)
            gold[row["question_id"]] = row["all_required_chunk_ids"]

    return gold


def main():
    if OUTPUT_PATH.exists():
        raise FileExistsError(
            f"Frozen dev reference already exists: {OUTPUT_PATH}"
        )

    print("\nFreezing development-derived baseline")

    development_ids = load_json(DEVELOPMENT_IDS_PATH)
    gold = load_gold(GOLD_PATH)

    print(f"Loaded {len(development_ids)} development question IDs")
    print(f"Loaded {len(gold)} gold mappings")

    missing_ids = [
        question_id
        for question_id in development_ids
        if question_id not in gold
    ]

    if missing_ids:
        raise ValueError(f"Development IDs missing from gold: {missing_ids}")

    answer_sets = [
        tuple(sorted(gold[question_id]))
        for question_id in development_ids
        if gold[question_id]
    ]

    print(f"Found {len(answer_sets)} non-empty development answers")

    counts = Counter(answer_sets)

    if not counts:
        raise ValueError("Development split contains no non-empty gold answers.")

    highest_count = max(counts.values())
    tied_answers = [
        answer
        for answer, count in counts.items()
        if count == highest_count
    ]

    # Deterministic tie-break if several answer sets occur equally often.
    most_frequent_answer = min(tied_answers)

    result = {
        "baseline": "most_frequent_dev_answer",
        "derived_from": "development",
        "chunk_ids": list(most_frequent_answer),
        "development_count": highest_count,
        "development_question_count": len(development_ids),
        "development_non_empty_question_count": len(answer_sets),
        "tied_maximum_count": len(tied_answers),
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Found {len(counts)} unique non-empty answer sets")
    print(f"Saved frozen reference to {OUTPUT_PATH}")
    print("\nFrozen most-frequent development answer:")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
