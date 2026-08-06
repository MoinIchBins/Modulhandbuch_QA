import numpy as np
from sentence_transformers import SentenceTransformer

class TextEmbedder:
    """Embed questions and chunks using one of three embedding methods."""

    supported_methods = {
        "TF_IDF", 
        "SENTENCE_BERT", 
        "RETRIEVAL_BI_ENCODER", 
    }

    default_models = {
        "SENTENCE_BERT":
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",

        "RETRIEVAL_BI_ENCODER":
            "intfloat/multilingual-e5-base",
    }

    def __init__(
        self,
        method: str,
        chunk_texts: list[str],
        model_name_or_path: str | None = None,
        batch_size: int = 32,
    ):

        method = method.upper()

        if method not in self.supported_methods:
            raise ValueError(
                f"Unknown embedding method: {method}. "
                f"Choose from {self.supported_methods}."
            )

        if not chunk_texts:
            raise ValueError("At least one chunk text is required.")

        self.method = method
        self.chunk_texts = chunk_texts
        self.batch_size = batch_size

        self.model = None
        self.vectorizer = None

        if self.method == "TF_IDF":
            from sklearn.feature_extraction.text import TfidfVectorizer
            self.vectorizer = TfidfVectorizer(
                lowercase=True,
                ngram_range=(1, 3),
            )
            self.vectorizer.fit(chunk_texts)
        else:
            # this makes the import not necessary for TF-IDF as the package is quite big
            try:
                from sentence_transformers import SentenceTransformer
            except ModuleNotFoundError as error:
                raise ModuleNotFoundError(
                    "Neural embeddings require the package sentence-transformers."
                ) from error

            self.model_name_or_path = (
                model_name_or_path or self.default_models[self.method]
            )

            self.model = SentenceTransformer(
                self.model_name_or_path
            )

    def preprocess(
        self,
        text: str,
        text_type: str,
    ) -> str:

        """Preprocessing for at least the retrieval bi-encoder as it needs prefixes for query and passage."""

        if self.method == "RETRIEVAL_BI_ENCODER":
            if text_type == "question":
                return f"query: {text}"

            if text_type == "chunk":
                return f"passage: {text}"

        return text

    def postprocess(
        self,
        embeddings: np.ndarray,
    ) -> np.ndarray:
        """Placeholder for future embedding post-processing."""
        return embeddings

    def embed(
        self,
        text: str,
        text_type: str = "question",
    ) -> np.ndarray:
        """Embed one question or chunk and return one vector."""

        return self.embed_many(
            [text],
            text_type=text_type,
        )[0]

    def embed_many(
        self,
        texts: list[str],
        text_type: str = "question",
    ) -> np.ndarray:
        """Embed multiple questions or chunks."""

        if text_type not in {"question", "chunk"}:
            raise ValueError(
                "text_type must be either 'question' or 'chunk'."
            )

        prepared_texts = [
            self.preprocess(text, text_type)
            for text in texts
        ]

        if self.method == "TF_IDF":
            embeddings = self.vectorizer.transform(prepared_texts).toarray()

        else:
            embeddings = self.model.encode(
                prepared_texts,
                batch_size=self.batch_size,
                convert_to_numpy=True,
                normalize_embeddings=False,
                show_progress_bar=len(texts) > self.batch_size,
            )

        return self.postprocess(embeddings)