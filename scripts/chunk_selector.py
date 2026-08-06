import numpy as np

class ChunkSelector:
    """Select chunks from a question-to-chunk score matrix."""

    def __init__(
        self,
        method: str,
        top_k: int | None,
        threshold: float | None = None,
        higher_is_better: bool = True # this was added in case euclidean distance was implemented later on, in which case lower would be better
    ):
    
        supported_methods = {
            "top_k",
            "threshold",
            "top_k_threshold",
        }

        if method not in supported_methods:
            raise ValueError(
                f"Unknown selector method: {method}. "
                f"Choose from {supported_methods}."
            )

        if method in {"top_k", "top_k_threshold"} and top_k is None:
            raise ValueError(
                f"A top_k is required for method '{method}'."
            )

        if method in {"top_k", "top_k_threshold"} and top_k < 1:
            raise ValueError("top_k must be at least 1.")

        if method in {"threshold", "top_k_threshold"} and threshold is None:
            raise ValueError(
                f"A threshold is required for method '{method}'."
            )

        self.method = method
        self.top_k = top_k
        self.threshold = threshold
        self.higher_is_better = higher_is_better

    def select(
        self,
        scores: np.ndarray,
        chunk_ids: list[str],
    ) -> list[dict]:

        """
        Select chunks for every question.

        Returns one dictionary per question containing:
        - chunk_ids
        - scores
        """

        # in case scores is no matrix
        scores = np.atleast_2d(scores)

        if scores.shape[1] != len(chunk_ids):
            raise ValueError(
                "The number of score columns must match the number of chunk IDs."
            )

        selections = []

        for question_scores in scores:
            selected_indices = self._select_indices(question_scores)

            selections.append(
                {
                    "chunk_ids": [
                        chunk_ids[index] for index in selected_indices
                    ],
                    "scores": [
                        float(question_scores[index]) for index in selected_indices
                    ],
                }
            )

        return selections

    def _select_indices(
        self,
        scores: np.ndarray,
    ) -> list[int]:

        """Select chunk indices for one question."""

        ranked_indices = self._rank_indices(scores)

        if self.method == "top_k":
            return ranked_indices[:self.top_k]

        passing_indices = [
            index for index in ranked_indices
            if self._passes_threshold(scores[index])
        ]

        if self.method == "threshold":
            return passing_indices

        if self.method == "top_k_threshold":
            # if passing_indices has less than self.top_k items, return all passing_indices
            if len(passing_indices) < self.top_k:
                return passing_indices
            return passing_indices[:self.top_k]
   

        raise RuntimeError("Unsupported selector method.")

    def _rank_indices(
        self,
        scores: np.ndarray,
    ) -> list[int]:
        """Rank indices from best to worst."""

        if self.higher_is_better:
            return np.argsort(-scores, kind="stable").tolist()

        return np.argsort(scores, kind="stable").tolist()

    def _passes_threshold(
        self,
        score: float,
    ) -> bool:

        """Check whether a score passes the threshold."""
        if self.higher_is_better:
            return score >= self.threshold

        return score <= self.threshold