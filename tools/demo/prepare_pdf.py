"""Prepare exact chunk-to-PDF positions (requires optional pdfplumber)."""

import hashlib
import json
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parents[2]


def normalized(text):
    return "".join(character for character in text.casefold() if character.isalnum())


def main():
    source = ROOT / "data/raw/PO_25_CL.pdf"
    chunks_path = ROOT / "data/frozen/PO_25_CL_chunks.jsonl"
    chunks = [json.loads(line) for line in chunks_path.read_text().splitlines()]
    pages = []
    with pdfplumber.open(source) as pdf:
        for page in pdf.pages:
            text, locations = "", []
            # Content-stream order keeps multi-line table cells together.
            for word in page.extract_words(x_tolerance=2, y_tolerance=3, use_text_flow=True):
                token = normalized(word["text"])
                text += token
                locations.extend([word] * len(token))
            pages.append((text, locations, page.height))

    entries = {}
    for chunk in chunks:
        # Chunk headings supply retrieval context; the body is verbatim PDF text.
        body = chunk["chunk_text"].partition("\n\n")[2] or chunk["chunk_text"]
        if chunk["content_type"] == "plan_status_note":
            body = body.partition("\n")[2]
        target = normalized(body)
        page_numbers = range(chunk["page_start"], chunk["page_end"] + 1)
        text = "".join(pages[number - 1][0] for number in page_numbers)
        locations = [
            (number, word) for number in page_numbers
            for word in pages[number - 1][1]
        ]
        start = text.find(target)
        if not target or start < 0:
            raise ValueError(f"No exact PDF match for {chunk['chunk_id']}")
        words = {
            (number, word["x0"], word["top"], word["x1"], word["bottom"])
            for number, word in locations[start:start + len(target)]
        }
        lines = {}
        for number, left, top, right, bottom in sorted(words):
            key = (number, round(top, 1), round(bottom, 1))
            if key in lines:
                lines[key][0] = min(lines[key][0], left)
                lines[key][2] = max(lines[key][2], right)
            else:
                height = pages[number - 1][2]
                lines[key] = [left, height - bottom, right, height - top]
        entries[chunk["chunk_id"]] = {
            "page": chunk["page_start"],
            "pages": {
                str(number): [
                    [round(value, 2) for value in rectangle]
                    for (page, top, bottom), rectangle in lines.items() if page == number
                ]
                for number in page_numbers
            },
        }
    positions = {
        "pdf_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "chunks_sha256": hashlib.sha256(chunks_path.read_bytes()).hexdigest(),
        "chunks": entries,
    }
    output = ROOT / "tools/demo/pdf_highlights.json"
    output.write_text(json.dumps(positions, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"Prepared exact PDF positions for {len(entries)} chunks: {output}")


if __name__ == "__main__":
    main()
