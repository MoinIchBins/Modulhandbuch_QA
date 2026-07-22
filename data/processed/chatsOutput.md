# Semantic Search / Embedding QA Data Readiness Report

## 1. Executive Summary

### Recommendation

**Current decision: No-Go for reliable model evaluation or production-oriented QA development.**

**Conditional Go:** The files are sufficiently well structured to build a disposable retrieval prototype or smoke test, but the current question labels would not produce trustworthy retrieval metrics.

The positive foundation is strong:

* `modules.json` contains 16 well-structured canonical module records.
* `retrieval_chunks.jsonl` contains 163 nonempty, metadata-rich chunks.
* `question_answer_mapping.json` contains 500 questions with valid references to existing chunks.
* All module, chunk, and question IDs are unique.
* Every module-level chunk correctly links to an existing module.
* Every referenced retrieval chunk exists.
* Page provenance is present throughout.
* Chunking is semantic and field-oriented rather than based only on arbitrary token windows.

The main blockers are in the QA supervision and missing source fields:

1. **328 of 500 questions label a generic `table` chunk as relevant**, although that chunk only says that a module table contains various fields and does not contain the requested field values.
2. **At least 17 questions are unsupported by the four supplied files**:

   * 16 questions request English module titles, which are not stored in the supplied module or chunk records.
   * The document-version question requests a date that is absent from the mapped chunk.
   * The exact document-title question is only partially supported.
3. Informal module names such as `MaGruLa`, `MoSy`, `SemPra`, `Stats`, and `OOP` appear throughout the questions but are absent from the retrieval text and keywords.
4. The QA file has no gold answer text, normalized answer value, answer span, answerability flag, relevance grades, or dataset split.
5. There are duplicate and ambiguous questions that would cause train/test leakage.
6. The README refers to table relationships, but no `tables.json` is included in the four-file dataset.
7. Several fields use inconsistent representations of “no value,” such as `null`, `Keine`, `keine`, `-keine-`, and empty arrays.

The data is therefore **retrieval-prototype ready, but not benchmark ready and not end-to-end QA ready**.

---

## 2. File-by-File Analysis

### 2.1 `modules.json`

**Observed purpose**

This is the canonical structured representation of the module handbook. It contains 16 module records and is the best available source for exact module-level facts such as:

* Module code and title
* ECTS
* Workload
* Duration and frequency
* Recommended semester
* Prerequisites
* Learning outcomes
* Content
* Examination information
* Courses or components
* Notes
* Cross-references
* Source pages
* Extraction confidence and notes

The records use stable IDs such as `module-2100`, and module page ranges proceed consistently from pages 4–35. The README also identifies `modules.json` as the canonical structured source.

**Strengths**

* All 16 records have unique `module_id` and `module_code` values.
* Required top-level fields are structurally consistent across modules.
* All modules include source page information.
* All modules have `extraction_confidence: "high"`.
* Cross-references are represented structurally where a prerequisite points to another module.
* Both raw prose and, in some cases, parsed item lists are retained.
* The source’s irregularities are sometimes preserved explicitly in `extraction_notes`. Seven modules have such notes, including source spellings and a semester/frequency inconsistency.

**Weaknesses**

* English module titles are absent.
* `responsible_persons` and `lecturers` are empty for all 16 modules.
* `literature.raw_text` is `null` for all modules.
* `exam_duration`, `graded`, and `weighting` are `null` for all modules.
* `learning_outcomes.items` is empty in 13 of 16 modules.
* `content.items` is empty in 9 of 16 modules.
* Some populated item lists contain incomplete line fragments caused by line wrapping or hyphenation. For example, learning-outcome items can end at `Lernma-` or omit the continuation on the next line.
* Absence is encoded inconsistently:

  * `null`
  * `[]`
  * `"Keine"`
  * `"keine"`
  * `"-keine-"`
* Two modules have `module_group: null`.
* The course-component schema is not fully uniform. Module 5100 introduces `course_codes`, whereas most components use a singular `course_code`.
* Aggregate workload fields do not explicitly distinguish assessment workload from contact and self-study workload. In ten modules, `total_hours` is larger than `contact_hours + self_study_hours`, apparently because examination or other workload is stored only in free text.

**Assessment**

The file is a good canonical base, but it needs normalization and several missing fields before it can support all questions.

---

### 2.2 `retrieval_chunks.jsonl`

**Observed purpose**

This is the embedding and retrieval corpus. It contains one JSON object per line.

There are:

* **163 total chunks**
* **160 module chunks**
* **3 document-level chunks**
* Exactly **10 chunks for each of the 16 modules**

Each module is represented through the same semantic chunk types:

* `overview`
* `semester_ects`
* `workload`
* `course_components`
* `content`
* `learning_outcomes`
* `prerequisites`
* `exam`
* `table`
* `notes`

The three document-level chunks cover:

* Table of contents
* Study goals
* Study structure

**Strengths**

* All 163 `chunk_id` values are unique.
* No chunks have empty text.
* All module-parent references resolve.
* The three chunks with `parent_module_id: null` are intentionally document-level.
* Module metadata repeated in chunks agrees with `modules.json`.
* Every chunk includes page provenance.
* Every chunk has keywords.
* Text is rendered with enough module-level context to be understandable independently.
* Semantic splitting is generally appropriate for field-specific questions.
* `structured_facts` provides a basis for exact field handling.
* `retrieval_priority` distinguishes 64 high-priority and 99 normal-priority chunks.

**Chunk-size profile**

Using words × 1.3 as a simple token estimate:

| Metric                            | Result |
| --------------------------------- | -----: |
| Minimum words                     |     21 |
| Median words                      |     52 |
| Mean words                        |   65.9 |
| Maximum words                     |    530 |
| Approximate median tokens         |     68 |
| Approximate maximum tokens        |    689 |
| Chunks at or below 100 tokens     |  80.4% |
| Chunks between 101 and 300 tokens |  19.0% |
| Chunks between 301 and 800 tokens |   0.6% |

Most chunks are compact and embedding-friendly. The main outlier is the 530-word study-structure chunk, which contains multiple study phases, mobility information, specialization, internship, thesis, and colloquium information.

**Critical table-chunk defect**

Each module’s `table` chunk does not contain the table rows. Instead, it contains a generic description such as:

> The module table contains all field-value information, including ECTS, workload, courses, semester recommendations, content, prerequisites, and examinations.

Its `structured_facts` contains only a `table_id`.

This chunk cannot directly answer questions about group size, ECTS, course numbers, admission requirements, or English titles. Despite that, it is marked as relevant for 328 questions.

This is the most serious retrieval-label issue in the dataset.

**Other weaknesses**

* Repeated boilerplate such as source, program, degree, module title, and ECTS appears in almost every module chunk. Some repetition is useful for independent retrieval, but excessive repetition can make section-level distinctions less clear.
* Informal aliases are not included in text or keywords.
* There is no `chunk_order`, source character span, token count, content hash, or schema version.
* `retrieval_priority` is undocumented.
* `text` mixes source facts and generated headers without distinguishing them.
* There is no separate raw text and embedding-normalized text.
* The document-title and version metadata were not made into retrievable facts.
* The `table` chunks imply that another table dataset exists, but no table file is included here.

**Assessment**

The field-aware chunks are a good foundation. The corpus needs targeted corrections rather than complete rechunking.

---

### 2.3 `question_answer_mapping.json`

**Observed purpose**

This file contains 500 question records. Each record includes:

* `question_id`
* `question_type`
* `target_scope`
* `requested_field`
* `question_text`
* `retrieval_chunk_ids`
* Usually a `target_identifier`
* Occasionally `constraints`

Despite its name, it maps questions to retrieval chunks rather than to answers. The questions cover document, program, module, and course-component scopes.

**Distribution**

| Scope            | Questions |
| ---------------- | --------: |
| Module           |       330 |
| Course component |       150 |
| Program          |        16 |
| Document         |         4 |

The largest intent categories are:

* Credits and workload: 109
* Semester timing: 79
* Course structure: 78
* Assessment: 66
* Module identity: 48

**Strengths**

* All 500 `question_id` values are unique and continuous from `q0001` to `q0500`.
* Every `retrieval_chunk_id` resolves to an existing chunk.
* All 163 chunks are referenced by at least one question.
* Questions contain useful colloquial and paraphrased language.
* Intent, target scope, and requested field are explicitly labeled.
* Module and course-component identifiers are usually present.
* Multiple relevant chunks can be assigned where genuinely necessary.

**Critical weaknesses**

#### A. No answers

There is no:

* `answer_text`
* Normalized answer value
* Answer datatype
* Answer span
* Gold structured field path
* Answerability flag
* Expected citation
* Acceptable answer variants

The file can supervise retrieval only. It cannot evaluate answer correctness, faithfulness, extraction, or generation.

#### B. Overly broad or incorrect positive labels

A generic table chunk is included in **328 of 500 records**, or 65.6% of the dataset.

For example, a question about a course number may map to:

* `course_components`
* `table`

Only the first chunk contains the course number. Treating both as equally relevant weakens Recall@k, MRR, and nDCG as meaningful measures.

#### C. Unsupported English-title questions

There are 16 questions with:

```json
"requested_field": "module_title_english"
```

The mapped `overview` and `table` chunks do not contain English titles, and `modules.json` has no English-title field.

These questions are unanswerable from the four supplied files.

#### D. Unsupported or partially supported document metadata

* The question asking for the version date maps to the table-of-contents chunk, but that chunk does not contain a version date.
* The question asking for the exact document title maps to a chunk containing the program and `PO 2025`, but not the exact handbook title.

#### E. Alias mismatch

At least 145 questions use one of these opaque aliases:

* `MaGruLa`
* `MoSy`
* `SemPra`
* `Stats`
* `OOP`

None of these aliases appears in the mapped chunks’ text or keywords.

A further 29 questions use `Machine Learning` for the German canonical title `Maschinelles Lernen`. A multilingual embedding model may handle that case, but the opaque abbreviations require explicit alias resolution.

#### F. Duplicate and ambiguous questions

The audit found:

* 24 groups of identical question text
* 25 excess duplicate records
* 11 duplicates with effectively the same target and label
* 14 cases where identical wording is used for different scopes

A common ambiguous pattern is:

```text
Wie groß sind die Gruppen in MaGruLa ungefähr?
```

This wording is assigned once to the whole module and once specifically to component `a`. The user text does not distinguish those interpretations.

#### G. Truncated target title

All 30 questions for module 2200 use the shortened target title:

```text
Basismodul – Grundlagen der Computerlinguistik und formale
```

The canonical title in `modules.json` is:

```text
Basismodul – Grundlagen der Computerlinguistik und formale Grammatikbeschreibung
```

This breaks strict consistency and can complicate entity-resolution evaluation.

#### H. Inconsistent optional fields

Only 10 records contain `constraints`; 490 do not. If answer modes such as `short`, `full`, or `table` are important, the annotation is incomplete. If they are not important, the field should be removed from this dataset layer.

#### I. Narrow component coverage

Course-component questions generally target only the first component, usually component `a`. The dataset therefore does not test retrieval reliably across all seminars, exercises, tutorials, and later components.

**Assessment**

This file is the primary blocker. It needs to be converted from a loose question-to-chunk mapping into a controlled retrieval and answer-evaluation dataset.

---

### 2.4 `readme.md`

**Observed purpose**

The README is an 866-byte table describing three data artifacts and their general relationships. It correctly identifies `modules.json` as canonical and `retrieval_chunks.jsonl` as the retrieval corpus.

**Problems**

* It does not document itself as the fourth file.
* It says the QA mapping has no relationships, although `retrieval_chunk_ids` directly reference the retrieval corpus.
* It refers to `tables.parent_module_id` and module table IDs, but no `tables.json` is included.
* It has no field-level schema.
* It does not document null conventions.
* It does not explain chunk construction.
* It does not explain how keywords or `retrieval_priority` should be used.
* It has no validation or reproducibility commands.
* It does not distinguish retrieval labels from answer labels.
* It provides no evaluation methodology or split policy.
* It does not disclose known unsupported questions.

**Assessment**

The README is insufficient for another developer to reproduce, validate, train, or evaluate a QA system.

---

## 3. Cross-File Relationships

The intended data flow is:

```text
modulhandbuch.pdf
        │
        ├── structured extraction ──> modules.json
        │                                │
        │                                └── module_id
        │                                      │
        └── semantic rendering ─────> retrieval_chunks.jsonl
                                         │
                                         └── chunk_id
                                               │
                                               └── question_answer_mapping.json
                                                    retrieval_chunk_ids
```

### Confirmed relationships

1. `modules.module_id` → `retrieval_chunks.parent_module_id`

   * Valid for all 160 module chunks.
   * Three document chunks correctly use `null`.

2. `question_answer_mapping.retrieval_chunk_ids` → `retrieval_chunks.chunk_id`

   * All 1,145 individual references resolve.
   * No dangling references were found.

3. Module metadata copied into chunks

   * Module code, title, ECTS, program, degree, group, and semester information agree with the canonical module records.

4. `modules.tables[]` → presumed table records

   * The IDs are present in modules.
   * Retrieval table chunks also contain table IDs.
   * No table-record file is included, so this relationship cannot be resolved within the supplied set.

### Important conceptual separation

* `modules.json` should remain the **canonical fact store**.
* `retrieval_chunks.jsonl` should be a **rendered retrieval view**.
* The QA file should be an **evaluation and supervision layer**, not another source of facts.
* The README should describe how each derived file is regenerated from the canonical data.

---

## 4. Data Readiness Assessment

### Embedding retrieval corpus

**Status: Mostly ready after targeted correction**

The semantic chunks are compact, self-contained, and have strong provenance. They are suitable for embedding once:

* Aliases are injected.
* Generic table chunks are removed or replaced.
* The long study-structure chunk is split.
* Embedding text is normalized separately from raw text.
* Missing document metadata and English titles are restored.

### Query corpus

**Status: Partially ready**

The questions provide useful paraphrases and intent labels. However:

* Several questions are unsupported.
* Many aliases cannot be resolved.
* Component coverage is narrow.
* Duplicates and templated patterns are substantial.

### Retrieval labels

**Status: Not ready**

A relevant-chunk label must mean that the chunk actually contains evidence needed to answer the question. The current table-chunk labeling violates that requirement in most affected records.

### End-to-end QA labels

**Status: Missing**

No gold answers or evidence spans exist.

### Reliable evaluation

**Status: Not supported**

Without cleaned positive labels, grouped splits, gold answers, and answerability annotations, model scores would be misleading.

---

## 5. Prerequisites Met vs. Missing

| Prerequisite                      | Status     | Evidence and consequence                                                 |
| --------------------------------- | ---------- | ------------------------------------------------------------------------ |
| Canonical entity IDs              | Met        | Unique module IDs and codes exist.                                       |
| Unique retrieval chunk IDs        | Met        | All 163 chunk IDs are unique.                                            |
| Valid cross-file joins            | Met        | All parent and QA chunk references resolve.                              |
| Nonempty retrieval text           | Met        | No empty chunks were found.                                              |
| Source/page provenance            | Met        | All chunks and modules contain page references.                          |
| Semantic chunking                 | Met        | Ten consistent field-oriented chunks per module.                         |
| Embedding-sized text              | Met        | Median approximately 68 tokens; maximum approximately 689.               |
| Structured metadata for filtering | Met        | Module code, title, group, ECTS, program, and chunk type are present.    |
| Canonical structured facts        | Mostly met | Core module facts exist, but some fields and normalizations are missing. |
| Alias/entity-resolution data      | Missing    | Important query aliases are absent from chunks and canonical records.    |
| Complete question answerability   | Not met    | English titles and document version are unsupported.                     |
| Accurate gold retrieval labels    | Not met    | 328 questions include generic table chunks that lack requested evidence. |
| Gold answer values or text        | Missing    | The QA file contains no answers.                                         |
| Gold evidence spans               | Missing    | Only chunk IDs are provided.                                             |
| Negative or hard-negative labels  | Missing    | No explicit nonrelevant candidates.                                      |
| Relevance grades                  | Missing    | Every listed chunk is implicitly treated equally.                        |
| Train/validation/test splits      | Missing    | No split field or split manifest.                                        |
| Leakage controls                  | Missing    | Duplicate and template-related questions are ungrouped.                  |
| Unanswerable questions            | Missing    | No negative or abstention set.                                           |
| Dataset/schema versioning         | Missing    | No schema version, build ID, source hash, or extraction timestamp.       |
| Reproducible preprocessing        | Missing    | README contains no pipeline commands or configuration.                   |
| Evaluation methodology            | Missing    | No metric definitions or relevance policy.                               |
| End-to-end QA evaluation          | Missing    | Cannot measure answer accuracy or groundedness.                          |

---

## 6. Data Quality Issues

### Severity 1: Blocking

1. **Generic table chunks are incorrectly labeled as relevant**

   * Affects 328 questions.
   * Gold labels must be regenerated from evidence-containing chunks.

2. **Gold answers are absent**

   * Blocks end-to-end QA evaluation.

3. **Aliases are absent**

   * Opaque aliases make many questions unretrievable without memorization or external alias logic.

4. **Unsupported questions are present**

   * At minimum, English-title and document-version questions need new source fields or removal.

5. **No leakage-safe split**

   * Duplicate and template-related questions could appear across train and test sets.

### Severity 2: High impact

6. **Question duplicates and scope ambiguity**

   * Identical wording maps to different targets.

7. **Module 2200 title truncation**

   * Thirty target identifiers disagree with the canonical title.

8. **Missing table dataset**

   * The schema refers to table records that are not part of the supplied set.

9. **Incomplete component coverage**

   * Mostly component `a` is evaluated.

10. **No answerability or abstention labels**

    * The system cannot be tested on unsupported questions.

### Severity 3: Quality and maintainability

11. **Inconsistent null/absence conventions**
12. **Broken bullet-item segmentation**
13. **Source hyphenation and line wrapping**
14. **All people and literature fields empty**
15. **Undocumented retrieval priority**
16. **No raw-versus-normalized text separation**
17. **No schema or pipeline versions**
18. **Repeated boilerplate in every embedding text**
19. **No exact source span offsets**
20. **No distinction between source anomalies and extraction errors beyond free-text notes**

### Data leakage risks

The questions appear strongly template-generated:

* The same 30-question structure is repeated across modules.
* Exact question wording repeats.
* Questions differing only by module name are highly similar.
* Multiple questions map to the same chunks.
* Duplicate paraphrases exist for program-level questions.

A random row-level split would allow the model to see nearly identical query templates and the same modules during training and testing. Such a split would substantially overestimate generalization.

---

## 7. Required Preprocessing

### 7.1 Establish a canonical source schema

Treat `modules.json` as canonical, then add:

* English title
* Aliases
* Normalized absence values
* Structured examination fields
* Structured semester/frequency fields
* Assessment workload or unallocated workload
* Schema version
* Source document ID and version
* Source checksum

Do not hand-edit retrieval chunks independently. Regenerate them from the canonical records.

### 7.2 Restore or remove table dependencies

Choose one of two designs:

**Preferred:** Restore `tables.json`, validate every table ID, and render evidence-containing table chunks from actual rows.

**Simpler:** Remove table references and generic table chunks, since `modules.json` already contains most canonical facts.

A table chunk must contain the actual relevant row values before it can be labeled as evidence.

### 7.3 Add alias normalization

Create a controlled alias map for every module:

```json
{
  "module_id": "module-2100",
  "official_title": "Basismodul – Mathematische und logische Grundlagen",
  "aliases": [
    "MaGruLa",
    "Mathematische Grundlagen",
    "Mathe und Logik"
  ]
}
```

Normalize aliases using:

* Unicode normalization
* Lowercasing
* Whitespace collapse
* Punctuation normalization
* German umlaut handling where appropriate
* Optional abbreviation expansion

Aliases should be available to both the query entity resolver and the embedding representation.

### 7.4 Create raw and embedding text separately

Preserve exact extracted text:

```json
"text_raw": "..."
```

Create a cleaned retrieval rendering:

```json
"text_embedding": "..."
```

Safe normalization for the embedding copy includes:

* Joining line-wrapped words
* Removing page headers and repeated boilerplate
* Normalizing whitespace
* Preserving numbers, course codes, ECTS, and examination numbers
* Adding section labels and aliases
* Retaining source text unchanged elsewhere for auditability

Source typos should not silently be changed in `text_raw`.

### 7.5 Improve chunking

Keep the existing field-oriented module chunks, with these changes:

* Remove or replace generic table chunks.
* Split the 530-word study-structure chunk into:

  * Study phases
  * Mobility semester
  * Specialization
  * Internship
  * Thesis and colloquium
* Consider splitting unusually long learning-outcome lists into coherent subchunks.
* Add stable `chunk_order`.
* Add token and word counts during preprocessing.

Arbitrary overlapping token chunks are not necessary for most module fields.

### 7.6 Regenerate retrieval labels

For each question, label only chunks that contain sufficient answer evidence.

Recommended structure:

* `primary_gold_chunk_ids`: smallest sufficient evidence
* `supporting_gold_chunk_ids`: useful but not sufficient alone
* `relevance_grade`: 0, 1, or 2

Generic overview chunks should not automatically be positive merely because they identify the correct module.

### 7.7 Add gold answers

For every question, add:

* Answer datatype
* Canonical normalized value
* Display text
* Acceptable variants
* Evidence chunk IDs
* Evidence field path or source span
* Answerability

Examples:

```json
"gold_answer": {
  "type": "integer",
  "value": 12,
  "unit": "ECTS",
  "display_text": "12 ECTS-Leistungspunkte"
}
```

For narrative questions:

```json
"gold_answer": {
  "type": "text",
  "reference_answer": "...",
  "required_facts": [
    "...",
    "..."
  ]
}
```

### 7.8 Clean the question set

* Remove true duplicate records.
* Rewrite identical module-level and component-level questions to make scope explicit.
* Correct module 2200’s title.
* Add questions for components beyond `a`.
* Add code-based, official-title, alias-based, and descriptive entity references.
* Add realistic misspellings separately and label them as such.
* Add unanswerable questions.
* Add cross-module comparison questions only after multi-document evaluation is designed.

### 7.9 Create leakage-safe splits

Do not split randomly by question row.

Recommended evaluation layers:

1. **Paraphrase split**

   * Group by module, requested field, and underlying answer.
   * Keep paraphrases together.

2. **Template split**

   * Store a `template_group_id`.
   * Keep questions generated from the same template in one split.

3. **Held-out-module test**

   * Reserve several complete modules for testing generalization.

4. **Alias challenge set**

   * Evaluate unseen aliases or surface forms separately.

5. **Unanswerable set**

   * Evaluate abstention and unsupported-query handling.

For only 16 modules, use a fixed split manifest or grouped cross-validation rather than claiming a large independent test set.

### 7.10 Add automated validation

The preprocessing pipeline should fail when:

* IDs are duplicated.
* References are unresolved.
* A gold evidence chunk lacks the answer.
* A requested field is unavailable.
* Official module metadata disagrees across files.
* A question has no gold answer.
* Duplicates cross split boundaries.
* A module alias maps to multiple modules without explicit disambiguation.

---

## 8. Recommended Target Schema

A normalized multi-file design is preferable to one oversized JSON document.

### `documents.json`

```json
{
  "document_id": "modulhandbuch-ba-cl-po2025",
  "source_file": "modulhandbuch.pdf",
  "title": "Modulhandbuch BA Computerlinguistik (integrativ) PO 2025",
  "program": "Computerlinguistik (integrativ)",
  "degree_level": "Bachelorstudium",
  "exam_regulation": "PO 2025",
  "version_date": "2025-09-30",
  "language": "de",
  "page_count": 35,
  "source_sha256": "...",
  "schema_version": "2.0"
}
```

### `modules.json`

```json
{
  "module_id": "module-2100",
  "document_id": "modulhandbuch-ba-cl-po2025",
  "module_code": "2100",
  "titles": {
    "official_de": "Basismodul – Mathematische und logische Grundlagen",
    "normalized_de": "basismodul mathematische und logische grundlagen",
    "official_en": "Basis module – mathematical and logical foundations",
    "aliases": ["MaGruLa"]
  },
  "module_group": "Basismodul",
  "ects": 12,
  "workload": {
    "total_hours": 360,
    "contact_hours": 120,
    "self_study_hours": 120,
    "assessment_hours": 120,
    "unallocated_hours": 0
  },
  "prerequisites": {
    "formal": [],
    "recommended_module_ids": [],
    "raw_text": "Formal: Keine\nInhaltlich: Keine"
  },
  "source": {
    "page_start": 4,
    "page_end": 5
  },
  "raw_fields": {},
  "validation_warnings": []
}
```

### `retrieval_chunks.jsonl`

```json
{
  "chunk_id": "modulhandbuch-po2025-2100-workload",
  "document_id": "modulhandbuch-ba-cl-po2025",
  "parent_module_id": "module-2100",
  "chunk_type": "workload",
  "section_title": "Workload",
  "chunk_order": 3,
  "text_raw": "...",
  "text_embedding": "Modul 2100, MaGruLa, Basismodul ... Gesamtworkload: 360 Stunden ...",
  "structured_facts": {
    "total_hours": 360,
    "contact_hours": 120,
    "self_study_hours": 120,
    "assessment_hours": 120
  },
  "source": {
    "pages": [4, 5],
    "field_names": ["Workload", "Kontaktzeit", "Selbststudium"]
  },
  "word_count": 58,
  "token_count": 76,
  "content_hash": "...",
  "schema_version": "2.0"
}
```

### `qa_examples.jsonl`

```json
{
  "question_id": "q0024",
  "question_text": "Wie viele Punkte bekomme ich für MaGruLa?",
  "language": "de",
  "question_type": "credits_workload",
  "target": {
    "scope": "module",
    "module_id": "module-2100",
    "requested_field": "ects"
  },
  "gold_answer": {
    "type": "integer",
    "value": 12,
    "unit": "ECTS",
    "display_text": "12 ECTS-Leistungspunkte"
  },
  "gold_evidence": [
    {
      "chunk_id": "modulhandbuch-po2025-2100-overview",
      "relevance_grade": 2,
      "field_path": "structured_facts.ects"
    }
  ],
  "answerable": true,
  "entity_surface_form": "MaGruLa",
  "template_group_id": "module-ects-informal-v1",
  "paraphrase_group_id": "module-2100-ects",
  "difficulty": "alias",
  "split": "test"
}
```

The current `question_answer_mapping.json` should be renamed to something like `question_retrieval_labels.json` until actual answers are added.

---

## 9. README Improvements

The README should contain at least the following sections.

### Dataset description

* Source handbook and program
* Regulation and document version
* Language
* Number of pages, modules, chunks, and QA examples
* Intended use and non-intended use

### File inventory

For every file:

* Format
* Record count
* Canonical versus derived status
* Primary key
* Foreign keys
* Regeneration source

The missing or optional status of `tables.json` must be clarified.

### Schema documentation

Document:

* All top-level and nested fields
* Types
* Required versus optional fields
* Null conventions
* Enumerations
* ID naming conventions
* Course-component special cases

### Processing pipeline

Describe:

```text
PDF → extraction → canonical modules → normalization →
retrieval rendering → QA annotation → validation → splits → embeddings
```

### Chunking methodology

Include:

* Why semantic section chunks were chosen
* Which headers are added
* Whether keywords are embedded
* How aliases are injected
* How long sections are split
* Whether chunks overlap

### Assumptions

Examples:

* Page numbers refer to PDF pages rather than printed page labels.
* Source spelling is preserved in raw text.
* `null` differs from “not applicable.”
* Empty people/literature fields may mean absent source data rather than extraction failure.

### Evaluation methodology

Define:

* What counts as relevant evidence
* Primary versus supporting chunks
* Recall@k, MRR, nDCG
* Answer exact match or normalized value accuracy
* Narrative-answer scoring
* Citation or groundedness checks
* Abstention evaluation
* Per-intent and per-alias slices

### Embedding pipeline

Document:

* Model name and version
* Input rendering
* Text normalization
* Distance metric
* Vector normalization
* Index type
* Metadata filters
* Top-k
* Reranking
* Index rebuild procedure

### Reproducibility

Provide commands for:

* Validating data
* Regenerating chunks
* Building embeddings
* Creating splits
* Running evaluation
* Producing reports

Record:

* Python and package versions
* Random seed
* Source checksum
* Dataset build ID
* Configuration files

### Known limitations

At minimum:

* Small number of modules
* Template-generated questions
* Alias dependency
* Sparse component coverage
* Missing English-title data in the supplied files
* No current gold answers
* Source typos and line-wrap artifacts
* Empty people and literature fields
* Potential source-level inconsistencies

---

## 10. Recommended Baseline Architecture

A reliable baseline should combine dense retrieval with deterministic structured answering.

### Offline indexing

1. Validate canonical data.
2. Resolve aliases and add them to entity metadata.
3. Generate cleaned field-aware chunks.
4. Embed a rendering containing:

   * Official module title
   * Aliases
   * Module code
   * Section title
   * Section-specific text
5. Store vectors together with:

   * `module_id`
   * `chunk_type`
   * Program
   * Degree
   * Source pages
6. Build a vector index.
7. Optionally build a lexical BM25 index for codes, aliases, examination numbers, and exact terminology.

### Query processing

1. Normalize the query.
2. Detect explicit module codes.
3. Resolve aliases and official titles to `module_id`.
4. Classify or infer the requested field.
5. Apply a module metadata filter when entity resolution is confident.
6. Retrieve top-k dense candidates.
7. Optionally fuse lexical and dense results.
8. Rerank the top candidates with a query–passage relevance model.
9. Reject results below a calibrated confidence threshold.

### Answer layer

Use two paths:

**Structured path**

For ECTS, workload, semester, course code, group size, prerequisites, and examination type:

* Retrieve or resolve the module.
* Read the value from canonical structured data.
* Cite the matching evidence chunk.

**Narrative path**

For content, learning outcomes, study goals, and study structure:

* Retrieve evidence chunks.
* Generate a concise answer limited to retrieved evidence.
* Return page citations.
* Abstain when evidence is insufficient.

This design avoids asking a language model to infer exact numerical values from loosely related prose.

### Baseline evaluation

Retrieval:

* Recall@1, @3, and @5
* MRR
* nDCG when relevance grades are used
* Entity-resolution accuracy
* Field-intent accuracy

Answering:

* Exact or normalized value accuracy for structured fields
* Token F1 or required-fact coverage for narrative answers
* Citation accuracy
* Unsupported-answer rate
* Abstention precision and recall

Report results separately for:

* Official titles
* Module codes
* Aliases
* Cross-language names
* Exact numeric questions
* Narrative questions
* Course-component questions
* Held-out modules
* Unanswerable questions

---

## 11. Prioritized Next Steps

### P0 — Must be completed before model evaluation

* [ ] Decide whether to restore `tables.json` or remove unresolved table dependencies.
* [ ] Replace generic table chunks with actual table evidence or remove them.
* [ ] Regenerate all question-to-chunk labels using minimal sufficient evidence.
* [ ] Add English module titles or remove the 16 English-title questions.
* [ ] Add exact document title and version metadata.
* [ ] Add a populated module-alias map.
* [ ] Correct all 30 truncated module-2200 target titles.
* [ ] Remove true duplicate QA records.
* [ ] Rewrite same-text module/component questions so scope is explicit.
* [ ] Add gold answers and answerability labels.
* [ ] Create grouped, leakage-safe train/validation/test splits.

### P1 — Required for a credible baseline

* [ ] Normalize null and “none” representations.
* [ ] Create separate raw and embedding-cleaned text.
* [ ] Repair item-list segmentation.
* [ ] Split the long study-structure chunk.
* [ ] Add chunk order, token count, content hash, and schema version.
* [ ] Expand questions to later course components.
* [ ] Add hard negatives and unanswerable questions.
* [ ] Add relevance grades and primary/supporting evidence distinctions.
* [ ] Implement automated cross-file validation.

### P2 — Required for maintainability and reproducibility

* [ ] Expand the README.
* [ ] Add source checksum and dataset build metadata.
* [ ] Version preprocessing and evaluation configurations.
* [ ] Document embedding rendering and retrieval settings.
* [ ] Add per-intent and per-alias evaluation reports.
* [ ] Preserve source anomalies in raw text while providing normalized retrieval text.
* [ ] Add regression tests for every previously detected data issue.

---

## 12. Final Go / No-Go Recommendation

### Retrieval prototype

**Conditional Go**

A simple embedding index can be built from the existing non-table semantic chunks to verify that the basic retrieval flow works. Results from such a prototype should be treated as exploratory only.

### Retrieval benchmark

**No-Go**

The current gold labels are not sufficiently precise. The generic table-chunk positives, unsupported questions, alias mismatch, and duplicate leakage would make reported retrieval metrics unreliable.

### End-to-end QA model

**No-Go**

Gold answers, evidence spans, answerability labels, and a proper evaluation split are missing.

### Production system

**No-Go**

The data needs P0 and P1 preprocessing, validation, alias resolution, abstention behavior, and reproducible evaluation before production-oriented development begins.

The correct sequence is:

```text
Fix canonical schema
→ restore missing facts
→ regenerate evidence chunks
→ repair QA annotations
→ create leakage-safe splits
→ validate
→ build baseline retriever
→ evaluate retrieval
→ add structured/narrative answer layer
```
