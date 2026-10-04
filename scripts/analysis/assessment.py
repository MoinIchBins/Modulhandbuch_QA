"""Subgroup scores and bootstrap intervals for a saved test result."""

import argparse
from collections import defaultdict
from pathlib import Path
import numpy as np

from ..core.config import load_config, read_json, read_jsonl, write_json
from ..core.evaluation import QAMappingEvaluator
from ..core.pipeline import experiment_name, require_stage, setting


def subset_metrics(rows):
    """Calculate mean F1, exact match and abstentions for a subset."""
    return {
        "question_count": len(rows),
        "mean_question_f1": (
            float(np.mean([r["f1"] for r in rows])) if rows else None
        ),
        "exact_match_rate": (
            float(np.mean([r["exact_match"] for r in rows])) if rows else None
        ),
        "abstention_count": sum(not r["predicted_chunk_ids"] for r in rows),
    }


def cluster_interval(rows, draws=10000, seed=20261003):
    """Resample gold-set clusters, keeping related questions together."""
    groups = defaultdict(list)

    for row in rows:
        gold = tuple(row["gold_chunk_ids"])
        key = ("gold", gold) if gold else ("zero_gold", row["question_id"])
        groups[key].append(row["f1"])

    values = list(groups.values())
    totals = np.array([sum(v) for v in values], dtype=float)
    sizes = np.array([len(v) for v in values], dtype=int)
    rng = np.random.default_rng(seed)
    sampled = rng.integers(0, len(values), size=(draws, len(values)))
    scores = totals[sampled].sum(axis=1) / sizes[sampled].sum(axis=1)
    lower, upper = np.quantile(scores, [0.025, 0.975])

    return {
        "method": "percentile_gold_set_cluster_bootstrap",
        "draws": draws,
        "seed": seed,
        "cluster_count": len(values),
        "confidence_level": 0.95,
        "lower": float(lower),
        "upper": float(upper),
        "interpretation": (
            "Conditional on the frozen winner and annotated test collection; not a new held-out evaluation or a paired protocol comparison."
        ),
    }


def describe_test(config, output_dir):
    """Compare saved scores with predictions and export subgroup results."""
    root = Path(config["output_dir"])
    require_stage(root / "test")

    row = read_jsonl(root / "test/summary.jsonl")[0]
    stem = experiment_name(setting(row))
    saved = read_json(root / "test" / f"{stem}_evaluation.json")
    ids = read_json(config["splits"]["test"])
    recomputed = QAMappingEvaluator(config["gold_path"]).eval(
        root / "test" / f"{stem}_predictions.jsonl", ids
    )

    if recomputed != {k: saved[k] for k in ("summary", "per_question")}:
        raise ValueError(
            "Saved evaluation does not match its predictions and gold"
        )

    rows = saved["per_question"]
    subsets = {
        "all": rows,
        "answerable": [r for r in rows if r["gold_chunk_ids"]],
        "zero_gold": [r for r in rows if not r["gold_chunk_ids"]],
        "single_gold": [r for r in rows if len(r["gold_chunk_ids"]) == 1],
        "multi_gold": [r for r in rows if len(r["gold_chunk_ids"]) > 1],
    }

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=False)

    result = {
        "experiment": config["name"],
        "winner": setting(row),
        "source_evaluation": str(root / "test" / f"{stem}_evaluation.json"),
        "subsets": {
            name: subset_metrics(values) for name, values in subsets.items()
        },
        "q_f1_cluster_interval": cluster_interval(rows),
    }

    write_json(output / "test_description.json", result)
    return result


def main():
    """Export test statistics after the --confirm-test check."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--confirm-test", action="store_true")
    args = parser.parse_args()

    if not args.confirm_test:
        parser.error(
            "--confirm-test is required to inspect saved test results"
        )
        
    result = describe_test(load_config(args.config), args.output_dir)
    print(
        f"Descriptive results: {args.output_dir}; "
        f"Q-F1 {result['subsets']['all']['mean_question_f1']:.6f}"
    )


if __name__ == "__main__":
    main()
