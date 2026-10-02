# Agent Handover Protocol — Hausarbeit: Evidence Retrieval for QA over a German Examination Regulation

## 0. Mission for the next agent

You are taking over a nearly completed empirical research project whose remaining goal is to write a short ACL-style seminar paper.

Your job is **not** to redesign the experiment. Your job is to understand the frozen experiment, verify any still-unfrozen details from the project artifacts, finish the remaining diagnostic work, and turn the project into a scientifically careful paper.

The project studies **evidence retrieval / chunk-set prediction for question answering over a German examination regulation**. It does **not** evaluate generated answers or end-to-end QA accuracy.

The central experimental question is:

> How well can similarity scores produced by different text representations identify the retrieval chunk or chunk set required to answer a question, and how does the chunk-selection / abstention rule affect performance?

The experiment has two equally important axes:

1. **Text representation**
   - TF-IDF
   - Sentence-BERT
   - multilingual E5

2. **Selector / abstention rule**
   - top-k
   - absolute threshold
   - top-k + threshold
   - relative margin

The model-selection loop is closed. Do not change the final model based on test performance.

---

# Audit status — second-pass environment review

This handover was re-audited against the later project artifacts and source code, not only against planning notes.

The second pass specifically checked:

- the final paper handover and ACL skeleton;
- the chunk-quality report;
- development and validation result files;
- the actual text-embedding implementation;
- the actual selector implementation;
- the similarity-matrix and ranking-analysis scripts;
- the baseline protocol;
- the unified manual-error-review tooling;
- the filled bibliography file.

Where the source code resolves an earlier “verify later” note, the verified implementation is recorded below. Where the available environment still does not contain a frozen output, the item remains explicitly marked unresolved.

A key rule for the writing agent is:

> **Do not silently convert a planning intention into an executed-method claim.**

For example, the codebase contains support for dot-product/Euclidean similarities and a `softmax_cumulative` selector, but the frozen paper comparison documented in the result artifacts is based on **cosine similarity** and the four selector families **top-k, threshold, top-k + threshold, and relative margin**. Do not add unused capabilities to the experimental story simply because they exist in code.

---

# 1. Authority hierarchy

Use this hierarchy whenever project notes disagree:

1. **Frozen experiment artifacts and evaluation outputs**
2. **Final ACL paper skeleton and later handover/audit notes**
3. **Final dataset/chunk quality reports and scripts**
4. **Earlier roadmap / planning notes**
5. **Conversation recollections or informal explanations**

Do not copy an older number simply because it appears in an earlier note if a later artifact corrects it.

Important known example:
- earlier working notes referred to a six-question Zugangsprüfung group;
- later split inspection showed the underlying group actually contains **eight test questions (Q0153–Q0160)** with the same gold evidence set, while six appeared in the then-current wrong-chunk review file.
- Therefore, verify the final per-question outcomes before stating a final failure count.

---

# 2. Paper/assignment constraints

The paper should be:

- written in **English**;
- written in **LaTeX**;
- formatted with the **ACL style**;
- cited with **BibTeX**;
- approximately **4–8 pages**, with roughly 5+ pages being a practical target.

Recommended structure:

1. Introduction
2. Motivation and Related Work
3. Methodology
4. Experimental Setup and Pipeline
5. Results and Evaluation
6. Conclusion
7. Limitations

The course/instructor values **evaluation, reflection, and explaining why methods worked or failed**, not just obtaining a high score. The lower test score is therefore not something to hide or “repair”; it is an important object of analysis.

Recommended working title already present in the ACL skeleton:

> **Comparing Text Representations and Chunk Selection with Abstention for Evidence Retrieval in German Examination Regulations**

---

# 3. Scientific scope and terminology

## 3.1 Prediction target

For each question, the system predicts a **set of retrieval chunk IDs**.

- Answerable questions have a non-empty intended gold evidence set.
- Unanswerable / zero-gold questions have `[]`.
- The system may predict one or more chunks or abstain by returning `[]`.

The principal reported score is therefore **mean question-level evidence-selection F1**.

Never write:

> “The QA model achieves 49% accuracy.”

Use wording such as:

> “The frozen retrieval configuration achieved a mean question-level evidence-selection F1 of 0.491 on the held-out test split.”

## 3.2 Preferred terminology

Use consistently:

- development
- validation
- test
- retrieval chunk
- gold evidence set
- predicted evidence set
- question-level F1
- abstention
- zero-gold question / unanswerable question
- representation
- selector

Do **not** call the development split “training”: the pretrained encoders were not trained on it. It was used for selector/hyperparameter development.

---

# 4. Source document and domain

The source document is the German examination regulation below. The paper handover cautions not to over-identify the institution unless necessary; use the full legal title where academically useful, but do not add unnecessary institutional detail.


> *Ordnung für die Prüfung in Studiengängen der Philosophischen Fakultät der Heinrich-Heine-Universität Düsseldorf mit dem Abschluss Bachelor of Arts vom 20.01.2026.*

The relevant domain is Bachelor Computerlinguistik.

Source layers used in the project include:

- general examination regulations (primarily pages 1–22);
- the Computerlinguistik-specific appendix;
- the exemplary/non-binding Computerlinguistik study plan;
- program-specific information such as modules, examinations, internship/practical-training rules, and thesis-related information.

Important semantic distinctions that were enforced during dataset construction:

- Studiengang vs. Modul vs. Lehrveranstaltung;
- Studienleistung (SL) vs. Modulprüfung (MP);
- LP vs. SWS;
- general faculty-wide rules vs. Computerlinguistik-specific rules;
- binding regulation vs. the **exemplary, non-binding** study plan;
- “keine Angabe” must not be interpreted as “none”;
- page 27 belongs to another degree program and was excluded from Computerlinguistik inference.

These distinctions matter because many retrieval errors can arise from semantically neighboring but legally different passages.

---

# 5. Retrieval chunks

## 5.1 Frozen chunk dataset and integrity

The final active retrieval collection contains exactly:

- **201 JSONL records**
- **201 active retrieval chunks**
- **201 unique chunk IDs**
- **0 invalid/unparseable records**
- **0 excluded/non-retrieval records**
- **0 duplicate chunk IDs**
- **0 empty `chunk_text` values**
- **0 context-header-only chunks**
- source order exactly **1–201**, unique and gap-free
- **100% required core and conditional metadata completeness**

The formal quality-audit readiness label is:

**`ready_with_minor_issues`**

This is important: the chunk collection passed the production-readiness gate and should not be portrayed as a broken preprocessing artifact.

## 5.2 Size and coverage statistics

Verified quality-report statistics:

- total active text: **10,194 words**
- approximate spaCy tokens: **12,547**
- mean chunk length: **50.72 words**
- median: **41 words**
- minimum: **8 words**
- maximum: **204 words**
- word-count standard deviation: **35.28**
- word-count CV: **0.70**
- mean approximate tokens: **62.42**
- median approximate tokens: **53**
- approximate-token range: **10–233**
- source coverage: **26 pages**
- pages without active chunks: **none**
- **18 chunks (8.96%)** span two pages
- **0 chunks** span three or more pages
- **133 chunks (66.17%)** belong to the general-regulation layer, accounting for **8,091 words**
- **136 chunks (67.66%)** fall within 30–220 words
- **65 chunks (32.34%)** are below the 30-word soft minimum
- none exceeds the 220-word soft target or the 350-word/500-token hard limits used by the quality audit

The token values above are **linguistic approximate tokens from a spaCy 3.8.11 blank German tokenizer**, not E5/SBERT model-token counts. Do not confuse them with embedding-model tokenization.

## 5.3 Chunk structure and IDs

The chunk IDs encode traceability back to source structure.

Examples:

`PO25CL-GEN-C04-P31-A01`

`PO25CL-PLAN-S04-M02`

Chunking principles to explain scientifically:

- chunks are the retrieval/evidence units and therefore define the prediction target;
- general regulation text preserves paragraph/subsection structure;
- tables, appendix information, and study-plan material are represented as coherent semantic units such as fields, module blocks, allocations, or semester summaries;
- standardized context headers make short/terse values independently interpretable;
- metadata preserves source layer, content type, page references, and relevant structural context;
- source-level repeated information is retained rather than collapsed when it belongs to different document layers.

A particularly important point is that terse source values such as `keine Angabe` or bare profile-area allocations are only independently retrievable because contextual headers were embedded with them. Do not imply that the raw terse cell value alone formed the retrieval text.

## 5.4 Duplicate/overlap audit

The quality report found:

- **0 exact duplicate chunk texts**
- **13 near-duplicate groups at similarity ≥0.80**

Most near-duplicates are **expected template repetition**, especially:

- semester summaries;
- profile-area/PBB allocations;
- parallel module-overview records.

Two general-regulation pairs were flagged as more suspicious because of similar wording in separate structural units.

Do not report “13 duplicate chunks.” They are near-duplicate **groups**, mostly benign/expected.

The report also found **84 chunks** meeting a deterministic “multiple-fact” heuristic, mainly long legal subsections and numerically dense curriculum rows. This is a review signal, not proof that 84 chunks violate the chunking strategy.

## 5.5 Source inconsistencies and minor data-quality issues

The frozen data intentionally preserves source wording. The quality audit records two explicit numerical discrepancies that must **not** be silently reconciled:

1. semester-6 PBB: **1 vs. 6 LP**
2. `Abschlussarbeit und Forschungskolloquium`: **2 vs. 4 SWS** across source layers

Other minor audit findings:

- one private-use bullet glyph (``) in `PO25CL-GEN-C01-P04-A03`;
- four prose chunks whose final punctuation should be checked against source layout if ever preprocessing a future version;
- two module-name pairs differing by capitalization/conjunction formatting and not linked through a stored canonical/base name;
- high expected template similarity in some appendix/study-plan structures.

A benign structural exception explicitly documented by the quality report is that **§27(1)–(2) is intentionally merged because the second subsection is anaphoric**.

These issues support limitations/future-work discussion but did not invalidate the frozen collection.

## 5.6 Known risks relevant to retrieval

Potential retrieval risks supported by the audit include:

- heterogeneous chunk lengths;
- short atomic chunks versus long legal subsections;
- neighboring/near-duplicate regulatory clauses;
- repeated contextual templates;
- source inconsistencies;
- formatting/name variants.

Possible future improvements suggested by the quality audit include:

- content-type-aware retrieval/reranking;
- controlled module aliases/canonical IDs;
- warnings for source-level numeric conflicts;
- preserving the standardized context headers;
- hybrid/reranking approaches.

These are **future-work ideas**, not methods used by the frozen experiment unless separately verified.

Do not attribute a specific number of test errors to these risks unless the finished manual error audit supports that count.

---

# 6. Question dataset construction

The final dataset contains **720 questions**.

Frozen aggregate counts:

- **600 answerable**
- **120 zero-gold / intentionally unanswerable**

The question side was created specifically for this project and underwent several iterations and audits.

## 6.1 Earlier design principles

The project initially planned broad coverage across:

- program entry;
- module identity;
- module components;
- exemplary semester;
- workload/credits;
- examination format/number;
- internship/practical training;
- study planning;
- discovery;
- comparison;
- aggregation;
- Bachelor thesis;
- general examination rules;
- terminology/document clarification.

Questions were intended to sound like realistic student questions, use German domain terminology where useful, and stay within the source document.

## 6.2 Important later revision

The question dataset was later simplified/audited so that questions should generally ask for **one information need** rather than complicated multi-part comparisons.

The later quality rules emphasized:

- exactly preserve question IDs;
- avoid comparisons requiring multiple independent answers;
- avoid multiple properties in one question;
- avoid calculations/rankings unless intentionally retained;
- ensure strong coverage of general regulation pages 1–22;
- prevent pages 24–26 / the study plan from dominating;
- maintain the distinction between module, semester, LP, SWS, SL, MP, etc.

When writing the paper, describe the **final audited dataset**, not the abandoned early target percentages as though they were the final distribution.

## 6.3 Zero-gold questions

Zero-gold questions are intentionally unanswerable from the supplied regulation.

Their purpose is to test whether a retriever can **abstain** rather than always returning the nearest chunk.

They should be framed as plausible questions that might tempt a retrieval model into selecting a related regulation passage—not arbitrary nonsense/out-of-domain prompts.

This is why abstention is scientifically central to the project.

---

# 7. Gold evidence mapping

Each question is mapped to:

`all_required_chunk_ids`

Interpret this as the **minimal intended complete evidence set** required to answer the question.

Gold mapping records also contained richer annotation information during construction/audit, including fields such as mapping status, evidence strength, confidence, primary chunk IDs, and supporting chunk IDs.

Important evaluation field:

`all_required_chunk_ids`

## 7.1 Zero-gold convention

Unanswerable questions use:

`all_required_chunk_ids = []`

## 7.2 Gold mapping quality control

Mappings were independently audited with rules such as:

- at least one selected chunk must actually contain the central answer;
- required conditions, definitions, exceptions, and reference chunks must not be missing;
- irrelevant/redundant chunks should be removed;
- all answer components must be supported;
- chunk IDs must exist;
- the selected set should be minimal but complete;
- roles/sets should be internally consistent.

## 7.3 Critical limitation

Do **not** claim the gold mapping exhaustively enumerates every semantically valid alternative chunk.

Manual test inspection found cases where a non-gold predicted chunk appeared capable of fully supporting the answer.

Therefore write:

> “The mapping specifies a minimal intended evidence set.”

not:

> “The mapping contains every valid evidence chunk.”

This distinction is important when discussing false positives and apparent retrieval errors.


## 7.4 Construction-workflow transparency

The final paper must describe the dataset-construction workflow honestly.

The project artifacts clearly show that chunking, question construction, gold mapping, quality checks, and later error review were supported by scripts and extensive structured auditing. The available handover explicitly warns that, **if language models were used to assist question generation, chunking, mapping, or auditing, their role must be disclosed rather than presenting the dataset as purely unaided manual annotation**.

The current environment does **not** provide one single frozen provenance record that is sufficient to state the exact division of labor between human work, scripts, and language-model assistance for every construction stage. Therefore:

- do not invent a “fully manual” annotation story;
- do not invent an “LLM-generated” story either;
- inspect the actual construction prompts/scripts/history before writing the final provenance paragraph;
- distinguish generation/assistance from later human or independent audit where applicable;
- state only what the project record supports.

This is a **remaining provenance-verification task**, not a reason to reopen the dataset.


---

# 8. Gold-set size distribution

Verified in the ACL skeleton:

| Split | N | 0 gold | 1 gold | 2 gold |
|---|---:|---:|---:|---:|
| Development | 432 | 74 | 340 | 18 |
| Validation | 144 | 24 | 116 | 4 |
| Test | 144 | 22 | 112 | 10 |
| **Total** | **720** | **120** | **568** | **32** |

There are no reported questions with more than two gold chunks in this frozen summary.

This matters because the final system uses `top_k = 1`.

For a genuine two-gold question, a top-1 system can never produce an exact full-set match. If it retrieves one of the two correct chunks, its maximum set F1 is:

- precision = 1
- recall = 1/2
- F1 = 2/3 ≈ 0.667

This is a **structural limitation of the frozen final selector**, not necessarily a representation error.

There are **10 such two-gold questions in test**.

---

# 9. Leakage-aware data split

Final split sizes:

- development: **432**
- validation: **144**
- test: **144**

The split was **not** simple question-random splitting.

Grouping rule:

`same_non_empty_gold_chunk_set`

Questions sharing the same non-empty `all_required_chunk_ids` set were grouped together and assigned to the same split.

Verified split integrity in the later paper skeleton:

- **315 groups**
- largest group: **13 questions**
- all 720 questions appear exactly once
- no group crosses dev/validation/test
- no non-empty gold set is duplicated across different groups
- the 120 zero-gold questions are singleton groups

## 9.1 Why this matters

Purpose:

- reduce leakage between semantically similar/paraphrased questions that require exactly the same evidence.

Trade-off:

- stronger leakage control can create more uneven evidence-group composition across splits;
- some evidence sets may be completely unseen during development/validation and appear only in test.

This split should therefore be described as a stricter test of **evidence-group generalization**, not merely new wording for familiar evidence.

Do not call the test split “unfair.” Use careful language such as:

> “The group-aware split produced split-specific evidence-group composition and therefore a stricter generalization setting.”

---

# 10. Text representations

The project compares one sparse lexical representation and two fixed pretrained dense representations. No representation was fine-tuned on the project dataset.

The actual `TextEmbedder` source now resolves several earlier open implementation questions.

## 10.1 TF-IDF — verified implementation

Implementation:

```python
TfidfVectorizer(
    lowercase=True,
    ngram_range=(1, 3),
)
```

Important consequences:

- lowercasing is explicitly enabled;
- word n-grams of length **1–3** are used;
- the vectorizer is fitted on **chunk texts only** (`vectorizer.fit(chunk_texts)`);
- questions are subsequently transformed into that chunk-derived vocabulary;
- no custom stop-word list, tokenizer/analyzer, `min_df`, `max_df`, or norm is passed in the project code, so those behaviors come from the installed scikit-learn defaults for that version;
- the ACL skeleton records a representation dimensionality of **13,232** for the frozen artifact.

Do **not** say that the TF-IDF vocabulary was fitted jointly on questions and chunks. The source code shows it was fitted on chunks.

Interpretation hypothesis:

TF-IDF performs strongly because the regulation and questions contain highly specific repeated terminology, including module names and legal/administrative expressions. Exact lexical overlap and short multiword phrases can be highly discriminative.

Safe wording:

> “TF-IDF remained competitive, plausibly because the corpus contains highly specific and repeated legal and curricular terminology.”

Do not claim that lexical overlap was quantitatively measured unless an additional analysis actually measured it.

## 10.2 Sentence-BERT — verified implementation

Checkpoint:

`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`

Recorded dimensionality:

**384**

Encoding behavior in the project source:

- `SentenceTransformer(model_name)`
- `batch_size=32` by default
- `convert_to_numpy=True`
- `normalize_embeddings=False`
- no custom query/document prefix for Sentence-BERT
- no custom post-processing; `postprocess()` returns embeddings unchanged

Pooling is whatever the loaded SentenceTransformer checkpoint implements internally; there is no separate custom pooling operation in the supplied embedder code.

Interpretation:

- this is a multilingual semantic sentence representation;
- general semantic proximity can be useful for paraphrases;
- in this regulation many neighboring chunks discuss closely related examination concepts;
- a general semantic embedding can therefore place multiple plausible-but-distinct clauses near each other;
- project ranking analysis found it weaker than TF-IDF and E5 in this setting.

Use:

> “The evaluated Sentence-BERT checkpoint underperformed the other representations in this experimental setting.”

Do not generalize this to Sentence-BERT or legal NLP broadly.

## 10.3 E5 / retrieval bi-encoder — verified implementation

Checkpoint:

`intfloat/multilingual-e5-base`

Recorded dimensionality:

**768**

The source code confirms retrieval-specific prefixes:

- questions: `query: {text}`
- chunks: `passage: {text}`

Encoding behavior:

- same `SentenceTransformer` interface;
- default project batch size **32**;
- `convert_to_numpy=True`;
- `normalize_embeddings=False`;
- no extra post-processing after encoding.

This means normalization is **not** applied by the embedder before storage; cosine similarity later performs the relevant vector-length normalization mathematically.

Interpretation:

- E5 can match semantically equivalent wording beyond exact token overlap;
- its retrieval-oriented training/setup is better aligned with query-to-passage ranking than a generic sentence-similarity representation;
- the query/passage prefixes used in the experiment match the intended E5 retrieval format.

Safe wording:

> “E5’s retrieval-oriented representation provides a plausible methodological advantage for question-to-passage matching, consistent with its stronger observed rankings.”

Do not say that retrieval-oriented training *caused* the observed score difference.

---

# 11. Similarity computation and representation-level ranking analysis

## 11.1 Frozen paper similarity

For each representation:

- all **720 questions** are represented;
- all **201 chunks** are represented;
- cosine similarity is computed for every question–chunk pair.

Matrix dimensions:

**720 × 201**

The frozen paper comparison documented by the selector results uses **cosine similarity**.

The matrix-generation utility in the repository can also compute **dot product** and **Euclidean distance**, but code capability is not evidence that those alternatives belong in the frozen experiment. Do not add dot/Euclidean results to the paper unless authoritative completed/frozen artifacts demonstrate that they were actually part of the experiment.

## 11.2 Ranking-analysis diagnostics

Before/alongside selector tuning, the project analyzed the similarity matrices directly.

The ranking-analysis script computes, among other diagnostics:

- Recall@k
- Hit@k
- All-Gold@k
- MRR
- best/worst/mean gold rank
- best gold and worst gold scores
- best non-gold score
- best-gold and complete-gold margins
- zero-gold top-score distributions
- per-gold-set-size diagnostics
- top-ranked chunk frequencies

The configured `k` values in that analysis are:

**1, 3, 5, 10**

MRR is based on the rank of the **best-ranked gold chunk**.

The ranking tie behavior recorded by the analysis is:

> similarity descending, then original chunk order

The high-level representation ordering from this stage is:

**E5 > TF-IDF > Sentence-BERT**

for this corpus.

These diagnostics are useful for explaining *why* a selector may fail, but the paper’s primary selection metric remains mean question-level evidence-selection F1.

---

# 12. Selector families — verified implementation

The selector source code ranks scores stably with NumPy (`kind="stable"`). For the frozen cosine experiments, higher scores are better.

The codebase contains an additional `softmax_cumulative` selector, but it is **not one of the four selector families in the frozen paper comparison**. Do not add it merely because it exists in the class.

## 12.1 Top-k

Procedure:

1. rank chunks by score;
2. return the first `k`.

Properties:

- cannot abstain by itself;
- output size is exactly `k` when enough chunks exist.

The strongest plain configuration uses `k = 1`.

## 12.2 Absolute threshold

Procedure:

1. rank chunks;
2. retain every chunk satisfying `score >= threshold`.

Properties:

- can return `[]`;
- can return multiple chunks;
- does not impose a top-k cap.

This is why pure thresholding can simultaneously help abstention and hurt precision through over-selection.

## 12.3 Top-k + threshold

Procedure in the source:

1. rank chunks;
2. keep all chunks satisfying the threshold;
3. return only the first `k` threshold-passing chunks.

Therefore it combines:

- absolute confidence filtering;
- abstention;
- rank ordering;
- output-size control.

The frozen final system uses:

- `k = 1`
- E5 threshold = **0.83959**

## 12.4 Relative margin

The exact implementation is now verified.

Let `s_k` be the score at rank `k` and `s_(k+1)` the next score. For higher-is-better similarity:

`relative_margin = (s_k - s_(k+1)) / max(|s_k|, 1e-12)`

The selector returns the top-k chunks **only if**:

`relative_margin >= configured_margin`

Otherwise it abstains and returns `[]`.

For the common `k=1` case, this tests whether the top result is sufficiently separated from the runner-up.

This family is competitive, particularly for E5 and TF-IDF, but does not beat the final E5 absolute-threshold configuration on validation.

---

# 13. How absolute-threshold search regions were constructed

The project used representation-specific search regions because E5, TF-IDF, and Sentence-BERT cosine scores are on different empirical scales.

The methodological note defines, on **development only**:

For an answerable question `q`:

- `G_q` = minimum similarity among all required gold chunks  
  (the **worst required-gold score**)
- `N_q` = maximum similarity among non-gold chunks  
  (the **strongest distractor score**)

For a zero-gold question:

- `Z_q` = maximum similarity among all chunks  
  (the strongest false-positive candidate)

Robust quantiles then define:

- lower bound `L = P10(G)`
- upper bound `U = max(P90(N), P90(Z))`

Recorded diagnostics:

| Representation | P10(G) | P90(N) | P90(Z) | Search region |
|---|---:|---:|---:|---:|
| E5 | 0.8331 | 0.8865 | 0.8695 | **0.8331–0.8865** |
| TF-IDF | 0.0591 | 0.2477 | 0.5162 | **0.0591–0.5162** |
| Sentence-BERT | 0.4740 | 0.7595 | 0.7172 | **0.4740–0.7595** |

Interpretation:

- the lower edge protects complete evidence retrieval on answerable items;
- the upper edge represents the region where the strongest non-gold/zero-gold scores lie;
- the overlap makes the precision/recall/abstention trade-off explicit.

The threshold sweep itself was evaluated on **development**, not validation or test.

Important historical note:

Some older/backward-compatible experiment scripts in the repository contain alternative automatically derived threshold-search logic. Do not infer the final methodology from a generic script default. Use the frozen experiment outputs plus the dedicated threshold-method note when describing the experiment that produced the reported finalists.

---

# 14. Evaluation protocol

Primary model-selection metric:

**mean question-level evidence-selection F1**

Why this is appropriate:

- missing required evidence contributes false negatives;
- unnecessary/wrong evidence contributes false positives;
- both failure types matter when the prediction target is an evidence set;
- averaging per-question F1 prevents large predicted sets on a few questions from dominating the metric in the way a single pooled score can.

Secondary metrics:

- mean question precision
- mean question recall
- exact-match rate
- mean Jaccard
- micro precision/recall/F1/Jaccard
- zero-gold abstention rate
- empty-selection rate
- average selected chunks

## 14.1 Evaluator special cases

The project evaluator treats:

### gold = `[]`, prediction = `[]`
- precision = 1
- recall = 1
- F1 = 1
- Jaccard = 1
- exact match = true

### gold = `[]`, prediction non-empty
- question precision/recall/F1/Jaccard = 0

### gold non-empty, prediction = `[]`
- question precision/recall/F1/Jaccard = 0

### Missing prediction record
A question with **no prediction record at all** is excluded from metric means and counted as unanswered.

This is different from an explicit empty prediction.

Therefore every authoritative result should have **100% prediction-record coverage** before being reported.

The development ranking artifact shows 432/432 predictions and zero unanswered for the leading configurations.

---

# 15. Development/model-selection protocol

Parameter search occurred only on the **development split**.

Ranking criterion:

1. mean question-level F1
2. tie-breaking project notes: exact match
3. then precision
4. then fewer selected chunks

After development selection:

- **five finalists were frozen**
- only those finalists were evaluated on validation
- no post-validation hyperparameter search
- validation winner was frozen
- exactly that system was evaluated once on test

This sequence is crucial to the scientific validity of the paper.

---

# 16. Development results

Authoritative development ranking includes the following key results.

## 16.1 Final development winner

**E5 + top-1 + threshold**

- `top_k = 1`
- threshold = **0.83959**
- mean question F1 = **0.6473765432**
- exact match = **0.6365740741**
- mean precision = **0.6527777778**
- mean recall = **0.6446759259**
- micro F1 = **0.6711772666**
- average selected chunks = **0.8402777778**
- empty-selection rate = **0.1597222222**
- zero-gold abstention = **34/74 = 0.4594594595**

## 16.2 E5 relative margin

`margin = 0.0025`, `top_k = 1`

- F1 = **0.6311728395**
- exact match = **0.6203703704**
- mean precision = **0.6365740741**
- mean recall = **0.6284722222**
- zero-gold abstention = **0.2972972973**

## 16.3 E5 plain top-1

- F1 = **0.6165123457**
- exact match = **0.6041666667**
- mean precision = **0.6226851852**
- mean recall = **0.6134259259**
- cannot abstain: zero-gold abstention = 0

## 16.4 Representation/selector summary

Plain top-1:

- E5 ≈ **0.617**
- TF-IDF ≈ **0.551**
- Sentence-BERT ≈ **0.374**

Best pure threshold:

- E5 ≈ **0.494**
- TF-IDF ≈ **0.487**
- Sentence-BERT ≈ **0.358**

Best top-1 + threshold:

- E5 ≈ **0.647**
- TF-IDF ≈ **0.567**
- Sentence-BERT ≈ **0.399**

Best relative-margin results:

- E5: **0.6312**, margin 0.0025, zero-gold abstention **0.2973**
- TF-IDF: **0.5702**, margin 0.235, zero-gold abstention **0.7703**
- Sentence-BERT: **0.3866**, margin 0.005, zero-gold abstention **0.1351**

Additional exact diagnostics for the strongest pure-threshold rows in `dev_ranking.csv`:

| Representation | Threshold | Q-F1 | Precision | Recall | Avg. chunks | Empty rate | Zero-gold abstention |
|---|---:|---:|---:|---:|---:|---:|---:|
| E5 | 0.866475 | 0.4941 | 0.4578 | 0.6285 | 1.5185 | 0.4468 | 0.8243 |
| TF-IDF | 0.127665 | 0.4866 | 0.4596 | 0.5706 | 1.4190 | 0.2407 | 0.2432 |
| Sentence-BERT | 0.7095375 | 0.3583 | 0.3343 | 0.4421 | 1.2616 | 0.5995 | 0.8919 |

This is useful interpretation: pure thresholding can obtain high abstention on some representations while still performing poorly overall because it has no output-size cap and must balance both answerable retrieval and zero-gold rejection.

Important conclusions:

1. representation choice strongly affects retrieval;
2. selector choice also strongly affects retrieval/abstention;
3. E5 is strongest overall;
4. TF-IDF is surprisingly competitive;
5. Sentence-BERT is clearly weaker in this setting;
6. pure thresholding alone is weaker;
7. adding threshold-based abstention to top-1 provides the strongest development result.

---

# 17. Frozen validation finalists

Five development finalists were frozen before validation:

| Rank | Configuration | Validation F1 |
|---|---|---:|
| 1 | E5 + top-1 + threshold 0.83959 | **0.6111** |
| 2 | E5 + top-1 | **0.5972** |
| 3 | E5 + relative margin 0.0025 | **0.5903** |
| 4 | TF-IDF + top-1 + threshold 0.0999 | **0.5000** |
| 5 | TF-IDF + relative margin 0.235 | **0.4236** |

Winner diagnostics:

- question F1: **0.6111**
- exact match: **0.5972**
- mean precision: **0.6181**
- mean recall: **0.6076**
- micro F1: **0.6475**
- average selected chunks: **0.8333**
- empty-selection rate: **0.1667**
- zero-gold abstention rate: **0.4167**

The development winner remained the validation winner.

Development winner F1: **0.6474**  
Validation winner F1: **0.6111**

Absolute development-to-validation drop:

`0.6474 - 0.6111 ≈ 0.0363`

This modest drop is useful context for the much larger validation-to-test drop, but no uncertainty estimate has been established that would justify calling either difference “within normal standard deviation.”

Therefore the final system was frozen as:

- representation: **E5**
- selector: **top-k + threshold**
- `top_k = 1`
- threshold = **0.83959**

---

# 18. Official held-out test result

The final system was evaluated on the 144-question held-out test split.

Official frozen results:

- questions: **144**
- mean question F1: **0.4907**
- exact match: **0.4861**
- mean precision: **0.4931**
- mean recall: **0.4896**
- micro F1: **0.5041**
- average selected chunks: **0.7917**
- empty-selection rate: **0.2083**
- zero-gold questions: **22**
- correct abstentions: **9**
- zero-gold abstention rate: **0.4091**
- total TP: **62**
- total FP: **52**
- total FN: **70**

This is the official endpoint.

Do not:
- change the threshold;
- change `k`;
- change representation;
- alter chunking;
- redraw the split;
- change evaluator behavior;
- select a new model based on test results.

The paper should analyze the drop rather than tune it away.

Validation F1 ≈ **0.611**
Test F1 ≈ **0.491**

Absolute drop:

`0.6111 - 0.4907 ≈ 0.1204`

This is a meaningful generalization gap and should be discussed.

---

# 19. Baselines

Three baseline families were defined in advance and are **contextual references**, not selector candidates.

## 19.1 Random top-1

- uniformly choose one retrieval chunk for every question
- **100 fixed seeds: 0–99**
- report mean ± standard deviation

## 19.2 Most-frequent development answer

- find the most frequent **non-empty exact gold chunk set** in development
- freeze it once
- return that same set for every validation/test question
- never recompute from validation/test

## 19.3 Always abstain

- predict `[]` for every question

The baseline scripts are in:

`artifacts/baselines/`

The development-derived reference is frozen in:

`artifacts/baselines/dev_reference/most_frequent_answer.json`

The baseline README uses an explicit confirmation gate for held-out test evaluation (`--confirm-test`). Preserve that freeze discipline. The system-comparison utility expects the evaluator JSON of a **single frozen system**, not an entire finalist-summary file.

At the time of the later paper handover, validation baseline outputs existed, while authoritative **test baseline numbers were not yet confirmed in the handover**.

Therefore:

**Do not invent or recover test baseline numbers from memory.**

Check whether `test_v1/` or equivalent authoritative test baseline outputs now exist. If not, run only the already-defined baseline evaluation on test. This is allowed because the baseline definitions were frozen before test and do not participate in model selection.

Final paper should ideally include:

| System | Q-F1 | Precision | Recall | Exact Match | Zero-gold abstention |
|---|---:|---:|---:|---:|---:|
| Random top-1 | verified value | ... | ... | ... | ... |
| Most-frequent development answer | verified value | ... | ... | ... | ... |
| Always abstain | verified value | ... | ... | ... | ... |
| **E5 top-1 + threshold** | **0.491** | **0.493** | **0.490** | **0.486** | **0.409** |

---

# 20. Why the methods behaved as they did

These are **interpretive explanations**, not measured causal facts.

## 20.1 Why TF-IDF is competitive

Plausible reasons:

- the corpus is terminology-heavy;
- legal/administrative expressions are highly discriminative;
- many questions reuse official terminology;
- 1–3 word n-grams capture informative short phrases;
- chunks are relatively focused/self-contained;
- exact lexical matching can distinguish narrowly different clauses.

Safe wording:

> “TF-IDF remained competitive, plausibly because the corpus contains highly specific and repeated legal and curricular terminology.”

## 20.2 Why Sentence-BERT is weaker

Plausible reasons:

- generic semantic similarity may cluster neighboring regulation passages;
- many wrong chunks are topically close to the correct one;
- the task requires precise evidence discrimination rather than only semantic relatedness;
- the chosen lightweight multilingual SBERT model is not specifically optimized for query–passage retrieval.

Safe wording:

> “The evaluated Sentence-BERT checkpoint appears less discriminative between closely related regulatory passages in this setting.”

## 20.3 Why E5 is strongest

Plausible reasons:

- dense semantics handle paraphrases/wording variation;
- retrieval-oriented training is more aligned with query/passage ranking;
- it better separates relevant evidence from semantically related distractors than the generic SBERT representation;
- it preserves advantages over purely lexical matching when wording differs.

Safe wording:

> “E5’s retrieval-oriented representation provides a plausible methodological advantage for question-to-passage matching, consistent with its stronger observed rankings.”

Do not write “E5 is universally better than TF-IDF.”

---

# 21. Error analysis

Error analysis is essential because the test result fell notably below validation.

An automatic prefilter divided non-exact test cases into:

1. `multi_gold_single_prediction`
2. `answerable_but_abstained`
3. `zero_gold_but_retrieved`
4. remaining wrong non-empty cases for manual review

The manual-review tooling later unified the categories.

## 21.1 Final review category vocabulary

- `valid_alternative_evidence`
- `gold_mapping_issue`
- `partial_evidence_only`
- `similar_wrong_chunk`
- `question_wording_or_lexical_issue`
- `near_duplicate_or_neighboring_clause`
- `chunking_issue`
- `source_ambiguity_or_inconsistency`
- `unrelated_retrieval_failure`
- `structural_top1_limitation`
- `threshold_abstention_failure`
- `false_positive_on_unanswerable`
- `needs_second_review`
- `other`

## 21.2 Critical conceptual distinction

`valid_alternative_evidence`:
- prediction fully supports the answer;
- gold may still be defensible;
- evaluation is strict because the alternative chunk is not listed.

`gold_mapping_issue`:
- the gold annotation itself appears wrong, incomplete, or overly restrictive.

Never merge these categories.

## 21.3 Known state of the review

A completed/partially completed earlier manual review covered **31 wrong non-empty cases**.

Later tooling was created to review **all four error groups** in one interface and import previous labels.

The handover did **not** yet establish a final frozen category-count table.

A working note provisionally suggested around **9 valid-alternative-evidence cases**, but explicitly warned not to report that number until labels are cleaned/frozen.

Therefore the next agent must look for the latest:

`manual_review_all_error_groups.csv`

and determine whether all cases are reviewed.

If complete:
- compute category counts and shares;
- verify unclear/second-review cases;
- freeze a final error-analysis table.

If incomplete:
- finish the audit without changing model predictions.

---

# 22. Structural top-1 limitation

This is a major limitation that should appear in Results/Limitations.

There are:

- **32** two-gold questions overall
- **10** two-gold questions in test

Because final `k = 1`, exact match is impossible for those questions when both chunks are genuinely required.

If the predicted chunk is one of the two gold chunks, maximum F1 is about **0.667**.

This partly distinguishes:
- representation/ranking errors
from
- selector-capacity errors.

The paper should explicitly acknowledge that the strongest aggregate development selector has a structural weakness on multi-evidence questions.

Do not retroactively choose `k = 2` after seeing this.

---

# 23. Abstention behavior

Final test system:

- empty-selection rate: **20.83%**
- zero-gold abstention: **9/22 = 40.91%**

Interpretation:

- the threshold creates meaningful abstention behavior;
- but fewer than half of zero-gold test questions are correctly rejected;
- the system also abstains on some answerable questions.

The problem is therefore not merely “too conservative” or “too permissive”; it contains both:
- false abstentions / under-retrieval;
- false-positive retrievals on unanswerable questions.

The error audit should quantify these separately.

---

# 24. Unseen evidence-group / Zugangsprüfung issue

A specific test evidence group is methodologically important.

Gold chunk:

`PO25CL-GEN-C03-P12-A02`

Later split inspection indicates group `G0040` contains **eight test questions Q0153–Q0160** sharing this gold set, and this gold set is absent from development and validation.

Six of those IDs were present in the then-current wrong-chunk manual-review CSV:

- Q0153
- Q0154
- Q0155
- Q0156
- Q0158
- Q0159

Do **not** state that “all six/eight failed” until the final per-question prediction/evaluation file is checked for Q0157 and Q0160.

If verified, this example can illustrate a consequence of the leakage-aware grouping rule:

- no same-evidence leakage;
- but some evidence groups are entirely unseen during development;
- group-specific failures can disproportionately affect the 144-question test split.

Use this as one failure mode, not as an excuse that invalidates the test.

---

# 25. Post-hoc diagnostic score calculation

A later paper handover records a specific **diagnostic/sensitivity calculation** intended to understand the raw validation-to-test drop. It is **not** an alternative official test score.

Official test mean question-level F1:

`0.4907407407 over 144 questions`

This corresponds to a summed question-level F1 of:

`0.4907407407 × 144 = 70.6667`

The working diagnostic assumptions were:

- **9** currently penalized cases are ultimately confirmed as fully valid alternative evidence and treated as F1 = 1;
- **6** zero-F1 Zugangsprüfung cases from the then-reviewed wrong-chunk set are excluded for the sensitivity calculation.

Under those assumptions:

`adjusted sum = 70.6667 + 9 = 79.6667`

`adjusted N = 144 - 6 = 138`

`diagnostic F1 = 79.6667 / 138 ≈ 0.5773`

The corresponding gap to validation would be:

`0.6111 - 0.5773 ≈ 0.0338`

For context, the development-to-validation decrease is approximately **0.0363**.

This calculation can be useful to illustrate how identifiable data/evaluation phenomena could account for a substantial portion of the raw validation-to-test gap. However, the assumptions are **not yet frozen**:

- the final all-error-groups audit must confirm the number of valid-alternative-evidence cases;
- the Zugangsprüfung group is actually an **eight-question test group (Q0153–Q0160)**, while the six cases above are the six then-observed wrong-nonempty cases;
- Q0157 and Q0160 still require outcome verification before any whole-group claim.

Therefore, if included in the paper, label it explicitly as a **post-hoc diagnostic/sensitivity analysis**, state every assumption, and never place 0.5773 in the main test-results table or present it as the system score.

---

# 26. Research questions for the paper

Lock the manuscript around these three RQs.

## RQ1 — Representation

> How do sparse lexical and dense semantic representations differ in their ability to retrieve answer-supporting chunks from a German examination regulation?

Evidence:
- TF-IDF
- Sentence-BERT
- E5
- development/ranking comparison

Conclusion direction:
- E5 strongest
- TF-IDF competitive
- Sentence-BERT weakest in this setting

## RQ2 — Selector and abstention

> How do different chunk-selection and abstention strategies affect evidence-retrieval performance?

Evidence:
- top-k
- threshold
- top-k + threshold
- relative margin
- abstention metrics

Conclusion direction:
- top-1 strong
- pure threshold weaker
- top-1 + threshold strongest overall
- relative margin competitive but not best
- abstention remains imperfect

## RQ3 — Generalization and failure modes

> How well does the selected configuration generalize to the held-out test split, and what explains its remaining errors?

Evidence:
- validation → test drop
- baseline comparison
- manual error categories
- multi-gold structural limitation
- unseen evidence groups
- alternative valid evidence / gold strictness

---

# 27. Core story of the paper

A good one-paragraph conceptual story is:

> We study evidence retrieval for question answering over a German examination regulation. A custom dataset of retrieval chunks, student-oriented questions, and minimal intended gold evidence mappings was constructed and audited. We compare a sparse lexical representation (TF-IDF) with two multilingual dense representations (Sentence-BERT and E5), while separately comparing chunk-selection and abstention strategies. Using a leakage-aware development/validation/test split that keeps questions sharing the same non-empty gold evidence set together, E5 consistently outperforms the other representations and a top-1 + absolute-threshold selector is selected. The frozen system reaches 0.611 question-level F1 on validation and 0.491 on held-out test. Detailed error analysis is required to explain the generalization gap, including imperfect abstention, strict gold mappings/alternative valid evidence, unseen evidence groups, and the structural inability of a top-1 selector to fully retrieve two-chunk evidence sets.

---

# 28. Results presentation plan

Recommended main-paper items:

## Table 1 — Dataset statistics

Include:

- 201 chunks
- 720 questions
- 600 answerable
- 120 zero-gold
- dev/validation/test counts
- 0/1/2-gold distribution

## Figure 1 — Pipeline

Show:

`Source document → chunks/questions/gold → representations → similarity matrices → selector → predicted evidence/abstention → evaluation`

## Figure/Table 2 — Development comparison

Show only representative/best values by representation and selector family, not every sweep point.

## Table 3 — Validation finalists

Five rows with:
- representation
- selector
- parameter
- development F1
- validation F1

## Table 4 — Final test vs baselines

Most important performance table.

## Table 5 — Error analysis

Category counts/shares after the review is frozen.

Optional appendix:
- threshold sweeps
- full development ranking
- full metric tables
- additional examples
- diagnostic subset scores
- uncertainty/bootstrapping if performed

---

# 29. Literature already present

An earlier roadmap said literature research had to start from zero. That is now obsolete: the environment contains a filled BibTeX set with **13 relevant entries**.

The available bibliography currently includes:

1. **Spärck Jones (1972)** — term specificity / IDF
2. **Salton, Wong & Yang (1975)** — vector-space model
3. **Reimers & Gurevych (2019)** — Sentence-BERT
4. **Reimers & Gurevych (2020)** — multilingual sentence embeddings via knowledge distillation
5. **Wang et al. (2022)** — original E5 / weakly supervised contrastive text embeddings
6. **Wang et al. (2024)** — multilingual E5 technical report
7. **Karpukhin et al. (2020)** — Dense Passage Retrieval
8. **Thakur et al. (2021)** — BEIR
9. **Muennighoff et al. (2023)** — MTEB
10. **Rajpurkar, Jia & Liang (2018)** — SQuAD 2.0 / unanswerable questions
11. **Geifman & El-Yaniv (2019)** — SelectiveNet / reject option
12. **Wrzalik & Krechel (2021)** — GerDaLIR, German legal information retrieval
13. **Büttner & Habernal (2024)** — answering lay legal questions in German civil law

The paper does not need to cite all 13. Keep the related-work section focused on the experimental choices.

Recommended literature roles:

- TF-IDF / sparse retrieval: Spärck Jones; Salton et al.
- Sentence-BERT: Reimers & Gurevych 2019
- multilingual semantic encoders: Reimers & Gurevych 2020 if useful
- E5: Wang et al. 2022 and/or 2024 multilingual report
- dense retrieval: DPR
- retrieval evaluation/embedding context: BEIR and/or MTEB
- abstention/unanswerable behavior: SQuAD 2.0 and/or SelectiveNet
- domain context: GerDaLIR and Büttner & Habernal

Before submission, still verify the entries against primary/authoritative publications and ensure capitalization, venue, year, DOI/URL, and ACL/PMLR metadata are correct.

Do not turn Related Work into a broad NLP or legal-NLP survey.

---

# 30. Recommended paper section contents

## 30.1 Introduction

Answer:

- what practical/research problem is addressed?
- what exactly is retrieved?
- why abstention matters?
- what representations/selectors are compared?
- what are the main findings?

State the test result rather than hiding it.

## 30.2 Motivation and Related Work

Cover:

- difficulty of retrieving precise evidence from long structured regulations;
- sparse vs. dense retrieval;
- generic semantic embeddings vs. retrieval-oriented embeddings;
- retrieval as an upstream component of QA;
- unanswerable questions / abstention.

## 30.3 Methodology

Explain concepts:

- TF-IDF
- Sentence-BERT
- E5
- cosine similarity
- top-k
- threshold
- top-k + threshold
- relative margin

Do not turn this section into chronological implementation history.

## 30.4 Experimental Setup

Explain actual executed pipeline:

- source document
- chunking
- question construction
- zero-gold design
- gold mapping
- 720 × 201 similarity matrices
- group-aware split
- development → frozen finalists → validation → frozen winner → test
- baselines
- metrics

## 30.5 Results and Evaluation

Suggested subsections:

1. Representation comparison
2. Selector/abstention comparison
3. Validation/frozen model selection
4. Held-out test
5. Baseline comparison
6. Error analysis
7. Interpretation/limitations

## 30.6 Conclusion

Summarize:

- E5 strongest
- TF-IDF competitive
- Sentence-BERT weaker
- selector design matters
- top-1 + threshold selected
- test generalization is weaker than validation
- failure analysis shows retrieval, abstention, evaluation, and structural issues

---

## 30.7 Practical ACL page budget

For a roughly five-page main paper:

- Introduction: **~0.6 pages**
- Motivation + Related Work: **~0.7**
- Methodology: **~1.0**
- Experimental Setup: **~1.0**
- Results + Evaluation: **~1.5**
- Conclusion + Limitations: **~0.4–0.6**

References are separate.

If space is available, expand **Results/Evaluation and error analysis**, not a general Related Work section.

## 30.8 Writing order

Recommended drafting order:

1. Experimental Setup
2. Methodology
3. tables/figures
4. Results
5. error analysis
6. Limitations
7. Motivation/Related Work
8. Introduction
9. Conclusion
10. Abstract last

## 30.9 What the paper should emphasize

Priority order:

1. **controlled experimental design**
2. **representation and selector as separate experimental axes**
3. **error analysis/generalization gap**
4. **dataset construction and leakage-aware evaluation**

The manuscript should read as an empirical retrieval study, not a chronological programming diary.

## 30.10 Discussion placement and future work

A separate Discussion section is optional. Given the short page limit, interpretation can remain inside Results and Evaluation.

Restrained future work supported by the project limitations includes:

- stronger multi-evidence retrieval rather than a hard top-1 cap;
- BM25/hybrid lexical+dense retrieval;
- reranking;
- content-type-aware retrieval/reranking;
- broader/multiple regulatory documents;
- improved canonicalization/alias handling;
- downstream generated-answer evaluation after retrieval;
- evaluation methods that can accommodate valid alternative evidence more flexibly.

Do **not** add new experiments now merely to make a limitation disappear.

The Conclusion/Summary should answer the three RQs directly rather than simply repeating the Introduction.

---

# 31. Claims that are safe now

Safe:

> “E5 achieved the strongest development and validation performance among the evaluated representations.”

Safe:

> “TF-IDF outperformed the evaluated Sentence-BERT representation on this dataset.”

Safe:

> “The top-1 + threshold selector produced the strongest development and validation configuration.”

Safe:

> “The frozen final system achieved a mean question-level evidence-selection F1 of approximately 0.491 on the held-out test split.”

Safe:

> “The group-aware split prevents questions with the same non-empty gold evidence set from crossing splits.”

Safe:

> “The final top-1 selector cannot produce an exact full-set match for questions that genuinely require two evidence chunks.”

Safe, phrased carefully:

> “A plausible explanation for TF-IDF’s competitiveness is the lexical specificity of the regulation.”

Safe after final manual review confirms it:

> “Some predictions penalized by the chunk-ID gold standard nevertheless contained sufficient alternative evidence.”

---

# 32. Claims to avoid

Avoid:

> “E5 is better than TF-IDF.”

Use:

> “E5 outperformed TF-IDF on the evaluated dataset.”

Avoid:

> “Sentence-BERT cannot distinguish legal text.”

Use:

> “The evaluated Sentence-BERT checkpoint underperformed the other two representations in this experimental setting.”

Avoid:

> “The test split was unfair.”

Use:

> “The group-aware split yielded split-specific evidence-group composition and a stricter evidence-generalization setting.”

Avoid:

> “The system answers 49% of questions correctly.”

The task is retrieval, not generated-answer correctness.

Avoid:

> “The adjusted test F1 is 0.577.”

Unless explicitly described as a verified post-hoc diagnostic under stated assumptions.

Avoid:

> “The drop is within normal standard deviation.”

No such uncertainty estimate is established for the final system unless bootstrapping/replication is actually performed.

Avoid causal overstatement:

> “E5 wins because it was retrieval trained.”

Use:

> “Its retrieval-oriented training objective provides a plausible methodological advantage consistent with the observed results.”

---

# 33. Remaining verification tasks before final prose

The second-pass audit resolved several earlier open items:

### Now verified from source code

- TF-IDF uses `lowercase=True`, `ngram_range=(1,3)`.
- TF-IDF vocabulary is fit on **chunk texts only**.
- Sentence-BERT checkpoint is `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.
- E5 checkpoint is `intfloat/multilingual-e5-base`.
- E5 uses `query:` for questions and `passage:` for chunks.
- neural encoding uses `normalize_embeddings=False`.
- default project embedding batch size is 32.
- relative-margin decision rule and denominator are verified.
- selector ranking is stable.
- the selector class also contains `softmax_cumulative`, but it is outside the frozen four-family paper comparison.
- the similarity utility supports cosine/dot/Euclidean, but the frozen paper result path is cosine.

### Still unresolved / must be checked before manuscript freeze

1. **Authoritative final test evaluation file**
   - confirm all headline test numbers once from the actual JSON/winner summary.

2. **100% test prediction-record coverage**
   - missing record and explicit `[]` have different evaluator semantics.

3. **Final test baselines**
   - locate authoritative test baseline output;
   - if absent, run only the already-frozen baseline definitions.

4. **Final all-error-groups manual audit**
   - locate `manual_review_all_error_groups.csv`;
   - ensure every case is reviewed or explicitly marked for second review;
   - clean `valid_alternative_evidence` vs `gold_mapping_issue`;
   - freeze counts and representative examples.

5. **Zugangsprüfung group outcomes**
   - verify Q0153–Q0160 individually;
   - the group contains eight test questions, while six were observed in the wrong-nonempty review file.

6. **Complete final hyperparameter grids**
   - extract them from the actual frozen experiment runs/results rather than a generic/older script default;
   - put full grids in appendix if useful.

7. **Construction provenance**
   - verify and document the actual roles of scripts, human review, and any language-model assistance in chunk/question/gold construction and audit.

8. **Uncertainty analysis**
   - determine whether bootstrapping or another uncertainty estimate was ever completed;
   - if not, make no significance/standard-deviation claims for the deterministic final system.

9. **Bibliography**
   - the filled BibTeX set exists, but verify every cited entry against the primary publication before submission.

10. **Material software versions**
    - record Python/library versions that materially affect reproduction (at minimum libraries whose defaults/encoders are relied on);
    - do not include a giant environment dump unless required.

Use artifact-driven values, not memory or planning notes.

---

# 34. Reproducibility/source paths visible in project notes

Useful paths mentioned repeatedly:

```text
data/frozen/PO_25_CL_chunks.jsonl
data/frozen/qa_mapping_merged.jsonl
data/frozen/split/development_question_ids.json
data/frozen/split/validation_question_ids.json
data/frozen/split/test_question_ids.json
data/frozen/split/gold_with_split.jsonl
```

Similarity matrices:

```text
artifacts/similarity_matrices/retrieval_bi_encoder/
artifacts/similarity_matrices/tf_idf/
artifacts/similarity_matrices/sentence_bert/
```

Selector outputs:

```text
artifacts/experiments/
```

Final test:

```text
artifacts/experiments/test/test_winner/
```

Final prediction/evaluation filenames mentioned:

```text
e5_top_k_threshold_top_k_1_threshold_0.83959_predictions.jsonl
e5_top_k_threshold_top_k_1_threshold_0.83959_evaluation.json
```

Error analysis:

```text
artifacts/experiments/test/test_winner/error_analysis/
```

Baselines:

```text
artifacts/baselines/
```

Important paper-side artifacts in the environment include:

- `Paper_Handover_Protocol_Final_Phase.md`
- `Paper_ACL_Skeleton.tex`
- `Paper Writing Roadmap.txt`
- `dev_ranking.csv`
- `PO_25_CL_chunk_quality_report.md`
- `retrieval_model_comparison_report.md`
- `threshold_region_method.md`
- `howToCite_filled.txt`

---


## 34.1 Source-code artifacts that now matter for reproducibility

In addition to frozen data/results, inspect/retain:

- `text_embedder.py` — exact TF-IDF and dense-encoder preprocessing/encoding behavior
- `compute_similarity_matrices.py` — available similarity functions
- `analyze_similarity_matrices.py` — ranking diagnostics and tie behavior
- `chunk_selector_relative_margin.py` / final selector implementation — exact selector logic
- `manual_error_review_all_groups.py` — final error taxonomy/review workflow
- baseline README/scripts — seed policy and test-confirmation discipline

Do not cite internal filenames in the prose unless useful; they are mainly the evidence base for accurate method descriptions.

## 34.2 Reproducibility checklist for the paper/appendix

Record:

- exact E5 checkpoint;
- exact Sentence-BERT checkpoint;
- exact TF-IDF construction;
- E5 query/passage prefixes;
- whether embeddings were normalized before similarity;
- cosine similarity;
- matrix dimensions;
- selector equations/rules;
- hyperparameter search ranges/grids;
- final threshold;
- development/validation/test sizes;
- gold-set grouping rule;
- baseline seed policy;
- primary ranking criterion and tie-breaks;
- evaluator special cases;
- materially relevant Python/library versions.

Do not report `.npy` storage mechanics or a full package dump unless the assignment requires them.

## 34.3 Suggested paper directory

```text
paper/
├── main.tex
├── references.bib
├── acl.sty
├── acl_natbib.bst
├── sections/
│   ├── introduction.tex
│   ├── related_work.tex
│   ├── methodology.tex
│   ├── experimental_setup.tex
│   ├── results.tex
│   ├── conclusion.tex
│   └── limitations.tex
├── figures/
│   ├── pipeline.pdf
│   ├── development_comparison.pdf
│   └── test_baselines.pdf
├── tables/
│   ├── dataset_stats.tex
│   ├── validation_results.tex
│   ├── test_results.tex
│   └── error_analysis.tex
└── generate_tables.py
```

This structure is a recommendation, not part of the scientific method.

---

# 35. Recommended next-agent workflow

## Phase A — freeze remaining evidence

1. Locate authoritative final test evaluator JSON/winner summary and re-check headline numbers.
2. Confirm 144/144 prediction-record coverage.
3. Locate final test baseline outputs.
4. If absent, run only the already-defined frozen test baselines.
5. Locate latest all-error-groups review CSV.
6. Finish/clean manual categories if needed.
7. Freeze error counts, percentages, and 3–5 representative cases.
8. Verify Q0153–Q0160 outcomes.
9. Extract the actual final development hyperparameter grids.
10. Verify construction provenance (human/script/language-model assistance).
11. Record materially relevant software versions.

## Phase B — build paper evidence

9. Generate dataset-statistics table.
10. Generate development-comparison table/figure.
11. Generate five-row validation-finalist table.
12. Generate final test-vs-baselines table.
13. Generate error-analysis table.
14. Finalize pipeline figure.
15. Verify bibliography.

## Phase C — write in this order

16. Experimental Setup
17. Methodology
18. Results
19. Error Analysis
20. Limitations
21. Motivation/Related Work
22. Introduction
23. Conclusion
24. Abstract last

## Phase D — final audit

25. Compile ACL LaTeX.
26. Check figure/table readability.
27. Verify every numerical value against the authoritative artifact.
28. Verify every literature citation.
29. Ensure terminology is consistent.
30. Ensure no claim turns an interpretation into a measured causal fact.
31. Ensure test result remains frozen and unmodified.
32. Ensure the paper consistently says **retrieval/evidence selection**, not end-to-end QA accuracy.

---

# 36. Audit completeness statement

Within the project materials currently available in this environment, this second-pass handover now includes the major information needed to write the paper:

- scientific scope and terminology;
- assignment/paper constraints;
- source-document structure;
- chunk construction, integrity, quality findings, and source inconsistencies;
- question/gold construction principles and limitations;
- exact gold-set size distribution;
- leakage-aware split design and integrity;
- exact representation checkpoints and verified preprocessing/encoding behavior;
- cosine similarity and ranking-analysis diagnostics;
- exact selector behavior including relative margin;
- threshold-search methodology;
- evaluator semantics;
- development-selection protocol and key development metrics;
- frozen validation finalists;
- official recorded test endpoint;
- baseline definitions and freeze discipline;
- error-analysis taxonomy and unresolved review state;
- structural top-1 limitation;
- unseen evidence-group issue;
- diagnostic-adjusted-score warning;
- research questions and core paper story;
- table/figure plan;
- full available literature set;
- paper structure, page budget, writing order, emphasis, and future work;
- safe/unsafe claims;
- reproducibility checklist and source paths;
- explicit remaining unresolved items.

What is **not** filled in is intentionally not available as a frozen fact in the currently inspected artifacts: final test baseline values, final error-category counts, exact outcomes for all eight Zugangsprüfung questions, a single authoritative construction-provenance statement, full final hyperparameter grids, and any completed uncertainty analysis.

Those gaps must be resolved from the underlying project artifacts rather than guessed.

---

# 37. One-sentence takeaway


The project’s strongest scientific contribution is not merely that E5 scored highest; it is the controlled demonstration that **both representation choice and evidence-selection/abstention policy materially affect retrieval from a terminology-heavy German regulation, and that a leakage-aware held-out evaluation exposes important generalization, abstention, gold-standard, and top-1 structural limitations that are hidden by development scores alone.**
