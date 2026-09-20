from pathlib import Path
import json

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


MATRICES = [
    (
        "tfidf_cosine",
        Path("data/produced_v2/similarity_matrices/tf_idf/cosine_similarity_matrix.npy"),
    ),
    (
        "sentence_bert",
        Path(
            "data/produced_v2/similarity_matrices/"
            "sentence_bert/cosine_similarity_matrix.npy"
        ),
    ),
    (
        "retrieval_bi_encoder",
        Path(
            "data/produced_v2/similarity_matrices/"
            "retrieval_bi_encoder/cosine_similarity_matrix.npy"
        ),
    ),
]

GOLD_PATH = Path("data/processed/qamappings/qa_mapping_merged.jsonl")
QUESTION_IDS_PATH = Path("data/produced_v2/similarity_matrices/tf_idf/question_ids.json")
CHUNK_IDS_PATH = Path("data/produced_v2/similarity_matrices/tf_idf/chunk_ids.json")
OUTPUT_DIR = Path("data/produced_v2/similarity_analysis")

K_VALUES = [1, 2, 3, 5, 10]
TOP_RESULTS_TO_STORE = 10
TOP_CHUNKS_TO_REPORT = 20


def summarize(values):
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


def read_inputs():
    with QUESTION_IDS_PATH.open("r", encoding="utf-8") as file:
        question_ids = json.load(file)
    with CHUNK_IDS_PATH.open("r", encoding="utf-8") as file:
        chunk_ids = json.load(file)

    gold = {}
    with GOLD_PATH.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                row = json.loads(line)
                gold[row["question_id"]] = row

    return question_ids, chunk_ids, gold


def metric_name(prefix, k):
    return f"{prefix}_at_{k}"


def gold_group(size):
    return "1" if size == 1 else "2" if size == 2 else "3+"


def analyze_matrix(matrix, question_ids, chunk_ids, gold):
    chunk_index = {
        chunk_id: index
        for index, chunk_id in enumerate(chunk_ids)
    }

    per_question_rows = []
    top1_indices = np.empty(matrix.shape[0], dtype=int)

    pooled_gold_ranks = []
    best_ranks = []
    worst_ranks = []
    mean_ranks = []
    reciprocal_ranks = []

    answerable_best_scores = []
    answerable_second_scores = []
    best_gold_scores = []
    worst_gold_scores = []
    best_non_gold_scores = []
    best_gold_margins = []
    complete_gold_margins = []

    zero_gold_best_scores = []
    zero_gold_second_scores = []
    zero_gold_top1_gaps = []

    ranking_values = {
        metric_name(metric, k): []
        for metric in ("recall", "hit", "all_gold")
        for k in K_VALUES
    }
    grouped_rows = {"1": [], "2": [], "3+": []}

    for row_index, question_id in enumerate(question_ids):
        scores = np.asarray(matrix[row_index], dtype=float)
        order = np.lexsort((np.arange(len(scores)), -scores))
        top1_indices[row_index] = order[0]

        gold_row = gold[question_id]
        gold_chunk_ids = list(gold_row.get("all_required_chunk_ids", []))
        gold_size = len(gold_chunk_ids)

        top_indices = order[:min(TOP_RESULTS_TO_STORE, len(chunk_ids))]
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
            "top_chunk_ids": json.dumps([chunk_ids[i] for i in top_indices], ensure_ascii=False),
            "top_scores": json.dumps([float(scores[i]) for i in top_indices]),
        }

        if gold_size == 0:
            zero_gold_best_scores.append(best_score)
            if second_score is not None:
                zero_gold_second_scores.append(second_score)
                zero_gold_top1_gaps.append(top1_gap)

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

            per_question_rows.append(record)
            continue

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

        pooled_gold_ranks.extend(gold_ranks.tolist())
        best_ranks.append(best_gold_rank)
        worst_ranks.append(worst_gold_rank)
        mean_ranks.append(mean_gold_rank)
        reciprocal_ranks.append(mrr)

        answerable_best_scores.append(best_score)
        if second_score is not None:
            answerable_second_scores.append(second_score)
        best_gold_scores.append(best_gold_score)
        worst_gold_scores.append(worst_gold_score)
        best_non_gold_scores.append(best_non_gold)
        best_gold_margins.append(best_margin)
        complete_gold_margins.append(complete_margin)

        metrics = {}
        for k in K_VALUES:
            top_k = set(order[:min(k, len(chunk_ids))].tolist())
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
                ranking_values[key].append(value)

        record.update(
            {
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
        )
        grouped_rows[gold_group(gold_size)].append(record)
        per_question_rows.append(record)

    per_question = pd.DataFrame(per_question_rows)

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
                "top1_share": float(top1_counts[index] / len(question_ids)),
            }
            for index, chunk_id in enumerate(chunk_ids)
        ]
    )

    ranking_metrics = {
        key: float(np.mean(values)) if values else None
        for key, values in ranking_values.items()
    }
    ranking_metrics["mrr"] = (
        float(np.mean(reciprocal_ranks))
        if reciprocal_ranks
        else None
    )

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
                grouped_metrics[group][key] = float(np.mean([row[key] for row in rows]))

    answerable_count = int(np.sum(per_question["gold_size"] > 0))
    zero_gold_count = int(np.sum(per_question["gold_size"] == 0))
    top_chunks = (
        per_chunk
        .sort_values(["top1_count", "similarity_mean"], ascending=[False, False])
        .head(TOP_CHUNKS_TO_REPORT)
    )

    analysis = {
        "question_counts": {
            "total": len(question_ids),
            "answerable": answerable_count,
            "zero_gold": zero_gold_count,
        },
        "ranking_metrics": ranking_metrics,
        "gold_rank_summary": {
            "pooled_gold_rank": summarize(pooled_gold_ranks),
            "best_gold_rank_per_question": summarize(best_ranks),
            "worst_gold_rank_per_question": summarize(worst_ranks),
            "mean_gold_rank_per_question": summarize(mean_ranks),
        },
        "score_summary": {
            "all_matrix_values": summarize(matrix.ravel()),
            "row_best_score": summarize(np.max(matrix, axis=1)),
            "row_mean_score": summarize(np.mean(matrix, axis=1)),
            "row_score_std": summarize(np.std(matrix, axis=1)),
            "column_mean_score": summarize(np.mean(matrix, axis=0)),
            "column_max_score": summarize(np.max(matrix, axis=0)),
            "answerable_best_score": summarize(answerable_best_scores),
            "answerable_second_best_score": summarize(answerable_second_scores),
            "best_gold_score": summarize(best_gold_scores),
            "worst_gold_score": summarize(worst_gold_scores),
            "best_non_gold_score": summarize(best_non_gold_scores),
            "best_gold_minus_best_non_gold": summarize(best_gold_margins),
            "worst_gold_minus_best_non_gold": summarize(complete_gold_margins),
            "zero_gold_best_score": summarize(zero_gold_best_scores),
            "zero_gold_second_best_score": summarize(zero_gold_second_scores),
            "zero_gold_top1_gap": summarize(zero_gold_top1_gaps),
        },
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

    return analysis, per_question, per_chunk


def save_current_figure(path):
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def make_matrix_plots(analysis, per_question, per_chunk, output_dir):
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

    plots = [
        (
            "worst_gold_rank_distribution.png",
            "worst required-gold rank",
            per_question.loc[per_question["gold_size"] > 0, "worst_gold_rank"].dropna(),
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

    answerable = per_question[per_question["gold_size"] > 0]
    if not answerable.empty:
        plt.figure(figsize=(8, 5))
        plt.hist(answerable["best_gold_score"].dropna(), bins=30, alpha=0.65, label="Best gold score")
        plt.hist(answerable["best_non_gold_score"].dropna(), bins=30, alpha=0.65, label="Best non-gold score")
        plt.xlabel("Similarity score")
        plt.ylabel("Questions")
        plt.title("Best gold vs. best non-gold score")
        plt.legend()
        path = output_dir / "best_gold_vs_best_non_gold_scores.png"
        save_current_figure(path)
        files.append(path.name)

    for prefix, title, filename in [
        ("recall", "Recall by gold-set size", "recall_by_gold_set_size.png"),
        ("all_gold", "All-Gold by gold-set size", "all_gold_by_gold_set_size.png"),
    ]:
        groups = [
            group for group in ("1", "2", "3+")
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
            plt.bar(x - 0.4 + width / 2 + i * width, values, width=width, label=f"@{k}")
        plt.xticks(x, [f"{group} gold" for group in groups])
        plt.xlabel("Required gold chunks per question")
        plt.ylabel("Mean metric value")
        plt.ylim(0, 1.02)
        plt.title(title)
        plt.legend()
        path = output_dir / filename
        save_current_figure(path)
        files.append(path.name)

    top_chunks = (
        per_chunk
        .sort_values(["top1_count", "similarity_mean"], ascending=[False, False])
        .head(TOP_CHUNKS_TO_REPORT)
    )
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


def make_overview_plots(overview):
    files = []

    for prefix, title, filename in [
        ("recall", "Recall comparison across matrices", "overview_recall_at_k.png"),
        ("hit", "Hit comparison across matrices", "overview_hit_at_k.png"),
        ("all_gold", "All-Gold comparison across matrices", "overview_all_gold_at_k.png"),
    ]:
        x = np.arange(len(overview))
        width = 0.8 / len(K_VALUES)
        plt.figure(figsize=(max(8, len(overview) * 1.8), 5))
        for i, k in enumerate(K_VALUES):
            plt.bar(
                x - 0.4 + width / 2 + i * width,
                overview[metric_name(prefix, k)],
                width=width,
                label=f"@{k}",
            )
        plt.xticks(x, overview["matrix_id"], rotation=30, ha="right")
        plt.xlabel("Similarity matrix")
        plt.ylabel("Mean metric value")
        plt.ylim(0, 1.02)
        plt.title(title)
        plt.legend()
        path = OUTPUT_DIR / filename
        save_current_figure(path)
        files.append(path.name)

    x = np.arange(len(overview))
    plt.figure(figsize=(max(8, len(overview) * 1.8), 5))
    plt.bar(x, overview["mrr"])
    plt.xticks(x, overview["matrix_id"], rotation=30, ha="right")
    plt.xlabel("Similarity matrix")
    plt.ylabel("MRR")
    plt.ylim(0, 1.02)
    plt.title("MRR comparison across matrices")
    path = OUTPUT_DIR / "overview_mrr.png"
    save_current_figure(path)
    files.append(path.name)

    plt.figure(figsize=(max(8, len(overview) * 1.8), 5))
    width = 0.36
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
    path = OUTPUT_DIR / "overview_best_score_medians.png"
    save_current_figure(path)
    files.append(path.name)

    plt.figure(figsize=(max(8, len(overview) * 1.8), 5))
    plt.bar(x, overview["complete_gold_margin_median"])
    plt.axhline(0, linestyle="--")
    plt.xticks(x, overview["matrix_id"], rotation=30, ha="right")
    plt.xlabel("Similarity matrix")
    plt.ylabel("Median worst-gold minus best-non-gold score")
    plt.title("Complete-gold score-separation comparison")
    path = OUTPUT_DIR / "overview_complete_gold_margin.png"
    save_current_figure(path)
    files.append(path.name)

    return files


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    question_ids, chunk_ids, gold = read_inputs()

    overview_rows = []

    for matrix_id, matrix_path in MATRICES:
        matrix = np.load(matrix_path)
        matrix_output_dir = OUTPUT_DIR / matrix_id
        matrix_output_dir.mkdir(parents=True, exist_ok=True)

        analysis, per_question, per_chunk = analyze_matrix(
            matrix,
            question_ids,
            chunk_ids,
            gold,
        )

        per_question.to_csv(matrix_output_dir / "per_question.csv", index=False)
        per_chunk.to_csv(matrix_output_dir / "per_chunk.csv", index=False)

        plot_files = make_matrix_plots(
            analysis,
            per_question,
            per_chunk,
            matrix_output_dir,
        )
        analysis["output_files"] = {
            "per_question": "per_question.csv",
            "per_chunk": "per_chunk.csv",
            "visualizations": plot_files,
        }

        with (matrix_output_dir / "analysis.json").open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(jsonable(analysis), file, ensure_ascii=False, indent=2)

        ranking = analysis["ranking_metrics"]
        scores = analysis["score_summary"]
        ranks = analysis["gold_rank_summary"]
        observations = analysis["notable_observations"]
        overview_row = {
            "matrix_id": matrix_id,
            "configured_path": str(matrix_path),
            "filename": matrix_path.name,
            "rows": int(matrix.shape[0]),
            "columns": int(matrix.shape[1]),
            "dtype": str(matrix.dtype),
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
        for k in K_VALUES:
            for prefix in ("recall", "hit", "all_gold"):
                key = metric_name(prefix, k)
                overview_row[key] = ranking[key]

        overview_rows.append(overview_row)
        print(f"Analyzed {matrix_id}: {matrix.shape}")

    overview = pd.DataFrame(overview_rows)
    overview.to_csv(OUTPUT_DIR / "overview.csv", index=False)

    overview_plot_files = make_overview_plots(overview)
    overview_json = {
        "matrices": overview.where(pd.notnull(overview), None).to_dict(orient="records"),
        "visualizations": overview_plot_files,
        "k_values": K_VALUES,
    }

    with (OUTPUT_DIR / "overview.json").open("w", encoding="utf-8") as file:
        json.dump(jsonable(overview_json), file, ensure_ascii=False, indent=2)

    print(f"\nAnalysis written to: {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
