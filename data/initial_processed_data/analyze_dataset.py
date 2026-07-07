#!/usr/bin/env python3
"""Analyze a structured RAG dataset extracted from a module handbook.

The script expects these files in the input directory by default:
  - document_metadata.json
  - modules.json
  - tables.json
  - retrieval_chunks.jsonl
  - quality_control_report.json

It writes CSV diagnostics, plots, and a Markdown report to analysis_output/.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


REQUIRED_FILES = {
    "document_metadata": "document_metadata.json",
    "modules": "modules.json",
    "tables": "tables.json",
    "retrieval_chunks": "retrieval_chunks.jsonl",
    "quality_control_report": "quality_control_report.json",
}

TOKEN_BUCKETS = ["0-100", "101-300", "301-800", "801-1200", "1201+"]
IMPORTANT_SECTION_GROUPS = [
    "overview",
    "learning_outcomes",
    "content",
    "prerequisites",
    "exam",
    "workload",
    "literature",
    "tables",
    "course_components",
]


# ---------------------------------------------------------------------------
# Loading and safety helpers
# ---------------------------------------------------------------------------

def load_json(path: Path) -> Any:
    """Load a JSON file with a clear error message."""
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Required file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Load JSON Lines safely, skipping blank lines and reporting invalid lines."""
    records: List[Dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSONL in {path} at line {line_no}: {exc}") from exc
                if isinstance(obj, dict):
                    records.append(obj)
                else:
                    records.append({"_non_object_record": obj, "_line_no": line_no})
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Required file not found: {path}") from exc
    return records


def validate_required_files(input_dir: Path) -> Dict[str, Path]:
    """Return resolved required file paths after checking existence."""
    paths = {key: input_dir / filename for key, filename in REQUIRED_FILES.items()}
    missing = [str(path) for path in paths.values() if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing required files:\n" + "\n".join(missing))
    return paths


def normalize_record_list(data: Any, preferred_key: str) -> List[Dict[str, Any]]:
    """Normalize common JSON container shapes into a list of dictionaries."""
    if isinstance(data, list):
        return [x if isinstance(x, dict) else {"_non_object_record": x} for x in data]
    if isinstance(data, dict):
        value = data.get(preferred_key)
        if isinstance(value, list):
            return [x if isinstance(x, dict) else {"_non_object_record": x} for x in value]
        # Some exporters use singular names or records arrays.
        for key in ("records", "items", "data"):
            value = data.get(key)
            if isinstance(value, list):
                return [x if isinstance(x, dict) else {"_non_object_record": x} for x in value]
        # If the object itself is one record, return it as a single-item list.
        if data.get("record_type"):
            return [data]
    return []


def safe_get(obj: Any, path: Sequence[Any], default: Any = None) -> Any:
    """Safely get a nested value from dictionaries/lists.

    Example: safe_get(module, ["workload", "total_hours"])
    """
    cur = obj
    for key in path:
        if isinstance(cur, dict):
            if key not in cur:
                return default
            cur = cur[key]
        elif isinstance(cur, list) and isinstance(key, int):
            if key < 0 or key >= len(cur):
                return default
            cur = cur[key]
        else:
            return default
    return cur


def is_missing(value: Any) -> bool:
    """Return True if a value should count as missing for completeness checks."""
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False


def has_value(value: Any) -> bool:
    return not is_missing(value)


def to_list(value: Any) -> List[Any]:
    """Normalize a scalar/list/null to a list."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def clean_str(value: Any) -> Optional[str]:
    """Return a stripped string or None."""
    if value is None:
        return None
    if isinstance(value, str):
        s = value.strip()
        return s if s else None
    return str(value).strip() or None


def first_non_missing(*values: Any) -> Any:
    """Return the first non-missing value from a list of candidates."""
    for value in values:
        if has_value(value):
            return value
    return None


def parse_numeric(value: Any) -> Optional[float]:
    """Extract the first numeric value from a field if possible."""
    if value is None:
        return None
    if isinstance(value, (int, float)) and not (isinstance(value, float) and math.isnan(value)):
        return float(value)
    text = str(value).replace("\u00a0", " ")
    match = re.search(r"[-+]?\d+(?:[.,]\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", "."))
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def word_count(text: Any) -> int:
    """Approximate word count preserving German words and common abbreviations."""
    if not isinstance(text, str) or not text.strip():
        return 0
    # Includes German umlauts, ß, numbers, internal hyphens/slashes for codes.
    words = re.findall(r"[A-Za-zÄÖÜäöüß0-9]+(?:[-/][A-Za-zÄÖÜäöüß0-9]+)*", text)
    return len(words)


def approx_token_count(text_or_words: Any) -> int:
    """Estimate tokens as words * 1.3 unless an integer word count is provided."""
    if isinstance(text_or_words, (int, np.integer)):
        wc = int(text_or_words)
    else:
        wc = word_count(text_or_words)
    return int(math.ceil(wc * 1.3))


def sentence_count(text: Any) -> int:
    """Simple sentence count using punctuation boundaries."""
    if not isinstance(text, str) or not text.strip():
        return 0
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    parts = [p for p in parts if p.strip()]
    return len(parts) if parts else 1


def token_bucket(tokens: Any) -> str:
    """Map approximate token count to required bucket labels."""
    try:
        n = int(tokens)
    except Exception:
        n = 0
    if n <= 100:
        return "0-100"
    if n <= 300:
        return "101-300"
    if n <= 800:
        return "301-800"
    if n <= 1200:
        return "801-1200"
    return "1201+"


def collect_strings(obj: Any, exclude_keys: Optional[set] = None) -> List[str]:
    """Recursively collect strings from a nested object."""
    exclude_keys = exclude_keys or set()
    strings: List[str] = []
    if isinstance(obj, str):
        if obj.strip():
            strings.append(obj.strip())
    elif isinstance(obj, dict):
        for key, value in obj.items():
            if key in exclude_keys:
                continue
            strings.extend(collect_strings(value, exclude_keys=exclude_keys))
    elif isinstance(obj, list):
        for value in obj:
            strings.extend(collect_strings(value, exclude_keys=exclude_keys))
    return strings


def flatten_module_text(module: Dict[str, Any]) -> str:
    """Flatten all meaningful module strings into a single text for volume metrics."""
    exclude = {"source_file", "record_type", "extraction_confidence"}
    return "\n".join(collect_strings(module, exclude_keys=exclude))


def normalize_semester(value: Any) -> Optional[str]:
    """Make semester values printable while avoiding assumptions."""
    if is_missing(value):
        return None
    if isinstance(value, str):
        return value.strip()
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def infer_module_group(module_title: Optional[str], explicit_group: Any = None) -> Optional[str]:
    """Use explicit module_group if present; otherwise infer the prefix before an en dash."""
    if has_value(explicit_group):
        return str(explicit_group)
    if not module_title:
        return None
    # This is only a display fallback for analysis, not a replacement in source data.
    if "–" in module_title:
        return module_title.split("–", 1)[0].strip()
    if "-" in module_title:
        return module_title.split("-", 1)[0].strip()
    return None


def infer_section_group(section_type: Any, chunk_type: Any = None, text: Any = None) -> str:
    """Map heterogeneous section/chunk labels to a stable coverage group."""
    haystack = " ".join(str(x or "") for x in (section_type, chunk_type, text[:200] if isinstance(text, str) else "")).lower()
    rules = [
        ("learning_outcomes", ["learning", "lernergebnis", "studieninhalt", "outcome"]),
        ("prerequisites", ["prerequisite", "voraussetzung", "teilnahme"]),
        ("exam", ["exam", "prüfung", "pruefung", "pnr", "modulprüfung", "modulpruefung"]),
        ("workload", ["workload", "ects", "kontaktzeit", "selbststudium", "sws"]),
        ("literature", ["literature", "literatur"]),
        ("tables", ["table", "tabelle"]),
        ("course_components", ["course", "component", "lehrveranstaltung", "lehrform", "belegung"]),
        ("content", ["content", "inhalt"]),
        ("overview", ["overview", "überblick", "ueberblick", "identity", "modulidentität", "modulidentitaet"]),
    ]
    for group, needles in rules:
        if any(needle in haystack for needle in needles):
            return group
    return "other"


def extract_page_numbers(page_start: Any, page_end: Any, page_refs: Any) -> List[int]:
    """Extract page numbers from page_start/page_end and mixed page_refs values."""
    pages: List[int] = []

    def add_page(value: Any) -> None:
        if value is None:
            return
        if isinstance(value, bool):
            return
        if isinstance(value, (int, np.integer)):
            pages.append(int(value))
            return
        if isinstance(value, float) and not math.isnan(value):
            if value.is_integer():
                pages.append(int(value))
            return
        if isinstance(value, str):
            for match in re.finditer(r"\d+", value):
                pages.append(int(match.group(0)))

    add_page(page_start)
    add_page(page_end)

    if isinstance(page_refs, list):
        for ref in page_refs:
            if isinstance(ref, dict):
                for key in ("page", "page_number", "page_start", "page_end"):
                    add_page(ref.get(key))
            else:
                add_page(ref)
    elif isinstance(page_refs, dict):
        for key in ("page", "page_number", "page_start", "page_end"):
            add_page(page_refs.get(key))
    else:
        add_page(page_refs)

    return sorted(set(p for p in pages if p > 0))


def pages_overlap(a_start: Any, a_end: Any, b_start: Any, b_end: Any) -> Optional[bool]:
    """Return whether page ranges overlap, or None when data is missing."""
    a_s, a_e = parse_numeric(a_start), parse_numeric(a_end)
    b_s, b_e = parse_numeric(b_start), parse_numeric(b_end)
    if a_s is None or a_e is None or b_s is None or b_e is None:
        return None
    return max(a_s, b_s) <= min(a_e, b_e)


# ---------------------------------------------------------------------------
# Dataframe builders
# ---------------------------------------------------------------------------

def build_chunk_dataframe(
    chunks: List[Dict[str, Any]],
    module_ids: set,
    module_page_ranges: Dict[str, Tuple[Any, Any]],
    page_count: Optional[int],
) -> pd.DataFrame:
    """Build a retrieval chunk diagnostics dataframe."""
    rows: List[Dict[str, Any]] = []
    for i, chunk in enumerate(chunks):
        chunk_id = clean_str(chunk.get("chunk_id")) or f"__missing_chunk_id_{i}"
        parent_module_id = clean_str(chunk.get("parent_module_id"))
        text = chunk.get("text") if isinstance(chunk.get("text"), str) else ""
        keywords = to_list(chunk.get("keywords"))
        page_start = chunk.get("page_start")
        page_end = chunk.get("page_end")
        page_refs = chunk.get("page_refs")
        pages = extract_page_numbers(page_start, page_end, page_refs)
        wc = word_count(text)
        tokens = approx_token_count(wc)
        module_range = module_page_ranges.get(parent_module_id or "")
        overlap = None
        if module_range:
            overlap = pages_overlap(page_start, page_end, module_range[0], module_range[1])
        pages_outside_doc = False
        if page_count and pages:
            pages_outside_doc = any(p < 1 or p > page_count for p in pages)
        section_type = clean_str(chunk.get("section_type")) or ""
        chunk_type = clean_str(chunk.get("chunk_type")) or ""
        section_group = infer_section_group(section_type, chunk_type, text)
        module_title = clean_str(chunk.get("module_title"))
        module_code = clean_str(chunk.get("module_code"))
        has_standalone_context = bool(
            module_title
            and pages
            and (module_code or parent_module_id)
            and wc >= 20
        )
        rows.append(
            {
                "chunk_id": chunk_id,
                "record_type": chunk.get("record_type"),
                "parent_module_id": parent_module_id,
                "source_file": chunk.get("source_file"),
                "page_start": page_start,
                "page_end": page_end,
                "page_refs_count": len(to_list(page_refs)),
                "extracted_page_numbers": ",".join(map(str, pages)),
                "program": chunk.get("program"),
                "degree_level": chunk.get("degree_level"),
                "module_code": module_code,
                "module_title": module_title,
                "module_group": chunk.get("module_group"),
                "recommended_semester": normalize_semester(chunk.get("recommended_semester")),
                "ects": parse_numeric(chunk.get("ects")),
                "language": chunk.get("language"),
                "section_type": section_type,
                "chunk_type": chunk_type,
                "section_group": section_group,
                "retrieval_priority": clean_str(chunk.get("retrieval_priority")) or "normal",
                "text": text,
                "text_char_count": len(text),
                "text_word_count": wc,
                "approx_token_count": tokens,
                "sentence_count": sentence_count(text),
                "keyword_count": len([k for k in keywords if has_value(k)]),
                "keywords_joined": "; ".join(str(k) for k in keywords if has_value(k)),
                "has_text": wc > 0,
                "is_near_empty": wc < 5,
                "has_page_refs": bool(pages),
                "has_parent_module_id": bool(parent_module_id),
                "has_module_title": bool(module_title),
                "has_keywords": len([k for k in keywords if has_value(k)]) > 0,
                "has_standalone_context": has_standalone_context,
                "is_too_short": wc < 20,
                "is_very_long": tokens > 1200,
                "token_bucket": token_bucket(tokens),
                "invalid_parent_module_id": bool(parent_module_id and parent_module_id not in module_ids),
                "pages_outside_document": pages_outside_doc,
                "chunk_pages_overlap_module_pages": overlap,
                "extraction_notes": "; ".join(str(x) for x in to_list(chunk.get("extraction_notes")) if has_value(x)),
            }
        )
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(
            columns=[
                "chunk_id", "parent_module_id", "module_code", "module_title", "section_type",
                "chunk_type", "section_group", "retrieval_priority", "text_word_count",
                "approx_token_count", "token_bucket", "has_page_refs", "invalid_parent_module_id",
            ]
        )
    df["duplicate_chunk_id"] = df["chunk_id"].duplicated(keep=False)
    return df


def module_has_exam(exam: Any) -> bool:
    """Return True if exam information is present, including explicit '-keine-' values."""
    if isinstance(exam, dict):
        return any(has_value(v) for v in exam.values())
    return has_value(exam)


def module_has_prerequisites(prereq: Any) -> bool:
    """Return True if prerequisite information is present, including explicit '-keine-' values."""
    if isinstance(prereq, dict):
        return any(has_value(v) for v in prereq.values())
    return has_value(prereq)


def build_module_dataframe(
    modules: List[Dict[str, Any]],
    chunks_df: pd.DataFrame,
    tables_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Build a module diagnostics dataframe."""
    chunk_counts = Counter()
    if chunks_df is not None and not chunks_df.empty and "parent_module_id" in chunks_df:
        chunk_counts = Counter(chunks_df["parent_module_id"].dropna().astype(str))
    table_counts = Counter()
    if tables_df is not None and not tables_df.empty and "parent_module_id" in tables_df:
        table_counts = Counter(tables_df["parent_module_id"].dropna().astype(str))

    rows: List[Dict[str, Any]] = []
    for i, module in enumerate(modules):
        module_id = clean_str(module.get("module_id")) or f"__missing_module_id_{i}"
        module_title = clean_str(module.get("module_title")) or ""
        source_pages = module.get("source_pages") if isinstance(module.get("source_pages"), dict) else {}
        page_start = safe_get(module, ["source_pages", "page_start"])
        page_end = safe_get(module, ["source_pages", "page_end"])
        page_refs = safe_get(module, ["source_pages", "page_refs"])
        pages = extract_page_numbers(page_start, page_end, page_refs)
        flat_text = flatten_module_text(module)
        learning_items = to_list(safe_get(module, ["learning_outcomes", "items"], []))
        content_items = to_list(safe_get(module, ["content", "items"], []))
        literature_items = to_list(safe_get(module, ["literature", "items"], []))
        responsible_persons = to_list(module.get("responsible_persons"))
        lecturers = to_list(module.get("lecturers"))
        components = to_list(module.get("courses_or_components"))
        notes = to_list(module.get("notes"))
        cross_refs = to_list(module.get("cross_references"))
        exam = module.get("exam")
        prereq = module.get("prerequisites")
        ects = parse_numeric(module.get("ects"))
        rows.append(
            {
                "module_id": module_id,
                "record_type": module.get("record_type"),
                "source_file": module.get("source_file"),
                "module_code": clean_str(module.get("module_code")),
                "module_title": module_title,
                "module_title_normalized": clean_str(module.get("module_title_normalized")),
                "program": module.get("program"),
                "degree_level": module.get("degree_level"),
                "module_group": infer_module_group(module_title, module.get("module_group")),
                "module_group_source_value": module.get("module_group"),
                "recommended_semester": normalize_semester(module.get("recommended_semester")),
                "ects": ects,
                "workload_total_hours": parse_numeric(safe_get(module, ["workload", "total_hours"])),
                "workload_contact_hours": parse_numeric(safe_get(module, ["workload", "contact_hours"])),
                "workload_self_study_hours": parse_numeric(safe_get(module, ["workload", "self_study_hours"])),
                "workload_details": safe_get(module, ["workload", "details"]),
                "duration": module.get("duration"),
                "frequency": module.get("frequency"),
                "language": module.get("language"),
                "responsible_person_count": len([x for x in responsible_persons if has_value(x)]),
                "lecturer_count": len([x for x in lecturers if has_value(x)]),
                "prerequisites_required": safe_get(module, ["prerequisites", "required"]),
                "prerequisites_recommended": safe_get(module, ["prerequisites", "recommended"]),
                "prerequisites_text": safe_get(module, ["prerequisites", "text"]),
                "learning_outcomes_word_count": word_count(safe_get(module, ["learning_outcomes", "raw_text"], "")),
                "learning_outcome_item_count": len([x for x in learning_items if has_value(x)]),
                "content_word_count": word_count(safe_get(module, ["content", "raw_text"], "")),
                "content_item_count": len([x for x in content_items if has_value(x)]),
                "exam_type": safe_get(module, ["exam", "exam_type"]),
                "exam_duration": safe_get(module, ["exam", "exam_duration"]),
                "exam_duration_numeric": parse_numeric(safe_get(module, ["exam", "exam_duration"])),
                "exam_graded": safe_get(module, ["exam", "graded"]),
                "exam_weighting": safe_get(module, ["exam", "weighting"]),
                "exam_details": safe_get(module, ["exam", "details"]),
                "exam_description_word_count": word_count("\n".join(collect_strings(exam))),
                "teaching_methods": module.get("teaching_methods"),
                "course_component_count": len([x for x in components if has_value(x)]),
                "literature_word_count": word_count(safe_get(module, ["literature", "raw_text"], "")),
                "literature_item_count": len([x for x in literature_items if has_value(x)]),
                "note_count": len([x for x in notes if has_value(x)]),
                "cross_reference_count": len([x for x in cross_refs if has_value(x)]),
                "source_page_start": page_start,
                "source_page_end": page_end,
                "source_page_refs_count": len(to_list(page_refs)),
                "extracted_page_numbers": ",".join(map(str, pages)),
                "module_total_text_chars": len(flat_text),
                "module_total_text_words": word_count(flat_text),
                "chunk_count": int(chunk_counts.get(module_id, 0)),
                "table_count": int(table_counts.get(module_id, 0)),
                "has_ects": ects is not None,
                "has_exam": module_has_exam(exam),
                "has_prerequisites": module_has_prerequisites(prereq),
                "has_recommended_semester": has_value(module.get("recommended_semester")),
                "has_language": has_value(module.get("language")),
                "has_source_pages": bool(pages),
                "extraction_confidence": clean_str(module.get("extraction_confidence")) or "unknown",
                "extraction_notes": "; ".join(str(x) for x in to_list(module.get("extraction_notes")) if has_value(x)),
            }
        )
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["module_id", "module_title", "chunk_count", "module_total_text_words"])
    df["duplicate_module_id"] = df["module_id"].duplicated(keep=False)
    df["duplicate_module_title"] = df["module_title"].duplicated(keep=False) & df["module_title"].notna()

    if len(df) >= 4 and df["module_total_text_words"].notna().any():
        q05 = df["module_total_text_words"].quantile(0.05)
        q95 = df["module_total_text_words"].quantile(0.95)
        df["unusually_small_text_volume"] = df["module_total_text_words"] <= q05
        df["unusually_large_text_volume"] = df["module_total_text_words"] >= q95
    else:
        df["unusually_small_text_volume"] = False
        df["unusually_large_text_text_volume"] = False
    return df


def build_table_dataframe(tables: List[Dict[str, Any]], module_ids: set) -> pd.DataFrame:
    """Build a table diagnostics dataframe."""
    rows: List[Dict[str, Any]] = []
    for i, table in enumerate(tables):
        table_id = clean_str(table.get("table_id")) or f"__missing_table_id_{i}"
        parent_module_id = clean_str(table.get("parent_module_id"))
        rows_list = to_list(table.get("rows"))
        cols_list = to_list(table.get("columns"))
        page_start = table.get("page_start")
        page_end = table.get("page_end")
        pages = extract_page_numbers(page_start, page_end, [])
        start_num = parse_numeric(page_start)
        end_num = parse_numeric(page_end)
        rows.append(
            {
                "table_id": table_id,
                "record_type": table.get("record_type"),
                "parent_module_id": parent_module_id,
                "source_file": table.get("source_file"),
                "page_start": page_start,
                "page_end": page_end,
                "extracted_page_numbers": ",".join(map(str, pages)),
                "caption": table.get("caption"),
                "context": table.get("context"),
                "row_count": len(rows_list),
                "column_count": len(cols_list),
                "has_caption": has_value(table.get("caption")),
                "has_context": has_value(table.get("context")),
                "has_rows": len(rows_list) > 0,
                "has_columns": len(cols_list) > 0,
                "spans_multiple_pages": bool(start_num is not None and end_num is not None and end_num > start_num),
                "extraction_confidence": clean_str(table.get("extraction_confidence")) or "unknown",
                "low_or_medium_confidence": str(table.get("extraction_confidence", "")).lower() in {"low", "medium"},
                "invalid_parent_module_id": bool(parent_module_id and parent_module_id not in module_ids),
                "extraction_notes": "; ".join(str(x) for x in to_list(table.get("extraction_notes")) if has_value(x)),
            }
        )
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(
            columns=[
                "table_id", "parent_module_id", "row_count", "column_count",
                "has_rows", "has_columns", "extraction_confidence",
            ]
        )
    df["duplicate_table_id"] = df["table_id"].duplicated(keep=False)
    return df


# ---------------------------------------------------------------------------
# Statistics and diagnostics
# ---------------------------------------------------------------------------

def describe_numeric(series: pd.Series, label: str) -> Dict[str, Any]:
    """Return common descriptive statistics for one numeric series."""
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return {
            "metric": label,
            "count": 0,
            "mean": np.nan,
            "median": np.nan,
            "min": np.nan,
            "max": np.nan,
            "std": np.nan,
            "p05": np.nan,
            "p10": np.nan,
            "p25": np.nan,
            "p75": np.nan,
            "p90": np.nan,
            "p95": np.nan,
        }
    return {
        "metric": label,
        "count": int(values.count()),
        "mean": float(values.mean()),
        "median": float(values.median()),
        "min": float(values.min()),
        "max": float(values.max()),
        "std": float(values.std(ddof=1)) if len(values) > 1 else 0.0,
        "p05": float(values.quantile(0.05)),
        "p10": float(values.quantile(0.10)),
        "p25": float(values.quantile(0.25)),
        "p75": float(values.quantile(0.75)),
        "p90": float(values.quantile(0.90)),
        "p95": float(values.quantile(0.95)),
    }


def calculate_chunk_length_statistics(chunks_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate length statistics for retrieval chunks."""
    rows = []
    for col, label in [
        ("text_char_count", "chunk_characters"),
        ("text_word_count", "chunk_words"),
        ("approx_token_count", "chunk_approx_tokens"),
        ("sentence_count", "chunk_sentences"),
    ]:
        if col in chunks_df:
            rows.append(describe_numeric(chunks_df[col], label))
    return pd.DataFrame(rows)


def count_missing(df: pd.DataFrame, column: str) -> int:
    """Count missing values in a dataframe column."""
    if column not in df:
        return 0
    return int(df[column].apply(is_missing).sum())


def calculate_metadata_completeness(
    modules_df: pd.DataFrame,
    chunks_df: pd.DataFrame,
    tables_df: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate metadata missingness for key module, chunk, and table fields."""
    checks: List[Tuple[str, str, str]] = [
        ("module", "module_code", "module_code"),
        ("module", "module_title", "module_title"),
        ("module", "program", "program"),
        ("module", "degree_level", "degree_level"),
        ("module", "module_group", "module_group"),
        ("module", "recommended_semester", "recommended_semester"),
        ("module", "ects", "ects"),
        ("module", "duration", "duration"),
        ("module", "frequency", "frequency"),
        ("module", "language", "language"),
        ("module", "responsible_person_count", "responsible_persons"),
        ("module", "lecturer_count", "lecturers"),
        ("module", "has_exam", "exam"),
        ("module", "has_prerequisites", "prerequisites"),
        ("module", "has_source_pages", "source_pages"),
        ("chunk", "chunk_id", "chunk_id"),
        ("chunk", "parent_module_id", "parent_module_id"),
        ("chunk", "module_title", "module_title"),
        ("chunk", "module_code", "module_code"),
        ("chunk", "section_type", "section_type"),
        ("chunk", "chunk_type", "chunk_type"),
        ("chunk", "retrieval_priority", "retrieval_priority"),
        ("chunk", "has_page_refs", "page_refs"),
        ("chunk", "has_text", "text"),
        ("table", "table_id", "table_id"),
        ("table", "parent_module_id", "parent_module_id"),
        ("table", "has_caption", "caption"),
        ("table", "has_context", "context"),
        ("table", "has_rows", "rows"),
        ("table", "has_columns", "columns"),
    ]
    df_map = {"module": modules_df, "chunk": chunks_df, "table": tables_df}
    rows: List[Dict[str, Any]] = []
    for entity, col, field in checks:
        df = df_map[entity]
        total = len(df)
        if total == 0:
            missing = 0
        elif col in {"has_exam", "has_prerequisites", "has_source_pages", "has_page_refs", "has_text", "has_caption", "has_context", "has_rows", "has_columns"}:
            missing = int((~df[col].fillna(False).astype(bool)).sum()) if col in df else total
        elif col in {"responsible_person_count", "lecturer_count"}:
            missing = int((pd.to_numeric(df[col], errors="coerce").fillna(0) == 0).sum()) if col in df else total
        else:
            missing = count_missing(df, col) if col in df else total
        rows.append(
            {
                "entity_type": entity,
                "field": field,
                "total_records": total,
                "missing_count": int(missing),
                "present_count": int(max(total - missing, 0)),
                "missing_percent": float((missing / total) * 100) if total else 0.0,
                "present_percent": float(((total - missing) / total) * 100) if total else 0.0,
            }
        )
    return pd.DataFrame(rows)


def calculate_summary_statistics(
    metadata: Dict[str, Any],
    qc_report: Dict[str, Any],
    modules_df: pd.DataFrame,
    chunks_df: pd.DataFrame,
    tables_df: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate an overview table with dataset size and coverage metrics."""
    pages_processed = safe_get(qc_report, ["coverage", "pages_processed"], [])
    uncertain_pages = safe_get(qc_report, ["coverage", "pages_with_uncertain_extraction"], [])
    page_count = first_non_missing(metadata.get("page_count"), len(pages_processed) if pages_processed else None)
    rows = [
        ("document_title", metadata.get("document_title")),
        ("institution", metadata.get("institution")),
        ("faculty", metadata.get("faculty")),
        ("language", metadata.get("language")),
        ("document_date", metadata.get("document_date")),
        ("version", metadata.get("version")),
        ("page_count_metadata", metadata.get("page_count")),
        ("page_count_effective", page_count),
        ("pages_processed_count", len(to_list(pages_processed))),
        ("pages_with_uncertain_extraction_count", len(to_list(uncertain_pages))),
        ("module_count", len(modules_df)),
        ("chunk_count", len(chunks_df)),
        ("table_count", len(tables_df)),
        ("program_count", modules_df["program"].nunique(dropna=True) if "program" in modules_df else 0),
        ("degree_level_count", modules_df["degree_level"].nunique(dropna=True) if "degree_level" in modules_df else 0),
        ("module_group_count", modules_df["module_group"].nunique(dropna=True) if "module_group" in modules_df else 0),
        ("recommended_semester_count", modules_df["recommended_semester"].nunique(dropna=True) if "recommended_semester" in modules_df else 0),
        ("section_type_count", chunks_df["section_type"].nunique(dropna=True) if "section_type" in chunks_df else 0),
        ("chunk_type_count", chunks_df["chunk_type"].nunique(dropna=True) if "chunk_type" in chunks_df else 0),
        ("high_priority_chunk_count", int((chunks_df.get("retrieval_priority", pd.Series(dtype=str)).astype(str).str.lower() == "high").sum()) if not chunks_df.empty else 0),
        ("normal_priority_chunk_count", int((chunks_df.get("retrieval_priority", pd.Series(dtype=str)).astype(str).str.lower() == "normal").sum()) if not chunks_df.empty else 0),
        ("low_priority_chunk_count", int((chunks_df.get("retrieval_priority", pd.Series(dtype=str)).astype(str).str.lower() == "low").sum()) if not chunks_df.empty else 0),
        ("modules_without_chunks", int((modules_df.get("chunk_count", pd.Series(dtype=int)) == 0).sum()) if not modules_df.empty else 0),
        ("tables_without_rows", int((~tables_df.get("has_rows", pd.Series(dtype=bool)).fillna(False).astype(bool)).sum()) if not tables_df.empty else 0),
        ("tables_without_columns", int((~tables_df.get("has_columns", pd.Series(dtype=bool)).fillna(False).astype(bool)).sum()) if not tables_df.empty else 0),
    ]
    return pd.DataFrame(rows, columns=["metric", "value"])


def calculate_rag_readiness(
    modules_df: pd.DataFrame,
    chunks_df: pd.DataFrame,
    tables_df: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate a compact RAG-readiness summary."""
    total_chunks = len(chunks_df)

    def pct(mask: Any) -> float:
        if total_chunks == 0:
            return 0.0
        return float((pd.Series(mask).fillna(False).astype(bool).sum() / total_chunks) * 100)

    avg_words = float(chunks_df["text_word_count"].mean()) if total_chunks and "text_word_count" in chunks_df else 0.0
    med_words = float(chunks_df["text_word_count"].median()) if total_chunks and "text_word_count" in chunks_df else 0.0
    avg_tokens = float(chunks_df["approx_token_count"].mean()) if total_chunks and "approx_token_count" in chunks_df else 0.0

    section_group_counts = chunks_df["section_group"].value_counts() if total_chunks and "section_group" in chunks_df else pd.Series(dtype=int)
    rows = [
        ("total_chunks", total_chunks),
        ("average_chunk_words", avg_words),
        ("median_chunk_words", med_words),
        ("average_approx_tokens", avg_tokens),
        ("percent_chunks_under_100_tokens", pct(chunks_df["approx_token_count"] <= 100) if total_chunks else 0.0),
        ("percent_chunks_100_to_800_tokens", pct((chunks_df["approx_token_count"] >= 100) & (chunks_df["approx_token_count"] <= 800)) if total_chunks else 0.0),
        ("percent_chunks_over_1200_tokens", pct(chunks_df["approx_token_count"] > 1200) if total_chunks else 0.0),
        ("percent_chunks_with_page_references", pct(chunks_df["has_page_refs"]) if total_chunks else 0.0),
        ("percent_chunks_with_parent_module_ids", pct(chunks_df["has_parent_module_id"]) if total_chunks else 0.0),
        ("percent_chunks_with_keywords", pct(chunks_df["has_keywords"]) if total_chunks else 0.0),
        ("percent_chunks_with_standalone_context", pct(chunks_df["has_standalone_context"]) if total_chunks else 0.0),
        ("overview_chunk_count", int(section_group_counts.get("overview", 0))),
        ("prerequisite_chunk_count", int(section_group_counts.get("prerequisites", 0))),
        ("exam_chunk_count", int(section_group_counts.get("exam", 0))),
        ("learning_outcome_chunk_count", int(section_group_counts.get("learning_outcomes", 0))),
        ("content_chunk_count", int(section_group_counts.get("content", 0))),
        ("modules_without_chunks", int((modules_df["chunk_count"] == 0).sum()) if "chunk_count" in modules_df else 0),
        ("chunks_with_invalid_parent_module_ids", int(chunks_df["invalid_parent_module_id"].sum()) if "invalid_parent_module_id" in chunks_df else 0),
        ("modules_missing_ects", int((~modules_df["has_ects"].fillna(False).astype(bool)).sum()) if "has_ects" in modules_df else 0),
        ("modules_missing_exam_information", int((~modules_df["has_exam"].fillna(False).astype(bool)).sum()) if "has_exam" in modules_df else 0),
        ("modules_missing_prerequisites", int((~modules_df["has_prerequisites"].fillna(False).astype(bool)).sum()) if "has_prerequisites" in modules_df else 0),
        ("tables_with_low_or_medium_confidence", int(tables_df["low_or_medium_confidence"].sum()) if "low_or_medium_confidence" in tables_df else 0),
    ]
    return pd.DataFrame(rows, columns=["metric", "value"])


def calculate_distributions(
    modules_df: pd.DataFrame,
    chunks_df: pd.DataFrame,
    tables_df: pd.DataFrame,
) -> Dict[str, pd.DataFrame]:
    """Calculate frequency distributions as dataframes."""
    out: Dict[str, pd.DataFrame] = {}

    def value_counts_df(df: pd.DataFrame, column: str, name: str) -> pd.DataFrame:
        if df.empty or column not in df:
            return pd.DataFrame(columns=[column, "count"])
        vc = df[column].fillna("(missing)").replace("", "(missing)").value_counts(dropna=False)
        return vc.rename_axis(column).reset_index(name="count")

    out["modules_per_program"] = value_counts_df(modules_df, "program", "modules_per_program")
    out["modules_per_module_group"] = value_counts_df(modules_df, "module_group", "modules_per_module_group")
    out["modules_per_semester"] = value_counts_df(modules_df, "recommended_semester", "modules_per_semester")
    out["section_type_distribution"] = value_counts_df(chunks_df, "section_type", "section_type_distribution")
    out["chunk_type_distribution"] = value_counts_df(chunks_df, "chunk_type", "chunk_type_distribution")
    out["retrieval_priority_distribution"] = value_counts_df(chunks_df, "retrieval_priority", "retrieval_priority_distribution")
    out["token_bucket_distribution"] = value_counts_df(chunks_df, "token_bucket", "token_bucket_distribution")
    out["ects_distribution"] = value_counts_df(modules_df, "ects", "ects_distribution")
    out["table_confidence_distribution"] = value_counts_df(tables_df, "extraction_confidence", "table_confidence_distribution")
    return out


def calculate_module_section_coverage(modules_df: pd.DataFrame, chunks_df: pd.DataFrame) -> pd.DataFrame:
    """Build a module-by-important-section coverage matrix using chunk groups."""
    base_cols = ["module_id", "module_code", "module_title", "chunk_count"]
    if modules_df.empty:
        return pd.DataFrame(columns=base_cols + IMPORTANT_SECTION_GROUPS)
    base = modules_df[[c for c in base_cols if c in modules_df.columns]].copy()
    for group in IMPORTANT_SECTION_GROUPS:
        base[group] = 0
    if chunks_df.empty or "parent_module_id" not in chunks_df or "section_group" not in chunks_df:
        return base
    counts = chunks_df.groupby(["parent_module_id", "section_group"]).size().reset_index(name="count")
    for _, row in counts.iterrows():
        module_id = row["parent_module_id"]
        group = row["section_group"]
        if group in IMPORTANT_SECTION_GROUPS:
            base.loc[base["module_id"] == module_id, group] = int(row["count"])
    return base


def calculate_top_keywords(chunks_df: pd.DataFrame, top_n: int = 50) -> pd.DataFrame:
    """Calculate top keywords from retrieval chunks."""
    counter: Counter = Counter()
    if chunks_df.empty or "keywords_joined" not in chunks_df:
        return pd.DataFrame(columns=["keyword", "count"])
    for value in chunks_df["keywords_joined"].dropna():
        for kw in str(value).split(";"):
            kw = kw.strip()
            if kw:
                counter[kw] += 1
    return pd.DataFrame(counter.most_common(top_n), columns=["keyword", "count"])


def detect_issues(
    metadata: Dict[str, Any],
    qc_report: Dict[str, Any],
    modules_df: pd.DataFrame,
    chunks_df: pd.DataFrame,
    tables_df: pd.DataFrame,
) -> List[str]:
    """Detect suspicious cases for the Markdown report."""
    issues: List[str] = []
    page_count = parse_numeric(metadata.get("page_count"))
    pages_processed = to_list(safe_get(qc_report, ["coverage", "pages_processed"], []))
    if page_count and pages_processed and len(set(pages_processed)) < int(page_count):
        issues.append(f"Only {len(set(pages_processed))} processed pages are listed, but page_count is {int(page_count)}.")
    if safe_get(qc_report, ["coverage", "pages_with_uncertain_extraction"], []):
        issues.append("Quality-control report lists pages with uncertain extraction.")
    if not modules_df.empty:
        if "duplicate_module_id" in modules_df and modules_df["duplicate_module_id"].any():
            issues.append("Duplicate module IDs detected.")
        if "duplicate_module_title" in modules_df and modules_df["duplicate_module_title"].any():
            issues.append("Duplicate module titles detected.")
        missing_ects = modules_df.loc[~modules_df.get("has_ects", pd.Series(False, index=modules_df.index)).fillna(False).astype(bool), "module_id"].tolist()
        if missing_ects:
            issues.append(f"Modules missing ECTS: {', '.join(map(str, missing_ects))}.")
        no_chunks = modules_df.loc[modules_df.get("chunk_count", pd.Series(0, index=modules_df.index)) == 0, "module_id"].tolist()
        if no_chunks:
            issues.append(f"Modules without retrieval chunks: {', '.join(map(str, no_chunks))}.")
        missing_language = modules_df.loc[~modules_df.get("has_language", pd.Series(False, index=modules_df.index)).fillna(False).astype(bool), "module_id"].tolist()
        if missing_language:
            issues.append(f"Modules missing language metadata: {', '.join(map(str, missing_language))}.")
        missing_resp = modules_df.loc[modules_df.get("responsible_person_count", pd.Series(0, index=modules_df.index)) == 0, "module_id"].tolist()
        if missing_resp:
            issues.append(f"Modules with no responsible persons listed: {len(missing_resp)}.")
    if not chunks_df.empty:
        if "duplicate_chunk_id" in chunks_df and chunks_df["duplicate_chunk_id"].any():
            issues.append("Duplicate chunk IDs detected.")
        invalid_parent_count = int(chunks_df.get("invalid_parent_module_id", pd.Series(False)).fillna(False).astype(bool).sum())
        if invalid_parent_count:
            issues.append(f"Chunks with invalid parent_module_id: {invalid_parent_count}.")
        no_page_count = int((~chunks_df.get("has_page_refs", pd.Series(False)).fillna(False).astype(bool)).sum())
        if no_page_count:
            issues.append(f"Chunks missing page references: {no_page_count}.")
        too_short_count = int(chunks_df.get("is_too_short", pd.Series(False)).fillna(False).astype(bool).sum())
        if too_short_count:
            issues.append(f"Very short chunks detected (<20 words): {too_short_count}.")
        very_long_count = int(chunks_df.get("is_very_long", pd.Series(False)).fillna(False).astype(bool).sum())
        if very_long_count:
            issues.append(f"Very long chunks detected (>1200 approx. tokens): {very_long_count}.")
        section_counts = chunks_df.get("section_type", pd.Series(dtype=str)).fillna("(missing)").value_counts()
        rare_sections = section_counts[section_counts == 1].index.tolist()
        if rare_sections:
            issues.append("Section types appearing only once: " + ", ".join(map(str, rare_sections[:20])) + ("." if len(rare_sections) <= 20 else ", ..."))
        overlap_col = chunks_df.get("chunk_pages_overlap_module_pages")
        if overlap_col is not None:
            bad_overlap = int((overlap_col == False).sum())  # noqa: E712 - intentional comparison with False
            if bad_overlap:
                issues.append(f"Chunks whose page range does not overlap their module page range: {bad_overlap}.")
    if not tables_df.empty:
        if "duplicate_table_id" in tables_df and tables_df["duplicate_table_id"].any():
            issues.append("Duplicate table IDs detected.")
        no_rows = int((~tables_df.get("has_rows", pd.Series(False)).fillna(False).astype(bool)).sum())
        if no_rows:
            issues.append(f"Tables without rows: {no_rows}.")
        no_cols = int((~tables_df.get("has_columns", pd.Series(False)).fillna(False).astype(bool)).sum())
        if no_cols:
            issues.append(f"Tables without columns: {no_cols}.")
        low_conf = int(tables_df.get("low_or_medium_confidence", pd.Series(False)).fillna(False).astype(bool).sum())
        if low_conf:
            issues.append(f"Tables with low or medium extraction confidence: {low_conf}.")
        invalid_table_parents = int(tables_df.get("invalid_parent_module_id", pd.Series(False)).fillna(False).astype(bool).sum())
        if invalid_table_parents:
            issues.append(f"Tables with invalid parent_module_id: {invalid_table_parents}.")
    if not issues:
        issues.append("No major structural issues detected by automated checks.")
    return issues


# ---------------------------------------------------------------------------
# Plotting helpers
# ---------------------------------------------------------------------------

def save_current_plot(path: Path) -> None:
    """Save and close the current matplotlib plot."""
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def bar_plot_from_counts(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    xlabel: str,
    ylabel: str,
    output_path: Path,
    rotate: int = 45,
    max_labels: Optional[int] = None,
) -> Optional[str]:
    """Create a bar chart from a dataframe with x/y columns."""
    if df.empty or x_col not in df or y_col not in df:
        return f"Skipped {output_path.name}: missing data."
    plot_df = df.copy()
    if max_labels:
        plot_df = plot_df.head(max_labels)
    plt.figure(figsize=(10, 5))
    plt.bar(plot_df[x_col].astype(str), plot_df[y_col])
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.xticks(rotation=rotate, ha="right" if rotate else "center")
    save_current_plot(output_path)
    return None


def create_visualizations(
    output_dir: Path,
    modules_df: pd.DataFrame,
    chunks_df: pd.DataFrame,
    tables_df: pd.DataFrame,
    metadata_completeness_df: pd.DataFrame,
    distributions: Dict[str, pd.DataFrame],
) -> Tuple[List[Path], List[str]]:
    """Generate required plots when supported by the data."""
    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    generated: List[Path] = []
    warnings: List[str] = []

    def warn_or_add(path: Path, warning: Optional[str]) -> None:
        if warning:
            warnings.append(warning)
        elif path.exists():
            generated.append(path)

    # Histograms.
    if not chunks_df.empty and "text_word_count" in chunks_df and chunks_df["text_word_count"].notna().any():
        path = plots_dir / "chunk_word_length_histogram.png"
        plt.figure(figsize=(9, 5))
        plt.hist(chunks_df["text_word_count"].dropna(), bins=20)
        plt.title("Retrieval chunk word length distribution")
        plt.xlabel("Words per chunk")
        plt.ylabel("Number of chunks")
        save_current_plot(path)
        generated.append(path)
    else:
        warnings.append("Skipped chunk_word_length_histogram.png: no chunk word counts available.")

    if not chunks_df.empty and "approx_token_count" in chunks_df and chunks_df["approx_token_count"].notna().any():
        path = plots_dir / "chunk_token_length_histogram.png"
        plt.figure(figsize=(9, 5))
        plt.hist(chunks_df["approx_token_count"].dropna(), bins=20)
        plt.title("Retrieval chunk approximate token length distribution")
        plt.xlabel("Approximate tokens per chunk")
        plt.ylabel("Number of chunks")
        save_current_plot(path)
        generated.append(path)
    else:
        warnings.append("Skipped chunk_token_length_histogram.png: no chunk token counts available.")

    # Boxplot by section type.
    if not chunks_df.empty and {"section_type", "text_word_count"}.issubset(chunks_df.columns):
        grouped = []
        labels = []
        for label, group in chunks_df.groupby("section_type"):
            values = group["text_word_count"].dropna().tolist()
            if values:
                labels.append(str(label) if str(label) else "(missing)")
                grouped.append(values)
        if grouped:
            path = plots_dir / "chunk_length_by_section_type_boxplot.png"
            plt.figure(figsize=(max(10, min(18, len(labels) * 0.8)), 6))
            plt.boxplot(grouped, label=labels, vert=True) #changed labels to label
            plt.title("Chunk word lengths by section type")
            plt.xlabel("Section type")
            plt.ylabel("Words per chunk")
            plt.xticks(rotation=45, ha="right")
            save_current_plot(path)
            generated.append(path)
        else:
            warnings.append("Skipped chunk_length_by_section_type_boxplot.png: no grouped chunk lengths available.")
    else:
        warnings.append("Skipped chunk_length_by_section_type_boxplot.png: section_type or length data missing.")

    # Bar charts from distributions.
    plot_specs = [
        ("section_type_distribution", "section_type", "count", "chunks_per_section_type.png", "Chunks per section type", "Section type", "Chunks"),
        ("retrieval_priority_distribution", "retrieval_priority", "count", "retrieval_priority_distribution.png", "Retrieval priority distribution", "Retrieval priority", "Chunks"),
        ("modules_per_semester", "recommended_semester", "count", "modules_per_semester.png", "Modules per recommended semester", "Recommended semester", "Modules"),
        ("ects_distribution", "ects", "count", "ects_distribution.png", "ECTS distribution", "ECTS", "Modules"),
        ("modules_per_module_group", "module_group", "count", "modules_per_module_group.png", "Modules per module group", "Module group", "Modules"),
    ]
    for dist_key, x_col, y_col, filename, title, xlabel, ylabel in plot_specs:
        path = plots_dir / filename
        warning = bar_plot_from_counts(distributions.get(dist_key, pd.DataFrame()), x_col, y_col, title, xlabel, ylabel, path)
        warn_or_add(path, warning)

    # Chunks per module.
    if not modules_df.empty and {"module_id", "chunk_count"}.issubset(modules_df.columns):
        plot_df = modules_df.sort_values("chunk_count", ascending=False).copy()
        label_col = "module_code" if "module_code" in plot_df and plot_df["module_code"].notna().any() else "module_id"
        path = plots_dir / "chunks_per_module.png"
        plt.figure(figsize=(11, 5))
        plt.bar(plot_df[label_col].fillna(plot_df["module_id"]).astype(str), plot_df["chunk_count"])
        plt.title("Chunks per module")
        plt.xlabel("Module")
        plt.ylabel("Retrieval chunks")
        plt.xticks(rotation=45, ha="right")
        save_current_plot(path)
        generated.append(path)
    else:
        warnings.append("Skipped chunks_per_module.png: module chunk counts unavailable.")

    # Metadata missingness.
    if not metadata_completeness_df.empty:
        plot_df = metadata_completeness_df.copy()
        plot_df["label"] = plot_df["entity_type"].astype(str) + ": " + plot_df["field"].astype(str)
        plot_df = plot_df.sort_values("missing_percent", ascending=False)
        path = plots_dir / "metadata_missingness.png"
        plt.figure(figsize=(12, max(6, min(16, len(plot_df) * 0.25))))
        plt.barh(plot_df["label"], plot_df["missing_percent"])
        plt.title("Metadata missingness by field")
        plt.xlabel("Missing percent")
        plt.ylabel("Field")
        plt.gca().invert_yaxis()
        save_current_plot(path)
        generated.append(path)
    else:
        warnings.append("Skipped metadata_missingness.png: metadata completeness table is empty.")

    # Scatter: module total words vs chunks.
    if not modules_df.empty and {"module_total_text_words", "chunk_count"}.issubset(modules_df.columns):
        path = plots_dir / "module_words_vs_chunks.png"
        plt.figure(figsize=(8, 5))
        plt.scatter(modules_df["module_total_text_words"], modules_df["chunk_count"])
        plt.title("Module text volume vs chunk count")
        plt.xlabel("Module total words")
        plt.ylabel("Chunk count")
        save_current_plot(path)
        generated.append(path)
    else:
        warnings.append("Skipped module_words_vs_chunks.png: module word or chunk count data missing.")

    # Scatter: ECTS vs module words.
    if not modules_df.empty and {"ects", "module_total_text_words"}.issubset(modules_df.columns) and modules_df["ects"].notna().any():
        path = plots_dir / "ects_vs_module_words.png"
        plt.figure(figsize=(8, 5))
        plt.scatter(modules_df["ects"], modules_df["module_total_text_words"])
        plt.title("ECTS vs module text volume")
        plt.xlabel("ECTS")
        plt.ylabel("Module total words")
        save_current_plot(path)
        generated.append(path)
    else:
        warnings.append("Skipped ects_vs_module_words.png: ECTS or module word data missing.")

    # Tables.
    if not tables_df.empty and {"table_id", "row_count"}.issubset(tables_df.columns):
        plot_df = tables_df.sort_values("row_count", ascending=False).copy()
        path = plots_dir / "table_rows_distribution.png"
        plt.figure(figsize=(10, 5))
        plt.bar(plot_df["table_id"].astype(str), plot_df["row_count"])
        plt.title("Rows per table")
        plt.xlabel("Table ID")
        plt.ylabel("Rows")
        plt.xticks(rotation=45, ha="right")
        save_current_plot(path)
        generated.append(path)
    else:
        warnings.append("Skipped table_rows_distribution.png: no table rows available.")

    path = plots_dir / "table_confidence_distribution.png"
    warning = bar_plot_from_counts(
        distributions.get("table_confidence_distribution", pd.DataFrame()),
        "extraction_confidence",
        "count",
        "Table extraction confidence distribution",
        "Extraction confidence",
        "Tables",
        path,
        rotate=0,
    )
    warn_or_add(path, warning)

    return generated, warnings


# ---------------------------------------------------------------------------
# Report writing
# ---------------------------------------------------------------------------

def format_value(value: Any) -> str:
    """Format values for Markdown."""
    if value is None:
        return ""
    if isinstance(value, float):
        if math.isnan(value):
            return ""
        return f"{value:.2f}"
    return str(value)


def markdown_table_from_pairs(pairs: Sequence[Tuple[Any, Any]]) -> str:
    """Create a simple two-column Markdown table without optional dependencies."""
    lines = ["| Metric | Value |", "|---|---:|"]
    for key, value in pairs:
        lines.append(f"| {key} | {format_value(value)} |")
    return "\n".join(lines)


def dataframe_preview_table(df: pd.DataFrame, max_rows: int = 10) -> str:
    """Create a small Markdown table preview without pandas.to_markdown."""
    if df.empty:
        return "_No records._"
    preview = df.head(max_rows).copy()
    cols = list(preview.columns)
    lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, row in preview.iterrows():
        values = [str(row.get(col, "")).replace("\n", " ") for col in cols]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def practical_recommendations(modules_df: pd.DataFrame, chunks_df: pd.DataFrame, tables_df: pd.DataFrame) -> List[str]:
    """Generate practical recommendations from calculated diagnostics."""
    recs: List[str] = []
    if chunks_df.empty:
        recs.append("No retrieval chunks were found; create chunk records before embedding.")
        return recs
    avg_tokens = chunks_df["approx_token_count"].mean() if "approx_token_count" in chunks_df else 0
    pct_under_100 = float((chunks_df["approx_token_count"] <= 100).mean() * 100) if "approx_token_count" in chunks_df else 0
    pct_over_1200 = float((chunks_df["approx_token_count"] > 1200).mean() * 100) if "approx_token_count" in chunks_df else 0
    if pct_under_100 > 40:
        recs.append("Many chunks are under 100 approximate tokens; consider merging tiny field chunks or adding more module context.")
    elif avg_tokens < 120:
        recs.append("Average chunk size is short; verify that chunks still include standalone module context.")
    else:
        recs.append("Average chunk size appears suitable for embedding-based retrieval, assuming page and module context are present.")
    if pct_over_1200 > 5:
        recs.append("Some chunks exceed 1200 approximate tokens; split long chunks by section or paragraph while preserving module boundaries.")
    if "has_page_refs" in chunks_df and (~chunks_df["has_page_refs"].fillna(False).astype(bool)).any():
        recs.append("Some chunks lack page references; fix these before citation-grounded QA.")
    if "has_standalone_context" in chunks_df and chunks_df["has_standalone_context"].mean() < 0.95:
        recs.append("Not all chunks contain enough standalone context; prepend module code/title/source page to every embedded chunk.")
    if not modules_df.empty:
        if "has_ects" in modules_df and (~modules_df["has_ects"].fillna(False).astype(bool)).any():
            recs.append("Some modules are missing ECTS; review extraction of module identity fields.")
        if "has_language" in modules_df and (~modules_df["has_language"].fillna(False).astype(bool)).any():
            recs.append("Language metadata is missing for some modules; if the whole document is German, consider adding a documented global default during preprocessing.")
        if "responsible_person_count" in modules_df and (modules_df["responsible_person_count"].fillna(0) == 0).all():
            recs.append("No responsible persons are listed in module records; keep this as null/empty unless verified from another authoritative source.")
    if not tables_df.empty:
        if "has_rows" in tables_df and (~tables_df["has_rows"].fillna(False).astype(bool)).any():
            recs.append("Some tables have no rows; inspect table extraction or decide whether these are layout templates rather than data tables.")
        if "low_or_medium_confidence" in tables_df and tables_df["low_or_medium_confidence"].any():
            recs.append("Low/medium-confidence tables need manual review before using them for answer generation.")
    elif tables_df.empty:
        recs.append("No tables were extracted; if the source visually contains table-like module templates, ensure their facts are represented in modules and chunks.")
    return recs


def write_markdown_report(
    output_dir: Path,
    metadata: Dict[str, Any],
    summary_df: pd.DataFrame,
    chunk_stats_df: pd.DataFrame,
    metadata_completeness_df: pd.DataFrame,
    rag_readiness_df: pd.DataFrame,
    modules_df: pd.DataFrame,
    chunks_df: pd.DataFrame,
    tables_df: pd.DataFrame,
    module_section_coverage_df: pd.DataFrame,
    top_keywords_df: pd.DataFrame,
    issues: List[str],
    plot_warnings: List[str],
    csv_files: List[Path],
    plot_files: List[Path],
) -> Path:
    """Write the final Markdown report."""
    report_path = output_dir / "rag_dataset_analysis_report.md"
    summary_pairs = list(summary_df.itertuples(index=False, name=None))
    rag_pairs = list(rag_readiness_df.itertuples(index=False, name=None))

    # Interesting longest/shortest diagnostics.
    longest_cols = ["chunk_id", "parent_module_id", "module_code", "section_type", "text_word_count", "approx_token_count"]
    longest_chunks = chunks_df.sort_values("text_word_count", ascending=False)[[c for c in longest_cols if c in chunks_df]].head(10) if not chunks_df.empty else pd.DataFrame()
    shortest_chunks = chunks_df.sort_values("text_word_count", ascending=True)[[c for c in longest_cols if c in chunks_df]].head(10) if not chunks_df.empty else pd.DataFrame()
    module_volume_cols = ["module_id", "module_code", "module_title", "module_total_text_words", "chunk_count", "ects"]
    largest_modules = modules_df.sort_values("module_total_text_words", ascending=False)[[c for c in module_volume_cols if c in modules_df]].head(10) if not modules_df.empty else pd.DataFrame()
    table_cols = ["table_id", "parent_module_id", "row_count", "column_count", "extraction_confidence", "has_caption", "has_context"]
    table_preview = tables_df.sort_values("row_count", ascending=False)[[c for c in table_cols if c in tables_df]].head(10) if not tables_df.empty else pd.DataFrame()

    recs = practical_recommendations(modules_df, chunks_df, tables_df)

    lines: List[str] = []
    lines.append("# RAG Dataset Analysis Report")
    lines.append("")
    lines.append("## 1. Dataset overview")
    lines.append("")
    lines.append(f"Source file: `{metadata.get('source_file', '')}`")
    lines.append("")
    lines.append(markdown_table_from_pairs(summary_pairs))
    lines.append("")

    lines.append("## 2. Main size statistics")
    lines.append("")
    lines.append("This section summarizes modules, retrieval chunks, tables, pages, programs, module groups, semesters, section types, and retrieval priorities.")
    lines.append("")
    lines.append(markdown_table_from_pairs(summary_pairs))
    lines.append("")

    lines.append("## 3. Chunk length analysis")
    lines.append("")
    lines.append(dataframe_preview_table(chunk_stats_df, max_rows=20))
    lines.append("")
    lines.append("### Longest chunks")
    lines.append(dataframe_preview_table(longest_chunks, max_rows=10))
    lines.append("")
    lines.append("### Shortest chunks")
    lines.append(dataframe_preview_table(shortest_chunks, max_rows=10))
    lines.append("")

    lines.append("## 4. Metadata completeness")
    lines.append("")
    missing_preview = metadata_completeness_df.sort_values("missing_percent", ascending=False) if not metadata_completeness_df.empty else metadata_completeness_df
    lines.append(dataframe_preview_table(missing_preview, max_rows=25))
    lines.append("")

    lines.append("## 5. RAG-readiness assessment")
    lines.append("")
    lines.append(markdown_table_from_pairs(rag_pairs))
    lines.append("")

    lines.append("## 6. Module structure analysis")
    lines.append("")
    lines.append("### Largest modules by total extracted text")
    lines.append(dataframe_preview_table(largest_modules, max_rows=10))
    lines.append("")
    lines.append("### Module coverage by important section groups")
    lines.append(dataframe_preview_table(module_section_coverage_df, max_rows=25))
    lines.append("")

    lines.append("## 7. Table analysis")
    lines.append("")
    lines.append(dataframe_preview_table(table_preview, max_rows=15))
    lines.append("")

    lines.append("## 8. Detected warnings and suspicious cases")
    lines.append("")
    for issue in issues:
        lines.append(f"- {issue}")
    for warning in plot_warnings:
        lines.append(f"- {warning}")
    lines.append("")

    lines.append("## 9. Generated CSV files")
    lines.append("")
    for path in csv_files:
        lines.append(f"- `{path.relative_to(output_dir)}`")
    lines.append("")

    lines.append("## 10. Generated plot files")
    lines.append("")
    if plot_files:
        for path in plot_files:
            lines.append(f"- `{path.relative_to(output_dir)}`")
    else:
        lines.append("_No plots were generated._")
    lines.append("")

    lines.append("## 11. Practical recommendations")
    lines.append("")
    for rec in recs:
        lines.append(f"- {rec}")
    if not top_keywords_df.empty:
        lines.append("")
        lines.append("## Top keywords preview")
        lines.append("")
        lines.append(dataframe_preview_table(top_keywords_df, max_rows=20))
    lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


# ---------------------------------------------------------------------------
# Main workflow
# ---------------------------------------------------------------------------

def save_csv(df: pd.DataFrame, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze a structured RAG dataset extracted from a module handbook.")
    parser.add_argument("--input-dir", type=Path, default=Path("data/initial_processed_data"), help="Directory containing the five RAG dataset files.")
    parser.add_argument("--output-dir", type=Path, default=Path("data/initial_processed_data/analysis_output"), help="Directory for CSVs, plots, and report.")
    args = parser.parse_args()

    input_dir = args.input_dir.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = validate_required_files(input_dir)
    metadata = load_json(paths["document_metadata"])
    modules_data = load_json(paths["modules"])
    tables_data = load_json(paths["tables"])
    chunks = load_jsonl(paths["retrieval_chunks"])
    qc_report = load_json(paths["quality_control_report"])

    if not isinstance(metadata, dict):
        metadata = {"_non_object_metadata": metadata}
    if not isinstance(qc_report, dict):
        qc_report = {"_non_object_quality_control_report": qc_report}

    modules = normalize_record_list(modules_data, "modules")
    tables = normalize_record_list(tables_data, "tables")

    module_ids = {clean_str(m.get("module_id")) for m in modules if clean_str(m.get("module_id"))}
    module_page_ranges = {
        clean_str(m.get("module_id")): (
            safe_get(m, ["source_pages", "page_start"]),
            safe_get(m, ["source_pages", "page_end"]),
        )
        for m in modules
        if clean_str(m.get("module_id"))
    }
    page_count = parse_numeric(metadata.get("page_count"))
    page_count_int = int(page_count) if page_count is not None else None

    # Build diagnostics dataframes.
    tables_df = build_table_dataframe(tables, module_ids=module_ids)
    chunks_df = build_chunk_dataframe(chunks, module_ids=module_ids, module_page_ranges=module_page_ranges, page_count=page_count_int)
    modules_df = build_module_dataframe(modules, chunks_df=chunks_df, tables_df=tables_df)

    # Recompute tables now that no module fields depend on it further.
    summary_df = calculate_summary_statistics(metadata, qc_report, modules_df, chunks_df, tables_df)
    chunk_stats_df = calculate_chunk_length_statistics(chunks_df)
    metadata_completeness_df = calculate_metadata_completeness(modules_df, chunks_df, tables_df)
    rag_readiness_df = calculate_rag_readiness(modules_df, chunks_df, tables_df)
    distributions = calculate_distributions(modules_df, chunks_df, tables_df)
    module_section_coverage_df = calculate_module_section_coverage(modules_df, chunks_df)
    top_keywords_df = calculate_top_keywords(chunks_df, top_n=50)
    issues = detect_issues(metadata, qc_report, modules_df, chunks_df, tables_df)

    # Save required and useful CSVs.
    csv_files: List[Path] = []
    csv_files.append(save_csv(summary_df, output_dir / "summary_overview.csv"))
    csv_files.append(save_csv(chunk_stats_df, output_dir / "chunk_length_statistics.csv"))
    csv_files.append(save_csv(chunks_df, output_dir / "chunk_diagnostics.csv"))
    csv_files.append(save_csv(modules_df, output_dir / "module_diagnostics.csv"))
    csv_files.append(save_csv(tables_df, output_dir / "table_diagnostics.csv"))
    csv_files.append(save_csv(metadata_completeness_df, output_dir / "metadata_completeness.csv"))
    csv_files.append(save_csv(distributions["section_type_distribution"], output_dir / "section_type_distribution.csv"))
    csv_files.append(save_csv(distributions["retrieval_priority_distribution"], output_dir / "retrieval_priority_distribution.csv"))
    csv_files.append(save_csv(module_section_coverage_df, output_dir / "module_section_coverage.csv"))
    csv_files.append(save_csv(top_keywords_df, output_dir / "top_keywords.csv"))
    csv_files.append(save_csv(rag_readiness_df, output_dir / "rag_readiness_summary.csv"))

    # Additional helpful distribution CSVs.
    extra_distribution_names = [
        "modules_per_program",
        "modules_per_module_group",
        "modules_per_semester",
        "chunk_type_distribution",
        "token_bucket_distribution",
        "ects_distribution",
        "table_confidence_distribution",
    ]
    for name in extra_distribution_names:
        csv_files.append(save_csv(distributions[name], output_dir / f"{name}.csv"))

    # Generate plots.
    plot_files, plot_warnings = create_visualizations(
        output_dir=output_dir,
        modules_df=modules_df,
        chunks_df=chunks_df,
        tables_df=tables_df,
        metadata_completeness_df=metadata_completeness_df,
        distributions=distributions,
    )

    report_path = write_markdown_report(
        output_dir=output_dir,
        metadata=metadata,
        summary_df=summary_df,
        chunk_stats_df=chunk_stats_df,
        metadata_completeness_df=metadata_completeness_df,
        rag_readiness_df=rag_readiness_df,
        modules_df=modules_df,
        chunks_df=chunks_df,
        tables_df=tables_df,
        module_section_coverage_df=module_section_coverage_df,
        top_keywords_df=top_keywords_df,
        issues=issues,
        plot_warnings=plot_warnings,
        csv_files=csv_files,
        plot_files=plot_files,
    )

    # Concise terminal summary.
    print("RAG dataset analysis complete.")
    print(f"Input directory: {input_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Modules: {len(modules_df)}")
    print(f"Retrieval chunks: {len(chunks_df)}")
    print(f"Tables: {len(tables_df)}")
    if not chunks_df.empty and "text_word_count" in chunks_df:
        print(f"Average chunk words: {chunks_df['text_word_count'].mean():.1f}")
    if not chunks_df.empty and "approx_token_count" in chunks_df:
        print(f"Average approximate tokens: {chunks_df['approx_token_count'].mean():.1f}")
    print(f"CSV files written: {len(csv_files)}")
    print(f"Plot files written: {len(plot_files)}")
    print(f"Markdown report: {report_path}")
    if plot_warnings:
        print("Plot warnings:")
        for warning in plot_warnings:
            print(f"  - {warning}")


if __name__ == "__main__":
    main()
