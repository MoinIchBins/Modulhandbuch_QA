import csv
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from urllib.parse import quote

CATEGORIES = {
    "1": "valid_alternative_evidence",
    "2": "gold_mapping_issue",
    "3": "partial_evidence_only",
    "4": "similar_wrong_chunk",
    "5": "question_wording_or_lexical_issue",
    "6": "near_duplicate_or_neighboring_clause",
    "7": "chunking_issue",
    "8": "source_ambiguity_or_inconsistency",
    "9": "unrelated_retrieval_failure",
    "10": "structural_top1_limitation",
    "11": "threshold_abstention_failure",
    "12": "false_positive_on_unanswerable",
    "13": "needs_second_review",
    "0": "other",
}

CATEGORY_DESCRIPTIONS = {
    "1": (
        "Predicted evidence fully supports the correct answer even though it differs from the current gold mapping."
    ),
    "2": (
        "The current gold mapping or answerability label appears wrong, incomplete, or too restrictive."
    ),
    "3": (
        "The prediction contains relevant evidence, but not enough to fully support the answer."
    ),
    "4": (
        "The prediction is semantically/topically similar, but does not provide the required evidence."
    ),
    "5": (
        "Question wording, terminology, or lexical mismatch plausibly contributed to the error."
    ),
    "6": (
        "A neighboring or near-duplicate clause was retrieved instead of the required evidence."
    ),
    "7": ("Chunk boundaries or stored context plausibly caused the failure."),
    "8": (
        "The source document itself is ambiguous, duplicated, or internally inconsistent."
    ),
    "9": ("The retrieved chunk is not sufficiently related to the question."),
    "10": (
        "The question genuinely requires multiple gold chunks, but the frozen top-1 selector can return at most one."
    ),
    "11": (
        "The question is answerable and the gold mapping is defensible, but the system abstained because no score passed the threshold."
    ),
    "12": (
        "The question is genuinely unanswerable from the source, but the system nevertheless returned a chunk."
    ),
    "13": ("The case cannot currently be classified confidently."),
    "0": "A different explanation not covered above.",
}

CATEGORY_CODES = {label: code for code, label in CATEGORIES.items()}


def load_csv(path):
    """Read review records in their existing order."""
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def split_ids(value):
    """Decode pipe-separated review IDs; an empty field denotes no chunks."""
    if not value:
        return []
    return [x.strip() for x in value.split("|") if x.strip()]


def open_chunk(chunk_id, browser_url):
    """Open a URL-encoded evidence ID in the local chunk browser."""
    url = f"{browser_url}?chunk_id={quote(chunk_id)}"
    webbrowser.open(url, new=0)


def save_rows(rows, output_path):
    """Atomically replace the review CSV so interrupted saves preserve decisions."""
    if not rows:
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(rows[0].keys())
    temp_path = output_path.with_suffix(".tmp")

    with temp_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    temp_path.replace(output_path)


def print_categories():
    """Show all review categories and their descriptions."""
    print()
    print("Categories:")

    for code, label in CATEGORIES.items():
        print(f" {code}  {label}")
        print(f"       {CATEGORY_DESCRIPTIONS[code]}")

    print()


def print_summary(rows):
    """Report reviewed cases and category counts within each input group."""
    print()
    print("Review summary:")

    groups = []
    for row in rows:
        group = row["source_error_group"]
        if group not in groups:
            groups.append(group)

    for group in groups:
        group_rows = [
            row for row in rows if row["source_error_group"] == group
        ]

        reviewed_rows = [
            row for row in group_rows if row.get("manual_category")
        ]

        print()
        print(f"{group}: {len(reviewed_rows)}/{len(group_rows)} reviewed")

        counts = {}
        for row in reviewed_rows:
            label = row["manual_category"]
            counts[label] = counts.get(label, 0) + 1

        for label, count in sorted(
            counts.items(),
            key=lambda item: (-item[1], item[0]),
        ):
            print(f"  {label}: {count}")

    print()


def normalize_source_row(row, error_group):
    """Standardize legacy evidence columns and initialize review fields."""
    normalized = dict(row)

    normalized["source_error_group"] = error_group
    normalized["manual_category_code"] = ""
    normalized["manual_category"] = ""
    normalized["manual_note"] = ""

    if "gold_chunk_ids" not in normalized:
        normalized["gold_chunk_ids"] = normalized.get(
            "gold_chunks", ""
        ) or normalized.get("gold_chunk_id", "")

    if "predicted_chunk_ids" not in normalized:
        normalized["predicted_chunk_ids"] = normalized.get(
            "predicted_chunks", ""
        ) or normalized.get("predicted_chunk_id", "")

    return normalized


def load_reviews(review_files, previous_manual_review, output_path):
    """Import earlier labels, then let resumable output decisions take precedence."""
    rows = []

    for error_group, path in review_files.items():
        source_rows = load_csv(path)

        for row in source_rows:
            rows.append(normalize_source_row(row, error_group))

    if previous_manual_review is not None and previous_manual_review.exists():
        previous_manual = {
            row["question_id"]: row for row in load_csv(previous_manual_review)
        }

        imported = 0

        for row in rows:
            if row["source_error_group"] != "manual_wrong_nonempty":
                continue

            old = previous_manual.get(row["question_id"])

            if not old:
                continue

            row["manual_category_code"] = old.get("manual_category_code", "")
            row["manual_category"] = old.get("manual_category", "")
            row["manual_note"] = old.get("manual_note", "")
            imported += 1

        print(
            f"Imported {imported} existing manual-review decisions "
            f"from {previous_manual_review}."
        )

    if output_path.exists():
        previous = {
            (
                row["question_id"],
                row["source_error_group"],
            ): row
            for row in load_csv(output_path)
        }

        for row in rows:
            old = previous.get(
                (
                    row["question_id"],
                    row["source_error_group"],
                )
            )

            if not old:
                continue

            old_label = old.get("manual_category", "")
            old_code = old.get("manual_category_code", "")

            if not old_code and old_label in CATEGORY_CODES:
                old_code = CATEGORY_CODES[old_label]

            row["manual_category_code"] = old_code
            row["manual_category"] = old_label
            row["manual_note"] = old.get("manual_note", "")

    return rows


def review_case(row, index, total, rows, output_path, browser_url):
    """Show one case, handle browsing commands and save its review label."""
    error_group = row["source_error_group"]
    gold_ids = split_ids(row.get("gold_chunk_ids", ""))
    predicted_ids = split_ids(row.get("predicted_chunk_ids", ""))

    print("=" * 76)
    print(f"[{index}/{total}] " f"{row['question_id']}  [{error_group}]")
    print()
    print(row.get("question", ""))
    print()
    print(f"Gold:      {', '.join(gold_ids) or '[]'}")
    print(f"Predicted: {', '.join(predicted_ids) or '[]'}")

    if row["manual_category"]:
        print()
        print(
            "Current category: "
            f"{row['manual_category_code']} "
            f"{row['manual_category']}"
        )
        if row["manual_note"]:
            print(f"Current note: {row['manual_note']}")

    print()

    if predicted_ids:
        open_chunk(predicted_ids[0], browser_url)
    elif gold_ids:
        open_chunk(gold_ids[0], browser_url)

    while True:
        choice = (
            input(
                "Category, p/g/a, ?, q"
                + (", or Enter to keep" if row["manual_category"] else "")
                + ": "
            )
            .strip()
            .lower()
        )

        if choice == "?":
            print_categories()
            continue

        if choice in ("p", "g", "a"):
            chunk_ids = {
                "p": predicted_ids,
                "g": gold_ids,
                "a": predicted_ids + gold_ids,
            }[choice]
            for chunk_id in chunk_ids:
                open_chunk(chunk_id, browser_url)
            continue

        if choice == "q":
            return False

        if choice == "" and row["manual_category"]:
            print("Kept existing category.")
            break

        if choice not in CATEGORIES:
            print("Unknown category. Enter ? to see the options.")
            continue

        category_label = CATEGORIES[choice]
        note = input("Short note: ").strip()

        row["manual_category_code"] = choice
        row["manual_category"] = category_label
        row["manual_note"] = note

        save_rows(rows, output_path)

        print(f"Saved: {choice} {category_label}")
        break

    return True


def run_review(
    chunks_path,
    browser_dir,
    review_files,
    previous_manual_review,
    output_path,
    port,
):
    """Start the evidence browser and review the supplied cases."""
    if not chunks_path.exists():
        raise FileNotFoundError(f"Chunk file not found: {chunks_path}")

    if not (browser_dir / "index.html").exists():
        raise FileNotFoundError(f"Chunk browser not found: {browser_dir}")

    missing_files = [
        str(path) for path in review_files.values() if not path.exists()
    ]

    if missing_files:
        raise FileNotFoundError(
            "Missing review input file(s):\n  " + "\n  ".join(missing_files)
        )
    rows = load_reviews(review_files, previous_manual_review, output_path)
    if not rows:
        print("No error cases to review.")
        return
    browser_url = f"http://localhost:{port}/"
    shutil.copyfile(
        chunks_path,
        browser_dir / "chunks.jsonl",
    )

    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port)],
        cwd=browser_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        time.sleep(0.7)

        if server.poll() is not None:
            raise RuntimeError(
                f"Could not start the chunk browser server on port {port}."
            )

        print(f"Loaded {len(rows)} review cases.")
        print()
        print("Browser commands:")
        print("  p  open predicted chunk(s)")
        print("  g  open gold chunk(s)")
        print("  a  open predicted and gold chunk(s)")
        print("  ?  show category descriptions")
        print("  q  save and quit")
        print()
        print("Enter the category number directly.")
        print("For an already reviewed case, press Enter to keep it.")

        for index, row in enumerate(rows, start=1):
            if not review_case(
                row, index, len(rows), rows, output_path, browser_url
            ):
                save_rows(rows, output_path)
                print_summary(rows)
                print(f"Saved to: {output_path}")
                return
    finally:
        if server.poll() is None:
            server.terminate()
            server.wait()

    save_rows(rows, output_path)
    print_summary(rows)
    print(f"Done. Results saved to: {output_path}")


def main():
    """Load the review files and resume the interactive review."""
    import argparse
    from ..core.config import load_config
    from ..core.pipeline import initialize_run, preflight, require_stage

    parser = argparse.ArgumentParser(
        description="Review the configured experiment's error groups"
    )
    parser.add_argument("--config", required=True)
    parser.add_argument("--split", choices=("validation", "test"))
    args = parser.parse_args()

    config = load_config(args.config)
    options = config.get("manual_review", {})
    split = args.split or options.get("split", "validation")
    root = Path(config["output_dir"])

    require_stage(root / split)
    preflight(config)
    initialize_run(config)

    folder = root / "manual_review" / split
    files = {
        "manual_wrong_nonempty": folder / "manual_review.csv",
        "multi_gold_single_prediction": folder
        / "category_2_multi_gold_single_prediction.csv",
        "answerable_but_abstained": folder
        / "category_3_answerable_but_abstained.csv",
        "zero_gold_but_retrieved": folder
        / "category_4_zero_gold_but_retrieved.csv",
    }

    previous = options.get("previous_review")
    previous = Path(config["project_root"]) / previous if previous else None

    # Copy browser assets into the experiment's review folder.
    browser_dir = folder / "browser"
    if not browser_dir.exists():
        shutil.copytree(
            Path(config["project_root"]) / "tools/chunk_browser",
            browser_dir,
            ignore=shutil.ignore_patterns("chunks.jsonl"),
        )
        
    run_review(
        Path(config["chunks_path"]),
        browser_dir,
        files,
        previous,
        folder / "manual_review_all_error_groups.csv",
        options.get("port", 8000),
    )


if __name__ == "__main__":
    main()
