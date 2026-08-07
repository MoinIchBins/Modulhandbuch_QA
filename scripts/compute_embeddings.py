import json
from pathlib import Path

import joblib
import numpy as np

from text_embedder import TextEmbedder


questions_file = Path(
    r"data/processed/qSet_PO.jsonl"
)

chunks_file = Path(
    r"data/processed/PO_25_CL_chunks.jsonl"
)

output_folder = Path(
    r"data/produced_v2/embeddings"
)

embedding_methods = [
    "TF_IDF",
    "SENTENCE_BERT",
    "RETRIEVAL_BI_ENCODER",
]

batch_size = 32

# Use None to use the default model defined in TextEmbedder.
model_names = {
    "TF_IDF": None,
    "SENTENCE_BERT": None,
    "RETRIEVAL_BI_ENCODER": None,
}


def load_jsonl(path: Path) -> list[dict]:
    rows = []

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                rows.append(json.loads(line))

    return rows


def save_json(path: Path, data) -> None:
    with path.open("w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )



question_rows = load_jsonl(questions_file)
chunk_rows = load_jsonl(chunks_file)

question_ids = [
    str(row["question_id"])
    for row in question_rows
]

question_texts = [
    str(row["question"])
    for row in question_rows
]

chunk_ids = [
    str(row["chunk_id"])
    for row in chunk_rows
]

chunk_texts = [
    str(row["chunk_text"])
    for row in chunk_rows
]

print(f"Loaded {len(question_ids)} questions.")
print(f"Loaded {len(chunk_ids)} chunks.")

output_folder.mkdir(
    parents=True,
    exist_ok=True,
)



for method in embedding_methods:
    print()
    print(f"Computing embeddings with {method}...")

    method_folder = output_folder / method.lower()

    method_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    embedder = TextEmbedder(
        method=method,
        chunk_texts=chunk_texts,
        model_name_or_path=model_names[method],
        batch_size=batch_size,
    )

    question_embeddings = embedder.embed_many(
        question_texts,
        text_type="question",
    )

    chunk_embeddings = embedder.embed_many(
        chunk_texts,
        text_type="chunk",
    )

    np.save(
        method_folder / "question_embeddings.npy",
        question_embeddings,
    )

    np.save(
        method_folder / "chunk_embeddings.npy",
        chunk_embeddings,
    )

    save_json(
        method_folder / "question_ids.json",
        question_ids,
    )

    save_json(
        method_folder / "chunk_ids.json",
        chunk_ids,
    )

    if method == "TF_IDF":
        joblib.dump(
            embedder.vectorizer,
            method_folder / "tfidf_vectorizer.joblib",
        )

    metadata = {
        "embedding_method": method,
        "model_name": getattr(
            embedder,
            "model_name_or_path",
            None,
        ),
        "questions_file": str(questions_file),
        "chunks_file": str(chunks_file),
        "number_of_questions": len(question_ids),
        "number_of_chunks": len(chunk_ids),
        "question_embeddings_shape": list(
            question_embeddings.shape
        ),
        "chunk_embeddings_shape": list(
            chunk_embeddings.shape
        ),
    }

    save_json(
        method_folder / "metadata.json",
        metadata,
    )

    print(
        f"Question embeddings: "
        f"{question_embeddings.shape}"
    )

    print(
        f"Chunk embeddings: "
        f"{chunk_embeddings.shape}"
    )

    print(f"Saved to: {method_folder}")

print()
print("Finished computing all embeddings.")