## TODO

### P1 — ops

- [x] add models for textEmbedder (locally or api)
  - [x] tf-idf baseline
  - [x] sentence bert
  - [x] retrieval-trained bi-encoder
- [x] make class for similarity measures
- [x] make class for selector
- [ ] make framework that
  - [ ] splits data
  - [ ] runs through train with various parameters
    - [ ] saves cached embeddings and similarities for performance
    - [ ] saves similarities for documentation
  - [ ] cumulates and saves final scores in dataframe

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

