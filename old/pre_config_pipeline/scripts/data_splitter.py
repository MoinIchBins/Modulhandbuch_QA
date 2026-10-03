import json
import random
from collections import defaultdict
from pathlib import Path


GOLD_FILE = Path("data/processed/qamappings/qa_mapping_merged.jsonl")
OUTPUT_DIR = Path("data/trash")
SPLIT_RATIOS = {
    "development": 0.60,
    "validation": 0.20,
    "test": 0.20,
}
RANDOM_SEED = 42


def group_questions(rows):
    grouped_questions = defaultdict(list)
    for row in rows:
        question_id = row["question_id"]
        gold_chunks = tuple(sorted(row["all_required_chunk_ids"]))
        group_key = gold_chunks if gold_chunks else ("empty", question_id)
        grouped_questions[group_key].append(question_id)

    groups = {
        f"G{i:04d}": sorted(question_ids)
        for i, question_ids in enumerate(
            sorted(grouped_questions.values(), key=lambda ids: ids[0]),
            start=1,
        )
    }

    return groups


def assign_splits(groups):
    rng = random.Random(RANDOM_SEED)
    group_ids = list(groups)
    rng.shuffle(group_ids)
    # Stable size sorting retains the shuffled order among equally sized groups.
    group_ids.sort(key=lambda group_id: len(groups[group_id]), reverse=True)

    total_questions = sum(len(ids) for ids in groups.values())
    target_sizes = {
        split: total_questions * ratio
        for split, ratio in SPLIT_RATIOS.items()
    }
    split_counts = {split: 0 for split in SPLIT_RATIOS}
    group_to_split = {}

    for group_id in group_ids:
        group_size = len(groups[group_id])
        split = min(
            SPLIT_RATIOS,
            key=lambda name: (split_counts[name] + group_size) / target_sizes[name],
        )
        group_to_split[group_id] = split
        split_counts[split] += group_size

    return group_to_split, split_counts


def write_splits(rows, groups, group_to_split):
    question_to_group = {}
    question_to_split = {}
    for group_id, ids in groups.items():
        for question_id in ids:
            question_to_group[question_id] = group_id
            question_to_split[question_id] = group_to_split[group_id]

    enriched_rows = []
    for row in rows:
        row = row.copy()
        question_id = row["question_id"]
        row["split_group_id"] = question_to_group[question_id]
        row["split"] = question_to_split[question_id]
        enriched_rows.append(row)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with (OUTPUT_DIR / "gold_with_split.jsonl").open("w", encoding="utf-8") as file:
        for row in enriched_rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")

    for split in SPLIT_RATIOS:
        split_ids = [
            row["question_id"]
            for row in enriched_rows
            if row["split"] == split
        ]
        with (OUTPUT_DIR / f"{split}_question_ids.json").open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(split_ids, file, ensure_ascii=False, indent=2)

    with (OUTPUT_DIR / "split_groups.json").open("w", encoding="utf-8") as file:
        json.dump(groups, file, ensure_ascii=False, indent=2)


def main():
    with GOLD_FILE.open("r", encoding="utf-8") as file:
        rows = [json.loads(line) for line in file if line.strip()]

    groups = group_questions(rows)
    group_to_split, split_counts = assign_splits(groups)
    total_questions = sum(split_counts.values())

    write_splits(rows, groups, group_to_split)

    print("\nQuestion split summary")
    print(f"Questions: {total_questions}")
    print(f"Groups:    {len(groups)}")
    print(f"Largest group: {max(len(ids) for ids in groups.values())}")

    for split in SPLIT_RATIOS:
        question_count = split_counts[split]
        print(
            f"{split:12} "
            f"{question_count:3} "
            f"({question_count / total_questions:.1%})"
        )


if __name__ == "__main__":
    main()
