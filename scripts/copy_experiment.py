"""Copy a config with a new run name and output directory."""

import argparse
from pathlib import Path

from .core.config import load_config, read_json, write_json


def copy_experiment(source, destination, name, output_dir):
    """Copy the config, keeping input paths relative to its project root."""
    config = read_json(source)
    root = Path(load_config(source)["project_root"])
    destination = Path(destination)
    output = (root / output_dir).resolve()
    if destination.exists() or output.exists():
        raise FileExistsError("Choose a new config path and output directory")
    config.update(project_root=str(root), name=name, output_dir=str(output))
    destination.parent.mkdir(parents=True, exist_ok=True)
    write_json(destination, config)
    return destination


def main():
    """Read the command-line arguments and write the copied config."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--destination", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    path = copy_experiment(
        args.config, args.destination, args.name, args.output_dir
    )
    print(f"Rerun config: {path}")


if __name__ == "__main__":
    main()
