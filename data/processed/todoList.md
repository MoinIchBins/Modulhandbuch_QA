
## 11. Prioritized Next Steps



### P0 — Must be completed before model evaluation

- [x] Decide whether to restore `tables.json` or remove unresolved table dependencies.
- [x] Replace generic table chunks with actual table evidence or remove them.
- [ ] Regenerate all question-to-chunk labels using minimal sufficient evidence.
- [x] Add English module titles or remove the 16 English-title questions.
- [ ] Add exact document title and version metadata.
- [ ] Add a populated module-alias map.
- [ ] Correct all 30 truncated module-2200 target titles.
- [ ] Remove true duplicate QA records.
- [ ] Rewrite same-text module/component questions so scope is explicit.
- [ ] Add gold answers and answerability labels.
- [ ] Create grouped, leakage-safe train/validation/test splits.



### P1 — Required for a credible baseline

- [ ] Normalize null and “none” representations.
- [ ] Create separate raw and embedding-cleaned text.
- [ ] Repair item-list segmentation.
- [ ] Split the long study-structure chunk.
- [ ] Add chunk order, token count, content hash, and schema version.
- [ ] Expand questions to later course components.
- [ ] Add hard negatives and unanswerable questions.
- [ ] Add relevance grades and primary/supporting evidence distinctions.
- [ ] Implement automated cross-file validation.



### P2 — Required for maintainability and reproducibility

- [ ] Expand the README.
- [ ] Add source checksum and dataset build metadata.
- [ ] Version preprocessing and evaluation configurations.
- [ ] Document embedding rendering and retrieval settings.
- [ ] Add per-intent and per-alias evaluation reports.
- [ ] Preserve source anomalies in raw text while providing normalized retrieval text.
- [ ] Add regression tests for every previously detected data issue.

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