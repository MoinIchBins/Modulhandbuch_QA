"""Experiment configuration, input checks and JSON utilities."""

import hashlib
import json
from pathlib import Path

import numpy as np

SPLITS = ("development", "validation", "test")
METHODS = {"top_k", "threshold", "top_k_threshold", "relative_margin"}


def read_json(path):
    """Read a UTF-8 JSON file."""
    with Path(path).open(encoding="utf-8") as file:
        return json.load(file)


def read_jsonl(path):
    """Read non-empty JSONL records in file order."""
    with Path(path).open(encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def write_json(path, value):
    """Write a readable UTF-8 JSON value and a trailing newline."""
    Path(path).write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path, rows):
    """Write one JSON record per line."""
    with Path(path).open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def file_hash(path):
    """Calculate a file's SHA-256 digest."""
    with Path(path).open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def load_config(path):
    """
    Resolve paths from the config's project root and check required
    settings.
    """
    path = Path(path).resolve()
    config = read_json(path)
    config.pop("schema_version", None)
    root = (path.parent / config["project_root"]).resolve()
    config["project_root"] = str(root)
    for key in ("gold_path", "chunks_path", "output_dir"):
        config[key] = str((root / config[key]).resolve())
    config["splits"] = {
        name: str((root / config["splits"][name]).resolve()) for name in SPLITS
    }
    if not config["representations"]:
        raise ValueError("Configure at least one representation")
    for name, files in config["representations"].items():
        if not name or Path(name).name != name or "/" in name or "\\" in name:
            raise ValueError(
                "Representation names must be plain directory names"
            )
        for key in ("matrix", "question_ids", "chunk_ids"):
            files[key] = str((root / files[key]).resolve())
        if not isinstance(files.get("higher_is_better"), bool):
            raise ValueError(
                f"{name}: higher_is_better must explicitly be true or false"
            )
    seeds = config.get("baselines", {}).get("random_seeds", [])
    if config.get("baselines", {}).get("enabled", False) and (
        not seeds
        or any(type(seed) is not int for seed in seeds)
        or len(seeds) != len(set(seeds))
    ):
        raise ValueError(
            "Enabled baselines require distinct integer random_seeds"
        )
    if config.get("baselines", {}).get("enabled", False):
        reference = config["baselines"].get("chunk_order_representation")
        if reference not in config["representations"]:
            raise ValueError(
                "Baselines require a configured chunk_order_representation"
            )
    return config


def unique_ids(values, label):
    """Check that IDs are non-empty, trimmed and unique."""
    if not values or any(
        not isinstance(value, str) or not value or value != value.strip()
        for value in values
    ):
        raise ValueError(f"{label}: expected non-empty, trimmed string IDs")
    if len(values) != len(set(values)):
        raise ValueError(f"{label}: duplicate IDs")


def validate_experiment(experiment, representations):
    """Check selector parameters and the available chunk count."""
    name = experiment["representation"]
    if name not in representations:
        raise ValueError(f"Unknown representation: {name}")
    method = experiment["method"]
    if method not in METHODS:
        raise ValueError(f"Unknown selector: {method}")
    allowed = {"representation", "method"}
    if method in ("top_k", "top_k_threshold", "relative_margin"):
        allowed.add("top_k")
        k = experiment.get("top_k")
        count = len(read_json(representations[name]["chunk_ids"]))
        if (
            type(k) is not int
            or not 1 <= k <= count
            or (method == "relative_margin" and k == count)
        ):
            raise ValueError(f"Invalid top_k for {name}/{method}: {k}")
    for parameter in ("threshold", "margin"):
        needed = (
            parameter == "threshold"
            and method in ("threshold", "top_k_threshold")
        ) or (parameter == "margin" and method == "relative_margin")
        if needed:
            allowed.add(parameter)
            value = experiment.get(parameter)
            if type(value) not in (int, float) or not np.isfinite(value):
                raise ValueError(
                    f"{name}/{method}: {parameter} must be finite"
                )
            if parameter == "margin" and not 0 <= value <= 1:
                raise ValueError("Relative margin must be between 0 and 1")
    extra = set(experiment) - allowed
    if extra:
        raise ValueError(f"Unexpected selector parameters: {sorted(extra)}")


def validate_inputs(config):
    """Check split membership, gold IDs and matrix shape."""
    gold_rows = read_jsonl(config["gold_path"])
    unique_ids([row["question_id"] for row in gold_rows], "gold")
    gold = {row["question_id"]: row for row in gold_rows}
    chunks = read_jsonl(config["chunks_path"])
    unique_ids([row["chunk_id"] for row in chunks], "chunks")
    for row in chunks:
        if not isinstance(row["chunk_text"], str):
            raise ValueError(f"Chunk text must be a string: {row['chunk_id']}")
    chunk_set = {row["chunk_id"] for row in chunks}
    splits = {name: read_json(path) for name, path in config["splits"].items()}
    seen = set()
    for name, ids in splits.items():
        unique_ids(ids, name)
        if seen.intersection(ids):
            raise ValueError(f"Overlapping split IDs: {name}")
        if set(ids) - gold.keys():
            raise ValueError(f"{name}: split contains IDs absent from gold")
        for question_id in ids:
            row = gold[question_id]
            if row.get("split", name) != name:
                raise ValueError(
                    f"Gold split label disagrees with {name}: {question_id}"
                )
            required = row["all_required_chunk_ids"]
            if (
                len(required) != len(set(required))
                or set(required) - chunk_set
            ):
                raise ValueError(f"Invalid gold chunks for {question_id}")
        seen.update(ids)
    if config.get("baselines", {}).get("enabled", False) and not any(
        gold[q]["all_required_chunk_ids"] for q in splits["development"]
    ):
        raise ValueError(
            "Frequent-answer baseline requires non-empty development gold"
        )
    paths = {
        config["gold_path"],
        config["chunks_path"],
        *config["splits"].values(),
    }
    for name, files in config["representations"].items():
        qids = read_json(files["question_ids"])
        cids = read_json(files["chunk_ids"])
        unique_ids(qids, f"{name} question IDs")
        unique_ids(cids, f"{name} chunk IDs")
        if seen - set(qids) or set(cids) != chunk_set:
            raise ValueError(
                f"{name}: matrix IDs do not cover the configured experiment"
            )
        matrix = np.load(files["matrix"], mmap_mode="r", allow_pickle=False)
        if (
            matrix.shape != (len(qids), len(cids))
            or not np.isfinite(matrix).all()
        ):
            raise ValueError(
                f"{name}: invalid matrix shape or non-finite values"
            )
        paths.update(
            files[key] for key in ("matrix", "question_ids", "chunk_ids")
        )
    output = Path(config["output_dir"])
    if any(Path(path).is_relative_to(output) for path in paths):
        raise ValueError(
            "Experiment output directory must not contain its input files"
        )
