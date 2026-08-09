import csv
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from urllib.parse import quote


# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

CHUNK_BROWSER_DIR = Path("data/visualization/chunk_browser")

CHUNKS_PATH = Path(
    "data/produced_v2/frozen/PO_25_CL_chunks.jsonl"
)

ERROR_ANALYSIS_DIR = Path(
    "data/produced_v2/selector_experiments/validation_finalists/"
    "error_analysis_of_best"
)

REVIEW_FILES = {
    "manual_wrong_nonempty": ERROR_ANALYSIS_DIR / "manual_review.csv",
    "multi_gold_single_prediction": (
        ERROR_ANALYSIS_DIR / "category_2_multi_gold_single_prediction.csv"
    ),
    "answerable_but_abstained": (
        ERROR_ANALYSIS_DIR / "category_3_answerable_but_abstained.csv"
    ),
    "zero_gold_but_retrieved": (
        ERROR_ANALYSIS_DIR / "category_4_zero_gold_but_retrieved.csv"
    ),
}

OUTPUT_PATH = (
    ERROR_ANALYSIS_DIR / "manual_review_all_error_groups.csv"
)

# Existing completed review of the 31 wrong-nonempty cases.
# If present, these decisions are imported automatically so you do not
# have to review those 31 questions again.
PREVIOUS_MANUAL_REVIEW = (
    ERROR_ANALYSIS_DIR / "manual_review_evaluated_v3.csv"
)

PORT = 8000
BROWSER_URL = f"http://localhost:{PORT}/"


# ---------------------------------------------------------------------
# Review categories
# ---------------------------------------------------------------------

# These are intentionally broad enough to work across all four
# error groups. The source_error_group column preserves which
# automatic error bucket a question originally came from.
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
        "Predicted evidence fully supports the correct answer even though "
        "it differs from the current gold mapping."
    ),
    "2": (
        "The current gold mapping or answerability label appears wrong, "
        "incomplete, or too restrictive."
    ),
    "3": (
        "The prediction contains relevant evidence, but not enough to "
        "fully support the answer."
    ),
    "4": (
        "The prediction is semantically/topically similar, but does not "
        "provide the required evidence."
    ),
    "5": (
        "Question wording, terminology, or lexical mismatch plausibly "
        "contributed to the error."
    ),
    "6": (
        "A neighboring or near-duplicate clause was retrieved instead "
        "of the required evidence."
    ),
    "7": (
        "Chunk boundaries or stored context plausibly caused the failure."
    ),
    "8": (
        "The source document itself is ambiguous, duplicated, or "
        "internally inconsistent."
    ),
    "9": (
        "The retrieved chunk is not sufficiently related to the question."
    ),
    "10": (
        "The question genuinely requires multiple gold chunks, but the "
        "frozen top-1 selector can return at most one."
    ),
    "11": (
        "The question is answerable and the gold mapping is defensible, "
        "but the system abstained because no score passed the threshold."
    ),
    "12": (
        "The question is genuinely unanswerable from the source, but the "
        "system nevertheless returned a chunk."
    ),
    "13": (
        "The case cannot currently be classified confidently."
    ),
    "0": "A different explanation not covered above.",
}

CATEGORY_CODES = {
    label: code
    for code, label in CATEGORIES.items()
}


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def load_csv(path):
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def split_ids(value):
    if not value:
        return []
    return [x.strip() for x in value.split("|") if x.strip()]


def open_chunk(chunk_id):
    url = f"{BROWSER_URL}?chunk_id={quote(chunk_id)}"
    webbrowser.open(url, new=0)


def save_rows(rows):
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(rows[0].keys())
    temp_path = OUTPUT_PATH.with_suffix(".tmp")

    with temp_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    temp_path.replace(OUTPUT_PATH)


def verify_saved(question_id, error_group, category_code, category_label):
    saved_rows = load_csv(OUTPUT_PATH)

    for row in saved_rows:
        if (
            row["question_id"] == question_id
            and row["source_error_group"] == error_group
        ):
            if (
                row.get("manual_category_code") == category_code
                and row.get("manual_category") == category_label
            ):
                return

            raise RuntimeError(
                f"Save verification failed for {question_id}: "
                f"expected {category_code} / {category_label}, "
                f"found {row.get('manual_category_code')} / "
                f"{row.get('manual_category')}"
            )

    raise RuntimeError(
        f"Save verification failed: {question_id} / {error_group} "
        "was not found in output."
    )


def print_categories(error_group=None):
    print()
    print("Categories:")

    recommended = {
        "manual_wrong_nonempty": {"1", "2", "3", "4", "5", "6", "7", "8", "9"},
        "multi_gold_single_prediction": {"2", "3", "7", "8", "10"},
        "answerable_but_abstained": {"2", "5", "7", "8", "11"},
        "zero_gold_but_retrieved": {"2", "4", "5", "8", "9", "12"},
    }.get(error_group, set(CATEGORIES))

    for code, label in CATEGORIES.items():
        marker = "*" if code in recommended else " "
        print(f" {marker} {code:>2}  {label}")
        print(f"       {CATEGORY_DESCRIPTIONS[code]}")

    print()
    print("* = especially relevant for this error group")
    print()


def print_summary(rows):
    print()
    print("Review summary:")

    groups = []
    for row in rows:
        group = row["source_error_group"]
        if group not in groups:
            groups.append(group)

    for group in groups:
        group_rows = [
            row for row in rows
            if row["source_error_group"] == group
        ]

        reviewed_rows = [
            row for row in group_rows
            if row.get("manual_category")
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
    normalized = dict(row)

    normalized["source_error_group"] = error_group
    normalized["manual_category_code"] = ""
    normalized["manual_category"] = ""
    normalized["manual_note"] = ""

    # The error-analysis CSVs should use these names already, but this
    # keeps the script usable if one of them uses singular/alternate names.
    if "gold_chunk_ids" not in normalized:
        normalized["gold_chunk_ids"] = (
            normalized.get("gold_chunks", "")
            or normalized.get("gold_chunk_id", "")
        )

    if "predicted_chunk_ids" not in normalized:
        normalized["predicted_chunk_ids"] = (
            normalized.get("predicted_chunks", "")
            or normalized.get("predicted_chunk_id", "")
        )

    return normalized


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main():
    if not CHUNKS_PATH.exists():
        raise FileNotFoundError(f"Chunk file not found: {CHUNKS_PATH}")

    if not (CHUNK_BROWSER_DIR / "index.html").exists():
        raise FileNotFoundError(
            f"Chunk browser not found: {CHUNK_BROWSER_DIR}"
        )

    missing_files = [
        str(path)
        for path in REVIEW_FILES.values()
        if not path.exists()
    ]

    if missing_files:
        raise FileNotFoundError(
            "Missing review input file(s):\n  "
            + "\n  ".join(missing_files)
        )

    # The browser expects chunks.jsonl in its own directory.
    shutil.copyfile(
        CHUNKS_PATH,
        CHUNK_BROWSER_DIR / "chunks.jsonl",
    )

    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(PORT)],
        cwd=CHUNK_BROWSER_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    time.sleep(0.7)

    if server.poll() is not None:
        raise RuntimeError(
            f"Could not start the chunk browser server on port {PORT}."
        )

    rows = []

    for error_group, path in REVIEW_FILES.items():
        source_rows = load_csv(path)

        for row in source_rows:
            rows.append(
                normalize_source_row(row, error_group)
            )

    # Import the already completed v3 review for the 31 manual
    # wrong-nonempty cases, if that file exists.
    if PREVIOUS_MANUAL_REVIEW.exists():
        previous_manual = {
            row["question_id"]: row
            for row in load_csv(PREVIOUS_MANUAL_REVIEW)
        }

        imported = 0

        for row in rows:
            if row["source_error_group"] != "manual_wrong_nonempty":
                continue

            old = previous_manual.get(row["question_id"])

            if not old:
                continue

            row["manual_category_code"] = old.get(
                "manual_category_code", ""
            )
            row["manual_category"] = old.get(
                "manual_category", ""
            )
            row["manual_note"] = old.get(
                "manual_note", ""
            )
            imported += 1

        print(
            f"Imported {imported} existing manual-review decisions "
            f"from {PREVIOUS_MANUAL_REVIEW}."
        )

    # Resume prior work from this combined output file.
    # Combined-output decisions take precedence over imported v3 decisions.
    if OUTPUT_PATH.exists():
        previous = {
            (
                row["question_id"],
                row["source_error_group"],
            ): row
            for row in load_csv(OUTPUT_PATH)
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

    print(f"Loaded {len(rows)} review cases.")
    print()
    print("Browser commands:")
    print("  p  open predicted chunk(s)")
    print("  g  open gold chunk(s)")
    print("  a  open predicted and gold chunk(s)")
    print("  ?  show category descriptions")
    print("  q  save and quit")
    print()
    print("Enter the category number directly, exactly like the old script.")
    print("For an already reviewed case, press Enter to keep it.")

    try:
        for index, row in enumerate(rows, start=1):
            error_group = row["source_error_group"]
            gold_ids = split_ids(row.get("gold_chunk_ids", ""))
            predicted_ids = split_ids(row.get("predicted_chunk_ids", ""))

            print("=" * 76)
            print(
                f"[{index}/{len(rows)}] "
                f"{row['question_id']}  [{error_group}]"
            )
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

            # For ordinary wrong retrievals and zero-gold false positives,
            # the prediction is the most useful first thing to inspect.
            if predicted_ids:
                open_chunk(predicted_ids[0])
            # For abstentions there is no prediction, so open the gold
            # evidence immediately instead.
            elif gold_ids:
                open_chunk(gold_ids[0])

            while True:
                choice = input(
                    "Category, p/g/a, ?, q"
                    + (", or Enter to keep" if row["manual_category"] else "")
                    + ": "
                ).strip().lower()

                if choice == "?":
                    print_categories(error_group)
                    continue

                if choice == "p":
                    for chunk_id in predicted_ids:
                        open_chunk(chunk_id)
                    continue

                if choice == "g":
                    for chunk_id in gold_ids:
                        open_chunk(chunk_id)
                    continue

                if choice == "a":
                    for chunk_id in predicted_ids + gold_ids:
                        open_chunk(chunk_id)
                    continue

                if choice == "q":
                    save_rows(rows)
                    print_summary(rows)
                    print(f"Saved to: {OUTPUT_PATH}")
                    return

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

                save_rows(rows)

                verify_saved(
                    row["question_id"],
                    error_group,
                    choice,
                    category_label,
                )

                print(
                    f"Saved and verified: "
                    f"{choice} {category_label}"
                )
                break

    finally:
        if server.poll() is None:
            server.terminate()

    save_rows(rows)
    print_summary(rows)
    print(f"Done. Results saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
