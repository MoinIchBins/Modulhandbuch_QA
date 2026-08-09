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

CHUNK_BROWSER_DIR = Path("chunk_browser")

CHUNKS_PATH = Path(
    "data/produced_v2/frozen/PO_25_CL_chunks.jsonl"
)

REVIEW_PATH = Path(
    "data/produced_v2/selector_experiments/test_final_v1/"
    "error_analysis/manual_review.csv"
)

OUTPUT_PATH = Path(
    "data/produced_v2/selector_experiments/test_final_v1/"
    "error_analysis/manual_review_evaluated.csv"
)

PORT = 8000
BROWSER_URL = f"http://localhost:{PORT}/"


# ---------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------

CATEGORIES = {
    "1": "similar_wrong_chunk",
    "5": "question_wording_or_lexical_issue",
    "6": "near_duplicate_or_neighboring_clause",
    "7": "chunking_issue",
    "8": "gold_mapping_issue",
    "9": "valid_alternative_evidence",
    "0": "other",
}

CATEGORY_CODES = {
    label: code
    for code, label in CATEGORIES.items()
}


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


def verify_saved(question_id, category_code, category_label):
    saved_rows = load_csv(OUTPUT_PATH)

    for row in saved_rows:
        if row["question_id"] == question_id:
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
        f"Save verification failed: {question_id} was not found in output."
    )


def print_categories():
    print()
    print("Categories:")
    for code, label in CATEGORIES.items():
        print(f"  {code}  {label}")
    print()


def print_summary(rows):
    counts = {label: 0 for label in CATEGORIES.values()}

    for row in rows:
        category = row.get("manual_category", "")
        if category in counts:
            counts[category] += 1

    print()
    print("Category counts:")
    for label, count in counts.items():
        print(f"  {label}: {count}")
    print()


def main():
    if not REVIEW_PATH.exists():
        raise FileNotFoundError(f"Review file not found: {REVIEW_PATH}")

    if not CHUNKS_PATH.exists():
        raise FileNotFoundError(f"Chunk file not found: {CHUNKS_PATH}")

    if not (CHUNK_BROWSER_DIR / "index.html").exists():
        raise FileNotFoundError(
            f"Chunk browser not found: {CHUNK_BROWSER_DIR}"
        )

    # The browser expects chunks.jsonl in its own directory.
    shutil.copyfile(CHUNKS_PATH, CHUNK_BROWSER_DIR / "chunks.jsonl")

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

    source_rows = load_csv(REVIEW_PATH)

    # Add the manual-review fields to every source row.
    rows = []
    for row in source_rows:
        reviewed = dict(row)
        reviewed["manual_category_code"] = ""
        reviewed["manual_category"] = ""
        reviewed["manual_note"] = ""
        rows.append(reviewed)

    # If an output file already exists, copy its previous decisions into
    # the current rows. They are shown again and can be kept or changed.
    if OUTPUT_PATH.exists():
        previous = {
            row["question_id"]: row
            for row in load_csv(OUTPUT_PATH)
        }

        for row in rows:
            old = previous.get(row["question_id"])
            if old:
                old_label = old.get("manual_category", "")
                old_code = old.get("manual_category_code", "")

                # Older output files did not contain the numeric code.
                # Recover it from the saved label when possible.
                if not old_code and old_label in CATEGORY_CODES:
                    old_code = CATEGORY_CODES[old_label]

                row["manual_category_code"] = old_code
                row["manual_category"] = old_label
                row["manual_note"] = old.get(
                    "manual_note", ""
                )

    print(f"Loaded {len(rows)} questions.")
    print()
    print("Browser commands:")
    print("  p  open predicted chunk")
    print("  g  open gold chunk")
    print("  a  open predicted and gold chunks")
    print("  ?  show categories")
    print("  q  save and quit")
    print()
    print("For an already reviewed question, press Enter to keep")
    print("the existing category, or enter a new category to replace it.")
    print_categories()

    try:
        for index, row in enumerate(rows, start=1):
            gold_ids = split_ids(row.get("gold_chunk_ids", ""))
            predicted_ids = split_ids(row.get("predicted_chunk_ids", ""))

            print("=" * 72)
            print(f"[{index}/{len(rows)}] {row['question_id']}")
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
                open_chunk(predicted_ids[0])

            while True:
                choice = input(
                    "Category, p/g/a, ?, q"
                    + (", or Enter to keep" if row["manual_category"] else "")
                    + ": "
                ).strip().lower()

                if choice == "?":
                    print_categories()
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
