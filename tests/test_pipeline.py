import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import numpy as np

from scripts.core.config import load_config, read_json, read_jsonl, write_json, write_jsonl
from scripts.core.evaluation import QAMappingEvaluator
from scripts.core.pipeline import development, initialize_run, preflight, test as test_stage, validation, require_stage
from scripts.core.ranking import group_winners
from scripts.core.search import neighboring_interval
from scripts.manual_review.prefilter import prefilter
from scripts.manual_review.review import load_reviews, review_case, run_review


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        write_jsonl(self.root / 'gold.jsonl', [
            {'question_id': 'd1', 'all_required_chunk_ids': ['a']},
            {'question_id': 'd2', 'all_required_chunk_ids': []},
            {'question_id': 'v1', 'all_required_chunk_ids': ['b']},
            {'question_id': 't1', 'all_required_chunk_ids': ['a']},
        ])
        write_jsonl(self.root / 'chunks.jsonl', [{'chunk_id': x, 'chunk_text': x} for x in ['a', 'b', 'c']])
        write_json(self.root / 'q.json', ['d1', 'd2', 'v1', 't1'])
        write_json(self.root / 'c.json', ['a', 'b', 'c'])
        for name, ids in [('development', ['d1', 'd2']), ('validation', ['v1']), ('test', ['t1'])]:
            write_json(self.root / (name + '.json'), ids)
        np.save(self.root / 'matrix.npy', [[.9, .2, .1], [.1, .1, .1], [.1, .8, .1], [.8, .2, .1]])
        self.config = {
            'schema_version': 1, 'name': 'fixture', 'project_root': '.',
            'gold_path': 'gold.jsonl', 'chunks_path': 'chunks.jsonl', 'output_dir': 'run',
            'splits': {name: name + '.json' for name in ['development', 'validation', 'test']},
            'representations': {'small': {'matrix': 'matrix.npy', 'question_ids': 'q.json', 'chunk_ids': 'c.json', 'higher_is_better': True}},
            'development': {'experiments': [{'representation': 'small', 'method': 'top_k_threshold', 'top_k': 1, 'threshold': .5}]},
            'validation_candidate_limit': 1, 'baselines': {'enabled': False}, 'reports': False,
        }
        self.path = self.root / 'config.json'

    def load(self):
        write_json(self.path, self.config)
        return load_config(self.path)

    def run_all(self):
        config = self.load()
        initialize_run(config, preflight(config))
        with contextlib.redirect_stdout(io.StringIO()):
            development(config)
            validation(config)
            test_stage(config)
        return config

    def test_full_run_and_overwrite_protection(self):
        config = self.run_all()
        for stage in ('development', 'validation', 'test'):
            require_stage(self.root / 'run' / stage)
            row = read_jsonl(self.root / 'run' / stage / 'summary.jsonl')[0]
            self.assertEqual(row['mean_question_f1'], 1)
        with self.assertRaises(FileExistsError):
            development(config)

    def test_split_overlap_and_label_mismatch_fail(self):
        config = self.load()
        write_json(self.root / 'test.json', ['v1'])
        with self.assertRaisesRegex(ValueError, 'Overlapping'):
            preflight(config)
        write_json(self.root / 'test.json', ['t1'])
        rows = read_jsonl(self.root / 'gold.jsonl')
        rows[0]['split'] = 'test'
        write_jsonl(self.root / 'gold.jsonl', rows)
        with self.assertRaisesRegex(ValueError, 'split label'):
            preflight(config)

    def test_matrix_alignment_and_nonfinite_fail(self):
        config = self.load()
        np.save(self.root / 'matrix.npy', np.zeros((1, 3)))
        with self.assertRaisesRegex(ValueError, 'matrix shape'):
            preflight(config)
        np.save(self.root / 'matrix.npy', np.full((4, 3), np.nan))
        with self.assertRaisesRegex(ValueError, 'non-finite'):
            preflight(config)

    def test_duplicate_ids_and_invalid_parameters_fail(self):
        config = self.load()
        write_json(self.root / 'development.json', ['d1', 'd1'])
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            preflight(config)
        write_json(self.root / 'development.json', ['d1', 'd2'])
        config['development']['experiments'][0]['top_k'] = 4
        with self.assertRaisesRegex(ValueError, 'Invalid top_k'):
            preflight(config)

    def test_distance_direction_is_used(self):
        self.config['representations']['small']['higher_is_better'] = False
        self.config['development']['experiments'][0]['threshold'] = .5
        matrix = np.load(self.root / 'matrix.npy')
        np.save(self.root / 'matrix.npy', 1 - matrix)
        self.run_all()
        self.assertEqual(read_jsonl(self.root / 'run/test/summary.jsonl')[0]['mean_question_f1'], 1)

    def test_changed_inputs_cannot_join_existing_run(self):
        config = self.run_all()
        matrix = np.load(self.root / 'matrix.npy'); matrix[0, 0] = .91
        np.save(self.root / 'matrix.npy', matrix)
        with self.assertRaisesRegex(ValueError, 'different config, inputs'):
            initialize_run(config, preflight(config))

    def test_winner_tampering_is_rejected(self):
        config = self.load()
        initialize_run(config, preflight(config))
        development(config); validation(config)
        path = self.root / 'run/validation/frozen_winner.json'
        frozen = read_json(path); frozen['winner']['threshold'] = .2
        write_json(path, frozen)
        with self.assertRaisesRegex(ValueError, 'artifact changed'):
            test_stage(config)

    def test_no_test_without_validation(self):
        config = self.load()
        initialize_run(config, preflight(config))
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            test_stage(config)

    def test_prefilter_writes_empty_categories(self):
        config = self.run_all()
        prefilter(config, 'validation')
        paths = list((self.root / 'run/manual_review/validation').glob('*.csv'))
        self.assertEqual(len(paths), 4)
        self.assertTrue(all(len(path.read_text().splitlines()) == 1 for path in paths))

    def test_missing_predictions_are_not_abstentions(self):
        config = self.load(); evaluator = QAMappingEvaluator(config['gold_path'])
        empty = evaluator.eval([{'question_id': 'd2', 'chunk_ids': []}], ['d2'])
        missing = evaluator.eval([], ['d2'])
        self.assertEqual(empty['summary']['mean_question_f1'], 1)
        self.assertEqual(missing['summary']['unanswered_question_count'], 1)
        self.assertEqual(missing['summary']['evaluated_question_count'], 0)

    def test_winning_rows_and_ties_are_preserved(self):
        common = {'representation': 'x', 'method': 'threshold', 'mean_question_f1': 1, 'exact_match_rate': 1, 'mean_question_precision': 1, 'average_selected_chunks': 1}
        winner = {**common, 'threshold': None}
        runner_up = {**common, 'mean_question_f1': .5, 'threshold': .8}
        self.assertEqual(group_winners([winner, runner_up]), [winner])
        self.assertEqual(group_winners([winner, {**winner, 'threshold': .9}]), [winner])

    def test_fine_interval_edges(self):
        self.assertEqual(neighboring_interval([.1, .2, .3], .1, 0, 1), (0, .2))
        self.assertEqual(neighboring_interval([.1, .2, .3], .3, 0, .35), (.2, .35))

    def test_fine_bounds_are_not_tested_against_a_fake_winner(self):
        self.config['development'] = {
            'experiments': [{'representation': 'small', 'method': 'threshold', 'threshold': x} for x in (.1, .5, .9)],
            'fine_searches': [{'representation': 'small', 'method': 'threshold', 'parameter': 'threshold', 'lower': .7, 'upper': .9, 'points': 3}],
        }
        preflight(self.load())

    def test_cli_requires_explicit_test_confirmation(self):
        from scripts.run_experiment import main
        self.load()
        with patch('sys.argv', ['run', '--config', str(self.path)]), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as failure:
                main()
        self.assertEqual(failure.exception.code, 2)
        self.assertFalse((self.root / 'run').exists())

    def test_existing_baseline_reference_cannot_be_changed(self):
        from scripts.core.baselines import freeze_reference
        config = self.load()
        self.assertEqual(freeze_reference(config), ['a'])
        path = self.root / 'run/baselines/most_frequent_answer.json'
        write_json(path, {'chunk_ids': ['b']})
        with self.assertRaisesRegex(ValueError, 'no longer matches'):
            freeze_reference(config)

    def test_review_commands_autosave_and_quit(self):
        row = {'question_id': 'x', 'question': 'test', 'source_error_group': 'manual_wrong_nonempty', 'gold_chunk_ids': 'a', 'predicted_chunk_ids': 'b', 'manual_category': '', 'manual_category_code': '', 'manual_note': ''}
        path = self.root / 'review.csv'
        commands = iter(['p', 'g', 'a', '1', 'note'])
        with patch('builtins.input', side_effect=lambda _: next(commands)), patch('scripts.manual_review.review.open_chunk') as opened, contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(review_case(row, 1, 1, [row], path, 'http://localhost:8000/'))
        self.assertEqual(opened.call_count, 5)
        self.assertIn('valid_alternative_evidence', path.read_text())
        self.assertFalse(path.with_suffix('.tmp').exists())
        with patch('builtins.input', return_value='q'), patch('scripts.manual_review.review.open_chunk'), contextlib.redirect_stdout(io.StringIO()):
            self.assertFalse(review_case(row, 1, 1, [row], path, 'http://localhost:8000/'))

    def test_review_startup_failure_stops_server(self):
        browser = self.root / 'browser'; browser.mkdir(); (browser / 'index.html').write_text('test')
        source = self.root / 'source.csv'
        source.write_text('question_id,question,gold_chunk_ids,predicted_chunk_ids\nx,test,a,b\n')
        server = Mock(); server.poll.return_value = None
        with patch('scripts.manual_review.review.subprocess.Popen', return_value=server), patch('scripts.manual_review.review.time.sleep', side_effect=RuntimeError('interrupted')):
            with self.assertRaisesRegex(RuntimeError, 'interrupted'):
                run_review(self.root / 'chunks.jsonl', browser, {'manual_wrong_nonempty': source}, None, self.root / 'review.csv', 8000)
        server.terminate.assert_called_once(); server.wait.assert_called_once()


if __name__ == '__main__':
    unittest.main()
