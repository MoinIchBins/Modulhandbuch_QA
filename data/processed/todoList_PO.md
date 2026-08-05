
## TODO



### P0 — DataSet

- [ ] change questions to only answer PO
- [ ] segment PO into chunks 
- [ ] create question to chunk mapping

### P1 — Evaluate Data

- [ ] Normalize null and “none” representations.
- [ ] add hard negatives and unanswerable questions
- [ ] Add chunk order, token count, content hash, and schema version.
- [ ] Add relevance grades and primary/supporting evidence distinctions.

### P2 — Required for maintainability and reproducibility

- [ ] Expand the README.
- [ ] Add source checksum and dataset build metadata.
- [ ] Version preprocessing and evaluation configurations.
- [ ] Document embedding rendering and retrieval settings.
- [ ] Add per-intent and per-alias evaluation reports.
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