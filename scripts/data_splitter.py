import json
import random
from collections import defaultdict
from pathlib import Path


gold_file = Path("data/processed/qamappings/qa_mapping_merged.jsonl")
output_dir = Path("data/trash")

split_ratios = {
    "development": 0.60,
    "validation": 0.20,
    "test": 0.20,
}

random_seed = 42


def load_jsonl(path):
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def save_jsonl(rows, path):
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def build_groups(rows):
    grouped_questions = defaultdict(list)

    for row in rows:
        question_id = row["question_id"]
        gold_chunks = tuple(sorted(row["all_required_chunk_ids"]))

        # Questions with the same non-empty gold set belong together.
        # Zero-gold questions each get their own group.
        if gold_chunks:
            group_key = gold_chunks
        else:
            group_key = ("empty", question_id)

        grouped_questions[group_key].append(question_id)

    question_groups = [
        sorted(question_ids)
        for question_ids in grouped_questions.values()
    ]

    question_groups.sort(key=lambda ids: ids[0])

    return {
        f"G{i:04d}": question_ids
        for i, question_ids in enumerate(question_groups, start=1)
    }


def create_split(groups):
    rng = random.Random(random_seed)

    group_ids = list(groups.keys())
    rng.shuffle(group_ids)

    # Put large groups first so they are easier to place sensibly
    group_ids.sort(
        key=lambda group_id: len(groups[group_id]),
        reverse=True,
    )

    total_questions = sum(len(ids) for ids in groups.values())

    target_sizes = {
        split: total_questions * ratio
        for split, ratio in split_ratios.items()
    }

    split_counts = {
        split: 0
        for split in split_ratios
    }

    group_to_split = {}

    for group_id in group_ids:
        group_size = len(groups[group_id])

        # Assign the whole group to the split that is furthest
        # from its target proportion.
        split = min(
            split_ratios,
            key=lambda split: (
                split_counts[split] + group_size
            ) / target_sizes[split],
        )

        group_to_split[group_id] = split
        split_counts[split] += group_size

    return group_to_split


def print_summary(groups, group_to_split):
    print("\nQuestion split summary")

    total_questions = sum(len(ids) for ids in groups.values())

    print(f"Questions: {total_questions}")
    print(f"Groups:    {len(groups)}")
    print(f"Largest group: {max(len(ids) for ids in groups.values())}")

    for split in split_ratios:
        question_count = sum(
            len(groups[group_id]) for group_id, assigned_split in group_to_split.items() if assigned_split == split
        )

        print(
            f"{split:12} "
            f"{question_count:3} "
            f"({question_count / total_questions:.1%})"
        )


def main():
    rows = load_jsonl(gold_file)

    question_ids = [row["question_id"] for row in rows]

    if len(question_ids) != len(set(question_ids)):
        raise ValueError("question_id values are not unique.")

    groups = build_groups(rows)
    group_to_split = create_split(groups)

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

    output_dir.mkdir(parents=True, exist_ok=True)

    save_jsonl(
        enriched_rows,
        output_dir / "gold_with_split.jsonl",
    )

    for split in split_ratios:
        split_ids = [
            row["question_id"]
            for row in enriched_rows
            if row["split"] == split
        ]

        save_json(
            split_ids,
            output_dir / f"{split}_question_ids.json",
        )

    save_json(
        groups,
        output_dir / "split_groups.json",
    )

    print_summary(groups, group_to_split)


if __name__ == "__main__":
    main()