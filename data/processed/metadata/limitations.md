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

