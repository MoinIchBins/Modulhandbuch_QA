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

REVIEW_PATH = Path(
    "data/produced_v2/selector_experiments/test_winner/"
    "error_analysis/manual_review.csv"
)

OUTPUT_PATH = Path(
    "data/produced_v2/selector_experiments/test_winner/"
    "error_analysis/manual_review_evaluated_v3.csv"
)

PORT = 8000
BROWSER_URL = f"http://localhost:{PORT}/"


# ---------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------

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
    "10": "needs_second_review",
    "0": "other",
}

CATEGORY_DESCRIPTIONS = {
    "1": (
        "Predicted chunk fully supports the correct answer, while the "
        "existing gold mapping is also defensible."
    ),
    "2": (
        "The existing gold mapping itself appears wrong, incomplete, "
        "or unjustifiably restrictive."
    ),
    "3": (
        "The predicted chunk contains relevant evidence, but not enough "
        "to fully support the answer."
    ),
    "4": (
        "The prediction is semantically/topically similar, but does not "
        "provide the required evidence."
    ),
    "5": (
        "Question wording, terminology, or lexical mismatch plausibly "
        "contributed to the retrieval failure."
    ),
    "6": (
        "The system retrieved a nearby or near-duplicate clause instead "
        "of the required one."
    ),
    "7": (
        "Chunk boundaries or stored context plausibly caused the failure."
    ),
    "8": (
        "The source document itself is ambiguous, duplicated, or "
        "internally inconsistent."
    ),
    "9": (
        "The predicted chunk is not sufficiently related to the required "
        "answer."
    ),
    "10": (
        "The case cannot currently be classified confidently and should "
        "be checked again."
    ),
    "0": "A different explanation not covered above.",
}

PREDICTION_SUPPORT = {
    "y": "fully_supports_answer",
    "p": "partially_supports_answer",
    "n": "does_not_support_answer",
    "u": "unclear",
}

GOLD_STATUS = {
    "y": "gold_mapping_acceptable",
    "n": "gold_mapping_problem",
    "u": "unclear",
}

CONFIDENCE = {
    "h": "high",
    "m": "medium",
    "l": "low",
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


def verify_saved(question_id, expected):
    saved_rows = load_csv(OUTPUT_PATH)

    for row in saved_rows:
        if row["question_id"] != question_id:
            continue

        for field, expected_value in expected.items():
            if row.get(field, "") != expected_value:
                raise RuntimeError(
                    f"Save verification failed for {question_id}: "
                    f"{field} expected {expected_value!r}, "
                    f"found {row.get(field, '')!r}"
                )
        return

    raise RuntimeError(
        f"Save verification failed: {question_id} was not found in output."
    )


def print_categories():
    print()
    print("Categories:")
    for code, label in CATEGORIES.items():
        print(f"  {code:>2}  {label}")
        print(f"      {CATEGORY_DESCRIPTIONS[code]}")
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


def ask_choice(prompt, choices, current=""):
    while True:
        suffix = f" [current: {current}]" if current else ""
        value = input(prompt + suffix + ": ").strip().lower()

        if value == "" and current:
            return current

        if value in choices:
            return choices[value]

        print("Unknown choice.")


def suggested_category(prediction_support, gold_status):
    if (
        prediction_support == "fully_supports_answer"
        and gold_status == "gold_mapping_acceptable"
    ):
        return "1"

    if gold_status == "gold_mapping_problem":
        return "2"

    if prediction_support == "partially_supports_answer":
        return "3"

    return None


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main():
    if not REVIEW_PATH.exists():
        raise FileNotFoundError(f"Review file not found: {REVIEW_PATH}")

    if not CHUNKS_PATH.exists():
        raise FileNotFoundError(f"Chunk file not found: {CHUNKS_PATH}")

    if not (CHUNK_BROWSER_DIR / "index.html").exists():
        raise FileNotFoundError(
            f"Chunk browser not found: {CHUNK_BROWSER_DIR}"
        )

    # The chunk visualizer expects chunks.jsonl in its own directory.
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

    source_rows = load_csv(REVIEW_PATH)

    rows = []
    for row in source_rows:
        reviewed = dict(row)
        reviewed["prediction_support"] = ""
        reviewed["gold_mapping_status"] = ""
        reviewed["manual_category_code"] = ""
        reviewed["manual_category"] = ""
        reviewed["review_confidence"] = ""
        reviewed["manual_note"] = ""
        rows.append(reviewed)

    # Resume only this new v3 review if it already exists.
    if OUTPUT_PATH.exists():
        previous = {
            row["question_id"]: row
            for row in load_csv(OUTPUT_PATH)
        }

        review_fields = [
            "prediction_support",
            "gold_mapping_status",
            "manual_category_code",
            "manual_category",
            "review_confidence",
            "manual_note",
        ]

        for row in rows:
            old = previous.get(row["question_id"])
            if old:
                for field in review_fields:
                    row[field] = old.get(field, "")

    print(f"Loaded {len(rows)} questions.")
    print()
    print("Chunk visualizer commands:")
    print("  p  open predicted chunk(s)")
    print("  g  open gold chunk(s)")
    print("  a  open predicted and gold chunks")
    print("  ?  show category definitions")
    print("  q  save and quit")
    print()
    print("Each case records:")
    print("  1. whether the predicted chunk itself supports the answer")
    print("  2. whether the original gold mapping is acceptable")
    print("  3. one primary error category")
    print("  4. confidence and a short note")
    print()
    print("The predicted chunk opens automatically for each question.")
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
                    "Current review:"
                    f"\n  prediction support: {row['prediction_support']}"
                    f"\n  gold mapping:       {row['gold_mapping_status']}"
                    f"\n  category:           "
                    f"{row['manual_category_code']} "
                    f"{row['manual_category']}"
                    f"\n  confidence:         {row['review_confidence']}"
                )
                if row["manual_note"]:
                    print(f"  note:               {row['manual_note']}")

            print()

            if predicted_ids:
                open_chunk(predicted_ids[0])

            while True:
                command = input(
                    "Enter r to review, p/g/a, ?, q"
                    + (", or Enter to keep" if row["manual_category"] else "")
                    + ": "
                ).strip().lower()

                if command == "?":
                    print_categories()
                    continue

                if command == "p":
                    for chunk_id in predicted_ids:
                        open_chunk(chunk_id)
                    continue

                if command == "g":
                    for chunk_id in gold_ids:
                        open_chunk(chunk_id)
                    continue

                if command == "a":
                    for chunk_id in predicted_ids + gold_ids:
                        open_chunk(chunk_id)
                    continue

                if command == "q":
                    save_rows(rows)
                    print_summary(rows)
                    print(f"Saved to: {OUTPUT_PATH}")
                    return

                if command == "" and row["manual_category"]:
                    print("Kept existing review.")
                    break

                if command != "r":
                    print("Unknown command.")
                    continue

                prediction_support = ask_choice(
                    "Does the prediction support a fully correct answer? "
                    "[y]es / [p]artial / [n]o / [u]nclear",
                    PREDICTION_SUPPORT,
                    row["prediction_support"],
                )

                gold_status = ask_choice(
                    "Is the original gold mapping acceptable? "
                    "[y]es / [n]o / [u]nclear",
                    GOLD_STATUS,
                    row["gold_mapping_status"],
                )

                print_categories()

                suggestion = suggested_category(
                    prediction_support,
                    gold_status,
                )

                if suggestion:
                    print(
                        "Suggested primary category: "
                        f"{suggestion} {CATEGORIES[suggestion]}"
                    )

                while True:
                    category_code = input(
                        "Primary category number"
                        + (
                            f" [suggested: {suggestion}]"
                            if suggestion
                            else ""
                        )
                        + ": "
                    ).strip()

                    if category_code == "" and suggestion:
                        category_code = suggestion

                    if category_code in CATEGORIES:
                        break

                    print("Unknown category. Enter ? before review to see all.")

                confidence = ask_choice(
                    "Review confidence [h]igh / [m]edium / [l]ow",
                    CONFIDENCE,
                    row["review_confidence"],
                )

                current_note = row["manual_note"]
                note_prompt = "Short note"
                if current_note:
                    note_prompt += f" [current: {current_note}]"

                note = input(note_prompt + ": ").strip()
                if note == "" and current_note:
                    note = current_note

                row["prediction_support"] = prediction_support
                row["gold_mapping_status"] = gold_status
                row["manual_category_code"] = category_code
                row["manual_category"] = CATEGORIES[category_code]
                row["review_confidence"] = confidence
                row["manual_note"] = note

                save_rows(rows)

                verify_saved(
                    row["question_id"],
                    {
                        "prediction_support": prediction_support,
                        "gold_mapping_status": gold_status,
                        "manual_category_code": category_code,
                        "manual_category": CATEGORIES[category_code],
                        "review_confidence": confidence,
                        "manual_note": note,
                    },
                )

                print(
                    "Saved and verified: "
                    f"{category_code} {CATEGORIES[category_code]}"
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
