# Determining Threshold Search Regions

Thresholds should be chosen separately for each representation because cosine-score distributions differ across E5, TF-IDF, and Sentence-BERT.

For each answerable development question, calculate:

- **Worst gold score**  
  \(G_q = \min_{c \in Gold(q)} s(q,c)\)  
  This is the lowest score among all required chunks.

- **Best non-gold score**  
  \(N_q = \max_{c \notin Gold(q)} s(q,c)\)  
  This is the strongest false-positive competitor.

For each zero-gold question, calculate:

- **Top zero-gold score**  
  \(Z_q = \max_c s(q,c)\)  
  This is the strongest score when the system should ideally abstain.

## Initial threshold region

Use robust quantiles rather than minima and maxima:

\[
L = P_{10}(G)
\]

\[
U = \max(P_{90}(N), P_{90}(Z))
\]

The initial coarse search region is:

\[
[\min(L,U),\ \max(L,U)]
\]

This region covers the trade-off between retaining required chunks and rejecting unwanted chunks.

## Current development-set regions

| Representation | \(P_{10}(G)\) | \(P_{90}(N)\) | \(P_{90}(Z)\) | Initial region |
|---|---:|---:|---:|---:|
| E5 | 0.8331 | 0.8865 | 0.8695 | 0.8331–0.8865 |
| TF-IDF | 0.0591 | 0.2477 | 0.5162 | 0.0591–0.5162 |
| Sentence-BERT | 0.4740 | 0.7595 | 0.7172 | 0.4740–0.7595 |

A small evenly spaced grid inside each region can then be evaluated on the development set. The best threshold is selected using the previously fixed development metric, rather than by inspecting the test set.
