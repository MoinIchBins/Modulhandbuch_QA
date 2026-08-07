# fRetrieval Model Comparison

## Why TF-IDF works well here

TF-IDF performs strongly because this retrieval task contains a lot of **specific, repeated terminology** from the Prüfungsordnung. Terms such as module names, *Prüfungsausschuss*, *Modulprüfung*, *Studienleistung*, *Prüfungsnummer*, and similar legal or administrative expressions are highly discriminative.

TF-IDF is a **lexical retrieval method**: it rewards overlap in important words and phrases. Because the questions often use the same terminology as the source chunks, this direct lexical matching is very effective. The use of **1–3 word n-grams** strengthens this further by capturing short phrases rather than only isolated words.

This also fits the chunk design: the retrieval chunks are relatively focused and self-contained, so matching the right technical term often already identifies the correct chunk.

## Why Sentence-BERT performs worse

Sentence-BERT produces **dense semantic embeddings** and is designed to place texts with similar meanings close together. This is useful for paraphrases, but it can become a weakness when many chunks are semantically similar and the task requires a very precise distinction.

For example, chunks about registration, withdrawal, repetition, or admission to an examination are all semantically related. Sentence-BERT may place these close together even though only one is the correct answer source.

The results reflect this: Sentence-BERT has lower Recall, MRR, and All-Gold scores, and its strongest non-gold chunks often score as highly as, or higher than, the correct chunks. In this dataset, broad semantic similarity is therefore less useful than precise discrimination between closely related regulations.

## Why E5 performs best

The E5 model combines semantic representation with an objective that is specifically designed for **information retrieval**. It encodes questions as `query:` texts and chunks as `passage:` texts, so it is trained to learn the relationship between a search query and a relevant passage rather than only general sentence similarity.

This gives it an advantage over both alternatives:

- unlike TF-IDF, it can still match paraphrases and wording differences;
- unlike the Sentence-BERT model, it is optimized to rank the most relevant passage above semantically related distractors.

The evaluation confirms this. E5 achieves the highest MRR, Recall@k, and All-Gold@k values and produces the best gold-rank distribution. It therefore appears to offer the best balance between **semantic matching** and **retrieval-specific discrimination** for this QA task.

## Conclusion

The current results are plausible for this dataset:

- **TF-IDF** is a strong baseline because the task is terminology-heavy and lexically precise.
- **Sentence-BERT** captures semantic similarity, but it does not separate closely related regulatory chunks well enough.
- **E5** performs best because it combines semantic understanding with a retrieval-specific training objective.

