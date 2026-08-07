import json
from pathlib import Path

import numpy as np

from similarity_calculator import SimilarityCalculator


EMBEDDINGS_FOLDER = Path(
    r"data/produced/embeddings"
)

OUTPUT_FOLDER = Path(
    r"data/produced/similarity_matrices"
)

EMBEDDING_METHODS = [
    "TF_IDF",
    "SENTENCE_BERT",
    "RETRIEVAL_BI_ENCODER",
]

SIMILARITY_METHODS = [
    "cosine",
    "dot",
    "euclidean",
]



def load_json(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_json(path: Path, data) -> None:
    with path.open("w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )


OUTPUT_FOLDER.mkdir(
    parents=True,
    exist_ok=True,
)

for embedding_method in EMBEDDING_METHODS:
    embedding_name = embedding_method.lower()

    embedding_folder = (
        EMBEDDINGS_FOLDER / embedding_name
    )

    question_embeddings_file = (
        embedding_folder / "question_embeddings.npy"
    )

    chunk_embeddings_file = (
        embedding_folder / "chunk_embeddings.npy"
    )

    question_ids_file = (
        embedding_folder / "question_ids.json"
    )

    chunk_ids_file = (
        embedding_folder / "chunk_ids.json"
    )

    print()
    print(
        f"Loading embeddings for "
        f"{embedding_method}..."
    )

    question_embeddings = np.load(
        question_embeddings_file
    )

    chunk_embeddings = np.load(
        chunk_embeddings_file
    )

    question_ids = load_json(question_ids_file)
    chunk_ids = load_json(chunk_ids_file)

    if question_embeddings.shape[0] != len(question_ids):
        raise ValueError(
            f"{embedding_method}: number of question "
            f"embeddings does not match question IDs."
        )

    if chunk_embeddings.shape[0] != len(chunk_ids):
        raise ValueError(
            f"{embedding_method}: number of chunk "
            f"embeddings does not match chunk IDs."
        )

    method_output_folder = (
        OUTPUT_FOLDER / embedding_name
    )

    method_output_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    save_json(
        method_output_folder / "question_ids.json",
        question_ids,
    )

    save_json(
        method_output_folder / "chunk_ids.json",
        chunk_ids,
    )

    matrix_metadata = {}

    for similarity_method in SIMILARITY_METHODS:
        print(
            f"Computing {similarity_method} "
            f"similarity matrix..."
        )

        calculator = SimilarityCalculator(
            method=similarity_method
        )

        similarity_matrix = calculator.compare(
            question_embeddings,
            chunk_embeddings,
        )

        matrix_file_name = (
            f"{similarity_method}_similarity_matrix.npy"
        )

        np.save(
            method_output_folder / matrix_file_name,
            similarity_matrix,
        )

        matrix_metadata[similarity_method] = {
            "file": matrix_file_name,
            "shape": list(similarity_matrix.shape),
            "higher_is_better": (
                similarity_method != "euclidean"
            ),
        }

        print(
            f"Saved matrix with shape "
            f"{similarity_matrix.shape}"
        )

    metadata = {
        "embedding_method": embedding_method,
        "number_of_questions": len(question_ids),
        "number_of_chunks": len(chunk_ids),
        "matrices": matrix_metadata,
    }

    save_json(
        method_output_folder / "metadata.json",
        metadata,
    )

    print(f"Saved to: {method_output_folder}")

print()
print("Finished computing all similarity matrices.")