"""Serve the base experiment's five finalists as a local retrieval demo."""

import argparse
import hashlib
from io import BytesIO
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from urllib.parse import parse_qs, urlsplit

# The demo uses the pinned checkpoints already cached during preparation.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import joblib
import numpy as np

from scripts.core.config import read_json, read_jsonl
from scripts.core.ranking import rank_key
from scripts.core.selection import ChunkSelector
from scripts.preparation.similarity import compare_embeddings
from scripts.preparation.text_embedder import TextEmbedder

ROOT = Path(__file__).resolve().parents[2]


def model_label(row):
    name = {"e5": "Multilingual E5", "tfidf": "TF-IDF"}[row["representation"]]
    rule = {
        "top_k": f"Top-{row['top_k']}",
        "top_k_threshold": f"Top-{row['top_k']} · Schwelle {row.get('threshold', 0):g}",
        "relative_margin": f"Top-{row['top_k']} · Margin {row.get('margin', 0):g}",
    }[row["method"]]
    return f"{name} · {rule}"


class Demo:
    def __init__(self, root=ROOT):
        self.root = root
        self.chunks = sorted(
            read_jsonl(root / "data/frozen/PO_25_CL_chunks.jsonl"),
            key=lambda row: row["source_order"],
        )
        rows = read_jsonl(root / "artifacts/experiments/base/validation/summary.jsonl")
        self.models = sorted(rows, key=rank_key, reverse=True)[:5]
        if len(self.models) != 5:
            raise ValueError("The base validation run must contain five finalists.")
        self.representations = {}
        self.lock = Lock()

    def catalog(self):
        return {
            "models": [
                {
                    "id": row["experiment"],
                    "label": model_label(row),
                    "validation_f1": row["mean_question_f1"],
                    "max_chunks": row["top_k"],
                }
                for row in self.models
            ],
            "chunks": self.chunks,
        }

    def highlighted_pdf(self, chunk_id):
        from pypdf import PdfReader, PdfWriter
        from pypdf.annotations import Highlight
        from pypdf.generic import (
            ArrayObject, DecodedStreamObject, DictionaryObject, FloatObject,
            NameObject, NullObject, NumberObject, RectangleObject,
        )

        positions = read_json(self.root / "tools/demo/pdf_highlights.json")
        source = self.root / "data/raw/PO_25_CL.pdf"
        chunks = self.root / "data/frozen/PO_25_CL_chunks.jsonl"
        if (
            hashlib.sha256(source.read_bytes()).hexdigest() != positions["pdf_sha256"]
            or hashlib.sha256(chunks.read_bytes()).hexdigest() != positions["chunks_sha256"]
        ):
            raise ValueError("PDF oder Chunks wurden geändert. Bitte die PDF-Markierungen neu vorbereiten.")
        if chunk_id not in positions["chunks"]:
            raise ValueError("Unbekannter Chunk.")
        entry = positions["chunks"][chunk_id]
        writer = PdfWriter()
        writer.clone_document_from_reader(PdfReader(source))
        for number, rectangles in entry["pages"].items():
            for left, bottom, right, top in rectangles:
                annotation = Highlight(
                    rect=(left, bottom, right, top),
                    quad_points=ArrayObject([FloatObject(value) for value in (
                        left, top, right, top, left, bottom, right, bottom
                    )]),
                    highlight_color="ffd54f", printing=True,
                )
                # Explicit appearances make highlights visible in PDF viewers
                # that do not synthesize them from annotation quad points.
                width, height = right - left, top - bottom
                appearance = DecodedStreamObject()
                appearance.set_data(
                    f"q /GS gs 1 0.835 0.31 rg 0 0 {width} {height} re f Q".encode("ascii")
                )
                appearance.update({
                    NameObject("/Type"): NameObject("/XObject"),
                    NameObject("/Subtype"): NameObject("/Form"),
                    NameObject("/FormType"): NumberObject(1),
                    NameObject("/BBox"): RectangleObject((0, 0, width, height)),
                    NameObject("/Resources"): DictionaryObject({
                        NameObject("/ExtGState"): DictionaryObject({
                            NameObject("/GS"): DictionaryObject({
                                NameObject("/Type"): NameObject("/ExtGState"),
                                NameObject("/ca"): FloatObject(0.35),
                                NameObject("/BM"): NameObject("/Multiply"),
                            }),
                        }),
                    }),
                })
                annotation[NameObject("/AP")] = DictionaryObject({
                    NameObject("/N"): writer._add_object(appearance),
                })
                writer.add_annotation(int(number) - 1, annotation)
        page_number = next(int(n) for n, rects in entry["pages"].items() if rects)
        page = writer.pages[page_number - 1]
        top = max(rect[3] for rect in entry["pages"][str(page_number)]) + 24
        writer._root_object[NameObject("/OpenAction")] = ArrayObject([
            page.indirect_reference, NameObject("/XYZ"), NullObject(),
            FloatObject(top), FloatObject(1.25),
        ])
        writer.page_layout = "/SinglePage"
        output = BytesIO()
        writer.write(output)
        return output.getvalue()

    def load_representation(self, name):
        if name not in self.representations:
            folder = self.root / "artifacts/representations/full_text" / name
            metadata = read_json(folder / "model_metadata.json")
            chunk_ids = read_json(folder / "chunk_ids.json")
            vectors = np.load(folder / "chunk_embeddings.npy")
            if vectors.shape[0] != len(chunk_ids) or set(chunk_ids) != {
                row["chunk_id"] for row in self.chunks
            }:
                raise ValueError("Chunk embeddings do not match the regulation.")
            if name == "tfidf":
                encoder = joblib.load(folder / "tfidf_vectorizer.joblib")
            else:
                encoder = TextEmbedder(
                    metadata["method"], [],
                    model_name_or_path=metadata["model_name_or_path"],
                    model_revision=metadata["requested_revision"],
                    max_seq_length=metadata["max_seq_length"],
                )
            self.representations[name] = (encoder, vectors, chunk_ids)
        return self.representations[name]

    def predict(self, question, model_id):
        if not isinstance(question, str) or not question.strip():
            raise ValueError("Bitte gib eine Frage ein.")
        question = question.strip()
        if len(question) > 4000:
            raise ValueError("Bitte begrenze die Frage auf 4.000 Zeichen.")
        model = next((row for row in self.models if row["experiment"] == model_id), None)
        if model is None:
            raise ValueError("Bitte wähle eines der fünf Modelle aus.")
        with self.lock:
            encoder, vectors, chunk_ids = self.load_representation(model["representation"])
            if model["representation"] == "tfidf":
                question_vector = encoder.transform([question]).toarray()
            else:
                question_vector = encoder.embed_many([question], text_type="question")
            scores = compare_embeddings("cosine", question_vector, vectors)
            if not np.isfinite(scores).all():
                raise ValueError("Das Modell hat ungültige Ähnlichkeitswerte geliefert.")
            selected = ChunkSelector(
                model["method"], top_k=model.get("top_k"),
                threshold=model.get("threshold"), margin=model.get("margin"),
            ).select(scores, chunk_ids)[0]
        # A display cap keeps the demo in the requested 0–2 range, even if the
        # finalist list changes. The published five finalists all use top_k=1.
        return {
            "question": question,
            "model_id": model_id,
            "chunk_ids": selected["chunk_ids"][:2],
            "scores": selected["scores"][:2],
        }


def make_handler(demo):
    assets = demo.root / "tools/demo"
    files = {
        "/": (assets / "index.html", "text/html; charset=utf-8"),
        "/app.js": (assets / "app.js", "text/javascript; charset=utf-8"),
        "/styles.css": (assets / "styles.css", "text/css; charset=utf-8"),
        "/regulation.pdf": (demo.root / "data/raw/PO_25_CL.pdf", "application/pdf"),
    }

    class Handler(BaseHTTPRequestHandler):
        def respond(self, status, body, content_type="application/json; charset=utf-8"):
            if isinstance(body, dict):
                body = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            url = urlsplit(self.path)
            path = url.path
            if path == "/api/catalog":
                self.respond(200, demo.catalog())
            elif path == "/regulation.pdf" and url.query:
                chunk_id = parse_qs(url.query).get("chunk_id", [""])[0]
                try:
                    pdf = demo.highlighted_pdf(chunk_id)
                except ValueError as error:
                    self.respond(400, {"error": str(error)})
                else:
                    self.respond(200, pdf, "application/pdf")
            elif path in files:
                file, content_type = files[path]
                self.respond(200, file.read_bytes(), content_type)
            else:
                self.respond(404, {"error": "Nicht gefunden."})

        def do_POST(self):
            if self.path != "/api/predict":
                self.respond(404, {"error": "Nicht gefunden."})
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 20000:
                    raise ValueError("Die Anfrage ist leer oder zu groß.")
                body = json.loads(self.rfile.read(size))
                if not isinstance(body, dict):
                    raise ValueError("Ungültige Anfrage.")
                result = demo.predict(body.get("question"), body.get("model_id"))
            except (ValueError, UnicodeDecodeError) as error:
                self.respond(400, {"error": str(error)})
            except OSError:
                self.respond(503, {"error": (
                    "Modell oder Dateien fehlen lokal. Bitte die vorbereiteten "
                    "Repräsentationen und den E5-Checkpoint aus der Projektvorbereitung "
                    "bereitstellen. Der Demo-Server lädt keine Gewichte herunter."
                )})
            except Exception:
                import traceback
                traceback.print_exc()
                self.respond(500, {"error": "Die Vorhersage ist fehlgeschlagen. Details stehen im Terminal."})
            else:
                self.respond(200, result)

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(Demo()))
    print(f"QA demo: http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
