## TODO

### P1 — ops

- [x] add models for textEmbedder (locally or api)
  - [x] tf-idf baseline
  - [x] sentence bert
  - [x] retrieval-trained bi-encoder
- [x] make class for similarity measures
- [x] make class for selector
- [x] compute embeddings
- [x] compute similarity matrices
- [x] split data
- [x] make framework that
  - [x] runs through selection with various parameters
  - [x] cumulates and saves final scores in dataframe
- [ ] do selector testing
  - [x] top k
  - [x] threshold
  - [x] top k absolute threshold
  - [ ] top k relative threshold

### P1 — optional data

- [ ] add hard negatives and unanswerable questions
- [ ] Add relevance grades and primary/supporting evidence distinctions.

### P2 —  maintainability and reproducibility

- [x] Expand the README.
- [ ] Add source checksum and dataset build metadata.
- [ ] Version preprocessing and evaluation configurations.
- [ ] Document embedding rendering and retrieval settings.
- [ ] Add per-intent and per-alias evaluation reports.
- [ ] Add regression tests for every previously detected data issue.

---

