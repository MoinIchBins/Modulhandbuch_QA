from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from sklearn.metrics import accuracy_score, f1_score, jaccard_score, precision_score, recall_score
from sklearn.preprocessing import MultiLabelBinarizer


class QAMappingEvaluator:
    """Evaluate predicted QA-to-chunk mappings against a gold JSONL file."""

    def __init__(self, gold_jsonl: str | Path) -> None:
        self.gold = self._load_gold(gold_jsonl)

    def eval(
        self,
        new_mapping: str | Path | Iterable[dict[str, Any]],
        question_ids: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        """Evaluate predictions, optionally restricted to a set of question IDs."""
        predictions = self._load_predictions(new_mapping)

        gold_ids = set(self.gold)
        if question_ids is None:
            scope_ids = gold_ids
        else:
            scope_ids = {str(question_id).strip() for question_id in question_ids}
            missing_gold_ids = scope_ids - gold_ids
            if missing_gold_ids:
                raise ValueError(
                    f"Question IDs not found in gold data: {sorted(missing_gold_ids)}"
                )

        prediction_ids = set(predictions)

        evaluated_ids = sorted(scope_ids & prediction_ids)
        unanswered_ids = sorted(scope_ids - prediction_ids)
        unknown_prediction_ids = sorted(prediction_ids - gold_ids)

        per_question = self._score_questions(evaluated_ids, predictions)
        summary = self._build_summary(
            per_question=per_question,
            gold_question_count=len(scope_ids),
            prediction_count=len(prediction_ids & scope_ids),
            unanswered_ids=unanswered_ids,
            unknown_prediction_ids=unknown_prediction_ids,
        )

        return {
            "summary": summary,
            "per_question": per_question,
        }

    def _score_questions(
        self,
        evaluated_ids: list[str],
        predictions: dict[str, set[str]],
    ) -> list[dict[str, Any]]:
        if not evaluated_ids:
            return []

        gold_sets = [self.gold[question_id] for question_id in evaluated_ids]
        predicted_sets = [predictions[question_id] for question_id in evaluated_ids]
        all_chunk_ids = sorted(set().union(*gold_sets, *predicted_sets))

        if all_chunk_ids:
            binarizer = MultiLabelBinarizer(classes=all_chunk_ids)
            y_true = binarizer.fit_transform(gold_sets)
            y_pred = binarizer.transform(predicted_sets)
        else:
            y_true = None
            y_pred = None

        results: list[dict[str, Any]] = []

        for index, question_id in enumerate(evaluated_ids):
            gold_chunks = gold_sets[index]
            predicted_chunks = predicted_sets[index]

            true_positive_chunks = gold_chunks & predicted_chunks
            false_positive_chunks = predicted_chunks - gold_chunks
            false_negative_chunks = gold_chunks - predicted_chunks

            if not gold_chunks and not predicted_chunks:
                precision = recall = f1 = jaccard = 1.0
                exact_match = True
            else:
                precision = float(
                    precision_score(y_true[index], y_pred[index], zero_division=0)
                )
                recall = float(
                    recall_score(y_true[index], y_pred[index], zero_division=0)
                )
                f1 = float(
                    f1_score(y_true[index], y_pred[index], zero_division=0)
                )
                jaccard = float(
                    jaccard_score(y_true[index], y_pred[index], zero_division=0)
                )
                exact_match = bool(
                    accuracy_score(
                        y_true[index].reshape(1, -1),
                        y_pred[index].reshape(1, -1),
                    )
                )

            results.append(
                {
                    "question_id": question_id,
                    "gold_chunk_ids": sorted(gold_chunks),
                    "predicted_chunk_ids": sorted(predicted_chunks),
                    "true_positive_chunk_ids": sorted(true_positive_chunks),
                    "false_positive_chunk_ids": sorted(false_positive_chunks),
                    "false_negative_chunk_ids": sorted(false_negative_chunks),
                    "tp": len(true_positive_chunks),
                    "fp": len(false_positive_chunks),
                    "fn": len(false_negative_chunks),
                    "precision": precision,
                    "recall": recall,
                    "f1": f1,
                    "jaccard": jaccard,
                    "exact_match": exact_match,
                }
            )

        return results

    def _build_summary(
        self,
        *,
        per_question: list[dict[str, Any]],
        gold_question_count: int,
        prediction_count: int,
        unanswered_ids: list[str],
        unknown_prediction_ids: list[str],
    ) -> dict[str, Any]:
        evaluated_count = len(per_question)

        if not per_question:
            return {
                "total_gold_questions": gold_question_count,
                "submitted_prediction_count": prediction_count,
                "evaluated_question_count": 0,
                "unanswered_question_count": len(unanswered_ids),
                "answer_coverage": 0.0,
                "unknown_prediction_count": len(unknown_prediction_ids),
                "exact_match_count": 0,
                "exact_match_rate": 0.0,
                "mean_question_precision": 0.0,
                "mean_question_recall": 0.0,
                "mean_question_f1": 0.0,
                "mean_question_jaccard": 0.0,
                "micro_precision": 0.0,
                "micro_recall": 0.0,
                "micro_f1": 0.0,
                "micro_jaccard": 0.0,
                "average_selected_chunks": 0.0,
                "empty_selection_rate": 0.0,
                "zero_gold_question_count": 0,
                "correct_abstention_count": 0,
                "zero_gold_abstention_rate": 0.0,
                "total_tp": 0,
                "total_fp": 0,
                "total_fn": 0,
                "unanswered_question_ids": unanswered_ids,
                "unknown_prediction_question_ids": unknown_prediction_ids,
            }

        exact_values = np.array([row["exact_match"] for row in per_question], dtype=int)
        precision_values = np.array([row["precision"] for row in per_question], dtype=float)
        recall_values = np.array([row["recall"] for row in per_question], dtype=float)
        f1_values = np.array([row["f1"] for row in per_question], dtype=float)
        jaccard_values = np.array([row["jaccard"] for row in per_question], dtype=float)
        selected_counts = np.array(
            [len(row["predicted_chunk_ids"]) for row in per_question], dtype=int
        )

        total_tp = sum(row["tp"] for row in per_question)
        total_fp = sum(row["fp"] for row in per_question)
        total_fn = sum(row["fn"] for row in per_question)

        gold_sets = [set(row["gold_chunk_ids"]) for row in per_question]
        predicted_sets = [set(row["predicted_chunk_ids"]) for row in per_question]
        all_chunk_ids = sorted(set().union(*gold_sets, *predicted_sets))

        if all_chunk_ids:
            binarizer = MultiLabelBinarizer(classes=all_chunk_ids)
            y_true = binarizer.fit_transform(gold_sets)
            y_pred = binarizer.transform(predicted_sets)

            micro_precision = float(
                precision_score(y_true, y_pred, average="micro", zero_division=0)
            )
            micro_recall = float(
                recall_score(y_true, y_pred, average="micro", zero_division=0)
            )
            micro_f1 = float(
                f1_score(y_true, y_pred, average="micro", zero_division=0)
            )
            micro_jaccard = float(
                jaccard_score(y_true, y_pred, average="micro", zero_division=0)
            )
        else:
            micro_precision = micro_recall = micro_f1 = micro_jaccard = 1.0

        zero_gold_rows = [row for row in per_question if not row["gold_chunk_ids"]]
        correct_abstentions = sum(
            not row["predicted_chunk_ids"] for row in zero_gold_rows
        )

        return {
            "total_gold_questions": gold_question_count,
            "submitted_prediction_count": prediction_count,
            "evaluated_question_count": evaluated_count,
            "unanswered_question_count": len(unanswered_ids),
            "answer_coverage": (
                evaluated_count / gold_question_count if gold_question_count else 0.0
            ),
            "unknown_prediction_count": len(unknown_prediction_ids),
            "exact_match_count": int(exact_values.sum()),
            "exact_match_rate": float(exact_values.mean()),
            "mean_question_precision": float(precision_values.mean()),
            "mean_question_recall": float(recall_values.mean()),
            "mean_question_f1": float(f1_values.mean()),
            "mean_question_jaccard": float(jaccard_values.mean()),
            "micro_precision": micro_precision,
            "micro_recall": micro_recall,
            "micro_f1": micro_f1,
            "micro_jaccard": micro_jaccard,
            "average_selected_chunks": float(selected_counts.mean()),
            "empty_selection_rate": float((selected_counts == 0).mean()),
            "zero_gold_question_count": len(zero_gold_rows),
            "correct_abstention_count": correct_abstentions,
            "zero_gold_abstention_rate": (
                correct_abstentions / len(zero_gold_rows) if zero_gold_rows else 0.0
            ),
            "total_tp": total_tp,
            "total_fp": total_fp,
            "total_fn": total_fn,
            "unanswered_question_ids": unanswered_ids,
            "unknown_prediction_question_ids": unknown_prediction_ids,
        }

    @staticmethod
    def _load_gold(path: str | Path) -> dict[str, set[str]]:
        gold: dict[str, set[str]] = {}

        for record in QAMappingEvaluator._read_jsonl(path):
            question_id = record["question_id"]
            chunk_ids = record["all_required_chunk_ids"]
            gold[str(question_id).strip()] = {
                str(chunk_id).strip() for chunk_id in chunk_ids
            }

        return gold

    @staticmethod
    def _load_predictions(
        source: str | Path | Iterable[dict[str, Any]],
    ) -> dict[str, set[str]]:
        if isinstance(source, (str, Path)):
            records = QAMappingEvaluator._read_jsonl(source)
        else:
            records = list(source)

        predictions: dict[str, set[str]] = {}

        for record in records:
            question_id = record["question_id"]
            chunk_ids = record["chunk_ids"]
            predictions[str(question_id).strip()] = {
                str(chunk_id).strip() for chunk_id in chunk_ids
            }

        return predictions

    @staticmethod
    def _read_jsonl(path: str | Path) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []

        with Path(path).open("r", encoding="utf-8") as file:
            for line in file:
                if line.strip():
                    records.append(json.loads(line))

        return records
