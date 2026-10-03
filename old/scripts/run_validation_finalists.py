import argparse
import csv
import json
from pathlib import Path

import numpy as np

from chunk_selector import ChunkSelector
from mapping_evaluator import QAMappingEvaluator


DEFAULT_CONFIG = Path("configs/manual_review_v1_validation.json")


def read_json(path):
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)


def experiment_name(representation, method, parameters):
    parts = [representation, method]
    for key in ("top_k", "threshold", "margin"):
        if key in parameters:
            parts.append(f"{key}_{parameters[key]}")
    return "_".join(parts)


def rank_row(row):
    return (
        row["mean_question_f1"],
        row["exact_match_rate"],
        row["mean_question_precision"],
        -row["average_selected_chunks"],
    )


def main():
    parser = argparse.ArgumentParser(description="Evaluate development-selected configurations on validation.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    config = read_json(args.config)
    candidate_file = Path(config["candidates_path"])
    candidate_document = read_json(candidate_file)
    candidates = candidate_document["candidates"]
    if not candidates:
        raise ValueError(f"No development candidates found in {candidate_file}")
    actual = [(candidate["representation"], candidate["method"]) for candidate in candidates]
    if len(set(actual)) != len(actual):
        raise ValueError(f"Validation candidates must have unique representation/selector pairs: {actual}")
    expected_candidate_count = config.get("expected_candidate_count")
    if expected_candidate_count is not None:
        if len(candidates) != expected_candidate_count:
            raise ValueError(
                f"Expected {expected_candidate_count} validation candidates, got {len(candidates)}"
            )
    else:
        expected = {
            (representation, method)
            for representation in config["representations"]
            for method in ("top_k", "threshold", "top_k_threshold", "relative_margin")
        }
        if set(actual) != expected or len(actual) != len(expected):
            raise ValueError(f"Unexpected validation candidates; expected {sorted(expected)}, got {actual}")

    validation_ids = read_json(config["split_ids_path"])
    output_dir = args.output_dir or Path(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=False)
    evaluator = QAMappingEvaluator(config["gold_path"])
    representations = {
        name: {key: Path(path) for key, path in files.items()}
        for name, files in config["representations"].items()
    }
    manifest = {
        "run_name": config["run_name"],
        "split": "validation",
        "config_path": str(args.config),
        "gold_path": config["gold_path"],
        "split_ids_path": config["split_ids_path"],
        "candidates_path": str(candidate_file),
        "candidate_sources": candidate_document.get("source_runs", []),
        "representations": {
            name: {key: str(path) for key, path in files.items()}
            for name, files in representations.items()
        },
        "finalist_count": len(candidates),
    }
    (output_dir / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    cache = {}
    summaries = []
    for candidate in candidates:
        representation = candidate["representation"]
        method = candidate["method"]
        parameters = candidate["parameters"]
        if representation not in representations:
            raise ValueError(f"No artifacts configured for representation: {representation}")
        if representation not in cache:
            files = representations[representation]
            matrix_question_ids = read_json(files["question_ids"])
            chunk_ids = read_json(files["chunk_ids"])
            row_by_question_id = {question_id: row for row, question_id in enumerate(matrix_question_ids)}
            missing = [question_id for question_id in validation_ids if question_id not in row_by_question_id]
            if missing:
                raise ValueError(f"Questions missing from {representation} matrix: {missing[:5]}")
            rows = [row_by_question_id[question_id] for question_id in validation_ids]
            cache[representation] = (np.load(files["matrix"], mmap_mode="r")[rows], chunk_ids)

        scores, chunk_ids = cache[representation]
        selector = ChunkSelector(
            method=method,
            top_k=parameters.get("top_k"),
            threshold=parameters.get("threshold"),
            margin=parameters.get("margin"),
        )
        selections = selector.select(scores, chunk_ids)
        predictions = [
            {"question_id": question_id, "chunk_ids": selection["chunk_ids"], "scores": selection["scores"]}
            for question_id, selection in zip(validation_ids, selections)
        ]
        result = evaluator.eval(
            [{"question_id": row["question_id"], "chunk_ids": row["chunk_ids"]} for row in predictions],
            question_ids=validation_ids,
        )
        name = experiment_name(representation, method, parameters)
        with (output_dir / f"{name}_predictions.jsonl").open("w", encoding="utf-8") as file:
            for row in predictions:
                file.write(json.dumps(row, ensure_ascii=False) + "\n")
        with (output_dir / f"{name}_evaluation.json").open("w", encoding="utf-8") as file:
            json.dump({"experiment": {"representation": representation, "method": method, **parameters}, "split": "validation", **result}, file, ensure_ascii=False, indent=2)

        summary = {
            "experiment": name,
            "representation": representation,
            "method": method,
            **parameters,
            **result["summary"],
        }
        summaries.append(summary)
        print(
            f"{name}: F1={summary['mean_question_f1']:.4f}, "
            f"exact={summary['exact_match_rate']:.4f}, "
            f"precision={summary['mean_question_precision']:.4f}, "
            f"avg_chunks={summary['average_selected_chunks']:.2f}"
        )

    ranked = sorted(summaries, key=rank_row, reverse=True)
    with (output_dir / "summary.jsonl").open("w", encoding="utf-8") as file:
        for row in ranked:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")
    with (output_dir / "validation_ranking.csv").open("w", encoding="utf-8", newline="") as file:
        columns = ["representation", "method", "top_k", "threshold", "margin", "mean_question_f1", "exact_match_rate", "mean_question_precision", "average_selected_chunks"]
        writer = csv.DictWriter(file, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(ranked)

    winner = ranked[0]
    winner_files = representations[winner["representation"]]
    frozen_winner = {
        "selected_by": "validation ranking",
        "validation_run_dir": str(output_dir),
        "validation_metrics": {key: winner[key] for key in ("mean_question_f1", "exact_match_rate", "mean_question_precision", "average_selected_chunks")},
        "winner": {
            "representation": winner["representation"],
            "method": winner["method"],
            **{key: winner[key] for key in ("top_k", "threshold", "margin") if key in winner and winner[key] is not None},
        },
        "gold_path": config["test_gold_path"],
        "split_ids_path": config["test_split_ids_path"],
        "representation_artifacts": {key: str(path) for key, path in winner_files.items()},
        "test_output_dir": config["test_output_dir"],
    }
    (output_dir / "frozen_winner.json").write_text(
        json.dumps(frozen_winner, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("\nValidation winner:")
    print(json.dumps(frozen_winner["winner"] | frozen_winner["validation_metrics"], ensure_ascii=False, indent=2))
    print(f"Validation outputs saved to: {output_dir}")


if __name__ == "__main__":
    main()
