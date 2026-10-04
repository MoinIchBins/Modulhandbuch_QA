import numpy as np

# Prevent division by zero when the boundary score is zero.
MARGIN_DENOMINATOR_FLOOR = 1e-12


class ChunkSelector:
    def __init__(
        self,
        method,
        top_k=None,
        threshold=None,
        margin=None,
        higher_is_better=True,
    ):
        """Store the selection method and its parameters."""
        self.method = method
        self.top_k = top_k
        self.threshold = threshold
        self.margin = margin
        self.higher_is_better = higher_is_better

    def select(self, scores, chunk_ids):
        """
        Return selected IDs and scores. Ties follow the input chunk order.
        """
        scores = np.atleast_2d(scores)
        selections = []

        for row in scores:
            if self.higher_is_better:
                ranked = np.argsort(-row, kind="stable").tolist()
            else:
                ranked = np.argsort(row, kind="stable").tolist()

            if self.method == "top_k":
                chosen = ranked[: self.top_k]
            elif self.method in ("threshold", "top_k_threshold"):
                if self.higher_is_better:
                    chosen = [i for i in ranked if row[i] >= self.threshold]
                else:
                    chosen = [i for i in ranked if row[i] <= self.threshold]
                
                if self.method == "top_k_threshold":
                    chosen = chosen[: self.top_k]
            elif self.method == "relative_margin":
                selected = ranked[self.top_k - 1]
                next_best = ranked[self.top_k]

                selected_score = float(row[selected])
                next_score = float(row[next_best])
                denominator = max(
                    abs(selected_score), MARGIN_DENOMINATOR_FLOOR
                )

                if self.higher_is_better:
                    relative_margin = (
                        selected_score - next_score
                    ) / denominator
                else:
                    relative_margin = (
                        next_score - selected_score
                    ) / denominator

                chosen = (
                    ranked[: self.top_k] if relative_margin >= self.margin else []
                )
            else:
                raise ValueError(f"Unknown selector method: {self.method}")

            selections.append(
                {
                    "chunk_ids": [chunk_ids[i] for i in chosen],
                    "scores": [float(row[i]) for i in chosen],
                }
            )

        return selections
