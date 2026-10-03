from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


def score_counts(tp, fp, fn):
    """An empty prediction against empty gold receives perfect scores."""
    if tp == fp == fn == 0:
        return 1.0, 1.0, 1.0, 1.0

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    jaccard = tp / (tp + fp + fn) if tp + fp + fn else 0.0

    return precision, recall, f1, jaccard


def mean(values):
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def score_question(question_id, gold_chunks, predicted_chunks):
    true_positive_chunks = gold_chunks & predicted_chunks
    false_positive_chunks = predicted_chunks - gold_chunks
    false_negative_chunks = gold_chunks - predicted_chunks

    tp = len(true_positive_chunks)
    fp = len(false_positive_chunks)
    fn = len(false_negative_chunks)
    precision, recall, f1, jaccard = score_counts(tp, fp, fn)

    return {
        "question_id": question_id,
        "gold_chunk_ids": sorted(gold_chunks),
        "predicted_chunk_ids": sorted(predicted_chunks),
        "true_positive_chunk_ids": sorted(true_positive_chunks),
        "false_positive_chunk_ids": sorted(false_positive_chunks),
        "false_negative_chunk_ids": sorted(false_negative_chunks),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "jaccard": jaccard,
        "exact_match": gold_chunks == predicted_chunks,
    }


def summarize_questions(per_question, scope_ids, prediction_ids, unanswered_ids, unknown_prediction_ids):
    selected_counts = [len(row["predicted_chunk_ids"]) for row in per_question]
    total_tp = sum(row["tp"] for row in per_question)
    total_fp = sum(row["fp"] for row in per_question)
    total_fn = sum(row["fn"] for row in per_question)
    if per_question:
        micro_precision, micro_recall, micro_f1, micro_jaccard = score_counts(
            total_tp,
            total_fp,
            total_fn,
        )
    else:
        micro_precision = micro_recall = micro_f1 = micro_jaccard = 0.0

    zero_gold_rows = [
        row for row in per_question
        if not row["gold_chunk_ids"]
    ]
    correct_abstentions = sum(
        not row["predicted_chunk_ids"]
        for row in zero_gold_rows
    )

    return {
        "total_gold_questions": len(scope_ids),
        "submitted_prediction_count": len(prediction_ids & scope_ids),
        "evaluated_question_count": len(per_question),
        "unanswered_question_count": len(unanswered_ids),
        "answer_coverage": len(per_question) / len(scope_ids) if scope_ids else 0.0,
        "unknown_prediction_count": len(unknown_prediction_ids),
        "exact_match_count": sum(row["exact_match"] for row in per_question),
        "exact_match_rate": mean(row["exact_match"] for row in per_question),
        "mean_question_precision": mean(row["precision"] for row in per_question),
        "mean_question_recall": mean(row["recall"] for row in per_question),
        "mean_question_f1": mean(row["f1"] for row in per_question),
        "mean_question_jaccard": mean(row["jaccard"] for row in per_question),
        "micro_precision": micro_precision,
        "micro_recall": micro_recall,
        "micro_f1": micro_f1,
        "micro_jaccard": micro_jaccard,
        "average_selected_chunks": mean(selected_counts),
        "empty_selection_rate": mean(count == 0 for count in selected_counts),
        "zero_gold_question_count": len(zero_gold_rows),
        "correct_abstention_count": correct_abstentions,
        "zero_gold_abstention_rate": (
            correct_abstentions / len(zero_gold_rows)
            if zero_gold_rows
            else 0.0
        ),
        "total_tp": total_tp,
        "total_fp": total_fp,
        "total_fn": total_fn,
        "unanswered_question_ids": unanswered_ids,
        "unknown_prediction_question_ids": unknown_prediction_ids,
    }


class QAMappingEvaluator:
    def __init__(self, gold_jsonl: str | Path) -> None:
        self.gold = {}

        with Path(gold_jsonl).open("r", encoding="utf-8") as file:
            for line in file:
                if not line.strip():
                    continue

                row = json.loads(line)
                self.gold[str(row["question_id"]).strip()] = {
                    str(chunk_id).strip()
                    for chunk_id in row["all_required_chunk_ids"]
                }

    def eval(
        self,
        new_mapping: str | Path | Iterable[dict[str, Any]],
        question_ids: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        if isinstance(new_mapping, (str, Path)):
            with Path(new_mapping).open("r", encoding="utf-8") as file:
                records = [json.loads(line) for line in file if line.strip()]
        else:
            records = list(new_mapping)

        predictions = {
            str(row["question_id"]).strip(): {
                str(chunk_id).strip()
                for chunk_id in row["chunk_ids"]
            }
            for row in records
        }

        scope_ids = (
            set(self.gold)
            if question_ids is None
            else {str(question_id).strip() for question_id in question_ids}
        )
        prediction_ids = set(predictions)
        evaluated_ids = sorted(scope_ids & prediction_ids)
        unanswered_ids = sorted(scope_ids - prediction_ids)
        unknown_prediction_ids = sorted(prediction_ids - set(self.gold))

        # Missing predictions are reported separately; they are not scored.
        per_question = []
        for question_id in evaluated_ids:
            per_question.append(score_question(question_id, self.gold[question_id], predictions[question_id]))

        summary = summarize_questions(per_question, scope_ids, prediction_ids, unanswered_ids, unknown_prediction_ids)

        return {
            "summary": summary,
            "per_question": per_question,
        }
