# first pass (5-10 mins)
Read:
- title
- abstract
- introduction
- conclusion

Fill role (core/supporting/optional), primary use (methodology/motication/results discussion/limitation), one-sentence relevance

# second pass
Read only the sections needed for the claim

## Ask: What do I need from this paper to establish?

### For SBERT:
What problem was SBERT designed to solve?
How does it produce sentence embeddings?
What architecture/training principle matters?
What kind of similarity tasks is it intended for?

### For BEIR:
How do sparse and dense retrieval behave across different datasets?
Do methods generalize consistently?
Does one representation dominate everywhere?
What does the paper say about zero-shot/domain robustness?

### For E5:
How are embeddings trained?
Why is it retrieval-oriented?
What do query: / passage: prefixes mean?
What does multilingual E5 change?

# third pass
Extract citation-ready evidence

## Claim

E5 is trained using contrastive objectives to produce general-purpose
text representations applicable to retrieval tasks.

Source location:
Section X, p. Y

Use in paper:
Methodology — representation methods

Possible paper sentence:
"E5 uses contrastive pre-training to learn general-purpose text
representations and is explicitly evaluated for retrieval-oriented
tasks \cite{...}."

Caveat:
The paper does not show that E5 must outperform SBERT on regulatory
documents. That is our empirical result.