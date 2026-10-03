from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances


def compare_embeddings(method, question_embeddings, chunk_embeddings):
    """Calculate cosine, dot-product or Euclidean question/chunk scores."""
    if method == "cosine":
        return cosine_similarity(question_embeddings, chunk_embeddings)

    if method == "dot":
        return question_embeddings @ chunk_embeddings.T

    if method == "euclidean":
        return euclidean_distances(question_embeddings, chunk_embeddings)

    raise ValueError(f"Unknown similarity method: {method}")
