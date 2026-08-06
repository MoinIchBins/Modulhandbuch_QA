import numpy as np
from sklearn.metrics.pairwise import (
    cosine_similarity,
    euclidean_distances,
)


class SimilarityCalculator:
    """Calculate similarities or distances between embeddings."""

    def __init__(self, method: str):
        supported_methods = {"cosine", "dot", "euclidean"}

        if method not in supported_methods:
            raise ValueError(
                f"Unknown similarity method: {method}. "
                f"Choose from {supported_methods}."
            )

        self.method = method

    def compare(
        self,
        question_embeddings: np.ndarray,
        chunk_embeddings: np.ndarray,
    ) -> np.ndarray:
        """
        Compare every question embedding with every chunk embedding.

        Returns a matrix with shape: (number of questions, number of chunks)
        """

        # in case only a single vector is passed in, make it 2 dimensional
        question_embeddings = np.atleast_2d(question_embeddings)
        chunk_embeddings = np.atleast_2d(chunk_embeddings)

        if question_embeddings.shape[1] != chunk_embeddings.shape[1]:
            raise ValueError(
                "Question and chunk embeddings must have the same number of dimensions."
            )

        if self.method == "cosine":
            return cosine_similarity(
                question_embeddings,
                chunk_embeddings,
            )

        if self.method == "dot":
            return question_embeddings @ chunk_embeddings.T

        if self.method == "euclidean":
            return euclidean_distances(
                question_embeddings,
                chunk_embeddings,
            )

        raise RuntimeError("Unsupported similarity method.")