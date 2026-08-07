import numpy as np


class ChunkSelector:
    """Select chunks from a question-to-chunk score matrix."""

    def __init__(
        self,
        method: str,
        top_k: int | None = None,
        threshold: float | None = None, # for softmax_cumulative between 0 and 1, else greater than 0
        margin: float | None = None, # relative gap required between rank k and rank k + 1
        higher_is_better: bool = True, # this was added in case euclidean distance was implemented later on, in which case lower would be better
        temperature: float = 0.05, # greater than 0
    ):
        supported_methods = {
            "top_k",
            "threshold",
            "top_k_threshold",
            "relative_margin",
            "softmax_cumulative",
        }

        if method not in supported_methods:
            raise ValueError(
                f"Unknown selector method: {method}. "
                f"Choose from {supported_methods}."
            )

        if method in {
            "top_k",
            "top_k_threshold",
            "relative_margin",
        } and top_k is None:
            raise ValueError(
                f"A top_k is required for method '{method}'."
            )

        if top_k is not None and top_k < 1:
            raise ValueError("top_k must be at least 1.")

        if method == "relative_margin":
            if margin is None:
                raise ValueError(
                    "A margin is required for method 'relative_margin'."
                )

            if margin < 0:
                raise ValueError(
                    "margin must be greater than or equal to 0."
                )

        if method in {
            "threshold",
            "top_k_threshold",
            "softmax_cumulative",
        } and threshold is None:
            raise ValueError(
                f"A threshold is required for method '{method}'."
            )

        if method == "softmax_cumulative":
            if not 0 < threshold <= 1:
                raise ValueError(
                    "For softmax_cumulative, threshold must be "
                    "greater than 0 and at most 1."
                )

            if temperature <= 0:
                raise ValueError(
                    "temperature must be greater than 0."
                )

        self.method = method
        self.top_k = top_k
        self.threshold = threshold
        self.margin = margin
        self.higher_is_better = higher_is_better
        self.temperature = temperature

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
        - weights for softmax_cumulative
        """

        # make sure score is a matrix
        scores = np.atleast_2d(scores)

        if scores.shape[1] != len(chunk_ids):
            raise ValueError(
                "The number of score columns must match the number of chunk IDs."
            )

        selections = []

        for question_scores in scores:
            selected_indices = self._select_indices(question_scores)

            selection = {
                "chunk_ids": [
                    chunk_ids[index]
                    for index in selected_indices
                ],
                "scores": [
                    float(question_scores[index])
                    for index in selected_indices
                ],
            }

            if self.method == "softmax_cumulative":
                weights = self._softmax(question_scores)

                selection["weights"] = [
                    float(weights[index])
                    for index in selected_indices
                ]

            selections.append(selection)

        return selections

    def _select_indices(
        self,
        scores: np.ndarray,
    ) -> list[int]:
        """Select chunk indices for one question."""

        ranked_indices = self._rank_indices(scores)

        if self.method == "top_k":
            return ranked_indices[:self.top_k]

        if self.method == "softmax_cumulative":
            return self._select_softmax_cumulative(
                scores,
                ranked_indices,
            )

        if self.method == "relative_margin":
            return self._select_relative_margin(
                scores,
                ranked_indices,
            )

        passing_indices = [
            index
            for index in ranked_indices
            if self._passes_threshold(scores[index])
        ]

        if self.method == "threshold":
            return passing_indices

        if self.method == "top_k_threshold":
            return passing_indices[:self.top_k]

        raise RuntimeError("Unsupported selector method.")

    def _select_relative_margin(
        self,
        scores: np.ndarray,
        ranked_indices: list[int],
    ) -> list[int]:
        """
        Return the top-k chunks only if rank k is clearly
        separated from rank k + 1.
        """

        if self.top_k >= len(ranked_indices):
            raise ValueError(
                "relative_margin requires at least one chunk "
                "outside the selected top_k."
            )

        selected_index = ranked_indices[self.top_k - 1]
        next_index = ranked_indices[self.top_k]

        selected_score = float(scores[selected_index])
        next_score = float(scores[next_index])

        denominator = max(abs(selected_score), 1e-12)

        if self.higher_is_better:
            relative_margin = (
                selected_score - next_score
            ) / denominator
        else:
            relative_margin = (
                next_score - selected_score
            ) / denominator

        if relative_margin >= self.margin:
            return ranked_indices[:self.top_k]

        return []

    def _select_softmax_cumulative(
        self,
        scores: np.ndarray,
        ranked_indices: list[int],
    ) -> list[int]:
        """
        Select the smallest ranked set whose cumulative
        softmax weight reaches the threshold.
        """

        weights = self._softmax(scores)

        selected_indices = []
        cumulative_weight = 0.0

        for index in ranked_indices:
            selected_indices.append(index)
            cumulative_weight += weights[index]

            if cumulative_weight >= self.threshold:
                break

            if (
                self.top_k is not None
                and len(selected_indices) >= self.top_k
            ):
                break

        return selected_indices

    def _softmax(
        self,
        scores: np.ndarray,
    ) -> np.ndarray:
        """Convert scores into normalized softmax weights."""

        if self.higher_is_better:
            relevance_scores = scores
        else:
            relevance_scores = -scores

        scaled_scores = relevance_scores / self.temperature

        # subtract the maximum to move below 0
        scaled_scores = scaled_scores - np.max(scaled_scores)

        exponentials = np.exp(scaled_scores)

        return exponentials / exponentials.sum()

    def _rank_indices(
        self,
        scores: np.ndarray,
    ) -> list[int]:
        """Rank indices from best to worst."""

        if self.higher_is_better:
            return np.argsort(
                -scores,
                kind="stable",
            ).tolist()

        return np.argsort(
            scores,
            kind="stable",
        ).tolist()

    def _passes_threshold(
        self,
        score: float,
    ) -> bool:
        """Check whether a score passes the threshold."""

        if self.higher_is_better:
            return score >= self.threshold

        return score <= self.threshold