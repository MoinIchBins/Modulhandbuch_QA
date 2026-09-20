
| Paper                   | Main job                                                         |
| ----------------------- | ---------------------------------------------------------------- |
| Spärck Jones 1972       | IDF / term specificity foundation                                |
| Salton et al. 1975      | vector-space retrieval foundation                                |
| SBERT 2019              | explain Sentence-BERT representation                             |
| Multilingual SBERT 2020 | justify/use multilingual sentence representations                |
| E5 2022                 | explain E5 training/objective and retrieval orientation          |
| Multilingual E5 2024    | explain the actual multilingual E5 family you use                |
| DPR 2020                | dense retrieval / bi-encoder conceptual background               |
| BEIR 2021               | sparse vs. dense retrieval, domain/generalization discussion     |
| MTEB 2023               | embedding models differ across tasks; avoid universal rankings   |
| SQuAD 2.0 2018          | unanswerable questions / abstention motivation                   |
| SelectiveNet 2019       | reject option / threshold-based selective prediction terminology |
| GerDaLIR 2021           | German legal/regulatory IR context                               |
| German Legal QA 2024    | German legal QA/retrieval context                                |


Gruppe A: Sparse / Lexikalisches Retrieval (TF-IDF Baseline)
Spärck Jones (1972) – A Statistical Interpretation of Term Specificity and Its Application in Retrieval
Inhalt: Grundlegendes mathematisches Konzept der Inverse Document Frequency (IDF) und Termspezifität.
Rolle: Theoretische Fundierung von IDF für den Sparse-Retrieval-Zweig
.
Salton, Wong & Yang (1975) – A Vector Space Model for Automatic Indexing
Inhalt: Das klassische Vektorraummodell (VSM), Term-Weighting und Cosine-Similarity für Dokumentenvektoren.
Rolle: Begründung des Vektorraummodells und des TF-IDF-Sparse-Ansatzes
.
Gruppe B: Dense Retrieval & Sentence Representations
Reimers & Gurevych (2019) – Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks
Inhalt: Siamesische BERT-Architektur zur Erzeugung semantisch aussagekräftiger Satz- und Text-Embeddings via Cosine-Similarity.
Rolle: Primärquelle für die SBERT-Repräsentation; Standardarchitektur für dichte Satz-Embeddings
.
Reimers & Gurevych (2020) – Making Monolingual Sentence Embeddings Multilingual using Knowledge Distillation
Inhalt: Cross-Lingual Knowledge Distillation (Lehrer-Schüler-Modell), um englisch trainierte Satzrepräsentationen auf andere Sprachen (u. a. Deutsch) zu übertragen
.
Rolle: Begründung der multilingualen Fähigkeiten des verwendeten SBERT-Modells auf deutschen Korpora
.
Wang et al. (2022) – Text Embeddings by Weakly-Supervised Contrastive Pre-training (E5)
Inhalt: Einführung der E5-Embeddings, kontrastives Vortraining auf massiven Textpaaren mit aufgabenspezifischen Präfixen (query: / passage:)
.
Rolle: Motivation des bi-encoder-basierten E5-Ansatzes und der Präfix-Struktur
.
Wang et al. (2024) – Multilingual E5 Text Embeddings: A Technical Report (mE5)
Inhalt: Erweiterung von E5 auf 100 Sprachen (multilingual-e5-base / large)
.
Rolle: Exakter technischer Beleg für das im Experiment als Gesamtsieger hervorgegangene Embedding-Modell
.
Karpukhin et al. (2020) – Dense Passage Retrieval for Open-Domain Question Answering (DPR)
Inhalt: Bi-Encoder-Architektur für Passage-Retrieval als vorgeschalteter Schritt vor einem QA-Reader
.
Rolle: Einordnung von Evidence Retrieval als unverzichtbare Upstream-Komponente für QA/RAG
.
Gruppe C: IR-Benchmarks & Embedding-Evaluierung
Thakur et al. (2021) – BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models
Inhalt: Heterogener Zero-Shot-Benchmark für IR; zeigt u. a., dass BM25/lexikalische Modelle in Domänen mit Fachbegriffen oft überraschend konkurrenzfähig gegen dichte Modelle sind
.
Rolle: Kontextualisierung der Zero-Shot-Performanz und Erklärung, warum TF-IDF bei spezifischer Verwaltungsterminologie stark abschneidet
.
Muennighoff et al. (2023) – MTEB: Massive Text Embedding Benchmark
Inhalt: Umfassender Benchmark für Embedding-Modelle über 8 Task-Typen hinweg (inkl. Retrieval, Reranking, STS)
.
Rolle: Beleg für die Rangordnung und Generalisierungsfähigkeit moderner Encodermodelle (wie mE5 vs. SBERT)
.
Gruppe D: Unbeantwortbare Fragen & Enthaltung (Abstention / Selective Prediction)
Rajpurkar, Jia & Liang (2018) – Know What You Don't Know: Unanswerable Questions for SQuAD (SQuAD 2.0)
Inhalt: Notwendigkeit für QA-Systeme zu erkennen, wann ein Text keine Antwort enthält (Plausible Distractors / Zero-Gold)
.
Rolle: Motivation für die 120 absichtlich unbeantwortbaren Fragen (Zero-Gold) im Prüfungsordnungs-Datensatz
.
Geifman & El-Yaniv (2019) – SelectiveNet: A Deep Neural Network with an Integrated Reject Option
Inhalt: Formale Modellierung von Vorhersagen mit Rückweisungs-Option (Reject Option / Abstention) zur Risikominimierung
.
Rolle: Theoretische Fundierung der Selektoren mit Schwellenwert-Enthaltung (threshold und relative margin)
.
Gruppe E: Domänenkontext – Deutsches Rechts- und Verwaltungscorpus
Wrzalik & Krechel (2021) – GerDaLIR: A German Dataset for Legal Information Retrieval
Inhalt: Benchmark für deutsches Rechtsretrieval; Vergleich klassischer Sparse-Baselines (BM25/TF-IDF) mit Transformern
.
Rolle: Einordnung der Herausforderungen der deutschen Rechtssprache und Beleg für sparse vs. dense Performanz im deutschen Rechtswesen
.
Büttner & Habernal (2024) – Answering legal questions from laymen in German civil law system (GerLayQA)
Inhalt: QA über deutsche Gesetzestexte (BGB) bei laiensprachigen Anfragen; zeigt, dass domänenspezifisches Vokabular und komplexe Bezüge erhebliche Hürden für Standard-Embeddings darstellen
.
Rolle: Untermauerung der Diskrepanz zwischen studentischer Alltagssprache und formeller Prüfungsordnungssprache
.


2. Zuordnung zu den Abschnitten der Hausarbeit (ACL-Struktur)
Abschnitt
Zu nutzende Literatur
Konkreter Verwendungszweck im Text
1. Introduction
Karpukhin et al. (2020)
<br>Rajpurkar et al. (2018)
Motiviert Retrieval als vorgeschaltete Voraussetzung für verlässliche QA
. Erklärt, warum Systeme bei administrativen Texten nicht raten dürfen, sondern sich enthalten müssen (Know What You Don't Know)
.
2. Motivation & Related Work
Spärck Jones (1972)
<br>Salton et al. (1975)
<br>Reimers & Gurevych (2019, 2020)
<br>Wang et al. (2022, 2024)
<br>Thakur et al. (2021)
<br>Geifman & El-Yaniv (2019)
<br>Wrzalik & Krechel (2021)
<br>Büttner & Habernal (2024)
Sparse vs. Dense: Gegenüberstellung von lexikalischem Matching und dichten Embeddings
.<br>Domain Context: Besonderheiten deutscher Verwaltungs- und Rechtsdokumente
.<br>Selective Retrieval: Selektion und Enthaltung als eigenständige Schutzschicht
. (Hinweis: Schlank halten, kein breiter Survey
).
3. Methodology
Salton et al. (1975)
<br>Reimers & Gurevych (2019)
<br>Wang et al. (2024)
<br>Geifman & El-Yaniv (2019)
Repräsentationen: Exakte mathematische Definition von TF-IDF VSM, SBERT-Bi-Encoder und Multilingual E5 (inkl. Aufgaben-Präfixen query: / passage:)
.<br>Selektoren & Abstention: Formale Definition von Top-k, Schwellenwerten (Threshold) und relativer Marge
.
4. Experimental Setup
Rajpurkar et al. (2018)
<br>Muennighoff et al. (2023)
Begründung des Datensatzdesigns: 720 Fragen, davon 120 gezielte Zero-Gold-Distraktoren zur Überprüfung der Enthaltungsfähigkeit
. Einbettung in standardisierte IR-Evaluationsmetriken (Fragen-F1, Precision, Recall)
.
5. Results & Evaluation / Error Analysis
Thakur et al. (2021)
<br>Büttner & Habernal (2024)
<br>Wrzalik & Krechel (2021)
Erklärung RQ1 (TF-IDF vs. Dense): Warum TF-IDF bei diskriminativer Prüfungsordnungsterminologie (Modulprüfung, SWS, Prüfungsausschuss) stark abschneidet (analog zu BEIR-Erkenntnissen)
.<br>Fehleranalyse: Semantische Nachbarschaften und laiensprachliche Formulierungen vs. formale Klauseln
.
6. Conclusion & 7. Limitations
Karpukhin et al. (2020)
<br>Thakur et al. (2021)
Ausblick auf fehlende Komponenten (Cross-Encoder Reranking, BM25, Hybrid-Retrieval, Downstream-Reader)
.