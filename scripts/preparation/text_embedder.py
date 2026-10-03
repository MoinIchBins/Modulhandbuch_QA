class TextEmbedder:
    default_sentence_model = (
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    default_e5_model = "intfloat/multilingual-e5-base"

    def __init__(
        self,
        method,
        chunk_texts,
        model_name_or_path=None,
        batch_size=32,
        model_revision=None,
    ):
        """Fit TF-IDF on chunks or load the requested neural encoder."""
        self.method = method.upper()
        self.batch_size = batch_size
        self.model_revision = model_revision

        if self.method == "TF_IDF":
            from sklearn.feature_extraction.text import TfidfVectorizer

            self.vectorizer = TfidfVectorizer(
                lowercase=True,
                ngram_range=(1, 3),
            )
            self.vectorizer.fit(chunk_texts)
            self.model = None
            self.model_name_or_path = None
            return

        if self.method == "SENTENCE_BERT":
            self.model_name_or_path = (
                model_name_or_path or self.default_sentence_model
            )
        elif self.method == "RETRIEVAL_BI_ENCODER":
            self.model_name_or_path = (
                model_name_or_path or self.default_e5_model
            )
        else:
            raise ValueError(f"Unknown embedding method: {method}")

        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(
            self.model_name_or_path, revision=model_revision
        )
        self.vectorizer = None

    def embed_many(self, texts, text_type="question"):
        """
        Encode a batch; E5 prefixes distinguish questions from evidence
        passages.
        """
        if self.method == "RETRIEVAL_BI_ENCODER":
            prefix = "query: " if text_type == "question" else "passage: "
            texts = [prefix + text for text in texts]

        if self.method == "TF_IDF":
            return self.vectorizer.transform(texts).toarray()

        return self.model.encode(
            texts,
            batch_size=self.batch_size,
            convert_to_numpy=True,
            normalize_embeddings=False,
            show_progress_bar=len(texts) > self.batch_size,
        )

    def embed(self, text, text_type="question"):
        """Encode a single text."""
        return self.embed_many([text], text_type=text_type)[0]
