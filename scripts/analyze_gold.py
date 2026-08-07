import json
import sys
from collections import Counter


def analyze_gold_sets(file_path):
    rows = []

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))

    gold_set_counts = Counter()
    chunk_counts = Counter()

    for row in rows:
        gold_chunks = row["all_required_chunk_ids"]

        gold_set = tuple(sorted(gold_chunks))
        gold_set_counts[gold_set] += 1

        for chunk_id in gold_chunks:
            chunk_counts[chunk_id] += 1

    single_sets = {
        gold_set: count
        for gold_set, count in gold_set_counts.items()
        if len(gold_set) == 1
    }

    multi_sets = {
        gold_set: count
        for gold_set, count in gold_set_counts.items()
        if len(gold_set) == 2
    }

    print("=== Gold-set diversity ===")
    print(f"Questions: {len(rows)}")
    print(f"Unique gold sets: {len(gold_set_counts)}")
    print()

    print(f"1-chunk questions: {sum(single_sets.values())}")
    print(f"Unique 1-chunk gold sets: {len(single_sets)}")
    print()

    print(f"2-chunk questions: {sum(multi_sets.values())}")
    print(f"Unique 2-chunk gold sets: {len(multi_sets)}")

    print("\n=== Two-chunk gold sets ===")
    for gold_set, count in sorted(
        multi_sets.items(),
        key=lambda x: (-x[1], x[0])
    ):
        print(f"{count:3d} questions | {list(gold_set)}")

    print("\n=== Most frequently required chunks ===")
    for chunk_id, count in chunk_counts.most_common(20):
        print(f"{count:3d} questions | {chunk_id}")

    print("\n=== Chunk coverage ===")
    print(f"Unique chunks used as gold: {len(chunk_counts)}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python analyze_gold_sets.py gold.jsonl")
        sys.exit(1)

    analyze_gold_sets(sys.argv[1])