# JSONL Chunk Browser

A local, dependency-free browser for reviewing retrieval chunks in `chunks.jsonl` and copying exact `chunk_id` values while creating a QA dataset.

## Files

```text
index.html
styles.css
app.js
chunks.jsonl   # input file supplied by the user
```

The application itself consists of `index.html`, `styles.css`, and `app.js`. It has no framework, package, build, database, API, CDN, or internet dependency.

## Setup and run

Place a valid JSONL file named `chunks.jsonl` in the same directory as the application files. Then start a static file server from that directory:

```bash
cd tools/chunk_browser
python -m http.server 8000
```

Open:

```text
http://localhost:8000/
```

Do not open `index.html` directly with a `file://` URL. Browsers normally block `fetch()` access to the adjacent JSONL file in that mode.

## Input behavior

The browser reads one JSON object per non-empty line from `chunks.jsonl`.

Display text is selected from the first string field found in this order:

1. `chunk_text`
2. `text`
3. `content`
4. `page_content`

The browser safely displays all JSONL values as text and never inserts dataset content with `innerHTML`.

### Ordering

- Records with a valid numeric `source_order` are sorted numerically.
- Equal `source_order` values use original JSONL line order as a stable tie-breaker.
- Records without a valid `source_order` retain their relative JSONL line order and appear after records with valid numeric order.
- `chunk_id` is never used as a sort key.

## Usage

- Click a chunk to select it.
- Use **Copy ID** on a chunk to copy only its exact `chunk_id`.
- Search filters case-insensitively across IDs and displayed text without changing order.
- The toolbar keeps the selected ID visible.
- The URL is updated as `?chunk_id=<encoded ID>` using `history.replaceState`.
- Opening a URL with a known `chunk_id` selects and scrolls to the first matching record.

### Keyboard shortcuts

| Key | Action |
|---|---|
| `ArrowUp` | Select previous visible chunk |
| `ArrowDown` | Select next visible chunk |
| `Enter` | Copy selected chunk ID |
| `Escape` | Clear search |
| `/` | Focus search, unless typing in a form field |

Keyboard shortcuts do not run while the user is typing, using a button, or actively selecting text.

## Error handling

The interface continues loading valid records when individual lines are malformed. It reports:

- malformed JSONL line numbers;
- missing or invalid `chunk_id` values;
- missing displayable text;
- duplicate `chunk_id` values;
- failed file loading;
- unknown `chunk_id` URL parameters.

Duplicate IDs are never renamed. Each rendered `<article>` gets a separate safe, unique DOM ID while retaining the exact original value in `data-chunk-id`.

## Data model and source compatibility

Each normalized record preserves the complete original JSON object and includes:

```javascript
{
  originalRecord,
  originalLineNumber,
  originalIndex,
  chunkId,
  displayText,
  sourceOrder,
  pageStart,
  pageEnd,
  sectionPath,
  hasValidChunkId,
  hasDisplayText
}
```

Rendered articles include:

```html
id="chunk-<safe-id>"
data-chunk-id="<original chunk_id>"
data-page-start="..."
data-page-end="..."
data-source-order="..."
```

The internal function `getSourceReference(chunk)` currently returns:

```javascript
{
  chunkId,
  pageStart,
  pageEnd,
  sectionPath
}
```

It is exposed as `window.chunkBrowser.getSourceReference` for future integration.

### Future paragraph-level source highlighting

A later version can optionally load a separate file such as `chunk_source_mapping.json`:

```json
{
  "CHUNK_ID": [
    "page-1-paragraph-3"
  ]
}
```

A source-document component could then:

1. read the selected chunk through `window.chunkBrowser.getSelectedChunk()`;
2. look up its exact `chunkId` in the mapping;
3. locate source elements by paragraph ID;
4. highlight or scroll those source elements;
5. fall back to `pageStart`, `pageEnd`, and `sectionPath` from `getSourceReference()` when no exact mapping exists.

The browser does not request this mapping file now, so it continues to work when the file is absent. No source-document pane is included in the current implementation.

## Runtime self-checks

`runSelfChecks()` verifies:

- rendered record count matches the prepared valid-record count;
- each rendered article maps to a normalized record;
- valid IDs are preserved in `data-chunk-id`;
- visible records remain in expected order;
- DOM IDs are unique;
- at most one record has `aria-selected="true"`;
- enabled copy buttons only belong to chunks with valid IDs.

Failures appear in a developer diagnostics section and in the browser console. The function is also available as:

```javascript
window.chunkBrowser.runSelfChecks()
```

## Assumptions and limitations

- The JSONL file must be named `chunks.jsonl` and be served from the same directory.
- JSON values must fit in browser memory. All valid chunks are intentionally rendered on one scrollable page.
- When duplicate `chunk_id` values exist, URL navigation selects the first matching record and shows a warning.
- Clipboard access varies by browser security policy. The app uses the Clipboard API when permitted and falls back to `document.execCommand("copy")`.
- The tool does not edit the JSONL file or write a QA dataset; it supports human review and ID capture.
