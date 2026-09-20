import json
from pathlib import Path


EVALUATION_FILES = [
    Path(
        "data/produced_v2/selector_experiments/validation_finalists/"
        "e5_top_k_threshold_top_k_1_threshold_0.83959_evaluation.json"
    )
]

OUTPUT_DIR = Path(
    "data/produced_v2/selector_experiments/"
    "single_gold_only_evaluations"
)


def ratio(numerator, denominator):
    return numerator / denominator if denominator else 0.0


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for path in EVALUATION_FILES:
        with path.open("r", encoding="utf-8") as file:
            result = json.load(file)

        all_rows = result["per_question"]
        single_gold_rows = [
            row for row in all_rows
            if len(row["gold_chunk_ids"]) == 1
        ]
        zero_gold_rows = [
            row for row in all_rows
            if len(row["gold_chunk_ids"]) == 0
        ]
        multi_gold_rows = [
            row for row in all_rows
            if len(row["gold_chunk_ids"]) > 1
        ]

        question_count = len(single_gold_rows)
        total_tp = sum(row["tp"] for row in single_gold_rows)
        total_fp = sum(row["fp"] for row in single_gold_rows)
        total_fn = sum(row["fn"] for row in single_gold_rows)
        selected_counts = [
            len(row["predicted_chunk_ids"])
            for row in single_gold_rows
        ]
        exact_match_count = sum(row["exact_match"] for row in single_gold_rows)

        micro_precision = ratio(total_tp, total_tp + total_fp)
        micro_recall = ratio(total_tp, total_tp + total_fn)

        def average(values):
            values = list(values)
            return sum(values) / len(values) if values else 0.0

        summary = {
            "evaluated_question_count": question_count,
            "exact_match_count": exact_match_count,
            "exact_match_rate": ratio(exact_match_count, question_count),
            "mean_question_precision": average(row["precision"] for row in single_gold_rows),
            "mean_question_recall": average(row["recall"] for row in single_gold_rows),
            "mean_question_f1": average(row["f1"] for row in single_gold_rows),
            "mean_question_jaccard": average(row["jaccard"] for row in single_gold_rows),
            "micro_precision": micro_precision,
            "micro_recall": micro_recall,
            "micro_f1": ratio(
                2 * micro_precision * micro_recall,
                micro_precision + micro_recall,
            ),
            "micro_jaccard": ratio(total_tp, total_tp + total_fp + total_fn),
            "average_selected_chunks": average(selected_counts),
            "empty_selection_rate": ratio(
                sum(1 for count in selected_counts if count == 0),
                question_count,
            ),
            "total_tp": total_tp,
            "total_fp": total_fp,
            "total_fn": total_fn,
        }

        output = {
            "source_file": str(path),
            "filter": {
                "included": "questions with exactly one gold chunk",
                "excluded_zero_gold_count": len(zero_gold_rows),
                "excluded_multi_gold_count": len(multi_gold_rows),
                "original_question_count": len(all_rows),
                "included_question_count": len(single_gold_rows),
            },
            "summary": summary,
            "per_question": single_gold_rows,
        }
        if "experiment" in result:
            output["experiment"] = result["experiment"]

        output_path = (
            OUTPUT_DIR
            / f"{path.parent.name}__{path.stem}__single_gold_only.json"
        )
        with output_path.open("w", encoding="utf-8") as file:
            json.dump(output, file, ensure_ascii=False, indent=2)

        print()
        print(path)
        print(f"  original questions: {len(all_rows)}")
        print(f"  single-gold kept:   {len(single_gold_rows)}")
        print(f"  zero-gold removed:  {len(zero_gold_rows)}")
        print(f"  multi-gold removed: {len(multi_gold_rows)}")
        print(f"  mean question F1:   {summary['mean_question_f1']:.4f}")
        print(f"  exact match:        {summary['exact_match_rate']:.4f}")
        print(f"  micro F1:           {summary['micro_f1']:.4f}")
        print(f"  saved to:           {output_path}")

    print()
    print("Finished.")


if __name__ == "__main__":
    main()
