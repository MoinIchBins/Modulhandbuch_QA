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
        max_seq_length=None,
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

        if max_seq_length is not None:
            limit = self.model[0].auto_model.config.max_position_embeddings
            if not isinstance(max_seq_length, int) or not (
                1 <= max_seq_length <= limit
            ):
                raise ValueError(f"max_seq_length must be between 1 and {limit}")

            self.model.max_seq_length = max_seq_length
            self.model.tokenizer.model_max_length = max_seq_length
        self.max_input_tokens = {}

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

        lengths = [
            len(ids) for ids in self.model.tokenizer(
                texts, truncation=False, padding=False
            )["input_ids"]
        ]
        maximum = max(lengths, default=0)
        self.max_input_tokens[text_type] = maximum
        
        if maximum > self.model.max_seq_length:
            raise ValueError(
                f"{text_type} input has {maximum} tokens; model limit is "
                f"{self.model.max_seq_length}. Encoding would truncate text."
            )

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
