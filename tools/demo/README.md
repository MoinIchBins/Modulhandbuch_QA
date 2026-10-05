# Prüfungsordnung QA-Demo

Die Demo liegt unter `tools/demo` im Projekt `PythonII_AP_QA_Model`.
Sie läuft als lokaler Python-Server auf deinem Rechner. Nach dem Start ist sie unter
[http://127.0.0.1:8001](http://127.0.0.1:8001) im Browser erreichbar.
Das Terminal muss während der Nutzung geöffnet bleiben.

## Start auf deinem Mac

Die Projektumgebung `.venv`, die vorbereiteten Repräsentationen und der E5-Checkpoint
sind auf diesem Rechner bereits vorhanden. Öffne ein Terminal und führe aus:

```bash
cd /Users/alexanderdrewes/Desktop/Projects/PythonII_AP_QA_Model
.venv/bin/python -m tools.demo
```

Öffne anschließend **http://127.0.0.1:8001** im Browser.
Eine Aktivierung der Umgebung ist bei diesem Aufruf nicht erforderlich.
Beim Start werden E5 und TF-IDF einschließlich ihrer Chunk-Embeddings geladen und
mit einer kurzen Frage aufgewärmt. Alle fünf auswählbaren Varianten teilen sich
diese beiden Encoder. Warte auf **All models ready** im Terminal; erst dann nimmt
der Server Fragen entgegen. Danach bleiben beide Modelle für alle Fragen und
Modellwechsel im Speicher. Jeder neue Serverprozess muss sie erneut laden; lass
das Terminal geöffnet, um diese Startzeit nicht wiederholen zu müssen.

Zum Beenden im Terminal **Ctrl+C** drücken. Zum erneuten Starten denselben Befehl
verwenden. Nach Änderungen an Python-Dateien den Server neu starten; nach Änderungen
an der Oberfläche die Browserseite neu laden.

## Wenn Port 8001 schon belegt ist

Falls die Demo noch aus Codex oder einem anderen Terminal läuft, kannst du diese
Instanz weiter nutzen. Für eine zweite Instanz wähle einen anderen Port:

```bash
.venv/bin/python -m tools.demo --port 8002
```

Öffne dann **http://127.0.0.1:8002**. Beende eine alte Instanz in dem Terminal, in dem
sie gestartet wurde, mit **Ctrl+C**.

## Einrichtung auf einem neuen Rechner

Benötigt werden **Python 3.11** und der vollständige Projektordner. Kopiere keine
bestehende `.venv` zwischen Rechnern, sondern lege dort eine neue Umgebung an.
Führe im Projektordner aus:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install --requirement requirements.txt
.venv/bin/python -m tools.demo
```

Die Demo liest diese Projektdateien:

- `data/raw/PO_25_CL.pdf`: Original-Prüfungsordnung.
- `data/frozen/PO_25_CL_chunks.jsonl`: Text und Metadaten der Chunks.
- `artifacts/experiments/base/validation/summary.jsonl`: fünf Modellvarianten und ihre Auswahlregeln.
- `artifacts/representations/full_text/`: gespeicherte Chunk-Embeddings, IDs, TF-IDF-Vektorisierer und Modellmetadaten.
- `tools/demo/pdf_highlights.json`: vorbereitete Positionen der PDF-Markierungen.

Für E5 muss zusätzlich der in den Modellmetadaten festgelegte Checkpoint im lokalen
Hugging-Face-Cache vorhanden sein. Auf deinem aktuellen Rechner ist das bereits der
Fall. Die Demo startet standardmäßig offline.

Wenn auf einem neuen Rechner die E5-Gewichte fehlen, kannst du ihren Download einmal
zulassen:

```bash
HF_HUB_OFFLINE=0 .venv/bin/python -m tools.demo
```

Beim Start wird der festgelegte E5-Checkpoint heruntergeladen; dafür ist Internet
erforderlich. Warte auf **All models ready**. Danach den Server mit
**Ctrl+C** beenden und wieder mit dem normalen Startbefehl starten. TF-IDF benötigt
keinen heruntergeladenen Checkpoint.

## Benutzung

1. Eine eigene Frage eingeben oder eine Beispielfrage anklicken.
2. Eine der fünf Modellvarianten auswählen.
3. **Textstellen finden** anklicken.
4. Die ausgewählten Chunks erscheinen gelb markiert in der Textansicht. **Nur Treffer** blendet andere Passagen aus.
5. Der Seitenlink eines Chunks öffnet eine vollständige PDF-Kopie mit diesem Chunk gelb markiert und 125 % Startzoom. Die Originaldatei wird nicht verändert.

Die Modelle sind bereits vor der ersten Frage geladen und aufgewärmt. Die fünf
Base-Finalisten verwenden Top-1; sie wählen deshalb null oder einen Chunk. Die
Anzeige unterstützt bis zu zwei Chunks. Top-1 ohne Schwelle wählt auch bei einer
unpassenden Frage einen Chunk. Ein Modell mit Schwelle oder Margin kann keine
Textstelle auswählen. Die Demo findet Belegstellen; sie formuliert keine Antwort.

Eigene Fragen werden zur Laufzeit eingebettet und mit den gespeicherten
Chunk-Embeddings verglichen. Die Auswahl nutzt dieselben Regeln wie das Experiment.
Lange Fragen über dem E5-Tokenlimit werden mit einer Fehlermeldung abgewiesen.
PDF-Viewer können den gewünschten Startzoom durch eigene Einstellungen überschreiben.

## Dateien der Demo

- `__main__.py`: Einstiegspunkt für `python -m tools.demo`.
- `app.py`: lokaler Server, Modellvorhersagen und PDF-Markierungen.
- `index.html`, `app.js`, `styles.css`: Oberfläche.
- `pdf_highlights.json`: Positionen der 201 Chunks im PDF.
- `prepare_pdf.py`: optionales Werkzeug zum erneuten Vorbereiten dieser Positionen.

Die Demo verwendet die gemeinsamen Funktionen des Projekts unter `scripts/`.
Der Ordner `tools/demo` allein reicht daher nicht zum Betrieb.

## PDF-Markierungen neu vorbereiten

Das ist nur erforderlich, wenn sich das PDF oder die Chunk-Datei geändert hat.
Prüfsummen verhindern, dass alte Markierungen auf geänderte Dateien angewendet
werden. Installiere hierfür die zusätzliche Vorbereitungsbibliothek `pdfplumber`:

```bash
.venv/bin/python -m pip install pdfplumber
.venv/bin/python -m tools.demo.prepare_pdf
```

Anschließend den Demo-Server neu starten. Für den normalen Betrieb ist
`pdfplumber` nicht nötig.

## Prüfungen

Aus dem Projektordner:

```bash
.venv/bin/python -m unittest discover -s tests -v
```
