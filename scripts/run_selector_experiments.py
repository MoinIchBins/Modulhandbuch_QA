import argparse
import json
from pathlib import Path

import numpy as np

from chunk_selector import ChunkSelector
from mapping_evaluator import QAMappingEvaluator


DEFAULT_CONFIG = Path("configs/manual_review_v1_coarse.json")


def read_json(path):
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)


def experiment_name(experiment):
    parts = [experiment["representation"], experiment["method"]]
    for key in ("top_k", "threshold", "margin"):
        if experiment.get(key) is not None:
            parts.append(str(experiment[key]))
    return "_".join(parts)


def result_rank(result):
    summary = result["summary"]
    return (
        summary["mean_question_f1"],
        summary["exact_match_rate"],
        summary["mean_question_precision"],
        -summary["average_selected_chunks"],
    )


def expand_sweeps(config):
    if config.get("experiments"):
        experiments = config["experiments"]
    else:
        representations = config["representations"]
        experiments = []
        for sweep in config["sweeps"]:
            method = sweep["method"]
            for representation in sweep.get("representations", representations):
                if method == "threshold":
                    values = sweep["thresholds_by_representation"][representation]
                    top_k_values = [None]
                    parameter = "threshold"
                elif method == "top_k_threshold":
                    values = sweep["thresholds_by_representation"][representation]
                    top_k_values = sweep.get("top_k_values", [1])
                    parameter = "threshold"
                elif method == "relative_margin":
                    values = sweep["margins_by_representation"][representation]
                    top_k_values = sweep.get("top_k_values", [1])
                    parameter = "margin"
                elif method == "top_k":
                    values = [None]
                    top_k_values = sweep["top_k_values"]
                    parameter = None
                else:
                    raise ValueError(f"Unsupported selector method: {method}")

                for top_k in top_k_values:
                    for value in values:
                        experiment = {"representation": representation, "method": method}
                        if top_k is not None:
                            experiment["top_k"] = top_k
                        if parameter:
                            experiment[parameter] = value
                        experiments.append(experiment)

    if config.get("require_all_combinations"):
        expected = {
            (representation, method)
            for representation in config["representations"]
            for method in ("top_k", "threshold", "top_k_threshold", "relative_margin")
        }
        actual = {(item["representation"], item["method"]) for item in experiments}
        if actual != expected:
            raise ValueError(f"Sweep is incomplete; expected {sorted(expected)}, got {sorted(actual)}")
    return experiments


def expand_fine_search(config, coarse_dir):
    coarse_manifest = read_json(coarse_dir / "run_manifest.json")
    for key in ("split", "gold_path", "split_ids_path", "representations"):
        if config[key] != coarse_manifest[key]:
            raise ValueError(f"Fine-search config does not match coarse run field '{key}'.")

    evaluations = []
    for path in coarse_dir.glob("*_evaluation.json"):
        result = read_json(path)
        result["_path"] = str(path)
        evaluations.append(result)
    if not evaluations:
        raise ValueError(f"No evaluations found in coarse run: {coarse_dir}")

    groups = {}
    for result in evaluations:
        experiment = result["experiment"]
        groups.setdefault((experiment["representation"], experiment["method"]), []).append(result)

    fine_searches = config.get("fine_searches", [])
    search_by_group = {}
    for search in fine_searches:
        key = (search["representation"], search["method"])
        if key in search_by_group:
            raise ValueError(f"Duplicate fine-search specification for {key}")
        search_by_group[key] = search

    expected_search_groups = {key for key in groups if key[1] != "top_k"}
    if set(search_by_group) != expected_search_groups:
        missing = sorted(expected_search_groups - set(search_by_group))
        extra = sorted(set(search_by_group) - expected_search_groups)
        raise ValueError(f"Fine-search specs do not match coarse methods; missing={missing}, extra={extra}")

    fine_experiments = []
    for (representation, method), results in sorted(groups.items()):
        if method == "top_k":
            fine_experiments.append(max(results, key=result_rank)["experiment"])
            continue

        search = search_by_group[(representation, method)]
        parameter = "margin" if method == "relative_margin" else "threshold"
        if search.get("parameter") != parameter:
            raise ValueError(f"{representation}/{method} fine search must tune '{parameter}'")
        top_k_values = search.get("top_k_values", [None])
        lower = float(search["lower"])
        upper = float(search["upper"])
        points = int(search["points"])
        if lower >= upper or points < 2:
            raise ValueError(f"Invalid fine-search range or density: {search}")
        if parameter == "margin" and (lower < 0 or upper > 1):
            raise ValueError(f"Relative margins must be in [0, 1]: {search}")
        if parameter == "threshold" and (lower < -1 or upper > 1):
            raise ValueError(f"Cosine thresholds must be in [-1, 1]: {search}")

        for top_k in top_k_values:
            matched = [
                result for result in results
                if result["experiment"].get("top_k") == top_k
                and parameter in result["experiment"]
            ]
            if not matched:
                raise ValueError(f"No coarse runs for {representation}/{method}, top_k={top_k}")
            # Carry forward the best coarse point as well as the manually specified fine grid.
            fine_experiments.append(max(matched, key=result_rank)["experiment"])
            for value in np.linspace(lower, upper, points):
                experiment = {"representation": representation, "method": method, parameter: round(float(value), 8)}
                if top_k is not None:
                    experiment["top_k"] = top_k
                fine_experiments.append(experiment)

    # Avoid duplicate runs when neighboring coarse points refine to the same grid.
    unique = {}
    for experiment in fine_experiments:
        key = tuple((field, experiment.get(field)) for field in ("representation", "method", "top_k", "threshold", "margin"))
        unique[key] = experiment
    return list(unique.values())


def main():
    parser = argparse.ArgumentParser(description="Run coarse or development-refinement selector experiments.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--coarse-run", type=Path, help="Required for a config with fine_search settings")
    args = parser.parse_args()

    config = read_json(args.config)
    if "fine_searches" in config:
        if args.coarse_run is None:
            parser.error("--coarse-run is required for fine-search configs")
        experiments = expand_fine_search(config, args.coarse_run)
    else:
        experiments = expand_sweeps(config)
    if not experiments:
        raise ValueError("The run config did not produce any experiments.")

    output_dir = args.output_dir or Path(config["output_dir"])
    development_ids = read_json(config["split_ids_path"])

    # Refuse existing folders so prior run artifacts remain intact.
    output_dir.mkdir(parents=True, exist_ok=False)
    evaluator = QAMappingEvaluator(config["gold_path"])
    manifest = {
        "run_name": config["run_name"],
        "split": config["split"],
        "config_path": str(args.config),
        "gold_path": config["gold_path"],
        "split_ids_path": config["split_ids_path"],
        "representations": config["representations"],
        "experiments": experiments,
    }
    if args.coarse_run:
        manifest["source_coarse_run"] = str(args.coarse_run)
        manifest["fine_searches"] = config["fine_searches"]
    (output_dir / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    by_representation = {}
    for experiment in experiments:
        by_representation.setdefault(experiment["representation"], []).append(experiment)

    summaries = []
    for representation, representation_experiments in by_representation.items():
        files = config["representations"][representation]
        matrix_question_ids = read_json(files["question_ids"])
        chunk_ids = read_json(files["chunk_ids"])
        row_by_question_id = {question_id: row for row, question_id in enumerate(matrix_question_ids)}
        missing = [question_id for question_id in development_ids if question_id not in row_by_question_id]
        if missing:
            raise ValueError(f"Questions missing from {representation} matrix: {missing[:5]}")
        rows = [row_by_question_id[question_id] for question_id in development_ids]
        scores = np.load(files["matrix"], mmap_mode="r")[rows]

        for experiment in representation_experiments:
            selector = ChunkSelector(
                method=experiment["method"],
                top_k=experiment.get("top_k"),
                threshold=experiment.get("threshold"),
                margin=experiment.get("margin"),
            )
            selections = selector.select(scores, chunk_ids)
            predictions = [
                {"question_id": question_id, "chunk_ids": selection["chunk_ids"], "scores": selection["scores"]}
                for question_id, selection in zip(development_ids, selections)
            ]
            result = evaluator.eval(
                [{"question_id": row["question_id"], "chunk_ids": row["chunk_ids"]} for row in predictions],
                question_ids=development_ids,
            )
            name = experiment_name(experiment)
            with (output_dir / f"{name}_predictions.jsonl").open("w", encoding="utf-8") as file:
                for row in predictions:
                    file.write(json.dumps(row, ensure_ascii=False) + "\n")
            with (output_dir / f"{name}_evaluation.json").open("w", encoding="utf-8") as file:
                json.dump({"experiment": experiment, "split": config["split"], **result}, file, ensure_ascii=False, indent=2)

            summary = {"experiment": name, **experiment, **result["summary"]}
            summaries.append(summary)
            print(
                f"{name}: F1={summary['mean_question_f1']:.4f}, "
                f"exact={summary['exact_match_rate']:.4f}, "
                f"avg_chunks={summary['average_selected_chunks']:.2f}"
            )

    with (output_dir / "summary.jsonl").open("w", encoding="utf-8") as file:
        for row in summaries:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Run saved to: {output_dir}")


if __name__ == "__main__":
    main()
