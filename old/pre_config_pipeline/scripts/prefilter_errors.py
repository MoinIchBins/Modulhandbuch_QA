import csv
import json
from pathlib import Path

GOLD_PATH = Path("data/frozen/split/gold_with_split.jsonl")
PREDICTIONS_PATH = Path(
    "artifacts/experiments/base/outputs/validation/finalists/"
    "e5_top_k_threshold_top_k_1_threshold_0.84_predictions.jsonl"
)
CHUNKS_PATH = Path("data/frozen/PO_25_CL_chunks.jsonl")

OUTPUT_DIR = Path(
    "artifacts/experiments/base/outputs/validation/finalists/error_analysis_of_best"
)

SPLIT = "validation"

def load_jsonl(path):
    with path.open(encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def classify(gold, prediction):
    if set(gold) == set(prediction):
        return None

    if gold and not prediction:
        return "category_3_answerable_but_abstained"

    if not gold and prediction:
        return "category_4_zero_gold_but_retrieved"

    if len(gold) > 1 and len(prediction) == 1:
        return "category_2_multi_gold_single_prediction"

    return "manual_review"


def write_csv(path, rows):
    if not rows:
        return

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def main():
    gold_rows = load_jsonl(GOLD_PATH)
    prediction_rows = load_jsonl(PREDICTIONS_PATH)
    chunks = load_jsonl(CHUNKS_PATH)

    gold_rows = [row for row in gold_rows if row.get("split") == SPLIT]

    predictions = {
        row["question_id"]: row["chunk_ids"]
        for row in prediction_rows
    }

    chunk_text = {
        row["chunk_id"]: row["chunk_text"]
        for row in chunks
    }

    groups = {
        "category_2_multi_gold_single_prediction": [],
        "category_3_answerable_but_abstained": [],
        "category_4_zero_gold_but_retrieved": [],
        "manual_review": [],
    }

    exact_matches = 0

    for row in gold_rows:
        question_id = row["question_id"]
        gold = row["all_required_chunk_ids"]
        prediction = predictions[question_id]

        category = classify(gold, prediction)

        if category is None:
            exact_matches += 1
            continue

        review_row = {
            "question_id": question_id,
            "question": row.get("question", ""),
            "gold_chunk_ids": " | ".join(gold),
            "predicted_chunk_ids": " | ".join(prediction),
            "gold_chunk_text": " || ".join(chunk_text.get(x, "") for x in gold),
            "predicted_chunk_text": " || ".join(
                chunk_text.get(x, "") for x in prediction
            ),
        }

        groups[category].append(review_row)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for category, rows in groups.items():
        write_csv(OUTPUT_DIR / f"{category}.csv", rows)

    total_errors = sum(len(rows) for rows in groups.values())

    print(f"Questions: {len(gold_rows)}")
    print(f"Exact matches: {exact_matches}")
    print(f"Errors: {total_errors}")

    for category, rows in groups.items():
        print(f"{category}: {len(rows)}")


if __name__ == "__main__":
    main()
