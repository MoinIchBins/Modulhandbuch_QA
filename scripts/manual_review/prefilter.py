import csv
from pathlib import Path

from ..core.config import load_config, read_json, read_jsonl
from ..core.pipeline import (
    experiment_name,
    setting,
    require_stage,
    initialize_run,
    preflight,
)


def classify(gold, prediction):
    """Group errors by gold and predicted evidence-set size."""
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
    """Write review inputs with a fixed header, including empty categories."""
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=(
                "question_id",
                "question",
                "gold_chunk_ids",
                "predicted_chunk_ids",
                "gold_chunk_text",
                "predicted_chunk_text",
            ),
        )
        writer.writeheader()
        writer.writerows(rows)


def prefilter(config, split):
    """Write the winner's non-exact predictions into review groups."""
    root = Path(config["output_dir"])

    require_stage(root / split)
    summary = read_jsonl(root / split / "summary.jsonl")[0]
    predictions_path = (
        root / split / f"{experiment_name(setting(summary))}_predictions.jsonl"
    )
    output_dir = root / "manual_review" / split
    split_ids = set(read_json(config["splits"][split]))
    gold_rows = read_jsonl(Path(config["gold_path"]))
    prediction_rows = read_jsonl(predictions_path)
    chunks = read_jsonl(Path(config["chunks_path"]))

    gold_rows = [row for row in gold_rows if row["question_id"] in split_ids]

    predictions = {
        row["question_id"]: row["chunk_ids"] for row in prediction_rows
    }

    chunk_text = {row["chunk_id"]: row["chunk_text"] for row in chunks}

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
            "gold_chunk_text": " || ".join(chunk_text[x] for x in gold),
            "predicted_chunk_text": " || ".join(
                chunk_text[x] for x in prediction
            ),
        }

        groups[category].append(review_row)

    output_dir.mkdir(parents=True, exist_ok=True)

    for category, rows in groups.items():
        write_csv(output_dir / f"{category}.csv", rows)

    total_errors = sum(len(rows) for rows in groups.values())

    print(f"Questions: {len(gold_rows)}")
    print(f"Exact matches: {exact_matches}")
    print(f"Errors: {total_errors}")

    for category, rows in groups.items():
        print(f"{category}: {len(rows)}")


def main():
    """Read the config and prepare review CSVs."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Prepare error groups for the configured winner"
    )
    parser.add_argument("--config", required=True)
    parser.add_argument("--split", choices=("validation", "test"))
    args = parser.parse_args()
    config = load_config(args.config)
    if not (Path(config["output_dir"]) / "experiment.json").exists():
        raise ValueError("Run the experiment before preparing reviews")
    preflight(config)
    initialize_run(config)
    prefilter(
        config, args.split or config.get("manual_review", {}).get("split", "validation"),
    )


if __name__ == "__main__":
    main()
