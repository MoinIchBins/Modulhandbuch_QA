# RAG JSON Dataset for `modulhandbuch.pdf`

This directory contains a structured, citation-ready representation of `modulhandbuch.pdf`, prepared for search, retrieval-augmented generation (RAG), question answering, review, and downstream analysis.

The dataset represents the original PDF as document metadata, structured module records, table records, retrieval chunks, and quality-control information.

## File Inventory

| File | Contains | Role in the PDF representation | Main relationships |
|---|---|---|---|
| `document_metadata.json` | One document-level metadata object | Describes the whole PDF: title, institution, language, version, page count, module count, table count, chunk count, extraction method, and global notes | Independent root metadata; useful for validation and display |
| `modules.json` | Array of module records | Canonical structured module data. Best source for exact module facts such as ECTS, workload, prerequisites, exam, courses/components, notes, and cross-references | `module_id` links to `retrieval_chunks.parent_module_id` and `tables.parent_module_id`; module `tables` lists table IDs |
| `tables.json` | Array of table records | Contains one table of contents table plus one structured field-value table per module | `table_id` is referenced from `modules[].tables`; `parent_module_id` links module tables back to `modules.json` |
| `retrieval_chunks.jsonl` | JSON Lines file, one retrieval chunk per line | Embedding/search-ready chunks. Each chunk repeats enough context to stand alone and includes page references | `parent_module_id` links module chunks to `modules.json`; document chunks have `parent_module_id: null` |
| `quality_control_report.json` | One quality-control object | Documents coverage, detected extraction issues, assumptions, and manual-review needs | Should be checked before trusting downstream QA results |

Core relationship model:

```text
document_metadata.json
        |
        | describes the whole source PDF
        v
modules.json  <---- linked by module_id ---->  retrieval_chunks.jsonl
        |
        | table IDs listed in module.tables
        v
tables.json

quality_control_report.json documents extraction assumptions, issues, and manual-review needs.
```

The strongest module identifier is `module_id`, for example:

```text
module-2100
module-4100
module-5900
```

The strongest citation fields are:

```text
page_start
page_end
page_refs
source_pages.page_start
source_pages.page_end
source_pages.page_refs
```

## Dataset Summary

| Item | Count |
|---|---:|
| PDF pages processed | 35 |
| Modules | 16 |
| Tables | 17 |
| Retrieval chunks | 163 |
| Document-level chunks | 3 |
| Module-level chunks | 160 |

## Data Model

### `document_metadata.json`

Expected structure:

| Field | Type | Meaning |
|---|---|---|
| `record_type` | string | Always `"document_metadata"` |
| `source_file` | string | Original PDF filename |
| `document_title` | string or null | Human-readable title |
| `institution` | string or null | Institution name |
| `faculty` | string or null | Faculty name |
| `programs` | array of strings | Programs represented in the PDF |
| `degree_levels` | array of strings | Degree level labels |
| `language` | string | Document language, here `"de"` |
| `document_date` | string or null | Source document date |
| `version` | string or null | Version label |
| `page_count` | integer | Number of PDF pages |
| `module_count` | integer | Number of detected module records |
| `table_count` | integer | Number of table records |
| `chunk_count` | integer | Number of retrieval chunks |
| `extraction_method` | string | Summary of extraction approach |
| `global_extraction_notes` | array of strings | Important document-wide caveats |

Important convention: metadata counts should match actual file counts. In this dataset, the expected values are 16 modules, 17 tables, and 163 chunks.

### `modules.json`

Each item is a module record. This file is the most authoritative structured representation for exact module facts.

| Field | Type | Meaning / expected values |
|---|---|---|
| `record_type` | string | Always `"module"` |
| `source_file` | string | Original PDF filename |
| `module_id` | string | Stable internal ID, usually `module-{module_code}` |
| `module_code` | string or null | Official module number, e.g. `"2100"` |
| `module_title` | string | Original German title |
| `module_title_normalized` | string | Lowercased normalized title for matching |
| `program` | string or null | Program name |
| `degree_level` | string or null | Degree level |
| `module_group` | string or null | Examples: `Basismodul`, `Aufbaumodul`, `Vertiefungsmodul`, `Basiswissen Linguistik` |
| `recommended_semester` | string or null | Raw semester text, often multi-line |
| `ects` | integer or null | Total ECTS |
| `workload` | object | Structured workload fields |
| `duration` | string or null | Example: `"1 Semester"` |
| `frequency` | string or null | Raw offer frequency |
| `language` | string or null | Usually `"de"` |
| `responsible_persons` | array | Empty if not present in source |
| `lecturers` | array | Empty if not present in source |
| `prerequisites` | object | Formal/content prerequisites |
| `learning_outcomes` | object | `raw_text` plus optional bullet `items` |
| `content` | object | `raw_text` plus optional bullet `items` |
| `teaching_methods` | string or null | Lehrveranstaltungen / Belegung text |
| `exam` | object | Exam type, duration, grading, weighting, details |
| `courses_or_components` | array of objects | Component-level course data |
| `literature` | object | Usually null/empty because source has no literature section |
| `tables` | array of strings | Table IDs associated with this module |
| `notes` | array of strings | “Sonstige Informationen” and similar notes |
| `cross_references` | array of objects | Detected prerequisite/cross-module references |
| `source_pages` | object | Page span and page references |
| `extraction_confidence` | string | Usually `"high"` |
| `extraction_notes` | array of strings | Module-specific caveats |

#### Workload object

```json
{
  "total_hours": 360,
  "contact_hours": 120,
  "self_study_hours": 120,
  "details": {
    "workload_text": "360 Stunden",
    "contact_time": "...",
    "self_study": "...",
    "exam_ects": "4 ECTS-Leistungspunkte"
  }
}
```

#### Prerequisites object

```json
{
  "required": "Keine",
  "recommended": "Keine",
  "text": "Formal: Keine\nInhaltlich: Keine"
}
```

#### Exam object

```json
{
  "exam_type": "Portfolio (Pnr. 2110)",
  "exam_duration": null,
  "graded": null,
  "weighting": null,
  "details": "..."
}
```

#### Course/component object

```json
{
  "label": "a",
  "title": "Einführung in die computationelle Logik",
  "teaching_form": "Seminar & Übung",
  "course_code": "2101",
  "recommended_semester": "1. Fachsemester (Wintersemester)",
  "frequency": "Jedes Wintersemester",
  "group_size": "Ca. 60 Studierende",
  "contact_time": "4 SWS / 60 Stunden / 2 ECTS-Leistungspunkte",
  "self_study": "60 Stunden / 2 ECTS-Leistungspunkte",
  "raw_text": "a: Einführung in die computationelle Logik (Seminar & Übung) / 2101"
}
```

#### Source pages object

```json
{
  "page_start": 4,
  "page_end": 5,
  "page_refs": [
    {"page": 4},
    {"page": 5}
  ]
}
```

Important convention: in `modules.json`, `source_pages.page_refs` is an array of objects; in `retrieval_chunks.jsonl`, `page_refs` is an array of page numbers.

### `tables.json`

The table records are structured JSON tables. The file contains the table of contents plus module field-value tables.

| Field | Type | Meaning |
|---|---|---|
| `record_type` | string | Always `"table"` |
| `table_id` | string | Stable table ID |
| `parent_module_id` | string or null | Null for document-level TOC; module ID for module tables |
| `source_file` | string | Original PDF filename |
| `page_start` | integer | First source page |
| `page_end` | integer | Last source page |
| `caption` | string or null | Table label |
| `context` | string or null | Description of table origin |
| `columns` | array of strings | Column names |
| `rows` | array of objects | Row data |
| `extraction_confidence` | string | Usually `"high"` |
| `extraction_notes` | array | Table-specific caveats |

Important convention: module tables are not necessarily native PDF tables. The module templates were transformed into synthetic field-value tables to preserve the handbook structure.

The table of contents table generally uses:

```json
"columns": ["entry", "page"]
```

Module tables generally use:

```json
"columns": ["field", "value"]
```

### `retrieval_chunks.jsonl`

This is the main file to index for RAG.

Each line is a complete JSON object. There is no surrounding array. Load it line by line.

| Field | Type | Meaning |
|---|---|---|
| `record_type` | string | Always `"retrieval_chunk"` |
| `chunk_id` | string | Unique chunk ID |
| `parent_module_id` | string or null | Module link; null for document-level chunks |
| `source_file` | string | Original PDF filename |
| `page_start` | integer | First source page |
| `page_end` | integer | Last source page |
| `page_refs` | array of integers | Source page references |
| `program` | string or null | Program context |
| `degree_level` | string or null | Degree context |
| `module_code` | string or null | Module code |
| `module_title` | string or null | Module title |
| `module_group` | string or null | Module group |
| `recommended_semester` | string or null | Semester text |
| `ects` | integer or null | ECTS |
| `language` | string or null | Usually `"de"` |
| `section_type` | string | Usually `"document"` or `"module"` |
| `chunk_type` | string | Chunk subtype |
| `retrieval_priority` | string | Usually `"high"` or `"normal"` |
| `text` | string | Standalone retrieval text |
| `structured_facts` | object | Machine-friendly extracted facts |
| `keywords` | array of strings | Search helper keywords |
| `extraction_notes` | array | Chunk-specific caveats |

Observed `chunk_type` values:

| Chunk type | Expected count | Meaning |
|---|---:|---|
| `table_of_contents` | 1 | TOC chunk |
| `study_goals` | 1 | “Ziele des Studiums” |
| `study_structure` | 1 | “Aufbau des Studiums” |
| `overview` | 16 | One overview per module |
| `semester_ects` | 16 | Semester, ECTS, duration, frequency |
| `workload` | 16 | Workload/contact/self-study |
| `course_components` | 16 | Course/component details |
| `content` | 16 | Inhalte |
| `learning_outcomes` | 16 | Angestrebte Lernergebnisse |
| `prerequisites` | 16 | Teilnahmevoraussetzungen |
| `exam` | 16 | Prüfungsformen and exam details |
| `table` | 16 | Module table chunk |
| `notes` | 16 | Sonstige Informationen / notes |

Important convention: every module should have 10 retrieval chunks. The dataset also has 3 document-level chunks with `parent_module_id: null`.

### `quality_control_report.json`

This file records extraction coverage and caveats.

| Field | Type | Meaning |
|---|---|---|
| `record_type` | string | Always `"quality_control_report"` |
| `source_file` | string | Original PDF filename |
| `coverage.pages_processed` | array of integers | Pages processed |
| `coverage.pages_with_uncertain_extraction` | array | Pages flagged uncertain |
| `coverage.modules_detected` | integer | Detected module count |
| `coverage.modules_with_missing_ects` | array | Module IDs/codes with missing ECTS |
| `coverage.modules_with_missing_exam` | array | Missing exam records |
| `coverage.modules_with_missing_prerequisites` | array | Missing prerequisites |
| `coverage.tables_detected` | integer | Detected table count |
| `detected_issues` | array of objects | Warnings and source issues |
| `assumptions` | array of strings | Extraction assumptions |
| `recommended_manual_checks` | array of strings | Suggested review items |

Known QC issue categories include:

- missing source fields for responsible persons, lecturers, literature, grading, weighting, and exam duration;
- source typos in some modules;
- possible semester/frequency inconsistency in one module;
- source formatting variations such as `-keine` versus `-keine-`.

## Segmentation Logic

### Document segmentation

The document is segmented into:

| Segment type | Representation |
|---|---|
| Whole document | `document_metadata.json` |
| Table of contents | `tables.json` record `table-document-toc` and retrieval chunk `document-toc-p001` |
| Introductory prose | Retrieval chunks `document-study-goals-p002` and `document-study-structure-p002-p003` |
| Modules | One object per module in `modules.json` |
| Module tables | One table per module in `tables.json` |
| RAG chunks | One JSONL line per chunk in `retrieval_chunks.jsonl` |

### Module segmentation

Modules are segmented by module-level headings and module codes. Example pattern:

```text
Modul: Basismodul – Mathematische und logische Grundlagen
Modul-Nummer: 2100
```

Each detected module becomes:

```text
module-{module_code}
```

For example:

```text
module-2100
module-2200
module-5900
```

Each module generally spans two pages.

### Chunk segmentation

Each module is split into 10 retrieval chunks:

```text
overview
semester_ects
workload
course_components
content
learning_outcomes
prerequisites
exam
table
notes
```

This allows retrieval to target a specific information need without retrieving the entire module every time.

Example chunk ID convention:

```text
modulhandbuch-po2025-2100-overview
modulhandbuch-po2025-2100-prerequisites
modulhandbuch-po2025-2100-exam
```

Document-level chunks use a different convention:

```text
document-toc-p001
document-study-goals-p002
document-study-structure-p002-p003
```

### Page, block, paragraph, section, table, image, and token group representation

| Concept | Present in files? | How represented |
|---|---|---|
| Page | Yes | `page_start`, `page_end`, `page_refs`, `source_pages` |
| Block | No explicit block IDs | Blocks are implicit in fields/chunks |
| Paragraph | No explicit paragraph IDs | Preserved as text with line breaks inside fields/chunks |
| Section | Yes, coarse | `chunk_type`, `section_type`, table `field` values |
| Heading | Implicit | Module title and section labels such as `Inhalte`, `Prüfungsformen` |
| Table | Yes | `tables.json` records |
| Image | No | No image records are present |
| Token group | No | No tokenizer output or token spans are present |
| Coordinates | No | No bounding boxes or coordinates are present |

Important limitation: there are no PDF coordinates, word-level spans, or OCR confidence values. Page-level citation is supported; exact coordinate highlighting is not.

### Ordering

Ordering is preserved by:

1. file order in `modules.json`;
2. file order in `retrieval_chunks.jsonl`;
3. `page_start` and `page_end`;
4. `module_code`;
5. `chunk_type` order within each module.

Recommended reconstruction order:

```text
document chunks by page_start
then modules by source_pages.page_start
then module chunks by a fixed chunk_type order
```

Suggested module chunk order:

```python
CHUNK_ORDER = [
    "overview",
    "semester_ects",
    "workload",
    "course_components",
    "content",
    "learning_outcomes",
    "prerequisites",
    "exam",
    "table",
    "notes",
]
```

## Usage Guide

### Load the data

```python
import json
from pathlib import Path

base = Path(".")

metadata = json.loads((base / "document_metadata.json").read_text(encoding="utf-8"))
modules = json.loads((base / "modules.json").read_text(encoding="utf-8"))
tables = json.loads((base / "tables.json").read_text(encoding="utf-8"))
qc = json.loads((base / "quality_control_report.json").read_text(encoding="utf-8"))

chunks = []
with (base / "retrieval_chunks.jsonl").open("r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            chunks.append(json.loads(line))
```

### Build useful indexes

```python
modules_by_id = {m["module_id"]: m for m in modules}
modules_by_code = {m["module_code"]: m for m in modules if m.get("module_code")}
tables_by_id = {t["table_id"]: t for t in tables}
chunks_by_id = {c["chunk_id"]: c for c in chunks}

chunks_by_module = {}
for c in chunks:
    chunks_by_module.setdefault(c.get("parent_module_id"), []).append(c)

tables_by_module = {}
for t in tables:
    tables_by_module.setdefault(t.get("parent_module_id"), []).append(t)
```

### Retrieve text by page

```python
def chunks_on_page(chunks, page_number):
    return [
        c for c in chunks
        if page_number in c.get("page_refs", [])
        or c.get("page_start") <= page_number <= c.get("page_end")
    ]

page_14_chunks = chunks_on_page(chunks, 14)
for chunk in page_14_chunks:
    print(chunk["chunk_id"], chunk["chunk_type"])
```

For page-level review, also search module records:

```python
def modules_on_page(modules, page_number):
    result = []
    for m in modules:
        sp = m.get("source_pages", {})
        if sp.get("page_start") <= page_number <= sp.get("page_end"):
            result.append(m)
    return result

for m in modules_on_page(modules, 14):
    print(m["module_code"], m["module_title"])
```

### Get all chunks in document order

```python
CHUNK_TYPE_ORDER = {
    "table_of_contents": 0,
    "study_goals": 1,
    "study_structure": 2,
    "overview": 10,
    "semester_ects": 11,
    "workload": 12,
    "course_components": 13,
    "content": 14,
    "learning_outcomes": 15,
    "prerequisites": 16,
    "exam": 17,
    "table": 18,
    "notes": 19,
}

ordered_chunks = sorted(
    chunks,
    key=lambda c: (
        c.get("page_start") or 9999,
        c.get("module_code") or "",
        CHUNK_TYPE_ORDER.get(c.get("chunk_type"), 999),
        c.get("chunk_id") or "",
    )
)

for c in ordered_chunks:
    print(c["page_start"], c["chunk_id"])
```

### Trace a chunk back to the source PDF

```python
def trace_chunk(chunk_id):
    chunk = chunks_by_id[chunk_id]
    module = modules_by_id.get(chunk.get("parent_module_id"))

    return {
        "chunk_id": chunk["chunk_id"],
        "source_file": chunk["source_file"],
        "pages": chunk.get("page_refs"),
        "page_start": chunk.get("page_start"),
        "page_end": chunk.get("page_end"),
        "module_id": chunk.get("parent_module_id"),
        "module_code": chunk.get("module_code"),
        "module_title": chunk.get("module_title"),
        "module_source_pages": module.get("source_pages") if module else None,
        "text": chunk.get("text"),
    }

trace = trace_chunk("modulhandbuch-po2025-4100-prerequisites")
print(trace)
```

### Use for RAG indexing

Recommended index record:

```python
embedding_records = []

for c in chunks:
    embedding_records.append({
        "id": c["chunk_id"],
        "text": c["text"],
        "metadata": {
            "source_file": c["source_file"],
            "page_start": c["page_start"],
            "page_end": c["page_end"],
            "page_refs": c["page_refs"],
            "parent_module_id": c["parent_module_id"],
            "module_code": c["module_code"],
            "module_title": c["module_title"],
            "module_group": c["module_group"],
            "chunk_type": c["chunk_type"],
            "section_type": c["section_type"],
            "retrieval_priority": c["retrieval_priority"],
            "ects": c["ects"],
            "language": c["language"],
        }
    })
```

Recommended retrieval logic:

1. Search `retrieval_chunks.jsonl`.
2. Use metadata filters when possible:
   - `module_code`
   - `module_group`
   - `chunk_type`
   - `recommended_semester`
   - `ects`
3. Retrieve top chunks.
4. Optionally expand to the parent module through `parent_module_id`.
5. Cite `source_file` plus `page_refs`.

Example answer citation format:

```text
Source: modulhandbuch.pdf, pp. 16–17
```

### Use for exact extraction

For exact module facts, prefer `modules.json` over free-text chunks:

```python
m = modules_by_code["4100"]

answer = {
    "module": m["module_title"],
    "ects": m["ects"],
    "exam": m["exam"]["exam_type"],
    "prerequisites": m["prerequisites"]["text"],
    "pages": m["source_pages"]["page_refs"],
}
```

### Use for table reconstruction

```python
def table_as_markdown(table):
    columns = table["columns"]
    rows = table["rows"]

    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join(["---"] * len(columns)) + " |"

    body = []
    for row in rows:
        body.append("| " + " | ".join(str(row.get(c, "")) for c in columns) + " |")

    return "\n".join([header, sep] + body)

table = tables_by_id["table-module-2100"]
print(table_as_markdown(table))
```

## Practical Workflows

### Workflow A: Find content on page X

```python
def find_content_on_page(page):
    page_chunks = chunks_on_page(chunks, page)
    page_modules = modules_on_page(modules, page)

    return {
        "page": page,
        "modules": [
            {
                "module_id": m["module_id"],
                "module_code": m["module_code"],
                "module_title": m["module_title"],
            }
            for m in page_modules
        ],
        "chunks": [
            {
                "chunk_id": c["chunk_id"],
                "chunk_type": c["chunk_type"],
                "module_code": c.get("module_code"),
                "title": c.get("module_title"),
                "text": c["text"],
            }
            for c in page_chunks
        ],
    }

result = find_content_on_page(28)
```

Use case: review page 28 or answer “What is on page 28?”

### Workflow B: Get all chunks in order

```python
def all_chunks_in_order():
    return sorted(
        chunks,
        key=lambda c: (
            c.get("page_start") or 9999,
            c.get("module_code") or "",
            CHUNK_TYPE_ORDER.get(c.get("chunk_type"), 999),
            c.get("chunk_id") or "",
        )
    )

ordered = all_chunks_in_order()
```

Use case: rebuild a readable Markdown representation or feed chunks into a sequential summarizer.

### Workflow C: Trace this chunk back to the PDF

```python
def citation_for_chunk(chunk_id):
    c = chunks_by_id[chunk_id]
    pages = c.get("page_refs") or []

    if len(pages) == 1:
        page_text = f"p. {pages[0]}"
    elif pages:
        page_text = f"pp. {min(pages)}–{max(pages)}"
    else:
        page_text = f"pp. {c.get('page_start')}–{c.get('page_end')}"

    return {
        "chunk_id": chunk_id,
        "source": f"{c.get('source_file')}, {page_text}",
        "module": c.get("module_title"),
        "module_code": c.get("module_code"),
        "chunk_type": c.get("chunk_type"),
    }

print(citation_for_chunk("modulhandbuch-po2025-5900-exam"))
```

Use case: citation-grounded generation.

### Workflow D: Answer a module-specific question

Question: “Welche Prüfungsform hat Modul 2300?”

```python
def module_exam_by_code(code):
    m = modules_by_code[code]
    return {
        "module_code": code,
        "module_title": m["module_title"],
        "exam_type": m["exam"]["exam_type"],
        "details": m["exam"]["details"],
        "source_pages": m["source_pages"],
    }

module_exam_by_code("2300")
```

For user-facing answers, cite the page span from `source_pages`.

### Workflow E: Find prerequisite chunks for retrieval

```python
prereq_chunks = [
    c for c in chunks
    if c.get("chunk_type") == "prerequisites"
]

for c in prereq_chunks:
    print(c["module_code"], c["module_title"], c["page_refs"])
```

Use case: answer prerequisite questions more accurately by filtering to `chunk_type == "prerequisites"` before semantic ranking.

## Risks and Limitations

| Risk / limitation | Explanation | Mitigation |
|---|---|---|
| No coordinates | The dataset has page references, but no bounding boxes or exact PDF coordinates. | Cite page numbers, not visual coordinates. Add coordinates in a future extraction pass if highlight-level traceability is required. |
| No images represented | The JSON does not include image segments. | Use rendered PDF pages separately if visual QA is needed. |
| No block/paragraph IDs | Paragraphs and blocks are implicit in text fields. | Use `chunk_type`, `table.rows[].field`, and module fields as the hierarchy. |
| Synthetic tables | Module tables are field-value reconstructions, not necessarily native PDF table extractions. | Treat them as structured normalization of module templates. |
| Empty arrays may mean “not present” | `responsible_persons`, `lecturers`, and literature items are empty because the source apparently did not include those fields. | Do not interpret empty lists as confirmed absence in all external university systems. |
| `language` is inferred | The language is set to `"de"` from document context, not from a module-level source field. | Use confidently for indexing, but document that it is dataset-level metadata. |
| `learning_outcomes.items` may be partial | Some bullet extraction may be imperfect where line breaks split phrases. | Prefer `learning_outcomes.raw_text` for authoritative text. |
| Source typos preserved | Examples include source-level misspellings or punctuation oddities. | Preserve raw source text for citations; optionally add a cleaned display layer. |
| Semester/frequency inconsistency | One module is flagged for a possible semester/frequency inconsistency. | Route flagged modules to manual review before advising students. |
| Grading/weighting absent | `exam.graded`, `exam.weighting`, and `exam.exam_duration` are mostly null. | Do not answer grading or exam-duration questions unless another source is added. |
| Duplicate semantic content | Some specialization modules may share similar content text but are different modules. | Never deduplicate across module codes. |
| JSONL loading | `retrieval_chunks.jsonl` is line-delimited, not a JSON array. | Load one JSON object per line. |

## Validation Checklist

### File-level checks

```text
[ ] All five files exist.
[ ] JSON files parse successfully.
[ ] JSONL parses line by line.
[ ] metadata.module_count == len(modules)
[ ] metadata.table_count == len(tables)
[ ] metadata.chunk_count == len(chunks)
[ ] metadata.page_count == max known source page, or greater.
```

### ID checks

```text
[ ] All module_id values are unique.
[ ] All module_code values are unique where not null.
[ ] All table_id values are unique.
[ ] All chunk_id values are unique.
[ ] Every module table ID in modules[].tables exists in tables.json.
[ ] Every chunk parent_module_id either exists in modules.json or is null for document-level chunks.
[ ] Every table parent_module_id either exists in modules.json or is null for the TOC.
```

### Page checks

```text
[ ] Every module has source_pages.page_start and source_pages.page_end.
[ ] Every chunk has page_start, page_end, and page_refs.
[ ] Every table has page_start and page_end.
[ ] No page reference is less than 1 or greater than document_metadata.page_count.
[ ] Module chunks overlap their parent module source page range.
```

### Content checks

```text
[ ] Every module has module_title.
[ ] Every module has ECTS unless explicitly unavailable.
[ ] Every module has prerequisites text.
[ ] Every module has exam details.
[ ] Every chunk has non-empty text.
[ ] Every module has an overview chunk.
[ ] Every module has prerequisites and exam chunks.
```

### Quality-control checks

```text
[ ] Review quality_control_report.detected_issues.
[ ] Review quality_control_report.assumptions.
[ ] Review quality_control_report.recommended_manual_checks.
[ ] Manually inspect flagged modules.
```

## Developer Recommendations

For a RAG system:

1. **Embed `retrieval_chunks.jsonl`, not `modules.json`.**  
   Chunks are smaller, standalone, and have retrieval metadata.

2. **Use `modules.json` as the authoritative structured fact store.**  
   When a user asks for exact ECTS, exam type, prerequisites, or workload, retrieve the relevant chunk, then verify against `modules.json`.

3. **Use `tables.json` for review and table-style display.**  
   It is especially useful for rebuilding module pages or comparing fields across modules.

4. **Use `quality_control_report.json` to suppress overconfident answers.**  
   If a question touches a flagged module or missing field, answer cautiously.

5. **Always cite page references.**  
   Use `page_refs` from chunks or `source_pages.page_refs` from modules.

6. **Do not invent missing fields.**  
   Nulls and empty arrays are meaningful. In particular, responsible persons, lecturers, literature, grading, weighting, and exam duration are not present as reliable module-level source fields.

## Minimal End-to-End RAG Pattern

```python
# 1. Load chunks and modules.
# 2. Index chunk["text"].
# 3. Store chunk metadata.
# 4. At query time, retrieve chunks.
# 5. Expand to module record if exact facts are needed.
# 6. Generate answer with citation.

def answer_with_trace(retrieved_chunk):
    module = modules_by_id.get(retrieved_chunk.get("parent_module_id"))

    citation_pages = retrieved_chunk.get("page_refs") or []
    citation = {
        "source_file": retrieved_chunk["source_file"],
        "pages": citation_pages,
    }

    return {
        "retrieved_text": retrieved_chunk["text"],
        "module_record": module,
        "citation": citation,
    }
```

Preferred answer path:

```text
query
 → retrieve relevant chunk(s)
 → inspect chunk metadata
 → load parent module from modules.json
 → answer from structured fields when possible
 → cite chunk/module page_refs
 → mention QC caveats if relevant
```

This gives the system both semantic flexibility and citation-grounded precision.
