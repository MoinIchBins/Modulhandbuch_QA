import json
from pathlib import Path

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


embeddings_dir = Path("data/produced_v1/embeddings")
similiarities_dir = Path("data/produced_v1/similarity_matrices")
gold_file = Path("data/processed/qamappings/qa_mapping_merged.jsonl")

embedding_methods = [
    "tf_idf",
    "sentence_bert",
    "retrieval_bi_encoder",
]

expected_question_count = 600
expected_chunk_count = 201

# Random matrix cells to recompute independently
cosine_spot_checks = 5
random_seed = 42


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_jsonl(path):
    rows = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    return rows


def check(condition, message):
    if condition:
        print(f"  [PASS] {message}")
        return True

    print(f"  [FAIL] {message}")
    return False


def main():
    print("qa retrieval embedding and similarity check")

    all_checks_passed = True
    gold_rows = load_jsonl(gold_file)

    # Keep the IDs so the methods can be compared afterward
    method_question_ids = {}
    method_chunk_ids = {}

    rng = np.random.default_rng(random_seed)

    for method in embedding_methods:
        print(f"method: {method}")

        embedding_dir = embeddings_dir / method
        similarity_dir = similiarities_dir / method

        question_embeddings_path = embedding_dir / "question_embeddings.npy"
        chunk_embeddings_path = embedding_dir / "chunk_embeddings.npy"
        embedding_question_ids_path = embedding_dir / "question_ids.json"
        embedding_chunk_ids_path = embedding_dir / "chunk_ids.json"

        similarity_matrix_path = similarity_dir / "cosine_similarity_matrix.npy"
        similarity_question_ids_path = similarity_dir / "question_ids.json"
        similarity_chunk_ids_path = similarity_dir / "chunk_ids.json"

        required_files = [
            question_embeddings_path,
            chunk_embeddings_path,
            embedding_question_ids_path,
            embedding_chunk_ids_path,
            similarity_matrix_path,
            similarity_question_ids_path,
            similarity_chunk_ids_path,
        ]

        files_exist = True

        for path in required_files:
            result = check(path.exists(), f"File exists: {path}")
            files_exist &= result
            all_checks_passed &= result

        if not files_exist:
            print(
                "\n  Cannot continue checks for this method because files are missing."
            )
            continue

        question_embeddings = np.load(question_embeddings_path)
        chunk_embeddings = np.load(chunk_embeddings_path)

        embedding_question_ids = load_json(embedding_question_ids_path)
        embedding_chunk_ids = load_json(embedding_chunk_ids_path)

        similarity_matrix = np.load(similarity_matrix_path)

        similarity_question_ids = load_json(similarity_question_ids_path)
        similarity_chunk_ids = load_json(similarity_chunk_ids_path)

        method_question_ids[method] = embedding_question_ids
        method_chunk_ids[method] = embedding_chunk_ids

        result = check(
            len(embedding_question_ids) == expected_question_count,
            f"{expected_question_count} question IDs "
            f"(found {len(embedding_question_ids)})",
        )
        all_checks_passed &= result

        result = check(
            len(embedding_chunk_ids) == expected_chunk_count,
            f"{expected_chunk_count} chunk IDs "
            f"(found {len(embedding_chunk_ids)})",
        )
        all_checks_passed &= result

        result = check(
            len(embedding_question_ids) == len(set(embedding_question_ids)),
            "Question IDs are unique",
        )
        all_checks_passed &= result

        result = check(
            len(embedding_chunk_ids) == len(set(embedding_chunk_ids)),
            "Chunk IDs are unique",
        )
        all_checks_passed &= result

        result = check(
            question_embeddings.shape[0] == len(embedding_question_ids),
            (
                "Question embedding rows match question IDs "
                f"({question_embeddings.shape[0]} rows)"
            ),
        )
        all_checks_passed &= result

        result = check(
            chunk_embeddings.shape[0] == len(embedding_chunk_ids),
            (
                "Chunk embedding rows match chunk IDs "
                f"({chunk_embeddings.shape[0]} rows)"
            ),
        )
        all_checks_passed &= result

        result = check(
            question_embeddings.shape[1] == chunk_embeddings.shape[1],
            (
                "Question and chunk embedding dimensions match "
                f"({question_embeddings.shape[1]})"
            ),
        )
        all_checks_passed &= result

        print(f"\n  Question embeddings shape: {question_embeddings.shape}")
        print(f"  Chunk embeddings shape:    {chunk_embeddings.shape}")

        expected_shape = (
            len(embedding_question_ids),
            len(embedding_chunk_ids),
        )

        result = check(
            similarity_matrix.shape == expected_shape,
            f"Cosine matrix shape is correct {similarity_matrix.shape}",
        )
        all_checks_passed &= result

        result = check(
            embedding_question_ids == similarity_question_ids,
            "Embedding and similarity question ID order matches exactly",
        )
        all_checks_passed &= result

        result = check(
            embedding_chunk_ids == similarity_chunk_ids,
            "Embedding and similarity chunk ID order matches exactly",
        )
        all_checks_passed &= result

        arrays = {
            "question embeddings": question_embeddings,
            "chunk embeddings": chunk_embeddings,
            "similarity matrix": similarity_matrix,
        }

        for name, array in arrays.items():
            result = check(
                not np.isnan(array).any(),
                f"No NaN values in {name}",
            )
            all_checks_passed &= result

            result = check(
                not np.isinf(array).any(),
                f"No infinite values in {name}",
            )
            all_checks_passed &= result

        minimum = float(similarity_matrix.min())
        maximum = float(similarity_matrix.max())

        print(f"\n  Cosine score range: {minimum:.6f} to {maximum:.6f}")

        # Leave a margin for floating-point overshoot
        result = check(
            minimum >= -1.000001 and maximum <= 1.000001,
            "Cosine scores are within [-1, 1]",
        )
        all_checks_passed &= result

        print("\n  Cosine spot checks:")
        spot_checks_passed = True

        for _ in range(cosine_spot_checks):
            q_index = rng.integers(0, question_embeddings.shape[0])
            c_index = rng.integers(0, chunk_embeddings.shape[0])

            recalculated = cosine_similarity(
                question_embeddings[q_index:q_index + 1],
                chunk_embeddings[c_index:c_index + 1],
            )[0, 0]

            stored = similarity_matrix[q_index, c_index]

            matches = np.isclose(
                recalculated,
                stored,
                rtol=1e-5,
                atol=1e-7,
            )

            q_id = embedding_question_ids[q_index]
            c_id = embedding_chunk_ids[c_index]

            if matches:
                print(f"    [PASS] {q_id} × {c_id}: {stored:.6f}")
            else:
                print(
                    f"    [FAIL] {q_id} × {c_id}: "
                    f"stored={stored:.6f}, "
                    f"recalculated={recalculated:.6f}"
                )

            spot_checks_passed &= matches

        all_checks_passed &= spot_checks_passed

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
            q_id = embedding_question_ids[q_index]

            print(f"\n    {q_id}")

            for rank, c_index in enumerate(top_indices, start=1):
                c_id = embedding_chunk_ids[c_index]
                score = scores[c_index]

                print(f"      {rank}. {c_id} {score:.6f}")

    # Make sure every method used the same ordering
    print("crossmethod in order")

    loaded_methods = list(method_question_ids.keys())

    if loaded_methods:
        reference_method = loaded_methods[0]
        reference_question_ids = method_question_ids[reference_method]
        reference_chunk_ids = method_chunk_ids[reference_method]

        for method in loaded_methods[1:]:
            result = check(
                method_question_ids[method] == reference_question_ids,
                f"{method} question order matches {reference_method}",
            )
            all_checks_passed &= result

            result = check(
                method_chunk_ids[method] == reference_chunk_ids,
                f"{method} chunk order matches {reference_method}",
            )
            all_checks_passed &= result

    print("gold label checks")

    if not loaded_methods:
        print("[FAIL] No embedding method was successfully loaded.")
        all_checks_passed = False

    else:
        question_ids = set(method_question_ids[loaded_methods[0]])
        chunk_ids = set(method_chunk_ids[loaded_methods[0]])

        gold_question_ids = []
        all_gold_chunk_ids = set()

        gold_size_counts = {
            "0": 0,
            "1": 0,
            "2": 0,
            "3+": 0,
        }

        for row in gold_rows:
            question_id = row["question_id"]
            required_chunks = row.get("all_required_chunk_ids", [])

            gold_question_ids.append(question_id)
            all_gold_chunk_ids.update(required_chunks)

            count = len(required_chunks)

            if count == 0:
                gold_size_counts["0"] += 1
            elif count == 1:
                gold_size_counts["1"] += 1
            elif count == 2:
                gold_size_counts["2"] += 1
            else:
                gold_size_counts["3+"] += 1

        result = check(
            len(gold_question_ids) == len(set(gold_question_ids)),
            "Gold question IDs are unique",
        )
        all_checks_passed &= result

        missing_questions = set(gold_question_ids) - question_ids

        result = check(
            len(missing_questions) == 0,
            "Every gold question exists in similarity matrix",
        )
        all_checks_passed &= result

        if missing_questions:
            print("\n  Missing gold questions:")

            for question_id in sorted(missing_questions):
                print(f"    {question_id}")

        missing_chunks = all_gold_chunk_ids - chunk_ids

        result = check(
            len(missing_chunks) == 0,
            "Every gold-required chunk exists in similarity matrix",
        )
        all_checks_passed &= result

        if missing_chunks:
            print("\n  Missing gold chunks:")

            for chunk_id in sorted(missing_chunks):
                print(f"    {chunk_id}")

    if all_checks_passed:
        print("READY TO RESUME: YES")
        print("\nAll automatic integrity checks passed.")
    else:
        print("READY TO RESUME: NO")
        print("\nAt least one integrity check failed.")
        print("Resolve the failed checks before running ranking evaluation.")


if __name__ == "__main__":
    main()
