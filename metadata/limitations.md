### Main weaknesses or risks for chunking

- The dataset is highly heterogeneous in length (word-count CV 0.70); 65 chunks are below the 30-word soft minimum.
- 84 chunks meet the deterministic multiple-fact heuristic, mainly long legal subsections and numerically dense curriculum rows.
- Repeated context templates create high near-duplicate similarity, especially for semester summaries, PBB allocations, and module-overview records; embedding retrieval should retain metadata filters or reranking.
- Two module naming pairs differ in capitalization/conjunction formatting and are not linked by a shared stored base name.
- The source contains explicit numerical inconsistencies that a QA system must not silently reconcile.


| Concept                                      | Chunk IDs                                | Observed discrepancy                                                                                  |
| -------------------------------------------- | ---------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Profile-building area in semester 6          | PO25CL-PLAN-S06-SUM, PO25CL-PLAN-S06-PBB | The semester summary states “davon 1 LP im PBB”; the dedicated profile-building-area row states 6 LP. |
| Abschlussarbeit und Forschungskolloquium SWS | PO25CL-APP-R07-M16, PO25CL-PLAN-S06-M02  | The appendix overview states 2 SWS; the study-plan module header states 4 SWS.                        |




#### Dataset summary

- **Total records (chunks):** 201  
- **Active chunks:** 201  
- **Excluded records:** 0  
- **Unique chunk IDs:** 201  
- **Duplicate chunk IDs:** 0



#### Chunk length statistics

- **Mean words:** 50.72  
- **Median words:** 41  
- **Min/Max words:** 8 / 204  
- **Std. dev (words):** 35.28  
- **10th/90th percentile (words):** 18.0 / 92.0  
- **Mean tokens:** 62.42  
- **Median tokens:** 53  
- **Min/Max tokens:** 10 / 233  
- **Std. dev (tokens):** 40.24  
- **10th/90th percentile (tokens):** 25.0 / 108.0



#### Coverage

- **Pages covered:** 26 (no pages without active chunks)  
- **Chunks covering multiple pages:** 18



#### Quality checks

- **Empty chunks:** 0  
- **Chunks over hard size limit:** 0  
- **Possible mid-sentence splits:** 4  
- **Chunks missing required metadata:** 0  
- **Exact duplicate chunk groups:** 0  
- **Near-duplicate chunk groups:** 13  
- **Source order gaps:** 0  
- **Source order duplicates:** 0



#### Readiness

- **Label:** ready_with_minor_issues  
- **Main reasons:**  
  - All 201 records parse and are active  
  - All IDs are unique and source_order is sequential 1-201  
  - No missing required metadata  
  - No chunk exceeds 220 words or the hard 350-word/500-token limit  
  - Minor normalization, naming-variant, template-similarity, and source-discrepancy issues remain



#### Limitation:

Evaluation and coverage metrics are specific to this dataset and do **not** generalize to unseen documents. The mapping and statistics are likely to be reliable for documents highly similar to those included here (e.g., other versions or variants of the same source), but their validity for substantially different data is not guaranteed.



question grouping before data splitting:

> Questions sharing the same non-empty gold evidence set were assigned to the same split to reduce dependence between evaluation partitions. This constitutes a conservative splitting strategy, as the retrieval representations themselves were frozen and the complete chunk corpus remained available in all partitions. A consequence is increased split-level variance: large evidence groups are evaluated entirely within one partition, so differences in group difficulty can affect validation–test comparability.

> The analysis indicates that this effect was non-negligible. After restricting evaluation to single-gold questions, the validation–test gap remained substantial, but test contained a larger proportion of questions belonging to difficult evidence groups. Thus, part of the observed drop reflects the composition induced by group-aware splitting rather than differences in zero-gold or multi-gold prevalence alone.

