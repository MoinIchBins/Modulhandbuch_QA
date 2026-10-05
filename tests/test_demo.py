"""Check the demo against published artifacts without loading neural weights."""

import unittest
from io import BytesIO
import hashlib

from pypdf import PdfReader

import numpy as np

from scripts.core.config import read_json, read_jsonl
from tools.demo.app import Demo, ROOT
from scripts.preparation.similarity import compare_embeddings


class DemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.demo = Demo()

    def test_catalog_matches_frozen_winner_and_document(self):
        catalog = self.demo.catalog()
        self.assertEqual(len(catalog["models"]), 5)
        self.assertEqual(len(catalog["chunks"]), 201)
        winner = read_json(ROOT / "artifacts/experiments/base/validation/frozen_winner.json")
        first = self.demo.models[0]
        for key, value in winner["winner"].items():
            self.assertEqual(first[key], value)
        self.assertEqual(
            [row["source_order"] for row in catalog["chunks"]],
            sorted(row["source_order"] for row in catalog["chunks"]),
        )

    def test_pdf_positions_cover_all_chunks(self):
        positions = read_json(ROOT / "tools/demo/pdf_highlights.json")["chunks"]
        self.assertEqual(set(positions), {chunk["chunk_id"] for chunk in self.demo.chunks})
        for chunk in self.demo.chunks:
            entry = positions[chunk["chunk_id"]]
            self.assertTrue(any(entry["pages"].values()), chunk["chunk_id"])
            self.assertEqual(set(map(int, entry["pages"])), set(range(chunk["page_start"], chunk["page_end"] + 1)))

    def test_pdf_highlights_preserve_document_and_open_large(self):
        source = ROOT / "data/raw/PO_25_CL.pdf"
        before = hashlib.sha256(source.read_bytes()).hexdigest()
        original = PdfReader(source)
        # Ordinary text, a cross-page paragraph, and a multi-line table cell.
        for chunk_id in ("PO25CL-GEN-C01-P01-A01", "PO25CL-GEN-C02-P06-U01", "PO25CL-APP-R01"):
            reader = PdfReader(BytesIO(self.demo.highlighted_pdf(chunk_id)))
            self.assertEqual(len(reader.pages), len(original.pages))
            self.assertEqual(float(reader.trailer["/Root"]["/OpenAction"][-1]), 1.25)
            self.assertEqual(reader.trailer["/Root"]["/PageLayout"], "/SinglePage")
            annotations = [annotation.get_object() for page in reader.pages for annotation in page.get("/Annots", [])]
            highlights = [annotation for annotation in annotations if annotation["/Subtype"] == "/Highlight"]
            self.assertTrue(highlights)
            for annotation in highlights:
                self.assertEqual(len(annotation["/QuadPoints"]), 8)
                self.assertIn("/AP", annotation)
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before)
        with self.assertRaises(ValueError):
            self.demo.highlighted_pdf("unknown")

    def test_invalid_questions_and_models(self):
        model_id = self.demo.models[0]["experiment"]
        for question in (None, "", "  ", "a" * 4001, []):
            with self.subTest(question=str(question)[:20]):
                with self.assertRaises(ValueError):
                    self.demo.predict(question, model_id)
        with self.assertRaises(ValueError):
            self.demo.predict("Eine Frage", "unknown")

    def test_new_question_and_abstention(self):
        for model in self.demo.models:
            if model["representation"] != "tfidf":
                continue
            selected = self.demo.predict(
                "Welche Regel gilt, wenn ich eine Prüfung erneut ablegen möchte?",
                model["experiment"],
            )
            self.assertLessEqual(len(selected["chunk_ids"]), 2)
            self.assertEqual(len(selected["chunk_ids"]), len(selected["scores"]))
            empty = self.demo.predict("zzzxxyyvvvqqq", model["experiment"])
            self.assertEqual(empty["chunk_ids"], [])

    def test_tfidf_scores_and_predictions_reproduce_validation(self):
        encoder, vectors, chunk_ids = self.demo.load_representation("tfidf")
        folder = ROOT / "artifacts/representations/full_text/tfidf"
        questions = {
            row["question_id"]: row["question"]
            for row in read_jsonl(ROOT / "data/frozen/qSet_PO.jsonl")
        }
        question_ids = read_json(folder / "question_ids.json")
        scores = compare_embeddings(
            "cosine", encoder.transform([questions[id] for id in question_ids]).toarray(), vectors
        )
        np.testing.assert_allclose(scores, np.load(folder / "matrix.npy"), atol=1e-12)
        for model in self.demo.models:
            if model["representation"] != "tfidf":
                continue
            path = ROOT / "artifacts/experiments/base/validation" / f"{model['experiment']}_predictions.jsonl"
            for expected in read_jsonl(path):
                actual = self.demo.predict(questions[expected["question_id"]], model["experiment"])
                self.assertEqual(actual["chunk_ids"], expected["chunk_ids"])


if __name__ == "__main__":
    unittest.main()
