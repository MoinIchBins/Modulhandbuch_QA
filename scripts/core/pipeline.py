"""Explicit development, validation and test stages over frozen matrices."""
import importlib.metadata
import platform
import sys
from pathlib import Path

import numpy as np

from .config import SPLITS, file_hash, read_json, read_jsonl, validate_experiment, validate_inputs, write_json, write_jsonl
from .evaluation import QAMappingEvaluator
from .ranking import group_winners, rank_key
from .search import expand_fine_search, expand_sweeps, validate_fine_searches
from .selection import ChunkSelector

IDENTITY_FIELDS = ("representation", "method", "top_k", "threshold", "margin")


def experiment_name(experiment):
    parts = [experiment["representation"], experiment["method"]]
    for key in ("top_k", "threshold", "margin"):
        if experiment.get(key) is not None:
            parts.append(f"{key}_{experiment[key]}")
    name = "_".join(parts)
    if Path(name).name != name or "/" in name or "\\" in name:
        raise ValueError("Representation names must not contain path separators")
    return name


def search_config(config):
    return {**config["development"], "representations": config["representations"]}


def preflight(config):
    hashes = validate_inputs(config)
    experiments = expand_sweeps(search_config(config))
    if not experiments:
        raise ValueError("No development experiments configured")
    names = []
    for experiment in experiments:
        validate_experiment(experiment, config["representations"])
        names.append(experiment_name(experiment))
    if len(names) != len(set(names)):
        raise ValueError("Duplicate development settings would overwrite each other")
    # Validate fine-search structure and bounds before creating any outputs.
    if config["development"].get("fine_searches"):
        validate_fine_searches(search_config(config), experiments)
    return hashes


def environment():
    versions = {}
    for name in ("numpy", "pandas", "matplotlib", "scikit-learn"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return {"python": sys.version, "platform": platform.platform(), "packages": versions}


def initialize_run(config, input_hashes):
    root = Path(config["output_dir"])
    code_root = Path(__file__).resolve().parents[1]
    code_hashes = {str(path.relative_to(code_root)): file_hash(path) for path in sorted(code_root.rglob("*.py"))}
    state = {"config": config, "input_sha256": input_hashes, "code_sha256": code_hashes, "environment": environment()}
    manifest = root / "experiment.json"
    if root.exists():
        if not manifest.is_file() or read_json(manifest) != state:
            raise ValueError("Existing run has different config, inputs, code or environment; choose a new output_dir")
    else:
        root.mkdir(parents=True)
        write_json(manifest, state)
    return root


def finish_stage(folder):
    # Record the files consumed by later stages; predictions remain available for inspection.
    names = ("summary.jsonl", "run_manifest.json", "validation_candidates.json", "frozen_winner.json")
    write_json(folder / "complete.json", {name: file_hash(folder / name) for name in names if (folder / name).exists()})


def require_stage(folder):
    receipt = folder / "complete.json"
    if not receipt.exists():
        raise ValueError(f"Stage is incomplete or has not run: {folder}")
    for name, expected in read_json(receipt).items():
        if file_hash(folder / name) != expected:
            raise ValueError(f"Completed stage artifact changed: {folder / name}")


def load_scores(files, question_ids):
    matrix_ids = read_json(files["question_ids"])
    rows = {question_id: index for index, question_id in enumerate(matrix_ids)}
    scores = np.load(files["matrix"], mmap_mode="r", allow_pickle=False)[[rows[q] for q in question_ids]]
    return scores, read_json(files["chunk_ids"])


def predict(experiment, files, scores, chunk_ids, question_ids):
    selector = ChunkSelector(
        method=experiment["method"], top_k=experiment.get("top_k"),
        threshold=experiment.get("threshold"), margin=experiment.get("margin"),
        higher_is_better=files["higher_is_better"],
    )
    selections = selector.select(scores, chunk_ids)
    return [{"question_id": question_id, **selection} for question_id, selection in zip(question_ids, selections)]


def evaluate_settings(config, experiments, split, folder):
    for experiment in experiments:
        validate_experiment(experiment, config["representations"])
    folder.mkdir(parents=True, exist_ok=False)
    ids = read_json(config["splits"][split])
    evaluator = QAMappingEvaluator(config["gold_path"])
    write_json(folder / "run_manifest.json", {"split": split, "experiments": experiments, "experiment_manifest": str(Path(config["output_dir"]) / "experiment.json")})
    cache = {}
    summaries = []
    for experiment in experiments:
        representation = experiment["representation"]
        files = config["representations"][representation]
        if representation not in cache:
            cache[representation] = load_scores(files, ids)
        scores, chunk_ids = cache[representation]
        predictions = predict(experiment, files, scores, chunk_ids, ids)
        result = evaluator.eval(predictions, question_ids=ids)
        if result["summary"]["unanswered_question_count"] or len(predictions) != len(ids):
            raise ValueError("Generated predictions do not cover the split")
        name = experiment_name(experiment)
        write_jsonl(folder / f"{name}_predictions.jsonl", predictions)
        write_json(folder / f"{name}_evaluation.json", {"experiment": experiment, "split": split, **result})
        summaries.append({"experiment": name, **experiment, **result["summary"]})
    if split == "validation":
        summaries.sort(key=rank_key, reverse=True)
    write_jsonl(folder / "summary.jsonl", summaries)
    print(f"{split}: evaluated {len(experiments)} settings → {folder}")
    return summaries


def setting(row):
    return {key: row[key] for key in IDENTITY_FIELDS if key in row and row[key] is not None}


def development(config):
    root = Path(config["output_dir"]) / "development"
    root.mkdir(parents=True, exist_ok=False)
    coarse = evaluate_settings(config, expand_sweeps(search_config(config)), "development", root / "coarse")
    finish_stage(root / "coarse")
    rows = coarse
    if config["development"].get("fine_searches"):
        evaluations = [{"experiment": setting(row), "summary": row} for row in coarse]
        experiments = expand_fine_search(search_config(config), evaluations)
        rows = evaluate_settings(config, experiments, "development", root / "fine")
        finish_stage(root / "fine")
    ranked = group_winners(rows)
    limit = config.get("validation_candidate_limit")
    candidates = [setting(row) for row in (ranked if limit is None else ranked[:limit])]
    write_json(root / "validation_candidates.json", {"selected_on": "development", "candidates": candidates})
    write_jsonl(root / "summary.jsonl", ranked)
    finish_stage(root)


def validation(config):
    root = Path(config["output_dir"])
    require_stage(root / "development")
    candidates = read_json(root / "development/validation_candidates.json")["candidates"]
    pairs = [(row["representation"], row["method"]) for row in candidates]
    if not candidates or len(set(pairs)) != len(pairs):
        raise ValueError("Expected one candidate per selected representation/selector pair")
    ranked = evaluate_settings(config, candidates, "validation", root / "validation")
    winner = setting(ranked[0])
    write_json(root / "validation/frozen_winner.json", {
        "selected_by": "validation ranking", "winner": winner,
        "validation_metrics": {key: value for key, value in ranked[0].items() if key not in IDENTITY_FIELDS and key != "experiment"},
    })
    finish_stage(root / "validation")


def test(config):
    root = Path(config["output_dir"])
    require_stage(root / "validation")
    frozen = read_json(root / "validation/frozen_winner.json")
    ranked = read_jsonl(root / "validation/summary.jsonl")
    if frozen["selected_by"] != "validation ranking" or not ranked or frozen["winner"] != setting(ranked[0]):
        raise ValueError("Frozen winner does not match the validation ranking")
    evaluate_settings(config, [frozen["winner"]], "test", root / "test")
    finish_stage(root / "test")
