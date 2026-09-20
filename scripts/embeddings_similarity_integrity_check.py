import json
from pathlib import Path

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


EMBEDDINGS_DIR = Path("data/produced_v2/embeddings")
SIMILARITIES_DIR = Path("data/produced_v2/similarity_matrices")
GOLD_FILE = Path("data/processed/qamappings/qa_mapping_merged.jsonl")

EMBEDDING_METHODS = [
    "tf_idf",
    "sentence_bert",
    "retrieval_bi_encoder",
]

EXPECTED_QUESTION_COUNT = 720
EXPECTED_CHUNK_COUNT = 201
SPOT_CHECKS = 5
RANDOM_SEED = 42


def read_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def report(ok, message):
    print(f"  [{'PASS' if ok else 'FAIL'}] {message}")
    return ok


def main():
    print("qa retrieval embedding and similarity check")

    all_ok = True
    rng = np.random.default_rng(RANDOM_SEED)
    method_question_ids = {}
    method_chunk_ids = {}

    with GOLD_FILE.open("r", encoding="utf-8") as file:
        gold_rows = [json.loads(line) for line in file if line.strip()]

    for method in EMBEDDING_METHODS:
        print(f"method: {method}")

        embedding_dir = EMBEDDINGS_DIR / method
        similarity_dir = SIMILARITIES_DIR / method

        required_files = [
            embedding_dir / "question_embeddings.npy",
            embedding_dir / "chunk_embeddings.npy",
            embedding_dir / "question_ids.json",
            embedding_dir / "chunk_ids.json",
            similarity_dir / "cosine_similarity_matrix.npy",
            similarity_dir / "question_ids.json",
            similarity_dir / "chunk_ids.json",
        ]
        missing_files = [path for path in required_files if not path.exists()]
        if missing_files:
            for path in missing_files:
                all_ok &= report(False, f"Missing file: {path}")
            continue

        question_embeddings = np.load(embedding_dir / "question_embeddings.npy")
        chunk_embeddings = np.load(embedding_dir / "chunk_embeddings.npy")
        similarity_matrix = np.load(similarity_dir / "cosine_similarity_matrix.npy")

        embedding_question_ids = read_json(embedding_dir / "question_ids.json")
        embedding_chunk_ids = read_json(embedding_dir / "chunk_ids.json")
        similarity_question_ids = read_json(similarity_dir / "question_ids.json")
        similarity_chunk_ids = read_json(similarity_dir / "chunk_ids.json")

        method_question_ids[method] = embedding_question_ids
        method_chunk_ids[method] = embedding_chunk_ids

        checks = [
            (
                len(embedding_question_ids) == EXPECTED_QUESTION_COUNT,
                f"{EXPECTED_QUESTION_COUNT} question IDs "
                f"(found {len(embedding_question_ids)})",
            ),
            (
                len(embedding_chunk_ids) == EXPECTED_CHUNK_COUNT,
                f"{EXPECTED_CHUNK_COUNT} chunk IDs "
                f"(found {len(embedding_chunk_ids)})",
            ),
            (
                question_embeddings.shape[0] == len(embedding_question_ids),
                "Question embedding rows match question IDs",
            ),
            (
                chunk_embeddings.shape[0] == len(embedding_chunk_ids),
                "Chunk embedding rows match chunk IDs",
            ),
            (
                question_embeddings.shape[1] == chunk_embeddings.shape[1],
                "Question and chunk embedding dimensions match",
            ),
            (
                similarity_matrix.shape
                == (len(embedding_question_ids), len(embedding_chunk_ids)),
                f"Cosine matrix shape is correct {similarity_matrix.shape}",
            ),
            (
                embedding_question_ids == similarity_question_ids,
                "Embedding and similarity question order matches",
            ),
            (
                embedding_chunk_ids == similarity_chunk_ids,
                "Embedding and similarity chunk order matches",
            ),
            (
                not np.isnan(question_embeddings).any()
                and not np.isnan(chunk_embeddings).any()
                and not np.isnan(similarity_matrix).any(),
                "No NaN values in embeddings or matrix",
            ),
            (
                not np.isinf(question_embeddings).any()
                and not np.isinf(chunk_embeddings).any()
                and not np.isinf(similarity_matrix).any(),
                "No infinite values in embeddings or matrix",
            ),
        ]
        for ok, message in checks:
            all_ok &= report(ok, message)

        minimum = float(similarity_matrix.min())
        maximum = float(similarity_matrix.max())
        print(f"\n  Cosine score range: {minimum:.6f} to {maximum:.6f}")
        all_ok &= report(
            minimum >= -1.000001 and maximum <= 1.000001,
            "Cosine scores are within [-1, 1]",
        )

        print("\n  Cosine spot checks:")
        for _ in range(SPOT_CHECKS):
            q_index = rng.integers(0, question_embeddings.shape[0])
            c_index = rng.integers(0, chunk_embeddings.shape[0])
            recalculated = cosine_similarity(
                question_embeddings[q_index:q_index + 1],
                chunk_embeddings[c_index:c_index + 1],
            )[0, 0]
            stored = similarity_matrix[q_index, c_index]
            ok = np.isclose(recalculated, stored, rtol=1e-5, atol=1e-7)
            q_id = embedding_question_ids[q_index]
            c_id = embedding_chunk_ids[c_index]

            if ok:
                print(f"    [PASS] {q_id} x {c_id}: {stored:.6f}")
            else:
                print(
                    f"    [FAIL] {q_id} x {c_id}: "
                    f"stored={stored:.6f}, recalculated={recalculated:.6f}"
                )
            all_ok &= ok

        print("\n  Example top-5 retrievals:")
        sample_indices = np.linspace(
            0,
            len(embedding_question_ids) - 1,
            num=min(4, len(embedding_question_ids)),
            dtype=int,
        )
        for q_index in sample_indices:
            scores = similarity_matrix[q_index]
            top_indices = np.argsort(scores)[::-1][:5]
            print(f"\n    {embedding_question_ids[q_index]}")
            for rank, c_index in enumerate(top_indices, start=1):
                print(f"      {rank}. {embedding_chunk_ids[c_index]} {scores[c_index]:.6f}")

    print("cross-method order")
    loaded_methods = list(method_question_ids)
    if loaded_methods:
        reference = loaded_methods[0]
        for method in loaded_methods[1:]:
            all_ok &= report(
                method_question_ids[method] == method_question_ids[reference],
                f"{method} question order matches {reference}",
            )
            all_ok &= report(
                method_chunk_ids[method] == method_chunk_ids[reference],
                f"{method} chunk order matches {reference}",
            )
    else:
        all_ok = False
        print("[FAIL] No embedding method was successfully loaded.")

    print("gold label checks")
    if loaded_methods:
        question_ids = set(method_question_ids[loaded_methods[0]])
        chunk_ids = set(method_chunk_ids[loaded_methods[0]])
        gold_question_ids = [row["question_id"] for row in gold_rows]
        gold_chunk_ids = {
            chunk_id
            for row in gold_rows
            for chunk_id in row.get("all_required_chunk_ids", [])
        }

        missing_questions = set(gold_question_ids) - question_ids
        missing_chunks = gold_chunk_ids - chunk_ids

        all_ok &= report(
            len(gold_question_ids) == len(set(gold_question_ids)),
            "Gold question IDs are unique",
        )
        all_ok &= report(
            not missing_questions,
            "Every gold question exists in similarity matrix",
        )
        all_ok &= report(
            not missing_chunks,
            "Every gold-required chunk exists in similarity matrix",
        )

        if missing_questions:
            print("\n  Missing gold questions:")
            for question_id in sorted(missing_questions):
                print(f"    {question_id}")

        if missing_chunks:
            print("\n  Missing gold chunks:")
            for chunk_id in sorted(missing_chunks):
                print(f"    {chunk_id}")

    if all_ok:
        print("READY TO RESUME: YES")
        print("\nAll automatic integrity checks passed.")
    else:
        print("READY TO RESUME: NO")
        print("\nAt least one integrity check failed.")
        print("Resolve the failed checks before running ranking evaluation.")


if __name__ == "__main__":
    main()
