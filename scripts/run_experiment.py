"""Run experiment stages from a JSON configuration."""

import argparse

from .core.config import load_config
from .core.pipeline import (
    development,
    initialize_run,
    preflight,
    test,
    validation,
)


def main():
    """Read command-line options and run the requested stages."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument(
        "--stage",
        choices=("check", "development", "validation", "test", "all"),
        default="all",
    )
    parser.add_argument(
        "--confirm-test",
        action="store_true",
        help="Required for test or all; freeze the protocol first",
    )
    args = parser.parse_args()
    if args.stage in ("test", "all") and not args.confirm_test:
        parser.error(
            (
                "--confirm-test is required for --stage test/all; use "
                "--stage development to tune"
            )
        )
    config = load_config(args.config)
    preflight(config)
    print("Input and configuration checks passed.")
    if args.stage == "check":
        return
    initialize_run(config)
    stages = (
        ("development", "validation", "test")
        if args.stage == "all"
        else (args.stage,)
    )
    for stage in stages:
        {"development": development, "validation": validation, "test": test}[
            stage
        ](config)
        if stage in ("validation", "test") and config.get("baselines", {}).get(
            "enabled", False
        ):
            from .core.baselines import run_baselines

            run_baselines(config, stage)
        if config.get("reports", True):
            from .core.reporting import report_stage

            report_stage(config, stage)


if __name__ == "__main__":
    main()
