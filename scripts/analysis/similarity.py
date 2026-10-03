import json

import matplotlib

import numpy as np
import pandas as pd

# Select the file-only backend before importing pyplot.
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

K_VALUES = [1, 2, 3, 5, 10]
TOP_RESULTS_TO_STORE = 10
TOP_CHUNKS_TO_REPORT = 20


def summarize(values):
    """
    Summarize finite numeric values; absent observations have null
    statistics.
    """
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


def jsonable(value):
    """Convert NumPy values and non-finite statistics into JSON-safe values."""
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [jsonable(item) for item in value]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        value = float(value)
        return value if np.isfinite(value) else None
    if isinstance(value, float):
        return value if np.isfinite(value) else None
    return value


def metric_name(prefix, k):
    """Build an at-k metric column name."""
    return f"{prefix}_at_{k}"


def gold_group(size):
    """Assign evidence sets to the 1, 2 or 3+ chunk group."""
    return "1" if size == 1 else "2" if size == 2 else "3+"


def gold_ranking_metrics(
    scores, order, gold_chunk_ids, chunk_ids, chunk_index
):
    """
    Measure gold ranks and score separation using the stable candidate
    order.
    """
    gold_size = len(gold_chunk_ids)
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
    best_non_gold = float(np.max(scores[non_gold_mask]))

    best_gold_rank = int(np.min(gold_ranks))
    worst_gold_rank = int(np.max(gold_ranks))
    mean_gold_rank = float(np.mean(gold_ranks))
    best_gold_score = float(np.max(gold_scores))
    worst_gold_score = float(np.min(gold_scores))
    best_margin = best_gold_score - best_non_gold
    complete_margin = worst_gold_score - best_non_gold
    mrr = 1.0 / best_gold_rank

    metrics = {}
    for k in K_VALUES:
        top_k = set(order[: min(k, len(chunk_ids))].tolist())
        gold_in_top_k = sum(int(index in top_k) for index in gold_indices)
        recall = gold_in_top_k / gold_size
        hit = float(gold_in_top_k > 0)
        all_gold = float(gold_in_top_k == gold_size)

        for prefix, value in (
            ("recall", recall),
            ("hit", hit),
            ("all_gold", all_gold),
        ):
            key = metric_name(prefix, k)
            metrics[key] = value

    return {
        "gold_chunk_ranks": json.dumps(gold_ranks.tolist()),
        "best_gold_rank": best_gold_rank,
        "worst_gold_rank": worst_gold_rank,
        "mean_gold_rank": mean_gold_rank,
        "mrr": mrr,
        "best_gold_score": best_gold_score,
        "worst_gold_score": worst_gold_score,
        "best_non_gold_score": best_non_gold,
        "best_gold_margin": best_margin,
        "complete_gold_margin": complete_margin,
        **metrics,
    }


def analyze_question(scores, question_id, chunk_ids, chunk_index, gold):
    """
    Build one diagnostic record; unanswerable questions have no gold
    ranks.
    """
    scores = np.asarray(scores, dtype=float)
    order = np.lexsort((np.arange(len(scores)), -scores))

    gold_row = gold[question_id]
    gold_chunk_ids = list(gold_row.get("all_required_chunk_ids", []))
    gold_size = len(gold_chunk_ids)

    top_indices = order[: min(TOP_RESULTS_TO_STORE, len(chunk_ids))]
    best_score = float(scores[order[0]])
    second_score = float(scores[order[1]]) if len(order) > 1 else None
    top1_gap = best_score - second_score if second_score is not None else None

    record = {
        "question_id": question_id,
        "question": gold_row.get("question", ""),
        "mapping_status": gold_row.get("mapping_status"),
        "gold_size": gold_size,
        "gold_chunk_ids": json.dumps(gold_chunk_ids, ensure_ascii=False),
        "best_score": best_score,
        "second_best_score": second_score,
        "top1_gap": top1_gap,
        "top_chunk_ids": json.dumps(
            [chunk_ids[i] for i in top_indices], ensure_ascii=False
        ),
        "top_scores": json.dumps([float(scores[i]) for i in top_indices]),
    }

    if gold_size == 0:
        record.update(
            {
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
            }
        )
        for k in K_VALUES:
            record[metric_name("recall", k)] = np.nan
            record[metric_name("hit", k)] = np.nan
            record[metric_name("all_gold", k)] = np.nan

        return record, int(order[0])

    record.update(
        gold_ranking_metrics(
            scores, order, gold_chunk_ids, chunk_ids, chunk_index
        )
    )
    return record, int(order[0])


def chunk_statistics(matrix, chunk_ids, top1_indices):
    """Summarize each candidate's scores and frequency of ranking first."""
    top1_counts = np.bincount(top1_indices, minlength=len(chunk_ids))
    per_chunk = pd.DataFrame(
        [
            {
                "chunk_id": chunk_id,
                "similarity_mean": float(np.mean(matrix[:, index])),
                "similarity_median": float(np.median(matrix[:, index])),
                "similarity_std": float(np.std(matrix[:, index])),
                "similarity_min": float(np.min(matrix[:, index])),
                "similarity_max": float(np.max(matrix[:, index])),
                "top1_count": int(top1_counts[index]),
                "top1_share": float(top1_counts[index] / matrix.shape[0]),
            }
            for index, chunk_id in enumerate(chunk_ids)
        ]
    )

    return per_chunk


def summarize_gold_sizes(grouped_rows):
    """Average ranking diagnostics within each non-empty gold-size group."""
    grouped_metrics = {}
    for group, rows in grouped_rows.items():
        if not rows:
            continue

        grouped_metrics[group] = {
            "question_count": len(rows),
            "mrr": float(np.mean([row["mrr"] for row in rows])),
            "worst_gold_rank": summarize(
                [row["worst_gold_rank"] for row in rows]
            ),
        }
        for k in K_VALUES:
            for prefix in ("recall", "hit", "all_gold"):
                key = metric_name(prefix, k)
                grouped_metrics[group][key] = float(
                    np.mean([row[key] for row in rows])
                )

    return grouped_metrics


def summarize_scores(matrix, answerable, zero_gold):
    """Summarize similarities for answerable and zero-gold questions."""
    best_gold_margins = [row["best_gold_margin"] for row in answerable]
    complete_gold_margins = [row["complete_gold_margin"] for row in answerable]
    return {
        "all_matrix_values": summarize(matrix.ravel()),
        "row_best_score": summarize(np.max(matrix, axis=1)),
        "row_mean_score": summarize(np.mean(matrix, axis=1)),
        "row_score_std": summarize(np.std(matrix, axis=1)),
        "column_mean_score": summarize(np.mean(matrix, axis=0)),
        "column_max_score": summarize(np.max(matrix, axis=0)),
        "answerable_best_score": summarize(
            [row["best_score"] for row in answerable]
        ),
        "answerable_second_best_score": summarize(
            [
                row["second_best_score"]
                for row in answerable
                if row["second_best_score"] is not None
            ]
        ),
        "best_gold_score": summarize(
            [row["best_gold_score"] for row in answerable]
        ),
        "worst_gold_score": summarize(
            [row["worst_gold_score"] for row in answerable]
        ),
        "best_non_gold_score": summarize(
            [row["best_non_gold_score"] for row in answerable]
        ),
        "best_gold_minus_best_non_gold": summarize(best_gold_margins),
        "worst_gold_minus_best_non_gold": summarize(complete_gold_margins),
        "zero_gold_best_score": summarize(
            [row["best_score"] for row in zero_gold]
        ),
        "zero_gold_second_best_score": summarize(
            [
                row["second_best_score"]
                for row in zero_gold
                if row["second_best_score"] is not None
            ]
        ),
        "zero_gold_top1_gap": summarize(
            [
                row["top1_gap"]
                for row in zero_gold
                if row["top1_gap"] is not None
            ]
        ),
    }


def summarize_matrix(matrix, records, per_question, per_chunk):
    """Combine ranking, score and evidence-size statistics."""
    answerable = [row for row in records if row["gold_size"] > 0]
    zero_gold = [row for row in records if row["gold_size"] == 0]
    # Pool individual gold ranks; other summaries weight each question equally.
    pooled_gold_ranks = [
        rank
        for row in answerable
        for rank in json.loads(row["gold_chunk_ranks"])
    ]
    grouped_rows = {
        group: [
            row for row in answerable if gold_group(row["gold_size"]) == group
        ]
        for group in ("1", "2", "3+")
    }
    ranking_values = {
        metric_name(metric, k): [
            row[metric_name(metric, k)] for row in answerable
        ]
        for metric in ("recall", "hit", "all_gold")
        for k in K_VALUES
    }
    reciprocal_ranks = [row["mrr"] for row in answerable]
    best_gold_margins = [row["best_gold_margin"] for row in answerable]
    complete_gold_margins = [row["complete_gold_margin"] for row in answerable]
    ranking_metrics = {
        key: float(np.mean(values)) if values else None
        for key, values in ranking_values.items()
    }
    ranking_metrics["mrr"] = (
        float(np.mean(reciprocal_ranks)) if reciprocal_ranks else None
    )

    grouped_metrics = summarize_gold_sizes(grouped_rows)

    answerable_count = int(np.sum(per_question["gold_size"] > 0))
    zero_gold_count = int(np.sum(per_question["gold_size"] == 0))
    top_chunks = per_chunk.sort_values(
        ["top1_count", "similarity_mean"], ascending=[False, False]
    ).head(TOP_CHUNKS_TO_REPORT)

    analysis = {
        "question_counts": {
            "total": len(records),
            "answerable": answerable_count,
            "zero_gold": zero_gold_count,
        },
        "ranking_metrics": ranking_metrics,
        "gold_rank_summary": {
            "pooled_gold_rank": summarize(pooled_gold_ranks),
            "best_gold_rank_per_question": summarize(
                [row["best_gold_rank"] for row in answerable]
            ),
            "worst_gold_rank_per_question": summarize(
                [row["worst_gold_rank"] for row in answerable]
            ),
            "mean_gold_rank_per_question": summarize(
                [row["mean_gold_rank"] for row in answerable]
            ),
        },
        "score_summary": summarize_scores(matrix, answerable, zero_gold),
        "by_gold_set_size": grouped_metrics,
        "notable_observations": {
            "answerable_questions": answerable_count,
            "zero_gold_questions": zero_gold_count,
            "questions_with_worst_gold_rank_gt_10": int(
                np.sum(per_question["worst_gold_rank"] > 10)
            ),
            "questions_with_worst_gold_rank_gt_20": int(
                np.sum(per_question["worst_gold_rank"] > 20)
            ),
            "questions_with_no_gold_in_top_10": int(
                np.sum(
                    (per_question["gold_size"] > 0)
                    & (per_question[metric_name("hit", 10)] == 0)
                )
            ),
            "best_gold_margin_positive_rate": (
                float(np.mean(np.asarray(best_gold_margins) > 0))
                if best_gold_margins
                else None
            ),
            "complete_gold_margin_positive_rate": (
                float(np.mean(np.asarray(complete_gold_margins) > 0))
                if complete_gold_margins
                else None
            ),
            "most_frequent_top1_chunks": top_chunks[
                ["chunk_id", "top1_count", "top1_share", "similarity_mean"]
            ].to_dict(orient="records"),
        },
    }

    return analysis


def analyze_matrix(matrix, question_ids, chunk_ids, gold):
    """Calculate summary statistics and question/chunk tables."""
    chunk_index = {chunk_id: index for index, chunk_id in enumerate(chunk_ids)}
    records = []
    top1_indices = np.empty(matrix.shape[0], dtype=int)
    for row_index, question_id in enumerate(question_ids):
        record, top1_index = analyze_question(
            matrix[row_index], question_id, chunk_ids, chunk_index, gold
        )
        records.append(record)
        top1_indices[row_index] = top1_index

    per_question = pd.DataFrame(records)
    per_chunk = chunk_statistics(matrix, chunk_ids, top1_indices)
    analysis = summarize_matrix(matrix, records, per_question, per_chunk)
    return analysis, per_question, per_chunk


def save_current_figure(path):
    """Save the plot and close its figure."""
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def plot_ranking_metrics(analysis, output_dir):
    """
    Plot recall, hit rate and complete-evidence rate over candidate
    ranks.
    """
    files = []
    ranking = analysis["ranking_metrics"]
    plt.figure(figsize=(8, 5))
    for prefix, label in [
        ("recall", "Recall"),
        ("hit", "Hit"),
        ("all_gold", "All-Gold"),
    ]:
        plt.plot(
            K_VALUES,
            [ranking[metric_name(prefix, k)] for k in K_VALUES],
            marker="o",
            label=label,
        )
    plt.xlabel("k")
    plt.ylabel("Mean metric value")
    plt.ylim(0, 1.02)
    plt.title("Ranking metrics at k")
    plt.legend()
    path = output_dir / "ranking_metrics_at_k.png"
    save_current_figure(path)
    files.append(path.name)

    return files


def plot_gold_distributions(per_question, output_dir):
    """Plot required-gold ranks and complete-evidence score separation."""
    files = []
    plots = [
        (
            "worst_gold_rank_distribution.png",
            "worst required-gold rank",
            per_question.loc[
                per_question["gold_size"] > 0, "worst_gold_rank"
            ].dropna(),
        ),
        (
            "complete_gold_margin_distribution.png",
            "complete-gold score separation",
            per_question.loc[
                per_question["gold_size"] > 0,
                "complete_gold_margin",
            ].dropna(),
        ),
    ]
    for filename, title, values in plots:
        if values.empty:
            continue
        plt.figure(figsize=(8, 5))
        plt.hist(values, bins=min(40, max(10, int(np.sqrt(len(values))))))
        if filename == "complete_gold_margin_distribution.png":
            plt.axvline(0, linestyle="--")
            plt.xlabel("Worst gold score - best non-gold score")
        else:
            plt.xlabel("Worst required-gold rank")
        plt.ylabel("Questions")
        plt.title(title.title())
        path = output_dir / filename
        save_current_figure(path)
        files.append(path.name)

    return files


def plot_best_scores(per_question, output_dir):
    """Compare top scores for answerable and zero-gold questions."""
    files = []
    answerable_best = per_question.loc[
        per_question["gold_size"] > 0,
        "best_score",
    ].dropna()
    zero_gold_best = per_question.loc[
        per_question["gold_size"] == 0,
        "best_score",
    ].dropna()
    if not answerable_best.empty or not zero_gold_best.empty:
        plt.figure(figsize=(8, 5))
        if not answerable_best.empty:
            plt.hist(answerable_best, bins=30, alpha=0.65, label="Answerable")
        if not zero_gold_best.empty:
            plt.hist(zero_gold_best, bins=30, alpha=0.65, label="Zero-gold")
        plt.xlabel("Best similarity score")
        plt.ylabel("Questions")
        plt.title("Best-score distribution")
        if not answerable_best.empty and not zero_gold_best.empty:
            plt.legend()
        path = output_dir / "best_score_distribution.png"
        save_current_figure(path)
        files.append(path.name)

    return files


def plot_gold_scores(per_question, output_dir):
    """Compare the best supporting and non-supporting candidate scores."""
    files = []
    answerable = per_question[per_question["gold_size"] > 0]
    if not answerable.empty:
        plt.figure(figsize=(8, 5))
        plt.hist(
            answerable["best_gold_score"].dropna(),
            bins=30,
            alpha=0.65,
            label="Best gold score",
        )
        plt.hist(
            answerable["best_non_gold_score"].dropna(),
            bins=30,
            alpha=0.65,
            label="Best non-gold score",
        )
        plt.xlabel("Similarity score")
        plt.ylabel("Questions")
        plt.title("Best gold vs. best non-gold score")
        plt.legend()
        path = output_dir / "best_gold_vs_best_non_gold_scores.png"
        save_current_figure(path)
        files.append(path.name)

    return files


def plot_gold_size_metrics(analysis, output_dir):
    """Compare at-k retrieval metrics across gold-size groups."""
    files = []
    for prefix, title, filename in [
        ("recall", "Recall by gold-set size", "recall_by_gold_set_size.png"),
        (
            "all_gold",
            "All-Gold by gold-set size",
            "all_gold_by_gold_set_size.png",
        ),
    ]:
        groups = [
            group
            for group in ("1", "2", "3+")
            if group in analysis["by_gold_set_size"]
        ]
        if not groups:
            continue

        plotted_k = [k for k in K_VALUES if k in (3, 5, 10)] or K_VALUES
        x = np.arange(len(groups))
        width = 0.8 / len(plotted_k)

        plt.figure(figsize=(8, 5))
        for i, k in enumerate(plotted_k):
            values = [
                analysis["by_gold_set_size"][group][metric_name(prefix, k)]
                for group in groups
            ]
            plt.bar(
                x - 0.4 + width / 2 + i * width,
                values,
                width=width,
                label=f"@{k}",
            )
        plt.xticks(x, [f"{group} gold" for group in groups])
        plt.xlabel("Required gold chunks per question")
        plt.ylabel("Mean metric value")
        plt.ylim(0, 1.02)
        plt.title(title)
        plt.legend()
        path = output_dir / filename
        save_current_figure(path)
        files.append(path.name)

    return files


def plot_chunk_frequency(per_chunk, output_dir):
    """Plot the most frequently top-ranked evidence chunks."""
    files = []
    top_chunks = per_chunk.sort_values(
        ["top1_count", "similarity_mean"], ascending=[False, False]
    ).head(TOP_CHUNKS_TO_REPORT)
    if not top_chunks.empty and top_chunks["top1_count"].max() > 0:
        plt.figure(figsize=(10, 6))
        positions = np.arange(len(top_chunks))
        plt.bar(positions, top_chunks["top1_count"])
        plt.xticks(positions, top_chunks["chunk_id"], rotation=75, ha="right")
        plt.xlabel("Chunk ID")
        plt.ylabel("Times ranked first")
        plt.title(f"Most frequent top-ranked chunks (top {len(top_chunks)})")
        path = output_dir / "top_ranked_chunk_frequency.png"
        save_current_figure(path)
        files.append(path.name)

    return files


def make_matrix_plots(analysis, per_question, per_chunk, output_dir):
    """Create the diagnostic plots and return their filenames."""
    files = []
    files.extend(plot_ranking_metrics(analysis, output_dir))
    files.extend(plot_gold_distributions(per_question, output_dir))
    files.extend(plot_best_scores(per_question, output_dir))
    files.extend(plot_gold_scores(per_question, output_dir))
    files.extend(plot_gold_size_metrics(analysis, output_dir))
    files.extend(plot_chunk_frequency(per_chunk, output_dir))
    return files
