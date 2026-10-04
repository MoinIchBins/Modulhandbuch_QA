import numpy as np

from .ranking import rank_key

def expand_sweeps(config):
    """Expand the coarse parameter grids."""
    if config.get("experiments"):
        experiments = config["experiments"]
    else:
        representations = config["representations"]
        experiments = []
        for sweep in config["sweeps"]:
            method = sweep["method"]
            for representation in sweep.get(
                "representations", representations
            ):
                if method == "threshold":
                    values = sweep["thresholds_by_representation"][
                        representation
                    ]
                    top_k_values = [None]
                    parameter = "threshold"
                elif method == "top_k_threshold":
                    values = sweep["thresholds_by_representation"][
                        representation
                    ]
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
                        experiment = {
                            "representation": representation,
                            "method": method,
                        }
                        if top_k is not None:
                            experiment["top_k"] = top_k
                        if parameter:
                            experiment[parameter] = value
                        experiments.append(experiment)

    if config.get("require_all_combinations"):
        expected = {
            (representation, method)
            for representation in config["representations"]
            for method in (
                "top_k",
                "threshold",
                "top_k_threshold",
                "relative_margin",
            )
        }
        actual = {
            (item["representation"], item["method"]) for item in experiments
        }
        if actual != expected:
            raise ValueError(
                f"Sweep is incomplete; expected {sorted(expected)}, got {sorted(actual)}"
            )
    return experiments


def neighboring_interval(
    coarse_values, best_value, search_lower, search_upper
):
    """Bracket a coarse winner, extending edge intervals within the bounds."""
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


def fine_search_bounds(search):
    """Validate a fine-search specification and return its numeric bounds."""
    parameter = (
        "margin" if search["method"] == "relative_margin" else "threshold"
    )
    if search.get("parameter") != parameter:
        raise ValueError(f"Fine search must tune {parameter}")

    lower, upper = search["lower"], search["upper"]
    if not np.isfinite([lower, upper]).all() or lower >= upper:
        raise ValueError("Fine-search bounds must be finite and increasing")

    if parameter == "margin" and not 0 <= lower < upper <= 1:
        raise ValueError("Fine-search margin bounds must be within [0, 1]")

    return parameter, float(lower), float(upper)


def validate_fine_searches(config, experiments):
    """Check that each continuous selector family has a refinement grid."""
    expected = {
        (row["representation"], row["method"])
        for row in experiments
        if row["method"] != "top_k"
    }

    searches = config.get("fine_searches", [])
    actual = [(row["representation"], row["method"]) for row in searches]
    if len(actual) != len(set(actual)) or set(actual) != expected:
        raise ValueError(
            (
                "Fine-search specs must cover each non-top_k coarse group exactly once"
            )
        )
    
    for search in searches:
        parameter, _, _ = fine_search_bounds(search)
        for top_k in search.get("top_k_values", [None]):
            values = {
                row[parameter]
                for row in experiments
                if row["representation"] == search["representation"]
                and row["method"] == search["method"]
                and row.get("top_k") == top_k
            }
            if len(values) < 2:
                raise ValueError(
                    (
                        "Each refined selector/top_k group needs at least two coarse values"
                    )
                )


def refine_selector(search, results):
    """Refine each k for one family and retain its best coarse point."""
    representation = search["representation"]
    method = search["method"]
    fine_experiments = []
    parameter, search_lower, search_upper = fine_search_bounds(search)
    top_k_values = search.get("top_k_values", [None])

    for top_k in top_k_values:
        matched = [
            result for result in results
            if result["experiment"].get("top_k") == top_k
            and parameter in result["experiment"]
        ]

        if not matched:
            raise ValueError(
                f"No coarse runs for {representation}/{method}, "
                f"top_k={top_k}"
            )

        best_coarse = max(
            matched, key=lambda result: rank_key(result["summary"])
        )["experiment"]
        best_value = float(best_coarse[parameter])
        coarse_values = sorted(
            {float(result["experiment"][parameter]) for result in matched}
        )

        if len(coarse_values) < 2:
            raise ValueError(
                f"Need at least two coarse {parameter} values for "
                f"{representation}/{method}, top_k={top_k}"
            )

        lower, upper = neighboring_interval(
            coarse_values, best_value, search_lower, search_upper
        )
        if lower >= upper:
            raise ValueError(
                f"Could not form a local fine-search range for "
                f"{representation}/{method}, "
                f"top_k={top_k}, best={best_value}"
            )

        # Keep the best coarse point even if the local grid does not land on it.
        fine_experiments.append(best_coarse)
        for value in np.linspace(lower, upper, 201):
            experiment = {
                "representation": representation,
                "method": method,
                parameter: round(float(value), 8),
            }
            if top_k is not None:
                experiment["top_k"] = top_k
            fine_experiments.append(experiment)

    return fine_experiments


def expand_fine_search(config, evaluations):
    """Refine coarse winners, retain their points and deduplicate settings."""
    if not evaluations:
        raise ValueError("No coarse evaluations supplied")

    groups = {}
    for result in evaluations:
        experiment = result["experiment"]
        groups.setdefault(
            (experiment["representation"], experiment["method"]), []
        ).append(result)

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
        raise ValueError(
            f"Fine-search specs do not match coarse methods; "
            f"missing={missing}, extra={extra}"
        )

    fine_experiments = []
    for (representation, method), results in sorted(groups.items()):
        if method == "top_k":
            fine_experiments.append(
                max(results, key=lambda result: rank_key(result["summary"]))[
                    "experiment"
                ]
            )
            continue

        fine_experiments.extend(
            refine_selector(
                search_by_group[(representation, method)],
                results,
            )
        )

    # Avoid duplicate runs when neighboring coarse points refine to the same grid.
    unique = {}
    for experiment in fine_experiments:
        key = tuple(
            (field, experiment.get(field))
            for field in (
                "representation",
                "method",
                "top_k",
                "threshold",
                "margin",
            )
        )
        unique[key] = experiment
    return list(unique.values())
