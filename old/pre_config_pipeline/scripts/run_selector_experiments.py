import argparse
import json
from pathlib import Path

import numpy as np

from experiment_pipeline import load_scores, make_predictions, read_json, write_jsonl
from mapping_evaluator import QAMappingEvaluator


DEFAULT_CONFIG = Path("artifacts/experiments/manual_review_v1/configs/manual_review_v1_coarse.json")


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


def neighboring_interval(coarse_values, best_value, search_lower, search_upper):
    best_index = coarse_values.index(best_value)
    if best_index > 0:
        lower = coarse_values[best_index - 1]
    else:
        lower = best_value - (coarse_values[1] - best_value)
    if best_index < len(coarse_values) - 1:
        upper = coarse_values[best_index + 1]
    else:
        upper = best_value + (best_value - coarse_values[-2])

    lower = max(lower, search_lower)
    upper = min(upper, search_upper)
    return lower, upper


def expand_fine_search(config, coarse_dir):
    coarse_manifest = read_json(coarse_dir / "run_manifest.json")
    for key in ("split", "gold_path", "split_ids_path", "representations"):
        if config[key] != coarse_manifest[key]:
            raise ValueError(f"Fine-search config does not match coarse run field '{key}'.")

    evaluations = []
    for path in coarse_dir.glob("*_evaluation.json"):
        result = read_json(path)
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
        points = int(search["points"])
        if points < 2:
            raise ValueError(f"Fine-search points must be at least 2: {search}")
        domain_lower, domain_upper = (0.0, 1.0) if parameter == "margin" else (-1.0, 1.0)
        search_lower = float(search.get("lower", domain_lower))
        search_upper = float(search.get("upper", domain_upper))
        if not domain_lower <= search_lower < search_upper <= domain_upper:
            raise ValueError(f"Fine-search bounds are outside the valid {parameter} domain: {search}")

        for top_k in top_k_values:
            matched = [
                result for result in results
                if result["experiment"].get("top_k") == top_k
                and parameter in result["experiment"]
            ]
            if not matched:
                raise ValueError(f"No coarse runs for {representation}/{method}, top_k={top_k}")
            best_coarse = max(matched, key=result_rank)["experiment"]
            best_value = float(best_coarse[parameter])
            coarse_values = sorted({float(result["experiment"][parameter]) for result in matched})
            if len(coarse_values) < 2:
                raise ValueError(
                    f"Need at least two coarse {parameter} values for {representation}/{method}, top_k={top_k}"
                )

            lower, upper = neighboring_interval(coarse_values, best_value, search_lower, search_upper)
            if lower >= upper:
                raise ValueError(
                    f"Could not form a local fine-search range for {representation}/{method}, "
                    f"top_k={top_k}, best={best_value}"
                )

            # Keep the best coarse point even if the local grid does not land on it.
            fine_experiments.append(best_coarse)
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
        scores, chunk_ids = load_scores(files, development_ids, representation)

        for experiment in representation_experiments:
            predictions = make_predictions(experiment, scores, chunk_ids, development_ids)
            result = evaluator.eval(
                predictions,
                question_ids=development_ids,
            )
            name = experiment_name(experiment)
            write_jsonl(output_dir / f"{name}_predictions.jsonl", predictions)
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
