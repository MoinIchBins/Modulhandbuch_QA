"""Reference predictions use the same configured splits and evaluator as the system."""
from collections import Counter
from pathlib import Path
import random
import statistics

from .config import read_json, read_jsonl, write_json, write_jsonl
from .evaluation import QAMappingEvaluator

METRICS = ("mean_question_f1", "exact_match_rate", "mean_question_precision", "mean_question_recall", "micro_f1", "average_selected_chunks", "empty_selection_rate", "zero_gold_abstention_rate")


def freeze_reference(config):
    folder = Path(config["output_dir"]) / "baselines"
    path = folder / "most_frequent_answer.json"
    gold = {row["question_id"]: row["all_required_chunk_ids"] for row in read_jsonl(config["gold_path"])}
    ids = read_json(config["splits"]["development"])
    counts = Counter(tuple(sorted(gold[q])) for q in ids if gold[q])
    if not counts:
        raise ValueError("Development has no non-empty gold answer for the frequent-answer baseline")
    maximum = max(counts.values())
    winner = min(chunks for chunks, count in counts.items() if count == maximum)
    result = {"derived_from": "development", "chunk_ids": list(winner), "development_count": maximum}
    if path.exists():
        if read_json(path) != result:
            raise ValueError("Frozen baseline reference no longer matches development gold")
    else:
        folder.mkdir(parents=True, exist_ok=True)
        write_json(path, result)
    return list(winner)


def run_baselines(config, split):
    frequent = freeze_reference(config)
    folder = Path(config["output_dir"]) / "baselines" / split
    folder.mkdir(parents=True, exist_ok=False)
    ids = read_json(config["splits"][split])
    # Use the configured reference representation's order to preserve seeded sampling.
    reference = config["baselines"]["chunk_order_representation"]
    chunks = read_json(config["representations"][reference]["chunk_ids"])
    evaluator = QAMappingEvaluator(config["gold_path"])
    runs = []
    for seed in config["baselines"]["random_seeds"]:
        rng = random.Random(seed)
        predictions = [{"question_id": q, "chunk_ids": [rng.choice(chunks)]} for q in ids]
        result = evaluator.eval(predictions, question_ids=ids)
        runs.append({"baseline": "random_top1", "seed": seed, **result["summary"]})
    random_summary = {"baseline": "random_top1", "run_count": len(runs)}
    for metric in METRICS:
        values = [row[metric] for row in runs]
        random_summary[metric] = statistics.mean(values)
        random_summary[metric + "_std"] = statistics.stdev(values) if len(values) > 1 else 0.0
    write_jsonl(folder / "random_top1_runs.jsonl", runs)
    write_json(folder / "random_top1_summary.json", random_summary)
    summaries = [random_summary]
    for name, selected in (("most_frequent_dev_answer", frequent), ("always_abstain", [])):
        predictions = [{"question_id": q, "chunk_ids": list(selected)} for q in ids]
        result = evaluator.eval(predictions, question_ids=ids)
        write_jsonl(folder / f"{name}_predictions.jsonl", predictions)
        write_json(folder / f"{name}_evaluation.json", result)
        summary = {"baseline": name}
        for metric in METRICS:
            summary[metric] = result["summary"][metric]
            summary[metric + "_std"] = 0.0
        summaries.append(summary)
    write_jsonl(folder / "summary.jsonl", summaries)
