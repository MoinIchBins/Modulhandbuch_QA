# Modulhandbuch_QA
Project for Python II, QA-model comparison on Modulhandbuch

## Description
QA-Model comparison on German corpus Modulhandbuch

1. Vector embedding and cosine similarity on passages
2. Machine learning approach for indices in main corpus (likely bad due to big data)
3. Machine learning approach for text passages

## Steps:
Handle Data (into sections, with metadata)
Create QA Trainingdata (Question-segment pairs, 200-400)
Split into training set, test set, validation set
Code QA-Model (embedding based, machine learning based, implemented QA Model)
Create Testing functions (EM, F1) to compare
Visualize results

## Struktur:
1. DL QA Project: extractive QA model that answers from a provided context chunk
a. collect source documents, turn into clean text
b. segment the source texts (100-400 words per chunk)
200-400QA pairs of differing question types
eg: Wie viele ECTS hat Modul X?, In welchem Semester wird Modul Y angeboten?, Wie oft darf eine Prüfung wiederholt werden?, Welche Voraussetzungen gelten für die Zulassung?
Was ist ein Wahlpflichtmodul?, Wann gilt eine Prüfung als endgültig nicht bestanden?, Bis wann muss man sich anmelden?, Welche Leistungen müssen für den Abschluss nachgewiesen werden?
c. build QA dataset 
[context, question, answertext, startindex]
d. apply pre-trained QA model (like bert-base-german-cased, deepset/gelectra-base-germanquad)
the segment on which to run must be determined first, here comes the comparison
i. run on all, choose highest confidence, ii. run on k-best determined BM25
also try processing the question first
i. no processing ii. lowercase iii. lemmatization and stemming iv. Query extension through list of synonyms v. score auf title, section und text
e. evaluate EM and F1

## Forschungsfrage:
"How well can a transformer-based extractive QA model answer student questions from official university documents?"
or "Can a German extractive QA model accurately answer questions based on Modulhandbuch text passages?"

Also: baseline first without fine-tuning

Then compare: 
pre-trained model without fine-tuning against after fine-tuning
and/or:
pre-trained model without segmenting against with segmenting, ran on all, choose highest confidence against with segmenting ran on k-best after bm25

The goal:
Train a german extractive QA model on manually created question-answer pairs from the PO25 and Modulhandbuch of CL integrativ.
Compare that model against a simple retrieval baseline.
Analyze common failure cases.