import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from scripts.core.config import (
    load_config,
    read_json,
    read_jsonl,
    write_json,
    write_jsonl,
)
from scripts.core.evaluation import QAMappingEvaluator
from scripts.core.pipeline import (
    development,
    initialize_run,
    preflight,
    test as test_stage,
    validation,
    require_stage,
)
from scripts.core.ranking import group_winners
from scripts.core.search import neighboring_interval


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        write_jsonl(
            self.root / "gold.jsonl",
            [
                {"question_id": "d1", "all_required_chunk_ids": ["a"]},
                {"question_id": "d2", "all_required_chunk_ids": []},
                {"question_id": "v1", "all_required_chunk_ids": ["b"]},
                {"question_id": "t1", "all_required_chunk_ids": ["a"]},
            ],
        )
        write_jsonl(
            self.root / "chunks.jsonl",
            [{"chunk_id": x, "chunk_text": x} for x in ["a", "b", "c"]],
        )
        write_json(self.root / "q.json", ["d1", "d2", "v1", "t1"])
        write_json(self.root / "c.json", ["a", "b", "c"])
        for name, ids in [
            ("development", ["d1", "d2"]),
            ("validation", ["v1"]),
            ("test", ["t1"]),
        ]:
            write_json(self.root / (name + ".json"), ids)
        np.save(
            self.root / "matrix.npy",
            [
                [0.9, 0.2, 0.1],
                [0.1, 0.1, 0.1],
                [0.1, 0.8, 0.1],
                [0.8, 0.2, 0.1],
            ],
        )
        self.config = {
            "name": "fixture",
            "project_root": ".",
            "gold_path": "gold.jsonl",
            "chunks_path": "chunks.jsonl",
            "output_dir": "run",
            "splits": {
                name: name + ".json"
                for name in ["development", "validation", "test"]
            },
            "representations": {
                "small": {
                    "matrix": "matrix.npy",
                    "question_ids": "q.json",
                    "chunk_ids": "c.json",
                    "higher_is_better": True,
                }
            },
            "development": {
                "experiments": [
                    {
                        "representation": "small",
                        "method": "top_k_threshold",
                        "top_k": 1,
                        "threshold": 0.5,
                    }
                ]
            },
            "baselines": {"enabled": False},
            "reports": False,
        }
        self.path = self.root / "config.json"

    def load(self):
        write_json(self.path, self.config)
        return load_config(self.path)

    def run_all(self):
        config = self.load()
        preflight(config)
        initialize_run(config)
        with contextlib.redirect_stdout(io.StringIO()):
            development(config)
            validation(config)
            test_stage(config)
        return config

    def test_full_run_and_overwrite_protection(self):
        self.config["representations"]["other"] = dict(
            self.config["representations"]["small"]
        )
        self.config["development"]["experiments"] = [
            {"representation": name, "method": method, **parameters}
            for name in ("small", "other")
            for method, parameters in (
                ("threshold", {"threshold": 0.5}),
                ("top_k_threshold", {"top_k": 1, "threshold": 0.5}),
                ("relative_margin", {"top_k": 1, "margin": 0.1}),
            )
        ]
        config = self.run_all()
        candidates = read_json(
            self.root / "run/development/validation_candidates.json"
        )["candidates"]
        self.assertEqual(len(candidates), 5)
        self.assertEqual(
            len(read_jsonl(self.root / "run/validation/summary.jsonl")), 5
        )
        for stage in ("development", "validation", "test"):
            require_stage(self.root / "run" / stage)
            row = read_jsonl(self.root / "run" / stage / "summary.jsonl")[0]
            self.assertEqual(row["mean_question_f1"], 1)
        with self.assertRaises(FileExistsError):
            development(config)

    def test_split_overlap_and_label_mismatch_fail(self):
        config = self.load()
        write_json(self.root / "test.json", ["v1"])
        with self.assertRaisesRegex(ValueError, "Overlapping"):
            preflight(config)
        write_json(self.root / "test.json", ["t1"])
        rows = read_jsonl(self.root / "gold.jsonl")
        rows[0]["split"] = "test"
        write_jsonl(self.root / "gold.jsonl", rows)
        with self.assertRaisesRegex(ValueError, "split label"):
            preflight(config)

    def test_matrix_alignment_and_nonfinite_fail(self):
        config = self.load()
        np.save(self.root / "matrix.npy", np.zeros((1, 3)))
        with self.assertRaisesRegex(ValueError, "matrix shape"):
            preflight(config)
        np.save(self.root / "matrix.npy", np.full((4, 3), np.nan))
        with self.assertRaisesRegex(ValueError, "non-finite"):
            preflight(config)

    def test_duplicate_ids_and_invalid_parameters_fail(self):
        config = self.load()
        write_json(self.root / "development.json", ["d1", "d1"])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            preflight(config)
        write_json(self.root / "development.json", ["d1", "d2"])
        config["development"]["experiments"][0]["top_k"] = 4
        with self.assertRaisesRegex(ValueError, "Invalid top_k"):
            preflight(config)

    def test_changed_config_cannot_join_existing_run(self):
        config = self.run_all()
        manifest = read_json(self.root / "run/experiment.json")
        self.assertEqual(set(manifest), {"config", "environment"})
        self.assertNotIn("schema_version", manifest["config"])
        initialize_run(config)
        config["name"] = "another_run"
        with self.assertRaisesRegex(ValueError, "different config"):
            initialize_run(config)

    def test_winner_tampering_is_rejected(self):
        config = self.load()
        preflight(config)
        initialize_run(config)
        development(config)
        validation(config)
        path = self.root / "run/validation/frozen_winner.json"
        frozen = read_json(path)
        frozen["winner"]["threshold"] = 0.2
        write_json(path, frozen)
        with self.assertRaisesRegex(ValueError, "artifact changed"):
            test_stage(config)

    def test_no_test_without_validation(self):
        config = self.load()
        preflight(config)
        initialize_run(config)
        with self.assertRaisesRegex(ValueError, "incomplete"):
            test_stage(config)

    def test_missing_predictions_are_not_abstentions(self):
        config = self.load()
        evaluator = QAMappingEvaluator(config["gold_path"])
        empty = evaluator.eval(
            [{"question_id": "d2", "chunk_ids": []}], ["d2"]
        )
        missing = evaluator.eval([], ["d2"])
        self.assertEqual(empty["summary"]["mean_question_f1"], 1)
        self.assertEqual(missing["summary"]["unanswered_question_count"], 1)
        self.assertEqual(missing["summary"]["evaluated_question_count"], 0)

    def test_winning_rows_and_ties_are_preserved(self):
        common = {
            "representation": "x",
            "method": "threshold",
            "mean_question_f1": 1,
            "exact_match_rate": 1,
            "mean_question_precision": 1,
            "average_selected_chunks": 1,
        }
        winner = {**common, "threshold": None}
        runner_up = {**common, "mean_question_f1": 0.5, "threshold": 0.8}
        self.assertEqual(group_winners([winner, runner_up]), [winner])
        self.assertEqual(
            group_winners([winner, {**winner, "threshold": 0.9}]), [winner]
        )

    def test_fine_interval_edges(self):
        self.assertEqual(
            neighboring_interval([0.1, 0.2, 0.3], 0.1, 0, 1), (0, 0.2)
        )
        self.assertEqual(
            neighboring_interval([0.1, 0.2, 0.3], 0.3, 0, 0.35), (0.2, 0.35)
        )

    def test_cli_requires_explicit_test_confirmation(self):
        from scripts.run_experiment import main

        self.load()
        with patch(
            "sys.argv", ["run", "--config", str(self.path)]
        ), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as failure:
                main()
        self.assertEqual(failure.exception.code, 2)
        self.assertFalse((self.root / "run").exists())


if __name__ == "__main__":
    unittest.main()
