"""Encode question/chunk texts and save their similarity matrices."""

import argparse
from pathlib import Path
import platform

import joblib
import numpy as np

from ..core.config import file_hash, read_json, read_jsonl, write_json
from .text_embedder import TextEmbedder
from .similarity import compare_embeddings


def main():
    """Create embeddings, similarity matrices and model metadata."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        required=True,
        help=(
            "Representation preparation JSON (separate from experiment config)"
        ),
    )
    args = parser.parse_args()
    
    config_path = Path(args.config).resolve()
    config = read_json(config_path)
    root = (config_path.parent / config["project_root"]).resolve()
    questions_path = root / config["questions_path"]
    chunks_path = root / config["chunks_path"]
    
    questions, chunks = read_jsonl(questions_path), read_jsonl(chunks_path)
    output = root / config["output_dir"]
    output.mkdir(parents=True, exist_ok=False)
    write_json(
        output / "preparation.json",
        {
            "config": config,
            "python": platform.python_version(),
            "inputs": {
                str(path): file_hash(path) for path in (questions_path, chunks_path)
            },
        },
    )
    
    artifacts = {}
    for name, model in config["models"].items():
        folder = output / name
        folder.mkdir()

        embedder = TextEmbedder(
            model["method"],
            [row["chunk_text"] for row in chunks],
            model_name_or_path=model.get("model_name_or_path"),
            batch_size=config.get("batch_size", 32),
            model_revision=model.get("revision"),
            max_seq_length=model.get("max_seq_length"),
        )

        question_vectors = embedder.embed_many(
            [row["question"] for row in questions], text_type="question"
        )
        chunk_vectors = embedder.embed_many(
            [row["chunk_text"] for row in chunks], text_type="chunk"
        )

        write_json(
            folder / "model_metadata.json",
            {
                "method": embedder.method,
                "model_name_or_path": embedder.model_name_or_path,
                "requested_revision": embedder.model_revision,
                "max_seq_length": (
                    embedder.model.max_seq_length
                    if embedder.model is not None
                    else None
                ),
                "query_prefix": (
                    "query: "
                    if embedder.method == "RETRIEVAL_BI_ENCODER"
                    else None
                ),
                "passage_prefix": (
                    "passage: "
                    if embedder.method == "RETRIEVAL_BI_ENCODER"
                    else None
                ),
                "normalize_embeddings": False,
                "max_input_tokens": (
                    embedder.max_input_tokens
                    if embedder.model is not None else None
                ),
            },
        )

        np.save(folder / "question_embeddings.npy", question_vectors)
        np.save(folder / "chunk_embeddings.npy", chunk_vectors)

        write_json(
            folder / "question_ids.json",
            [row["question_id"] for row in questions],
        )
        write_json(
            folder / "chunk_ids.json", [row["chunk_id"] for row in chunks]
        )

        if model["method"].upper() == "TF_IDF":
            joblib.dump(
                embedder.vectorizer, folder / "tfidf_vectorizer.joblib"
            )

        metric = model.get("similarity", "cosine")
        np.save(
            folder / "matrix.npy",
            compare_embeddings(metric, question_vectors, chunk_vectors),
        )

        artifacts[name] = {
            "matrix": str((folder / "matrix.npy").resolve()),
            "question_ids": str((folder / "question_ids.json").resolve()),
            "chunk_ids": str((folder / "chunk_ids.json").resolve()),
            "higher_is_better": metric != "euclidean",
        }
        
    write_json(output / "representations.json", artifacts)

    print(
        f"New artifacts: {output}; "
        "copy representations.json into an experiment config"
    )


if __name__ == "__main__":
    main()
