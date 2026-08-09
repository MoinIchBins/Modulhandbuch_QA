import json
from pathlib import Path


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

# Add the evaluation JSON files you want to recompute here.
# Each file must contain a "per_question" list, as produced by
# QAMappingEvaluator.
EVALUATION_FILES = [
    # Path(
    #     "data/produced_v2/selector_experiments/test_winner/"
    #     "e5_top_k_threshold_top_k_1_threshold_0.83959_evaluation.json"
    # ),
    Path(
        "data/produced_v2/selector_experiments/validation_finalists/"
        "e5_top_k_threshold_top_k_1_threshold_0.83959_evaluation.json"
    )
]

OUTPUT_DIR = Path(
    "data/produced_v2/selector_experiments/"
    "single_gold_only_evaluations"
)


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def load_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_json(path, data):
    with path.open("w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )


def safe_divide(numerator, denominator):
    if denominator == 0:
        return 0.0
    return numerator / denominator


def mean(values):
    if not values:
        return 0.0
    return sum(values) / len(values)


def output_name(input_path):
    # Prefix with the parent directory so files with the same stem from
    # different experiment folders do not overwrite each other.
    return (
        f"{input_path.parent.name}__"
        f"{input_path.stem}__single_gold_only.json"
    )


def summarize(rows):
    question_count = len(rows)

    total_tp = sum(row["tp"] for row in rows)
    total_fp = sum(row["fp"] for row in rows)
    total_fn = sum(row["fn"] for row in rows)

    exact_match_count = sum(
        1 for row in rows
        if row["exact_match"]
    )

    selected_counts = [
        len(row["predicted_chunk_ids"])
        for row in rows
    ]

    empty_selection_count = sum(
        1 for count in selected_counts
        if count == 0
    )

    micro_precision = safe_divide(
        total_tp,
        total_tp + total_fp,
    )

    micro_recall = safe_divide(
        total_tp,
        total_tp + total_fn,
    )

    micro_f1 = safe_divide(
        2 * micro_precision * micro_recall,
        micro_precision + micro_recall,
    )

    micro_jaccard = safe_divide(
        total_tp,
        total_tp + total_fp + total_fn,
    )

    return {
        "evaluated_question_count": question_count,
        "exact_match_count": exact_match_count,
        "exact_match_rate": safe_divide(
            exact_match_count,
            question_count,
        ),
        "mean_question_precision": mean(
            [row["precision"] for row in rows]
        ),
        "mean_question_recall": mean(
            [row["recall"] for row in rows]
        ),
        "mean_question_f1": mean(
            [row["f1"] for row in rows]
        ),
        "mean_question_jaccard": mean(
            [row["jaccard"] for row in rows]
        ),
        "micro_precision": micro_precision,
        "micro_recall": micro_recall,
        "micro_f1": micro_f1,
        "micro_jaccard": micro_jaccard,
        "average_selected_chunks": mean(selected_counts),
        "empty_selection_rate": safe_divide(
            empty_selection_count,
            question_count,
        ),
        "total_tp": total_tp,
        "total_fp": total_fp,
        "total_fn": total_fn,
    }


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def process_file(path):
    result = load_json(path)

    if "per_question" not in result:
        raise ValueError(
            f"{path} does not contain a 'per_question' list. "
            "Use the full evaluation JSON, not a compact summary file."
        )

    all_rows = result["per_question"]

    zero_gold_rows = [
        row
        for row in all_rows
        if len(row["gold_chunk_ids"]) == 0
    ]

    single_gold_rows = [
        row
        for row in all_rows
        if len(row["gold_chunk_ids"]) == 1
    ]

    multi_gold_rows = [
        row
        for row in all_rows
        if len(row["gold_chunk_ids"]) > 1
    ]

    output = {
        "source_file": str(path),
        "filter": {
            "included": "questions with exactly one gold chunk",
            "excluded_zero_gold_count": len(zero_gold_rows),
            "excluded_multi_gold_count": len(multi_gold_rows),
            "original_question_count": len(all_rows),
            "included_question_count": len(single_gold_rows),
        },
        "summary": summarize(single_gold_rows),
        "per_question": single_gold_rows,
    }

    if "experiment" in result:
        output["experiment"] = result["experiment"]

    return output


def main():
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not EVALUATION_FILES:
        raise ValueError(
            "EVALUATION_FILES is empty."
        )

    for path in EVALUATION_FILES:
        if not path.exists():
            raise FileNotFoundError(
                f"Evaluation file not found: {path}"
            )

        output = process_file(path)

        output_path = (
            OUTPUT_DIR / output_name(path)
        )

        save_json(
            output_path,
            output,
        )

        summary = output["summary"]
        filtering = output["filter"]

        print()
        print(path)
        print(
            f"  original questions: "
            f"{filtering['original_question_count']}"
        )
        print(
            f"  single-gold kept:   "
            f"{filtering['included_question_count']}"
        )
        print(
            f"  zero-gold removed:  "
            f"{filtering['excluded_zero_gold_count']}"
        )
        print(
            f"  multi-gold removed: "
            f"{filtering['excluded_multi_gold_count']}"
        )
        print(
            f"  mean question F1:   "
            f"{summary['mean_question_f1']:.4f}"
        )
        print(
            f"  exact match:        "
            f"{summary['exact_match_rate']:.4f}"
        )
        print(
            f"  micro F1:           "
            f"{summary['micro_f1']:.4f}"
        )
        print(
            f"  saved to:           "
            f"{output_path}"
        )

    print()
    print("Finished.")


if __name__ == "__main__":
    main()
