import json
from pathlib import Path

import joblib
import numpy as np

from text_embedder import TextEmbedder


QUESTIONS_FILE = Path("data/frozen/qSet_PO.jsonl")
CHUNKS_FILE = Path("data/frozen/PO_25_CL_chunks.jsonl")
OUTPUT_FOLDER = Path("artifacts/embeddings")

EMBEDDING_METHODS = [
    "TF_IDF",
    "SENTENCE_BERT",
    "RETRIEVAL_BI_ENCODER",
]
BATCH_SIZE = 32


def read_jsonl(path):
    with path.open("r", encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def main():
    question_rows = read_jsonl(QUESTIONS_FILE)
    chunk_rows = read_jsonl(CHUNKS_FILE)

    question_ids = [str(row["question_id"]) for row in question_rows]
    question_texts = [str(row["question"]) for row in question_rows]
    chunk_ids = [str(row["chunk_id"]) for row in chunk_rows]
    chunk_texts = [str(row["chunk_text"]) for row in chunk_rows]

    print(f"Loaded {len(question_ids)} questions.")
    print(f"Loaded {len(chunk_ids)} chunks.")

    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    for method in EMBEDDING_METHODS:
        print()
        print(f"Computing embeddings with {method}...")

        method_folder = OUTPUT_FOLDER / method.lower()
        method_folder.mkdir(parents=True, exist_ok=True)

        embedder = TextEmbedder(
            method=method,
            chunk_texts=chunk_texts,
            batch_size=BATCH_SIZE,
        )

        question_embeddings = embedder.embed_many(
            question_texts,
            text_type="question",
        )
        chunk_embeddings = embedder.embed_many(
            chunk_texts,
            text_type="chunk",
        )

        np.save(method_folder / "question_embeddings.npy", question_embeddings)
        np.save(method_folder / "chunk_embeddings.npy", chunk_embeddings)

        with (method_folder / "question_ids.json").open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(question_ids, file, ensure_ascii=False, indent=2)

        with (method_folder / "chunk_ids.json").open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(chunk_ids, file, ensure_ascii=False, indent=2)

        if method == "TF_IDF":
            joblib.dump(
                embedder.vectorizer,
                method_folder / "tfidf_vectorizer.joblib",
            )

        print(f"Question embeddings: {question_embeddings.shape}")
        print(f"Chunk embeddings: {chunk_embeddings.shape}")
        print(f"Saved to: {method_folder}")

    print()
    print("Finished computing all embeddings.")


if __name__ == "__main__":
    main()
