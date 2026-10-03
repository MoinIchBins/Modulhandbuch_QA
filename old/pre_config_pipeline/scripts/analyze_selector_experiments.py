import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


PARAMETERS = ("threshold", "margin")


def rank_key(row):
    return (
        row["mean_question_f1"],
        row["exact_match_rate"],
        row["mean_question_precision"],
        -row["average_selected_chunks"],
    )


def load_results(run_dir):
    rows = []
    for path in sorted(run_dir.glob("*_evaluation.json")):
        with path.open("r", encoding="utf-8") as file:
            result = json.load(file)
        experiment = result["experiment"]
        rows.append({
            "experiment": path.stem.removesuffix("_evaluation"),
            "representation": experiment["representation"],
            "method": experiment["method"],
            "top_k": experiment.get("top_k"),
            "threshold": experiment.get("threshold"),
            "margin": experiment.get("margin"),
            **result["summary"],
        })
    return rows


def group_results(rows):
    groups = {}
    for row in rows:
        groups.setdefault((row["representation"], row["method"]), []).append(row)

    return groups


def make_suggestions(rows):
    suggestions = []
    groups = group_results(rows)

    for (representation, method), group in sorted(groups.items()):
        best = max(group, key=rank_key)
        parameter = next((name for name in PARAMETERS if best[name] is not None), None)
        if parameter is None:
            continue
        top_k = best["top_k"]
        values = sorted({
            row[parameter]
            for row in group
            if row["top_k"] == top_k and row[parameter] is not None
        })
        if len(values) < 3:
            continue
        # Report observed neighbors; the runner additionally extends edge intervals.
        index = values.index(best[parameter])
        suggestions.append({
            "representation": representation,
            "method": method,
            "top_k": top_k,
            "parameter": parameter,
            "best_coarse_value": best[parameter],
            "suggested_interval": [values[max(0, index - 1)], values[min(len(values) - 1, index + 1)]],
            "mean_question_f1": best["mean_question_f1"],
            "exact_match_rate": best["exact_match_rate"],
        })
    return suggestions


def plot_numeric_results(rows, output_dir):
    frame = pd.DataFrame(rows)
    for method in sorted(frame["method"].unique()):
        method_rows = frame[frame["method"] == method]
        parameter = next((name for name in PARAMETERS if method_rows[name].notna().any()), None)
        fig, ax = plt.subplots(figsize=(9, 5))
        if parameter:
            for (representation, top_k), group in method_rows.groupby(["representation", "top_k"], dropna=False):
                group = group.dropna(subset=[parameter]).sort_values(parameter)
                if group.empty:
                    continue
                label = representation if pd.isna(top_k) else f"{representation}, top_k={int(top_k)}"
                ax.plot(group[parameter], group["mean_question_f1"], marker="o", label=label)
            ax.set_xlabel(parameter.replace("_", " ").title())
        else:
            for representation, group in method_rows.groupby("representation"):
                group = group.sort_values("top_k")
                ax.plot(group["top_k"], group["mean_question_f1"], marker="o", label=representation)
            ax.set_xlabel("Top K")
        ax.set_ylabel("Mean question-level F1")
        ax.set_title(f"Development coarse sweep: {method}")
        ax.grid(alpha=0.25)
        ax.legend()
        fig.tight_layout()
        fig.savefig(output_dir / f"{method}_development.png", dpi=200)
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Compare all methods and representations in one development run.")
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    rows = load_results(args.run_dir)
    if not rows:
        raise ValueError(f"No evaluation files found in {args.run_dir}")
    output_dir = args.output_dir or args.run_dir / "comparison"
    output_dir.mkdir(parents=True, exist_ok=False)

    results = pd.DataFrame(rows).sort_values(
        ["representation", "method", "mean_question_f1"],
        ascending=[True, True, False],
    )
    results.to_csv(output_dir / "development_comparison.csv", index=False)
    suggestions = make_suggestions(rows)
    (output_dir / "fine_search_suggestions.json").write_text(
        json.dumps(suggestions, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    plot_numeric_results(rows, output_dir)

    print("\nBest coarse configuration per representation and selector")
    best_rows = {
        key: max(group, key=rank_key)
        for key, group in group_results(rows).items()
    }
    for key, row in sorted(best_rows.items()):
        parameter = next((name for name in ("top_k", "threshold", "margin") if row[name] is not None), None)
        setting = f"{parameter}={row[parameter]}" if parameter else "default"
        print(f"  {key[0]} / {key[1]} / {setting}: F1={row['mean_question_f1']:.4f}")

    print("\nSuggested local intervals for fine search")
    for item in suggestions:
        print(
            f"  {item['representation']} / {item['method']} / top_k={item['top_k']} "
            f"{item['parameter']}={item['best_coarse_value']}: "
            f"[{item['suggested_interval'][0]}, {item['suggested_interval'][1]}]"
        )
    print(f"\nComparison saved to: {output_dir}")


if __name__ == "__main__":
    main()
