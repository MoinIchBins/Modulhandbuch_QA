from pathlib import Path
import tempfile
import unittest

from scripts.core.config import write_json, write_jsonl
from scripts.preparation.dataset import rebuild_dataset


class DatasetTests(unittest.TestCase):

    def test_dataset_replay_rejects_overlap_before_writing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_jsonl(
                root / "questions.jsonl",
                [{"question_id": q} for q in ("a", "b", "c")],
            )
            write_jsonl(
                root / "gold.jsonl",
                [
                    {"question_id": q, "all_required_chunk_ids": []}
                    for q in ("a", "b", "c")
                ],
            )
            for split, ids in (
                ("development", ["a"]),
                ("validation", ["a"]),
                ("test", ["c"]),
            ):
                write_json(root / f"{split}_question_ids.json", ids)
            with self.assertRaisesRegex(ValueError, "disjoint"):
                rebuild_dataset(
                    root / "questions.jsonl",
                    root / "gold.jsonl",
                    root,
                    root / "out",
                    False,
                )
            self.assertFalse((root / "out").exists())


if __name__ == "__main__":
    unittest.main()
