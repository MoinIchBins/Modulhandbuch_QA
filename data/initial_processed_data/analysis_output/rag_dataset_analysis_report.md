# RAG Dataset Analysis Report

## 1. Dataset overview

Source file: `modulhandbuch.pdf`

| Metric | Value |
|---|---:|
| document_title | Modulhandbuch BA Computerlinguistik (integrativ) |
| institution | Heinrich-Heine-Universität Düsseldorf |
| faculty | Philosophische Fakultät |
| language | de |
| document_date | 30.09.2025 |
| version | Vorläufige Lesefassung - Stand 30.09.2025 |
| page_count_metadata | 35 |
| page_count_effective | 35 |
| pages_processed_count | 35 |
| pages_with_uncertain_extraction_count | 0 |
| module_count | 16 |
| chunk_count | 163 |
| table_count | 17 |
| program_count | 1 |
| degree_level_count | 1 |
| module_group_count | 4 |
| recommended_semester_count | 13 |
| section_type_count | 2 |
| chunk_type_count | 13 |
| high_priority_chunk_count | 64 |
| normal_priority_chunk_count | 99 |
| low_priority_chunk_count | 0 |
| modules_without_chunks | 0 |
| tables_without_rows | 0 |
| tables_without_columns | 0 |

## 2. Main size statistics

This section summarizes modules, retrieval chunks, tables, pages, programs, module groups, semesters, section types, and retrieval priorities.

| Metric | Value |
|---|---:|
| document_title | Modulhandbuch BA Computerlinguistik (integrativ) |
| institution | Heinrich-Heine-Universität Düsseldorf |
| faculty | Philosophische Fakultät |
| language | de |
| document_date | 30.09.2025 |
| version | Vorläufige Lesefassung - Stand 30.09.2025 |
| page_count_metadata | 35 |
| page_count_effective | 35 |
| pages_processed_count | 35 |
| pages_with_uncertain_extraction_count | 0 |
| module_count | 16 |
| chunk_count | 163 |
| table_count | 17 |
| program_count | 1 |
| degree_level_count | 1 |
| module_group_count | 4 |
| recommended_semester_count | 13 |
| section_type_count | 2 |
| chunk_type_count | 13 |
| high_priority_chunk_count | 64 |
| normal_priority_chunk_count | 99 |
| low_priority_chunk_count | 0 |
| modules_without_chunks | 0 |
| tables_without_rows | 0 |
| tables_without_columns | 0 |

## 3. Chunk length analysis

| metric | count | mean | median | min | max | std | p05 | p10 | p25 | p75 | p90 | p95 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| chunk_characters | 163 | 598.4417177914111 | 488.0 | 217.0 | 4325.0 | 460.0429810590771 | 233.1 | 244.2 | 408.0 | 603.0 | 1169.2000000000005 | 1434.2 |
| chunk_words | 163 | 64.1963190184049 | 51.0 | 21.0 | 532.0 | 53.20515371116283 | 24.0 | 26.0 | 42.0 | 66.5 | 119.20000000000005 | 157.30000000000004 |
| chunk_approx_tokens | 163 | 83.91411042944786 | 67.0 | 28.0 | 692.0 | 69.16007543543199 | 32.0 | 34.0 | 55.0 | 87.0 | 155.00000000000006 | 205.10000000000005 |
| chunk_sentences | 163 | 2.668711656441718 | 1.0 | 1.0 | 20.0 | 2.90179853705906 | 1.0 | 1.0 | 1.0 | 3.0 | 6.0 | 9.0 |

### Longest chunks
| chunk_id | parent_module_id | module_code | section_type | text_word_count | approx_token_count |
|---|---|---|---|---|---|
| document-study-structure-p002-p003 | nan | nan | document | 532 | 692 |
| document-study-goals-p002 | nan | nan | document | 230 | 299 |
| modulhandbuch-po2025-1400-overview | module-1400 | 1400 | module | 202 | 263 |
| modulhandbuch-po2025-4500-overview | module-4500 | 4500 | module | 201 | 262 |
| modulhandbuch-po2025-3000-overview | module-3000 | 3000 | module | 183 | 238 |
| modulhandbuch-po2025-4300-overview | module-4300 | 4300 | module | 164 | 214 |
| modulhandbuch-po2025-2200-overview | module-2200 | 2200 | module | 161 | 210 |
| modulhandbuch-po2025-1300-overview | module-1300 | 1300 | module | 161 | 210 |
| modulhandbuch-po2025-2300-overview | module-2300 | 2300 | module | 158 | 206 |
| modulhandbuch-po2025-4100-overview | module-4100 | 4100 | module | 151 | 197 |

### Shortest chunks
| chunk_id | parent_module_id | module_code | section_type | text_word_count | approx_token_count |
|---|---|---|---|---|---|
| modulhandbuch-po2025-5100-prerequisites | module-5100 | 5100 | module | 21 | 28 |
| modulhandbuch-po2025-2300-prerequisites | module-2300 | 2300 | module | 23 | 30 |
| modulhandbuch-po2025-1300-prerequisites | module-1300 | 1300 | module | 23 | 30 |
| modulhandbuch-po2025-1400-prerequisites | module-1400 | 1400 | module | 23 | 30 |
| modulhandbuch-po2025-3000-notes | module-3000 | 3000 | module | 23 | 30 |
| modulhandbuch-po2025-4300-notes | module-4300 | 4300 | module | 23 | 30 |
| modulhandbuch-po2025-5100-notes | module-5100 | 5100 | module | 23 | 30 |
| modulhandbuch-po2025-2300-notes | module-2300 | 2300 | module | 23 | 30 |
| modulhandbuch-po2025-4500-notes | module-4500 | 4500 | module | 24 | 32 |
| modulhandbuch-po2025-4400-notes | module-4400 | 4400 | module | 24 | 32 |

## 4. Metadata completeness

| entity_type | field | total_records | missing_count | present_count | missing_percent | present_percent |
|---|---|---|---|---|---|---|
| module | responsible_persons | 16 | 16 | 0 | 100.0 | 0.0 |
| module | lecturers | 16 | 16 | 0 | 100.0 | 0.0 |
| module | module_group | 16 | 2 | 14 | 12.5 | 87.5 |
| table | parent_module_id | 17 | 1 | 16 | 5.88235294117647 | 94.11764705882352 |
| chunk | module_title | 163 | 3 | 160 | 1.8404907975460123 | 98.15950920245399 |
| chunk | module_code | 163 | 3 | 160 | 1.8404907975460123 | 98.15950920245399 |
| chunk | parent_module_id | 163 | 3 | 160 | 1.8404907975460123 | 98.15950920245399 |
| module | degree_level | 16 | 0 | 16 | 0.0 | 100.0 |
| module | ects | 16 | 0 | 16 | 0.0 | 100.0 |
| module | duration | 16 | 0 | 16 | 0.0 | 100.0 |
| module | recommended_semester | 16 | 0 | 16 | 0.0 | 100.0 |
| module | program | 16 | 0 | 16 | 0.0 | 100.0 |
| module | module_title | 16 | 0 | 16 | 0.0 | 100.0 |
| module | module_code | 16 | 0 | 16 | 0.0 | 100.0 |
| module | prerequisites | 16 | 0 | 16 | 0.0 | 100.0 |
| module | exam | 16 | 0 | 16 | 0.0 | 100.0 |
| module | frequency | 16 | 0 | 16 | 0.0 | 100.0 |
| module | language | 16 | 0 | 16 | 0.0 | 100.0 |
| module | source_pages | 16 | 0 | 16 | 0.0 | 100.0 |
| chunk | section_type | 163 | 0 | 163 | 0.0 | 100.0 |
| chunk | chunk_type | 163 | 0 | 163 | 0.0 | 100.0 |
| chunk | chunk_id | 163 | 0 | 163 | 0.0 | 100.0 |
| chunk | retrieval_priority | 163 | 0 | 163 | 0.0 | 100.0 |
| chunk | page_refs | 163 | 0 | 163 | 0.0 | 100.0 |
| chunk | text | 163 | 0 | 163 | 0.0 | 100.0 |

## 5. RAG-readiness assessment

| Metric | Value |
|---|---:|
| total_chunks | 163.00 |
| average_chunk_words | 64.20 |
| median_chunk_words | 51.00 |
| average_approx_tokens | 83.91 |
| percent_chunks_under_100_tokens | 80.98 |
| percent_chunks_100_to_800_tokens | 19.02 |
| percent_chunks_over_1200_tokens | 0.00 |
| percent_chunks_with_page_references | 100.00 |
| percent_chunks_with_parent_module_ids | 98.16 |
| percent_chunks_with_keywords | 100.00 |
| percent_chunks_with_standalone_context | 98.16 |
| overview_chunk_count | 1.00 |
| prerequisite_chunk_count | 16.00 |
| exam_chunk_count | 16.00 |
| learning_outcome_chunk_count | 16.00 |
| content_chunk_count | 1.00 |
| modules_without_chunks | 0.00 |
| chunks_with_invalid_parent_module_ids | 0.00 |
| modules_missing_ects | 0.00 |
| modules_missing_exam_information | 0.00 |
| modules_missing_prerequisites | 0.00 |
| tables_with_low_or_medium_confidence | 0.00 |

## 6. Module structure analysis

### Largest modules by total extracted text
| module_id | module_code | module_title | module_total_text_words | chunk_count | ects |
|---|---|---|---|---|---|
| module-4500 | 4500 | Aufbaumodul – Objektorientierte Programmierung | 510 | 10 | 12.0 |
| module-2300 | 2300 | Basismodul – Python-Programmierung | 440 | 10 | 12.0 |
| module-2200 | 2200 | Basismodul – Grundlagen der Computerlinguistik und formale Grammatikbeschreibung | 413 | 10 | 12.0 |
| module-1400 | 1400 | Basiswissen Linguistik – Semantik und Pragmatik | 404 | 10 | 9.0 |
| module-3000 | 3000 | Praktikum & Orientierung | 368 | 10 | 12.0 |
| module-4300 | 4300 | Aufbaumodul – Parsing | 367 | 10 | 6.0 |
| module-4100 | 4100 | Aufbaumodul – Maschinelles Lernen | 319 | 10 | 12.0 |
| module-5100 | 5100 | Vertiefungsmodul – Interdisziplinär | 315 | 10 | 12.0 |
| module-2400 | 2400 | Basismodul – Statistische Methoden in der Computerlinguistik | 312 | 10 | 6.0 |
| module-5300 | 5300 | Vertiefungsmodul – Computerlinguistik 2 | 306 | 10 | 9.0 |

### Module coverage by important section groups
| module_id | module_code | module_title | chunk_count | overview | learning_outcomes | content | prerequisites | exam | workload | literature | tables | course_components |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| module-2100 | 2100 | Basismodul – Mathematische und logische Grundlagen | 10 | 0 | 1 | 0 | 1 | 1 | 7 | 0 | 0 | 0 |
| module-2200 | 2200 | Basismodul – Grundlagen der Computerlinguistik und formale Grammatikbeschreibung | 10 | 1 | 1 | 1 | 1 | 1 | 2 | 0 | 1 | 1 |
| module-2300 | 2300 | Basismodul – Python-Programmierung | 10 | 0 | 1 | 0 | 1 | 1 | 7 | 0 | 0 | 0 |
| module-1300 | 1300 | Basiswissen Linguistik – Morphologie und Syntax | 10 | 0 | 1 | 0 | 1 | 1 | 7 | 0 | 0 | 0 |
| module-1400 | 1400 | Basiswissen Linguistik – Semantik und Pragmatik | 10 | 0 | 1 | 0 | 1 | 1 | 7 | 0 | 0 | 0 |
| module-2400 | 2400 | Basismodul – Statistische Methoden in der Computerlinguistik | 10 | 0 | 1 | 0 | 1 | 1 | 7 | 0 | 0 | 0 |
| module-4100 | 4100 | Aufbaumodul – Maschinelles Lernen | 10 | 0 | 1 | 0 | 1 | 1 | 7 | 0 | 0 | 0 |
| module-4200 | 4200 | Aufbaumodul – Mathematische Linguistik | 10 | 0 | 1 | 0 | 1 | 1 | 7 | 0 | 0 | 0 |
| module-4300 | 4300 | Aufbaumodul – Parsing | 10 | 0 | 1 | 0 | 1 | 1 | 7 | 0 | 0 | 0 |
| module-4400 | 4400 | Aufbaumodul – Logische Programmierung | 10 | 0 | 1 | 0 | 1 | 1 | 7 | 0 | 0 | 0 |
| module-4500 | 4500 | Aufbaumodul – Objektorientierte Programmierung | 10 | 0 | 1 | 0 | 1 | 1 | 7 | 0 | 0 | 0 |
| module-3000 | 3000 | Praktikum & Orientierung | 10 | 0 | 1 | 0 | 1 | 1 | 7 | 0 | 0 | 0 |
| module-5100 | 5100 | Vertiefungsmodul – Interdisziplinär | 10 | 0 | 1 | 0 | 1 | 1 | 7 | 0 | 0 | 0 |
| module-5200 | 5200 | Vertiefungsmodul – Computerlinguistik 1 | 10 | 0 | 1 | 0 | 1 | 1 | 7 | 0 | 0 | 0 |
| module-5300 | 5300 | Vertiefungsmodul – Computerlinguistik 2 | 10 | 0 | 1 | 0 | 1 | 1 | 7 | 0 | 0 | 0 |
| module-5900 | 5900 | Abschlussarbeit und Forschungskolloquium | 10 | 0 | 1 | 0 | 1 | 1 | 7 | 0 | 0 | 0 |

## 7. Table analysis

| table_id | parent_module_id | row_count | column_count | extraction_confidence | has_caption | has_context |
|---|---|---|---|---|---|---|
| table-module-2100 | module-2100 | 21 | 2 | high | True | True |
| table-module-4300 | module-4300 | 21 | 2 | high | True | True |
| table-module-2200 | module-2200 | 21 | 2 | high | True | True |
| table-module-2300 | module-2300 | 21 | 2 | high | True | True |
| table-module-1300 | module-1300 | 21 | 2 | high | True | True |
| table-module-1400 | module-1400 | 21 | 2 | high | True | True |
| table-module-2400 | module-2400 | 21 | 2 | high | True | True |
| table-module-4100 | module-4100 | 21 | 2 | high | True | True |
| table-module-4200 | module-4200 | 21 | 2 | high | True | True |
| table-module-5100 | module-5100 | 21 | 2 | high | True | True |

## 8. Detected warnings and suspicious cases

- Modules with no responsible persons listed: 16.

## 9. Generated CSV files

- `summary_overview.csv`
- `chunk_length_statistics.csv`
- `chunk_diagnostics.csv`
- `module_diagnostics.csv`
- `table_diagnostics.csv`
- `metadata_completeness.csv`
- `section_type_distribution.csv`
- `retrieval_priority_distribution.csv`
- `module_section_coverage.csv`
- `top_keywords.csv`
- `rag_readiness_summary.csv`
- `modules_per_program.csv`
- `modules_per_module_group.csv`
- `modules_per_semester.csv`
- `chunk_type_distribution.csv`
- `token_bucket_distribution.csv`
- `ects_distribution.csv`
- `table_confidence_distribution.csv`

## 10. Generated plot files

- `plots/chunk_word_length_histogram.png`
- `plots/chunk_token_length_histogram.png`
- `plots/chunk_length_by_section_type_boxplot.png`
- `plots/chunks_per_section_type.png`
- `plots/retrieval_priority_distribution.png`
- `plots/modules_per_semester.png`
- `plots/ects_distribution.png`
- `plots/modules_per_module_group.png`
- `plots/chunks_per_module.png`
- `plots/metadata_missingness.png`
- `plots/module_words_vs_chunks.png`
- `plots/ects_vs_module_words.png`
- `plots/table_rows_distribution.png`
- `plots/table_confidence_distribution.png`

## 11. Practical recommendations

- Many chunks are under 100 approximate tokens; consider merging tiny field chunks or adding more module context.
- No responsible persons are listed in module records; keep this as null/empty unless verified from another authoritative source.

## Top keywords preview

| keyword | count |
|---|---|
| Computerlinguistik (integrativ) | 162 |
| Bachelorstudium | 161 |
| 12 ECTS | 80 |
| -keine- | 60 |
| Aufbaumodul | 50 |
| Basismodul | 40 |
| 6 ECTS | 40 |
| ECTS | 32 |
| Studieninhalte | 32 |
| Vertiefungsmodul | 31 |
| 9 ECTS | 30 |
| Seminar | 26 |
| Praktikum | 26 |
| Basiswissen Linguistik | 20 |
| Modulübersicht | 16 |
| Overview | 16 |
| Fachsemester | 16 |
| Semester | 16 |
| Dauer | 16 |
| Häufigkeit | 16 |
