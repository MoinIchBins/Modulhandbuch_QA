import numpy as np
from sentence_transformers import SentenceTransformer


class TextEmbedder:
    """Embed text using a local SentenceTransformer model."""

    def __init__(self, model_name_or_path: str, batch_size: int = 32):
        self.model_name_or_path = model_name_or_path
        self.batch_size = batch_size
        self.model = SentenceTransformer(model_name_or_path)

    def preprocess(self, text: str) -> str:
        """Placeholder for future text preprocessing."""
        return text

    def postprocess(self, embeddings: np.ndarray) -> np.ndarray:
        """Placeholder for future embedding post-processing."""
        return embeddings

    def embed(self, text: str) -> np.ndarray:
        """Embed a single text and return one vector."""
        return self.embed_many([text])[0]

    def embed_many(self, texts: list[str]) -> np.ndarray:
        """Embed multiple texts and return one vector per text."""
        prepared_texts = [self.preprocess(text) for text in texts]

        embeddings = self.model.encode(
            prepared_texts,
            batch_size=self.batch_size,
            convert_to_numpy=True,
            normalize_embeddings=False,
            show_progress_bar=len(texts) > self.batch_size,
        )

        return self.postprocess(embeddings)