"""Compare a rerun's summaries and winner with a published experiment."""

import argparse
import json
import math
from pathlib import Path

STAGE_COUNTS = {
    "development/coarse": 157,
    "development/fine": 4227,
    "development": 12,
    "validation": 5,
    "test": 1,
}


def read_summaries(directory, stage):
    path = directory / stage / "summary.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    summaries = {row["experiment"]: row for row in rows}
    if len(summaries) != len(rows):
        raise ValueError(f"{path}: duplicate setting names")
    return summaries


def compare_results(reference, rerun):
    for stage, count in STAGE_COUNTS.items():
        expected = read_summaries(reference, stage)
        actual = read_summaries(rerun, stage)
        if len(expected) != count or len(actual) != count:
            raise ValueError(
                f"{stage}: expected {count} settings; "
                f"reference has {len(expected)}, rerun has {len(actual)}"
            )
        if actual.keys() != expected.keys():
            raise ValueError(f"{stage}: setting names differ")
        for name, row in expected.items():
            if actual[name].keys() != row.keys():
                raise ValueError(f"{stage}, {name}: summary fields differ")
            for key, value in row.items():
                result = actual[name][key]
                if isinstance(value, float):
                    matches = isinstance(result, (int, float)) and (
                        math.isclose(result, value, rel_tol=0, abs_tol=1e-12)
                    )
                else:
                    matches = result == value
                if not matches:
                    raise ValueError(
                        f"{stage}, {name}, {key}: "
                        f"reference={value!r}, rerun={result!r}"
                    )
    winners = []
    for directory in (reference, rerun):
        path = directory / "validation/frozen_winner.json"
        winners.append(json.loads(path.read_text())["winner"])
    if winners[0] != winners[1]:
        raise ValueError("validation: frozen winners differ")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path, help="published run directory")
    parser.add_argument("rerun", type=Path, help="new run directory")
    args = parser.parse_args()
    try:
        compare_results(args.reference, args.rerun)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"Comparison failed: {error}\n")
    print(f"{args.rerun}: stage counts, summary values and winner match.")


if __name__ == "__main__":
    main()
