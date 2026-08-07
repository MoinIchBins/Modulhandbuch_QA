"""Analyze retrieval similarity matrices against gold chunk mappings.

The script evaluates ranking quality, score separation, zero-gold behavior,
per-question diagnostics, per-chunk score behavior, and cross-matrix comparisons.
Edit only the configuration section below to point it at the current artifacts.
"""

from pathlib import Path
import json
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


matrix_paths = [
    "data/produced_v2/similarity_matrices/tf_idf/cosine_similarity_matrix.npy",
    "data/produced_v2/similarity_matrices/sentence_bert/cosine_similarity_matrix.npy",
    "data/produced_v2/similarity_matrices/retrieval_bi_encoder/cosine_similarity_matrix.npy",
]

# Optional readable names. Leave empty to derive names from parent folder + filename.
matrix_names = {
    "data/produced_v2/similarity_matrices/tf_idf/cosine_similarity_matrix.npy": "tfidf_cosine",
    "data/produced_v2/similarity_matrices/sentence_bert/cosine_similarity_matrix.npy": "sentence_bert",
    "data/produced_v2/similarity_matrices/retrieval_bi_encoder/cosine_similarity_matrix.npy": "retrieval_bi_encoder",
}

gold_path = "data/processed/qamappings/qa_mapping_merged.jsonl"
question_ids_path = "data/produced_v2/similarity_matrices/tf_idf/question_ids.json"
chunk_ids_path = "data/produced_v2/similarity_matrices/tf_idf/chunk_ids.json"

output_dir = "data/produced_v2/similarity_analysis"

k_values = [1, 2, 3, 5, 10]
top_results_to_store = 10
top_chunks_to_report = 20

# Optional: if one of these exists next to a matrix, scalar metadata is copied
# into that matrix's analysis.json.
SIDECAR_METADATA_FILENAMES = [
    "metadata.json",
]



# Loading
def load_matrix(path):
    """Load a .npy or single-array .npz similarity matrix."""
    path = Path(path)

    if path.suffix == ".npy":
        matrix = np.load(path)
    elif path.suffix == ".npz":
        archive = np.load(path)
        if len(archive.files) != 1:
            raise ValueError(
                f"{path} contains {len(archive.files)} arrays; expected exactly one."
            )
        matrix = archive[archive.files[0]]
    else:
        raise ValueError(f"Unsupported matrix format: {path.suffix}")

    if matrix.ndim != 2:
        raise ValueError(f"{path} is not two-dimensional: shape={matrix.shape}")

    return matrix


def load_id_list(path, preferred_key):
    """Load an ID list from a JSON list or a simple JSON object."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        if preferred_key in data and isinstance(data[preferred_key], list):
            return data[preferred_key]

        list_values = [value for value in data.values() if isinstance(value, list)]
        if len(list_values) == 1:
            return list_values[0]

    raise ValueError(f"Could not find a single ID list in {path}")


def load_gold(path):
    """Load gold mappings keyed by question_id."""
    gold = {}

    with open(path, "r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            if not line.strip():
                continue

            row = json.loads(line)
            question_id = row["question_id"]

            if question_id in gold:
                raise ValueError(f"Duplicate question_id in gold: {question_id}")

            gold[question_id] = row

    return gold


def load_sidecar_metadata(matrix_path):
    """Read small scalar metadata fields from a nearby metadata JSON if present."""
    matrix_path = Path(matrix_path)

    candidates = [
        matrix_path.parent / f"{matrix_path.stem}_metadata.json",
        *[
            matrix_path.parent / filename
            for filename in SIDECAR_METADATA_FILENAMES
        ],
    ]

    for candidate in candidates:
        if not candidate.exists():
            continue

        try:
            with open(candidate, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        if not isinstance(data, dict):
            continue

        scalar_metadata = {}
        for key, value in data.items():
            if isinstance(value, (str, int, float, bool)) or value is None:
                scalar_metadata[key] = value

        return str(candidate), scalar_metadata

    return None, {}


# Helpers
def safe_name(value):
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return value.strip("_") or "matrix"


def matrix_identifier(path):
    path = Path(path)
    configured_name = matrix_names.get(str(path))

    if configured_name:
        return safe_name(configured_name)

    parent = path.parent.name
    if parent:
        return safe_name(f"{parent}_{path.stem}")

    return safe_name(path.stem)


def summary(values):
    """Return practical distribution statistics for a numeric sequence."""
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]

    if values.size == 0:
        return {
            "count": 0,
            "min": None,
            "p05": None,
            "p25": None,
            "median": None,
            "p75": None,
            "p95": None,
            "max": None,
            "mean": None,
            "std": None,
        }

    return {
        "count": int(values.size),
        "min": float(np.min(values)),
        "p05": float(np.percentile(values, 5)),
        "p25": float(np.percentile(values, 25)),
        "median": float(np.median(values)),
        "p75": float(np.percentile(values, 75)),
        "p95": float(np.percentile(values, 95)),
        "max": float(np.max(values)),
        "mean": float(np.mean(values)),
        "std": float(np.std(values)),
    }


def json_ready(value):
    """Convert NumPy values and NaN/inf into JSON-safe Python values."""
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}

    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]

    if isinstance(value, np.ndarray):
        return [json_ready(item) for item in value.tolist()]

    if isinstance(value, (np.integer,)):
        return int(value)

    if isinstance(value, (np.floating, float)):
        value = float(value)
        return value if np.isfinite(value) else None

    return value


def deterministic_order(scores):
    """Sort by score descending, then by original chunk order ascending."""
    chunk_order = np.arange(len(scores))
    return np.lexsort((chunk_order, -scores))


def metric_key(prefix, k):
    return f"{prefix}_at_{k}"


def gold_size_group(size):
    if size == 1:
        return "1"
    if size == 2:
        return "2"
    return "3+"



# Analysis
def analyze_matrix(matrix, question_ids, chunk_ids, gold, metadata):
    """Compute ranking, separation, row, and column diagnostics."""
    if matrix.shape != (len(question_ids), len(chunk_ids)):
        raise ValueError(
            "Matrix shape does not match configured IDs: "
            f"{matrix.shape} vs ({len(question_ids)}, {len(chunk_ids)})"
        )

    missing_gold = [question_id for question_id in question_ids if question_id not in gold]
    if missing_gold:
        raise ValueError(
            f"{len(missing_gold)} matrix question IDs are missing from the gold file. "
            f"First: {missing_gold[:5]}"
        )

    chunk_index = {chunk_id: i for i, chunk_id in enumerate(chunk_ids)}
    per_question_rows = []

    pooled_gold_ranks = []
    answerable_best_ranks = []
    answerable_worst_ranks = []
    answerable_mean_gold_ranks = []

    answerable_best_scores = []
    answerable_second_best_scores = []
    answerable_best_gold_scores = []
    answerable_worst_gold_scores = []
    answerable_best_non_gold_scores = []
    best_gold_margins = []
    complete_gold_margins = []

    zero_gold_best_scores = []
    zero_gold_second_best_scores = []
    zero_gold_top1_gaps = []

    ranking_accumulators = {
        metric_key(metric, k): []
        for metric in ("recall", "hit", "all_gold")
        for k in k_values
    }
    reciprocal_ranks = []

    grouped_rows = {"1": [], "2": [], "3+": []}

    top1_indices = np.empty(matrix.shape[0], dtype=int)

    for row_index, question_id in enumerate(question_ids):
        scores = np.asarray(matrix[row_index], dtype=float)
        order = deterministic_order(scores)
        top1_indices[row_index] = order[0]

        row_gold = gold[question_id]
        gold_chunk_ids = list(row_gold.get("all_required_chunk_ids", []))
        gold_size = len(gold_chunk_ids)

        top_n = min(top_results_to_store, len(chunk_ids))
        top_indices = order[:top_n]
        top_chunk_ids = [chunk_ids[i] for i in top_indices]
        top_scores = [float(scores[i]) for i in top_indices]

        best_score = float(scores[order[0]])
        second_best_score = (
            float(scores[order[1]]) if len(order) > 1 else None
        )
        top1_gap = (
            best_score - second_best_score
            if second_best_score is not None
            else None
        )

        record = {
            "question_id": question_id,
            "question": row_gold.get("question", ""),
            "mapping_status": row_gold.get("mapping_status"),
            "gold_size": gold_size,
            "gold_chunk_ids": json.dumps(gold_chunk_ids, ensure_ascii=False),
            "best_score": best_score,
            "second_best_score": second_best_score,
            "top1_gap": top1_gap,
            "top_chunk_ids": json.dumps(top_chunk_ids, ensure_ascii=False),
            "top_scores": json.dumps(top_scores),
        }

        if gold_size == 0:
            zero_gold_best_scores.append(best_score)
            if second_best_score is not None:
                zero_gold_second_best_scores.append(second_best_score)
                zero_gold_top1_gaps.append(top1_gap)

            record.update({
                "gold_chunk_ranks": "[]",
                "best_gold_rank": np.nan,
                "worst_gold_rank": np.nan,
                "mean_gold_rank": np.nan,
                "mrr": np.nan,
                "best_gold_score": np.nan,
                "worst_gold_score": np.nan,
                "best_non_gold_score": np.nan,
                "best_gold_margin": np.nan,
                "complete_gold_margin": np.nan,
            })

            for k in k_values:
                record[metric_key("recall", k)] = np.nan
                record[metric_key("hit", k)] = np.nan
                record[metric_key("all_gold", k)] = np.nan

            per_question_rows.append(record)
            continue

        missing_chunks = [
            chunk_id for chunk_id in gold_chunk_ids
            if chunk_id not in chunk_index
        ]
        if missing_chunks:
            raise ValueError(
                f"{question_id} contains unknown gold chunks: {missing_chunks}"
            )

        gold_indices = np.array(
            [chunk_index[chunk_id] for chunk_id in gold_chunk_ids],
            dtype=int,
        )

        inverse_ranks = np.empty(len(chunk_ids), dtype=int)
        inverse_ranks[order] = np.arange(1, len(chunk_ids) + 1)
        gold_ranks = inverse_ranks[gold_indices]

        gold_scores = scores[gold_indices]
        non_gold_mask = np.ones(len(chunk_ids), dtype=bool)
        non_gold_mask[gold_indices] = False
        best_non_gold_score = (
            float(np.max(scores[non_gold_mask]))
            if np.any(non_gold_mask)
            else np.nan
        )

        best_gold_rank = int(np.min(gold_ranks))
        worst_gold_rank = int(np.max(gold_ranks))
        mean_gold_rank = float(np.mean(gold_ranks))

        best_gold_score = float(np.max(gold_scores))
        worst_gold_score = float(np.min(gold_scores))
        best_gold_margin = best_gold_score - best_non_gold_score
        complete_gold_margin = worst_gold_score - best_non_gold_score

        mrr = 1.0 / best_gold_rank

        pooled_gold_ranks.extend(gold_ranks.tolist())
        answerable_best_ranks.append(best_gold_rank)
        answerable_worst_ranks.append(worst_gold_rank)
        answerable_mean_gold_ranks.append(mean_gold_rank)

        answerable_best_scores.append(best_score)
        if second_best_score is not None:
            answerable_second_best_scores.append(second_best_score)
        answerable_best_gold_scores.append(best_gold_score)
        answerable_worst_gold_scores.append(worst_gold_score)
        answerable_best_non_gold_scores.append(best_non_gold_score)
        best_gold_margins.append(best_gold_margin)
        complete_gold_margins.append(complete_gold_margin)
        reciprocal_ranks.append(mrr)

        row_metrics = {}
        for k in k_values:
            effective_k = min(k, len(chunk_ids))
            top_k_indices = set(order[:effective_k].tolist())
            gold_in_top_k = sum(
                int(index in top_k_indices)
                for index in gold_indices
            )

            recall = gold_in_top_k / gold_size
            hit = float(gold_in_top_k > 0)
            all_gold = float(gold_in_top_k == gold_size)

            row_metrics[metric_key("recall", k)] = recall
            row_metrics[metric_key("hit", k)] = hit
            row_metrics[metric_key("all_gold", k)] = all_gold

            ranking_accumulators[metric_key("recall", k)].append(recall)
            ranking_accumulators[metric_key("hit", k)].append(hit)
            ranking_accumulators[metric_key("all_gold", k)].append(all_gold)

        record.update({
            "gold_chunk_ranks": json.dumps(gold_ranks.tolist()),
            "best_gold_rank": best_gold_rank,
            "worst_gold_rank": worst_gold_rank,
            "mean_gold_rank": mean_gold_rank,
            "mrr": mrr,
            "best_gold_score": best_gold_score,
            "worst_gold_score": worst_gold_score,
            "best_non_gold_score": best_non_gold_score,
            "best_gold_margin": best_gold_margin,
            "complete_gold_margin": complete_gold_margin,
            **row_metrics,
        })

        grouped_rows[gold_size_group(gold_size)].append(record)
        per_question_rows.append(record)

    per_question = pd.DataFrame(per_question_rows)

    top1_counts = np.bincount(top1_indices, minlength=len(chunk_ids))
    chunk_rows = []

    for column_index, chunk_id in enumerate(chunk_ids):
        column = np.asarray(matrix[:, column_index], dtype=float)
        chunk_rows.append({
            "chunk_id": chunk_id,
            "similarity_mean": float(np.mean(column)),
            "similarity_median": float(np.median(column)),
            "similarity_std": float(np.std(column)),
            "similarity_min": float(np.min(column)),
            "similarity_max": float(np.max(column)),
            "top1_count": int(top1_counts[column_index]),
            "top1_share": float(top1_counts[column_index] / len(question_ids)),
        })

    per_chunk = pd.DataFrame(chunk_rows)

    ranking_metrics = {
        key: float(np.mean(values)) if values else None
        for key, values in ranking_accumulators.items()
    }
    ranking_metrics["mrr"] = (
        float(np.mean(reciprocal_ranks))
        if reciprocal_ranks
        else None
    )

    gold_rank_summary = {
        "pooled_gold_rank": summary(pooled_gold_ranks),
        "best_gold_rank_per_question": summary(answerable_best_ranks),
        "worst_gold_rank_per_question": summary(answerable_worst_ranks),
        "mean_gold_rank_per_question": summary(answerable_mean_gold_ranks),
    }

    score_summary = {
        "all_matrix_values": summary(matrix.ravel()),
        "row_best_score": summary(np.max(matrix, axis=1)),
        "row_mean_score": summary(np.mean(matrix, axis=1)),
        "row_score_std": summary(np.std(matrix, axis=1)),
        "column_mean_score": summary(np.mean(matrix, axis=0)),
        "column_max_score": summary(np.max(matrix, axis=0)),
        "answerable_best_score": summary(answerable_best_scores),
        "answerable_second_best_score": summary(answerable_second_best_scores),
        "best_gold_score": summary(answerable_best_gold_scores),
        "worst_gold_score": summary(answerable_worst_gold_scores),
        "best_non_gold_score": summary(answerable_best_non_gold_scores),
        "best_gold_minus_best_non_gold": summary(best_gold_margins),
        "worst_gold_minus_best_non_gold": summary(complete_gold_margins),
        "zero_gold_best_score": summary(zero_gold_best_scores),
        "zero_gold_second_best_score": summary(zero_gold_second_best_scores),
        "zero_gold_top1_gap": summary(zero_gold_top1_gaps),
    }

    by_gold_set_size = {}
    for group, rows in grouped_rows.items():
        if not rows:
            continue

        group_metrics = {
            "question_count": len(rows),
            "mrr": float(np.mean([row["mrr"] for row in rows])),
            "worst_gold_rank": summary(
                [row["worst_gold_rank"] for row in rows]
            ),
        }

        for k in k_values:
            for prefix in ("recall", "hit", "all_gold"):
                key = metric_key(prefix, k)
                group_metrics[key] = float(np.mean([row[key] for row in rows]))

        by_gold_set_size[group] = group_metrics

    answerable_count = int(np.sum(per_question["gold_size"] > 0))
    zero_gold_count = int(np.sum(per_question["gold_size"] == 0))

    no_gold_top_10_count = int(
        np.sum(
            (per_question["gold_size"] > 0)
            & (per_question[metric_key("hit", 10)] == 0)
        )
    ) if 10 in k_values else None

    worst_over_10 = int(
        np.sum(per_question["worst_gold_rank"] > 10)
    )
    worst_over_20 = int(
        np.sum(per_question["worst_gold_rank"] > 20)
    )

    complete_margin_array = np.asarray(complete_gold_margins, dtype=float)
    best_margin_array = np.asarray(best_gold_margins, dtype=float)

    complete_margin_positive_rate = (
        float(np.mean(complete_margin_array > 0))
        if complete_margin_array.size
        else None
    )
    best_margin_positive_rate = (
        float(np.mean(best_margin_array > 0))
        if best_margin_array.size
        else None
    )

    top_chunks = (
        per_chunk
        .sort_values(["top1_count", "similarity_mean"], ascending=[False, False])
        .head(top_chunks_to_report)
    )

    notable_observations = {
        "answerable_questions": answerable_count,
        "zero_gold_questions": zero_gold_count,
        "questions_with_worst_gold_rank_gt_10": worst_over_10,
        "questions_with_worst_gold_rank_gt_20": worst_over_20,
        "questions_with_no_gold_in_top_10": no_gold_top_10_count,
        "best_gold_margin_positive_rate": best_margin_positive_rate,
        "complete_gold_margin_positive_rate": complete_margin_positive_rate,
        "most_frequent_top1_chunks": top_chunks[
            ["chunk_id", "top1_count", "top1_share", "similarity_mean"]
        ].to_dict(orient="records"),
    }

    analysis = {
        "matrix_metadata": metadata,
        "question_counts": {
            "total": len(question_ids),
            "answerable": answerable_count,
            "zero_gold": zero_gold_count,
        },
        "ranking_metrics": ranking_metrics,
        "gold_rank_summary": gold_rank_summary,
        "score_summary": score_summary,
        "by_gold_set_size": by_gold_set_size,
        "notable_observations": notable_observations,
    }

    return analysis, per_question, per_chunk



# Plots
def save_figure(path):
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def plot_ranking_metrics(analysis, output_dir):
    ranking = analysis["ranking_metrics"]

    plt.figure(figsize=(8, 5))
    for prefix, label in [
        ("recall", "Recall"),
        ("hit", "Hit"),
        ("all_gold", "All-Gold"),
    ]:
        values = [ranking[metric_key(prefix, k)] for k in k_values]
        plt.plot(k_values, values, marker="o", label=label)

    plt.xlabel("k")
    plt.ylabel("Mean metric value")
    plt.ylim(0, 1.02)
    plt.title("Ranking metrics at k")
    plt.legend()
    path = output_dir / "ranking_metrics_at_k.png"
    save_figure(path)
    return path.name


def plot_worst_gold_ranks(per_question, output_dir):
    values = per_question.loc[
        per_question["gold_size"] > 0,
        "worst_gold_rank",
    ].dropna()

    if values.empty:
        return None

    plt.figure(figsize=(8, 5))
    bins = min(40, max(10, int(np.sqrt(len(values)))))
    plt.hist(values, bins=bins)
    plt.xlabel("Worst required-gold rank")
    plt.ylabel("Questions")
    plt.title("Distribution of worst required-gold rank")
    path = output_dir / "worst_gold_rank_distribution.png"
    save_figure(path)
    return path.name


def plot_best_score_distributions(per_question, output_dir):
    answerable = per_question.loc[
        per_question["gold_size"] > 0,
        "best_score",
    ].dropna()

    zero_gold = per_question.loc[
        per_question["gold_size"] == 0,
        "best_score",
    ].dropna()

    if answerable.empty and zero_gold.empty:
        return None

    plt.figure(figsize=(8, 5))
    if not answerable.empty:
        plt.hist(answerable, bins=30, alpha=0.65, label="Answerable")
    if not zero_gold.empty:
        plt.hist(zero_gold, bins=30, alpha=0.65, label="Zero-gold")

    plt.xlabel("Best similarity score")
    plt.ylabel("Questions")
    plt.title("Best-score distribution")
    if not answerable.empty and not zero_gold.empty:
        plt.legend()

    path = output_dir / "best_score_distribution.png"
    save_figure(path)
    return path.name


def plot_gold_vs_non_gold_scores(per_question, output_dir):
    answerable = per_question[per_question["gold_size"] > 0]

    gold_scores = answerable["best_gold_score"].dropna()
    non_gold_scores = answerable["best_non_gold_score"].dropna()

    if gold_scores.empty or non_gold_scores.empty:
        return None

    plt.figure(figsize=(8, 5))
    plt.hist(gold_scores, bins=30, alpha=0.65, label="Best gold score")
    plt.hist(non_gold_scores, bins=30, alpha=0.65, label="Best non-gold score")
    plt.xlabel("Similarity score")
    plt.ylabel("Questions")
    plt.title("Best gold vs. best non-gold score")
    plt.legend()
    path = output_dir / "best_gold_vs_best_non_gold_scores.png"
    save_figure(path)
    return path.name


def plot_complete_margin(per_question, output_dir):
    values = per_question.loc[
        per_question["gold_size"] > 0,
        "complete_gold_margin",
    ].dropna()

    if values.empty:
        return None

    plt.figure(figsize=(8, 5))
    plt.hist(values, bins=30)
    plt.axvline(0, linestyle="--")
    plt.xlabel("Worst gold score - best non-gold score")
    plt.ylabel("Questions")
    plt.title("Complete-gold score separation")
    path = output_dir / "complete_gold_margin_distribution.png"
    save_figure(path)
    return path.name


def plot_gold_size_metric(analysis, output_dir, prefix, title, filename):
    groups = [
        group
        for group in ("1", "2", "3+")
        if group in analysis["by_gold_set_size"]
    ]

    if not groups:
        return None

    k_values_no_one = [k for k in k_values if k in (3, 5, 10)]
    if not k_values_no_one:
        k_values_no_one = k_values

    x = np.arange(len(groups))
    width = 0.8 / len(k_values_no_one)

    plt.figure(figsize=(8, 5))

    for i, k in enumerate(k_values_no_one):
        values = [
            analysis["by_gold_set_size"][group][metric_key(prefix, k)]
            for group in groups
        ]
        positions = x - 0.4 + width / 2 + i * width
        plt.bar(positions, values, width=width, label=f"@{k}")

    plt.xticks(x, [f"{group} gold" for group in groups])
    plt.xlabel("Required gold chunks per question")
    plt.ylabel("Mean metric value")
    plt.ylim(0, 1.02)
    plt.title(title)
    plt.legend()

    path = output_dir / filename
    save_figure(path)
    return path.name


def plot_top1_chunk_frequency(per_chunk, output_dir):
    top = (
        per_chunk
        .sort_values(["top1_count", "similarity_mean"], ascending=[False, False])
        .head(top_chunks_to_report)
    )

    if top.empty or top["top1_count"].max() == 0:
        return None

    plt.figure(figsize=(10, 6))
    positions = np.arange(len(top))
    plt.bar(positions, top["top1_count"])
    plt.xticks(positions, top["chunk_id"], rotation=75, ha="right")
    plt.xlabel("Chunk ID")
    plt.ylabel("Times ranked first")
    plt.title(f"Most frequent top-ranked chunks (top {len(top)})")
    path = output_dir / "top_ranked_chunk_frequency.png"
    save_figure(path)
    return path.name


def create_plots(analysis, per_question, per_chunk, output_dir):
    files = []

    plot_functions = [
        lambda: plot_ranking_metrics(analysis, output_dir),
        lambda: plot_worst_gold_ranks(per_question, output_dir),
        lambda: plot_best_score_distributions(per_question, output_dir),
        lambda: plot_gold_vs_non_gold_scores(per_question, output_dir),
        lambda: plot_complete_margin(per_question, output_dir),
        lambda: plot_gold_size_metric(
            analysis,
            output_dir,
            "recall",
            "Recall by gold-set size",
            "recall_by_gold_set_size.png",
        ),
        lambda: plot_gold_size_metric(
            analysis,
            output_dir,
            "all_gold",
            "All-Gold by gold-set size",
            "all_gold_by_gold_set_size.png",
        ),
        lambda: plot_top1_chunk_frequency(per_chunk, output_dir),
    ]

    for create_plot in plot_functions:
        filename = create_plot()
        if filename:
            files.append(filename)

    return files


# Overview
def overview_row(matrix_id, analysis):
    metadata = analysis["matrix_metadata"]
    ranking = analysis["ranking_metrics"]
    scores = analysis["score_summary"]
    ranks = analysis["gold_rank_summary"]
    observations = analysis["notable_observations"]

    row = {
        "matrix_id": matrix_id,
        "configured_path": metadata["configured_path"],
        "filename": metadata["filename"],
        "rows": metadata["rows"],
        "columns": metadata["columns"],
        "dtype": metadata["dtype"],
        "answerable_questions": analysis["question_counts"]["answerable"],
        "zero_gold_questions": analysis["question_counts"]["zero_gold"],
        "mrr": ranking["mrr"],
        "mean_gold_rank": ranks["pooled_gold_rank"]["mean"],
        "median_gold_rank": ranks["pooled_gold_rank"]["median"],
        "mean_worst_gold_rank": ranks["worst_gold_rank_per_question"]["mean"],
        "median_worst_gold_rank": ranks["worst_gold_rank_per_question"]["median"],
        "p95_worst_gold_rank": ranks["worst_gold_rank_per_question"]["p95"],
        "answerable_best_score_median": scores["answerable_best_score"]["median"],
        "zero_gold_best_score_median": scores["zero_gold_best_score"]["median"],
        "best_gold_score_median": scores["best_gold_score"]["median"],
        "best_non_gold_score_median": scores["best_non_gold_score"]["median"],
        "complete_gold_margin_median": scores[
            "worst_gold_minus_best_non_gold"
        ]["median"],
        "complete_gold_margin_positive_rate": observations[
            "complete_gold_margin_positive_rate"
        ],
        "questions_with_worst_gold_rank_gt_10": observations[
            "questions_with_worst_gold_rank_gt_10"
        ],
        "questions_with_worst_gold_rank_gt_20": observations[
            "questions_with_worst_gold_rank_gt_20"
        ],
    }

    for k in k_values:
        for prefix in ("recall", "hit", "all_gold"):
            key = metric_key(prefix, k)
            row[key] = ranking[key]

    return row


def grouped_overview_plot(overview, prefix, title, filename, output_dir):
    x = np.arange(len(overview))
    width = 0.8 / len(k_values)

    plt.figure(figsize=(max(8, len(overview) * 1.8), 5))

    for i, k in enumerate(k_values):
        positions = x - 0.4 + width / 2 + i * width
        plt.bar(
            positions,
            overview[metric_key(prefix, k)],
            width=width,
            label=f"@{k}",
        )

    plt.xticks(x, overview["matrix_id"], rotation=30, ha="right")
    plt.xlabel("Similarity matrix")
    plt.ylabel("Mean metric value")
    plt.ylim(0, 1.02)
    plt.title(title)
    plt.legend()

    path = output_dir / filename
    save_figure(path)
    return path.name


def create_overview_plots(overview, output_dir):
    files = []

    files.append(
        grouped_overview_plot(
            overview,
            "recall",
            "Recall comparison across matrices",
            "overview_recall_at_k.png",
            output_dir,
        )
    )
    files.append(
        grouped_overview_plot(
            overview,
            "hit",
            "Hit comparison across matrices",
            "overview_hit_at_k.png",
            output_dir,
        )
    )
    files.append(
        grouped_overview_plot(
            overview,
            "all_gold",
            "All-Gold comparison across matrices",
            "overview_all_gold_at_k.png",
            output_dir,
        )
    )

    plt.figure(figsize=(max(8, len(overview) * 1.8), 5))
    x = np.arange(len(overview))
    plt.bar(x, overview["mrr"])
    plt.xticks(x, overview["matrix_id"], rotation=30, ha="right")
    plt.xlabel("Similarity matrix")
    plt.ylabel("MRR")
    plt.ylim(0, 1.02)
    plt.title("MRR comparison across matrices")
    path = output_dir / "overview_mrr.png"
    save_figure(path)
    files.append(path.name)

    plt.figure(figsize=(max(8, len(overview) * 1.8), 5))
    width = 0.36
    x = np.arange(len(overview))
    plt.bar(
        x - width / 2,
        overview["answerable_best_score_median"],
        width=width,
        label="Answerable",
    )
    plt.bar(
        x + width / 2,
        overview["zero_gold_best_score_median"],
        width=width,
        label="Zero-gold",
    )
    plt.xticks(x, overview["matrix_id"], rotation=30, ha="right")
    plt.xlabel("Similarity matrix")
    plt.ylabel("Median best similarity score")
    plt.title("Best-score medians: answerable vs. zero-gold")
    plt.legend()
    path = output_dir / "overview_best_score_medians.png"
    save_figure(path)
    files.append(path.name)

    plt.figure(figsize=(max(8, len(overview) * 1.8), 5))
    x = np.arange(len(overview))
    plt.bar(x, overview["complete_gold_margin_median"])
    plt.axhline(0, linestyle="--")
    plt.xticks(x, overview["matrix_id"], rotation=30, ha="right")
    plt.xlabel("Similarity matrix")
    plt.ylabel("Median worst-gold minus best-non-gold score")
    plt.title("Complete-gold score-separation comparison")
    path = output_dir / "overview_complete_gold_margin.png"
    save_figure(path)
    files.append(path.name)

    return files



# Main
def main():
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    question_ids = load_id_list(question_ids_path, "question_ids")
    chunk_ids = load_id_list(chunk_ids_path, "chunk_ids")
    gold = load_gold(gold_path)

    overview_rows = []
    seen_ids = set()

    for configured_path in matrix_paths:
        matrix_path = Path(configured_path)
        matrix_id = matrix_identifier(matrix_path)

        if matrix_id in seen_ids:
            raise ValueError(
                f"Duplicate matrix identifier '{matrix_id}'. "
                "Use MATRIX_NAMES to assign unique names."
            )
        seen_ids.add(matrix_id)

        matrix = load_matrix(matrix_path)

        sidecar_path, sidecar_metadata = load_sidecar_metadata(matrix_path)

        metadata = {
            "matrix_id": matrix_id,
            "configured_path": str(configured_path),
            "resolved_path": str(matrix_path.resolve()),
            "filename": matrix_path.name,
            "shape": [int(matrix.shape[0]), int(matrix.shape[1])],
            "rows": int(matrix.shape[0]),
            "columns": int(matrix.shape[1]),
            "dtype": str(matrix.dtype),
            "file_size_bytes": int(matrix_path.stat().st_size),
            "question_ids_path": str(question_ids_path),
            "chunk_ids_path": str(chunk_ids_path),
            "gold_path": str(gold_path),
            "ranking_tie_break": "similarity descending, then original chunk order",
            "k_values": k_values,
            "sidecar_metadata_path": sidecar_path,
            "sidecar_metadata": sidecar_metadata,
        }

        matrix_output_dir = output_root / matrix_id
        matrix_output_dir.mkdir(parents=True, exist_ok=True)

        analysis, per_question, per_chunk = analyze_matrix(
            matrix=matrix,
            question_ids=question_ids,
            chunk_ids=chunk_ids,
            gold=gold,
            metadata=metadata,
        )

        per_question_filename = "per_question.csv"
        per_chunk_filename = "per_chunk.csv"

        per_question.to_csv(
            matrix_output_dir / per_question_filename,
            index=False,
        )
        per_chunk.to_csv(
            matrix_output_dir / per_chunk_filename,
            index=False,
        )

        visualization_files = create_plots(
            analysis,
            per_question,
            per_chunk,
            matrix_output_dir,
        )

        analysis["output_files"] = {
            "per_question": per_question_filename,
            "per_chunk": per_chunk_filename,
            "visualizations": visualization_files,
        }

        with open(
            matrix_output_dir / "analysis.json",
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                json_ready(analysis),
                f,
                ensure_ascii=False,
                indent=2,
            )

        overview_rows.append(overview_row(matrix_id, analysis))

        print(f"Analyzed {matrix_id}: {matrix.shape}")

    overview = pd.DataFrame(overview_rows)
    overview.to_csv(output_root / "overview.csv", index=False)

    overview_records = overview.where(
        pd.notnull(overview),
        None,
    ).to_dict(orient="records")

    overview_plot_files = create_overview_plots(
        overview,
        output_root,
    )

    overview_json = {
        "matrices": json_ready(overview_records),
        "visualizations": overview_plot_files,
        "k_values": k_values,
    }

    with open(output_root / "overview.json", "w", encoding="utf-8") as f:
        json.dump(
            json_ready(overview_json),
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"\nAnalysis written to: {output_root.resolve()}")


if __name__ == "__main__":
    main()
