
| File               | Contains                                                                                                                                                                                                                      | Description / Role                                                                                   | Main                                                            |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| `qSet_PO.jsonl`    | File with 720 questions in jsonl format, first 600 created with chatgpt 5.6 sol with 2.5 hours of thinktime, checked and adapted manually in about 3 hour, last 120 created with with 1 hour of thinktime, all non-answerable | provides the questions for the QA dataset                                                            | unique identifier: question_id, source identifier: source_pages |
| PO_25_chunks.jsonl | File with 201 chunks including metadata created from PO_25_CL.pdf (raw data) using deterministic rules (s.u.)                                                                                                                 | provides the chunks for the QA dataset. inconsistent glyphs in PO25CL-GEN-C01-P04-A03 were replaceds | unique identifier: chunk_id                                     |




## Attachment: Chunking Algorithm Rules (English)

This document specifies the rules for the deterministic chunking algorithm used to segment the source document. The following steps and constraints must be followed in order to reproduce the chunking result.

### 1. Visual Order and Normalization

- Process the document in its visual reading order.
- Normalize page numbers, repeated headers/footers, and hyphenation at line breaks.



### 2. Structural Segmentation

- Divide the document into: Title page, Table of contents, General section, Program-specific appendix, and Exemplar course plan.



### 3. Inclusion/Exclusion

- Exclude the table of contents from active retrieval chunks; only store it as a structural index.



### 4. General Section Chunking

- Use each numbered paragraph as a primary candidate for a chunk.
- Paragraphs without numbered subsections are stored as single, complete chunks.
- Always keep introductions and directly related lists together as one chunk.
- Short paragraphs with pre-defined anaphoric trigger phrases are merged with the immediately preceding paragraph within the same section.
- Never join content across different paragraphs into one chunk.



### 5. Program-Specific Appendix

- Treat each standard key-value line as its own chunk.
- For the table row "Art und Inhalt der Module und der Prüfungen", create exactly one chunk per visible module row.
- Assign the “Praktikum” table row at the top of page 24 to the program-specific appendix.



### 6. Exemplar Course Plan

- Store the status note and the abbreviation legend as individual chunks.
- Store each semester header together with its summary row as a `semester_summary` chunk.
- Begin a new module block at every visually emphasized module row.
- Attach all following event and exam rows to the current module block, until a new module, specialization section, or semester start is encountered.
- Merge module blocks that continue across page boundaries.
- Where modules have [1/2] and [2/2] blocks in different semesters, store separately but link under a common base name.
- Store specialization (Profilbildungsbereich) rows as separate, semester-linked chunks.



### 7. Chunk Size Constraints

- Target chunk size: soft range of 80–220 words.
- Independent structural units (e.g. table headers, legends) may be under 30 words.
- Hard upper limit: 350 words or 500 tokens.
- If a chunk exceeds the maximum:
  - First, split at numbered paragraph boundaries.
  - Next, split at complete list items.
  - Lastly, split at complete sentences.
- Never split in the middle of a sentence, list item, table row, or module block.



### 8. Overlap and Repetition Rules

- Do not use general text overlap.
- If a list must be split, repeat the introductory sentence at the beginning of the next part.
- If a running text paragraph must be split, repeat the first full sentence of the split-off part as a marked context line.



### 9. Metadata and Context

- Store chapter, paragraph title, paragraph number, table-area, study program, semester, and module name as metadata fields.
- Add paragraph and table context headers to the beginning of `chunk_text` for standardization.
- Store document title and page numbers primarily as metadata.



### 10. Identification and Ordering

- Assign a deterministic, position-based chunk ID to each chunk.
- Maintain a global, sequential `source_order` for all chunks.



### 11. Redundancy and Layering

- Do not delete repeated information; distinguish it using `source_layer`, `content_type`, and source position metadata.

These rules must be strictly followed to ensure reproducible and consistent chunking of the source document.