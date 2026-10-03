import json
from collections import Counter

split_path = (
    "data/frozen/split/test_question_ids.json"
)

prediction_path = (
    "artifacts/experiments/base/outputs/test/winner/"
    "e5_top_k_threshold_top_k_1_threshold_0.84_predictions.jsonl"
)

SPOT_CHECK_QUESTION_IDS = ("Q0157", "Q0160")


def main():
    with open(split_path, encoding="utf-8") as file:
        split_ids = [str(x).strip() for x in json.load(file)]

    with open(prediction_path, encoding="utf-8") as file:
        rows = [
            json.loads(line)
            for line in file
            if line.strip()
        ]

    prediction_ids = [
        str(row["question_id"]).strip()
        for row in rows
    ]

    counts = Counter(prediction_ids)

    missing = sorted(set(split_ids) - set(prediction_ids))
    extra = sorted(set(prediction_ids) - set(split_ids))
    duplicates = sorted(
        question_id
        for question_id, count in counts.items()
        if count > 1
    )

    print("Split questions:       ", len(split_ids))
    print("Prediction rows:       ", len(rows))
    print("Unique prediction IDs: ", len(set(prediction_ids)))
    print("Missing:               ", missing)
    print("Extra:                 ", extra)
    print("Duplicates:            ", duplicates)

    print("\nZugangsprüfung check:")
    for question_id in SPOT_CHECK_QUESTION_IDS:
        matches = [
            row for row in rows
            if row["question_id"] == question_id
        ]
        print(question_id, matches)


if __name__ == "__main__":
    main()
