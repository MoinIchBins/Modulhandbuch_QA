"""Create tables and plots from completed experiment stages."""

import argparse
from pathlib import Path

from .core.config import load_config
from .core.pipeline import initialize_run, preflight
from .core.reporting import report_stage


def main():
    """Write reports for the completed stages."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config = load_config(args.config)
    root = Path(config["output_dir"])
    if not (root / "experiment.json").exists():
        raise ValueError("No experiment run to report")
    preflight(config)
    initialize_run(config)
    for stage in ("development", "validation", "test"):
        if (root / stage / "complete.json").exists():
            report_stage(config, stage)


if __name__ == "__main__":
    main()
