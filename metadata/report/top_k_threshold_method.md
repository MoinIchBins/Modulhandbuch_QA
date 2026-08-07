# Top-k + Threshold: Clean Development Search

For the combined selector, candidates are first ranked by similarity and only the first \(k\) positions are eligible. A candidate is returned only if its score is at least the threshold \(\tau\):

\[
S(q;k,\tau)
=
\{c_{(r)} \mid 1 \le r \le k,\ s_r(q) \ge \tau\}
\]

with

\[
s_1(q) \ge s_2(q) \ge s_3(q) \ge \dots
\]

For \(k=1\), the threshold only decides between returning the top-ranked chunk and abstaining. For \(k>1\), it additionally decides whether the second- or third-ranked candidate is retained.

## Rank-specific threshold regions

Because every retrieved chunk is incorrect for a zero-gold question, the relevant score distributions can be defined from zero-gold development questions:

\[
Z_r = \{s_r(q) \mid q \in Q_0\}
\]

where \(Z_r\) is the distribution of the score at rank \(r\).

For each value of \(k\), the search region is defined as:

\[
L_k = P_{10}(Z_k)
\]

\[
U_k = P_{90}(Z_1)
\]

\[
\tau \in [L_k,U_k]
\]

The lower bound therefore reaches scores at which the \(k\)-th candidate can meaningfully enter the result set, while the upper bound reaches scores that reject most zero-gold questions completely. The final optimum is still selected by development-set evaluation across both answerable and zero-gold questions.

Threshold regions are calculated separately for every representation and every \(k \in \{1,2,3\}\), because both similarity-score scales and rank-specific score distributions differ between representations.

Each region is sampled with 21 evenly spaced thresholds. This is a broad first search; a later local refinement is only necessary if a competitive optimum remains poorly localized or lies on a search boundary.
