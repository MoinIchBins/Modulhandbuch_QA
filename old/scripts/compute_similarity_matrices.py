import json
from pathlib import Path

import numpy as np

from similarity_calculator import compare_embeddings


EMBEDDINGS_FOLDER = Path("artifacts/embeddings")
OUTPUT_FOLDER = Path("artifacts/similarity_matrices")

EMBEDDING_METHODS = [
    "TF_IDF",
    "SENTENCE_BERT",
    "RETRIEVAL_BI_ENCODER",
]
SIMILARITY_METHODS = ["cosine", "dot", "euclidean"]


def main():
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    for embedding_method in EMBEDDING_METHODS:
        embedding_name = embedding_method.lower()
        embedding_folder = EMBEDDINGS_FOLDER / embedding_name
        method_output_folder = OUTPUT_FOLDER / embedding_name
        method_output_folder.mkdir(parents=True, exist_ok=True)

        print()
        print(f"Loading embeddings for {embedding_method}...")

        question_embeddings = np.load(embedding_folder / "question_embeddings.npy")
        chunk_embeddings = np.load(embedding_folder / "chunk_embeddings.npy")

        with (embedding_folder / "question_ids.json").open(
            "r",
            encoding="utf-8",
        ) as file:
            question_ids = json.load(file)

        with (embedding_folder / "chunk_ids.json").open(
            "r",
            encoding="utf-8",
        ) as file:
            chunk_ids = json.load(file)

        with (method_output_folder / "question_ids.json").open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(question_ids, file, ensure_ascii=False, indent=2)

        with (method_output_folder / "chunk_ids.json").open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(chunk_ids, file, ensure_ascii=False, indent=2)

        for similarity_method in SIMILARITY_METHODS:
            print(f"Computing {similarity_method} similarity matrix...")
            matrix = compare_embeddings(
                similarity_method,
                question_embeddings,
                chunk_embeddings,
            )
            np.save(
                method_output_folder / f"{similarity_method}_similarity_matrix.npy",
                matrix,
            )
            print(f"Saved matrix with shape {matrix.shape}")

        print(f"Saved to: {method_output_folder}")

    print()
    print("Finished computing all similarity matrices.")


if __name__ == "__main__":
    main()
