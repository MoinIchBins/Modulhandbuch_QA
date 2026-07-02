# Modulhandbuch_QA

Project for Python II, QA-model comparison on Modulhandbuch

## Description

QA-Model comparison on German corpus Modulhandbuch

- Vector embedding with library and cosine similarity on passages (Python II), try different embeddings
- Machine learning approach for indices in main corpus (likely bad due to big data) (Python II / Deep Learning)
- Machine learning approach for text passages (Deep Learning)
- Finish RAG with generating answer in full text

## Steps:

- Handle Data (into sections, with metadata)
  - by hand
  - algorithmically?
- Create QA Trainingdata (Question-segment pairs, 200-400)
  - by hand
  - automatically with ai?
- Split into training set, test set, validation set
- Code QA-Models (embedding based, machine learning based, implemented QA Model)
- Create Testing functions (Accuracy, EM, F1) to compare
- Visualize results

## Some Details

- segment the source texts (100-400 words per chunk) 200-400QA pairs of differing question types
eg: Wie viele ECTS hat Modul X?, In welchem Semester wird Modul Y angeboten?, Wie oft darf eine Prüfung wiederholt werden?, Welche Voraussetzungen gelten für die Zulassung?
Was ist ein Wahlpflichtmodul?, Wann gilt eine Prüfung als endgültig nicht bestanden?, Bis wann muss man sich anmelden?, Welche Leistungen müssen für den Abschluss nachgewiesen werden?
- QA dataset  [context, question, answertext, startindex]
- some pre-trained QA models for Deep Learning part (like bert-base-german-cased, deepset/gelectra-base-germanquad) the segment on which to run must be determined first, here comes the comparison
- run on all, choose highest confidence, ii. run on k-best determined BM25 
- one step further: preprocessing the question? 
  - no processing 
  - lowercase 
  - lemmatization and stemming 
  - Query extension through list of synonyms 
  - score auf title, section und text

## Forschungsfrage:

DL: "How well can a transformer-based extractive QA model answer student questions from official university documents?" or "Can a German extractive QA model accurately answer questions based on Modulhandbuch text passages?"

Python: "How well can similarity of various embeddings pick sections to answer questions towards a corpus?" or "In how far does preprocessing the corpus first effect the results?" or "In how far does preprocessing the question effect the results?"

DL: compare:  pre-trained model without fine-tuning against after fine-tuning and/or: pre-trained model without segmenting against with segmenting, ran on all, choose highest confidence against with segmenting ran on k-best after bm25  
The goal:  
Train a german extractive QA model on manually created question-answer pairs from the PO25 and Modulhandbuch of CL integrativ.  
Compare that model against a simple retrieval baseline.  
Analyze common failure cases.

Python: compare different embeddings, compare different preprocessing of data and question  
The goal: Create a rudimentary QA model that picks out the segment(s) of text that answer a question.