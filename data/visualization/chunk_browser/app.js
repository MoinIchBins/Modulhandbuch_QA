"use strict";

const TEXT_FIELD_PRIORITY = ["chunk_text", "text", "content", "page_content"];

const state = {
  chunks: [],
  visibleChunks: [],
  malformedLines: [],
  duplicateIds: new Map(),
  selectedChunk: null,
  domIdSet: new Set(),
  urlWarning: "",
  loadError: ""
};

const elements = {};

document.addEventListener("DOMContentLoaded", init);

async function init() {
  cacheElements();
  bindStaticEvents();

  try {
    const jsonlText = await loadJsonl("chunks.jsonl");
    const parsed = parseJsonl(jsonlText);
    const prepared = validateAndPrepareChunks(parsed.records);
    state.malformedLines = parsed.malformedLines;
    state.duplicateIds = prepared.duplicateIds;
    state.chunks = sortChunks(prepared.chunks);
    state.visibleChunks = [...state.chunks];

    renderChunks(state.chunks);
    renderDatasetSummary();
    applySearch("");

    const requestedId = readChunkIdFromUrl();
    if (requestedId !== null) {
      const matches = state.chunks.filter((chunk) => chunk.hasValidChunkId && chunk.chunkId === requestedId);
      if (matches.length > 0) {
        selectChunk(matches[0], { updateUrl: false, scroll: true, focus: false });
        if (matches.length > 1) {
          state.urlWarning = `The URL chunk_id matches ${matches.length} records. The first matching record was selected.`;
        }
      } else {
        state.urlWarning = `No chunk matches the URL chunk_id “${requestedId}”.`;
      }
    }

    renderNotices();
    updateControls();
    runSelfChecks();
    const missingIdCount = state.chunks.filter((chunk) => !chunk.hasValidChunkId).length;
    const missingTextCount = state.chunks.filter((chunk) => !chunk.hasDisplayText).length;
    elements.loadStatus.textContent = `${state.chunks.length} valid · ${state.malformedLines.length} malformed · ${missingIdCount} missing IDs · ${missingTextCount} missing text`;
  } catch (error) {
    state.loadError = error instanceof Error ? error.message : String(error);
    elements.loadStatus.textContent = "Load failed";
    elements.emptyState.hidden = false;
    elements.emptyState.textContent = "chunks.jsonl could not be loaded. See the notice above for details.";
    renderNotices();
    updateControls();
    runSelfChecks();
  }
}

function cacheElements() {
  elements.loadStatus = document.querySelector("#load-status");
  elements.searchInput = document.querySelector("#search-input");
  elements.clearSearch = document.querySelector("#clear-search");
  elements.previousChunk = document.querySelector("#previous-chunk");
  elements.nextChunk = document.querySelector("#next-chunk");
  elements.selectedChunkId = document.querySelector("#selected-chunk-id");
  elements.copySelected = document.querySelector("#copy-selected");
  elements.matchCount = document.querySelector("#match-count");
  elements.noticeArea = document.querySelector("#notice-area");
  elements.warningMessage = document.querySelector("#warning-message");
  elements.errorSummary = document.querySelector("#error-summary");
  elements.errorSummaryContent = document.querySelector("#error-summary-content");
  elements.chunkList = document.querySelector("#chunk-list");
  elements.emptyState = document.querySelector("#empty-state");
  elements.liveRegion = document.querySelector("#live-region");
  elements.diagnostics = document.querySelector("#diagnostics");
  elements.diagnosticsOutput = document.querySelector("#diagnostics-output");
}

function bindStaticEvents() {
  elements.searchInput.addEventListener("input", () => applySearch(elements.searchInput.value));
  elements.clearSearch.addEventListener("click", clearSearch);
  elements.previousChunk.addEventListener("click", () => navigateVisible(-1));
  elements.nextChunk.addEventListener("click", () => navigateVisible(1));
  elements.copySelected.addEventListener("click", () => {
    if (state.selectedChunk) {
      copyChunkId(state.selectedChunk, elements.copySelected);
    }
  });
  document.addEventListener("keydown", handleGlobalKeydown);
}

async function loadJsonl(url) {
  let response;
  try {
    response = await fetch(url, { cache: "no-store" });
  } catch (error) {
    throw new Error(`Unable to fetch ${url}. Run the files through a local static server instead of opening index.html directly. ${String(error)}`);
  }

  if (!response.ok) {
    throw new Error(`Unable to load ${url}: HTTP ${response.status} ${response.statusText}`);
  }

  return response.text();
}

function parseJsonl(text) {
  const records = [];
  const malformedLines = [];
  const lines = text.split(/\r?\n/);

  lines.forEach((line, lineIndex) => {
    const originalLineNumber = lineIndex + 1;
    if (line.trim() === "") {
      return;
    }

    try {
      records.push({
        originalRecord: JSON.parse(line),
        originalLineNumber,
        originalIndex: records.length
      });
    } catch (error) {
      malformedLines.push({
        lineNumber: originalLineNumber,
        message: error instanceof Error ? error.message : String(error)
      });
    }
  });

  return { records, malformedLines };
}

function validateAndPrepareChunks(parsedRecords) {
  const idOccurrences = new Map();

  const chunks = parsedRecords.map((parsedRecord) => {
    const record = isPlainObject(parsedRecord.originalRecord) ? parsedRecord.originalRecord : {};
    const chunkIdValue = record.chunk_id;
    const hasValidChunkId = typeof chunkIdValue === "string" && chunkIdValue.trim().length > 0;
    const chunkId = typeof chunkIdValue === "string" ? chunkIdValue : "";

    let displayText;
    let displayTextField = null;
    for (const field of TEXT_FIELD_PRIORITY) {
      if (Object.prototype.hasOwnProperty.call(record, field) && typeof record[field] === "string") {
        displayText = record[field];
        displayTextField = field;
        break;
      }
    }
    const hasDisplayText = typeof displayText === "string" && displayText.length > 0;

    const sourceOrder = parseFiniteNumber(record.source_order);
    const normalized = {
      originalRecord: parsedRecord.originalRecord,
      originalLineNumber: parsedRecord.originalLineNumber,
      originalIndex: parsedRecord.originalIndex,
      chunkId,
      displayText: typeof displayText === "string" ? displayText : "",
      displayTextField,
      sourceOrder,
      pageStart: record.page_start ?? null,
      pageEnd: record.page_end ?? null,
      sectionPath: record.section_path ?? null,
      contentType: record.content_type ?? null,
      sourceLayer: record.source_layer ?? null,
      hasValidChunkId,
      hasDisplayText,
      domId: "",
      element: null
    };

    if (hasValidChunkId) {
      const occurrences = idOccurrences.get(chunkId) ?? [];
      occurrences.push(normalized);
      idOccurrences.set(chunkId, occurrences);
    }

    return normalized;
  });

  const duplicateIds = new Map(
    [...idOccurrences.entries()].filter(([, occurrences]) => occurrences.length > 1)
  );

  return { chunks, duplicateIds };
}

function sortChunks(chunks) {
  return [...chunks].sort((a, b) => {
    const aHasOrder = Number.isFinite(a.sourceOrder);
    const bHasOrder = Number.isFinite(b.sourceOrder);

    if (aHasOrder && bHasOrder) {
      return a.sourceOrder - b.sourceOrder || a.originalIndex - b.originalIndex;
    }
    if (aHasOrder !== bHasOrder) {
      return aHasOrder ? -1 : 1;
    }
    return a.originalIndex - b.originalIndex;
  });
}

function renderChunks(chunks) {
  elements.chunkList.replaceChildren();
  state.domIdSet.clear();
  const fragment = document.createDocumentFragment();

  chunks.forEach((chunk, index) => {
    const article = document.createElement("article");
    article.className = "chunk-card";
    article.id = createUniqueDomId(chunk);
    article.dataset.chunkId = chunk.chunkId;
    article.dataset.recordIndex = String(chunk.originalIndex);
    article.dataset.lineNumber = String(chunk.originalLineNumber);
    article.setAttribute("role", "option");
    article.setAttribute("aria-selected", "false");
    article.tabIndex = -1;

    setOptionalDataAttribute(article, "pageStart", chunk.pageStart);
    setOptionalDataAttribute(article, "pageEnd", chunk.pageEnd);
    setOptionalDataAttribute(article, "sourceOrder", chunk.sourceOrder);

    const header = document.createElement("header");
    header.className = "chunk-header";

    const identity = document.createElement("div");
    identity.className = "chunk-identity";

    const idLabel = document.createElement("span");
    idLabel.className = "chunk-id";
    idLabel.textContent = chunk.hasValidChunkId ? chunk.chunkId : "Missing chunk_id";
    identity.append(idLabel);

    if (!chunk.hasValidChunkId) {
      const missingMarker = document.createElement("span");
      missingMarker.className = "missing-marker";
      missingMarker.textContent = "ID unavailable";
      identity.append(missingMarker);
    }

    const selectedMarker = document.createElement("span");
    selectedMarker.className = "selected-marker";
    selectedMarker.textContent = "Selected";
    identity.append(selectedMarker);

    const order = document.createElement("span");
    order.className = "chunk-order";
    order.textContent = `${index + 1} / ${chunks.length}`;
    identity.append(order);

    const copyButton = document.createElement("button");
    copyButton.className = "copy-id-button";
    copyButton.type = "button";
    copyButton.textContent = "Copy ID";
    copyButton.disabled = !chunk.hasValidChunkId;
    copyButton.setAttribute(
      "aria-label",
      chunk.hasValidChunkId ? `Copy chunk ID ${chunk.chunkId}` : "Copy unavailable because chunk_id is missing"
    );
    copyButton.addEventListener("click", (event) => {
      event.stopPropagation();
      selectChunk(chunk, { updateUrl: true, scroll: false, focus: false });
      copyChunkId(chunk, copyButton);
    });

    header.append(identity, copyButton);
    article.append(header);

    if (chunk.hasDisplayText) {
      const text = document.createElement("p");
      text.className = "chunk-text";
      text.textContent = chunk.displayText;
      article.append(text);
    } else {
      const warning = document.createElement("div");
      warning.className = "missing-text-warning";
      warning.setAttribute("role", "note");
      warning.textContent = `No displayable text was found. Checked fields: ${TEXT_FIELD_PRIORITY.join(", ")}.`;
      article.append(warning);
    }

    article.addEventListener("click", (event) => {
      if (event.target.closest("button, input, textarea, select, a")) {
        return;
      }
      if (hasActiveTextSelectionInside(article)) {
        return;
      }
      selectChunk(chunk, { updateUrl: true, scroll: false, focus: false });
    });

    chunk.domId = article.id;
    chunk.element = article;
    fragment.append(article);
  });

  elements.chunkList.append(fragment);
}

function selectChunk(chunk, options = {}) {
  const { updateUrl = true, scroll = false, focus = false } = options;
  if (!chunk || !chunk.element) {
    return;
  }

  if (state.selectedChunk?.element) {
    state.selectedChunk.element.setAttribute("aria-selected", "false");
    state.selectedChunk.element.tabIndex = -1;
  }

  state.selectedChunk = chunk;
  chunk.element.setAttribute("aria-selected", "true");
  chunk.element.tabIndex = 0;

  if (chunk.hasValidChunkId) {
    elements.selectedChunkId.textContent = chunk.chunkId;
  } else {
    elements.selectedChunkId.textContent = `Missing chunk_id (line ${chunk.originalLineNumber})`;
  }

  if (updateUrl) {
    updateUrlForSelection(chunk);
  }

  if (scroll) {
    chunk.element.scrollIntoView({ block: "center", behavior: "auto" });
  }
  if (focus) {
    chunk.element.focus({ preventScroll: true });
  }

  updateControls();
}

async function copyChunkId(chunk, triggerButton) {
  if (!chunk?.hasValidChunkId) {
    announce("This chunk has no copyable chunk_id.");
    return false;
  }

  try {
    let copied = false;
    if (navigator.clipboard && window.isSecureContext) {
      try {
        await navigator.clipboard.writeText(chunk.chunkId);
        copied = true;
      } catch (clipboardError) {
        console.warn("Clipboard API failed; trying fallback copy.", clipboardError);
      }
    }

    if (!copied) {
      copied = fallbackCopyText(chunk.chunkId);
    }
    if (!copied) {
      throw new Error("No clipboard method succeeded.");
    }

    showCopyConfirmation(triggerButton);
    announce(`Copied chunk ID ${chunk.chunkId}.`);
    return true;
  } catch (error) {
    console.error("Copy failed", error);
    announce(`Could not copy chunk ID ${chunk.chunkId}.`);
    return false;
  }
}

function applySearch(query) {
  const normalizedQuery = query.toLocaleLowerCase();
  state.visibleChunks = [];

  for (const chunk of state.chunks) {
    const idMatches = chunk.chunkId.toLocaleLowerCase().includes(normalizedQuery);
    const textMatches = chunk.displayText.toLocaleLowerCase().includes(normalizedQuery);
    const isVisible = normalizedQuery === "" || idMatches || textMatches;
    chunk.element.hidden = !isVisible;
    if (isVisible) {
      state.visibleChunks.push(chunk);
    }
  }

  elements.clearSearch.disabled = query.length === 0;
  elements.matchCount.textContent = query.length > 0
    ? `${state.visibleChunks.length} of ${state.chunks.length} matches`
    : `${state.chunks.length} chunks`;
  elements.emptyState.hidden = state.visibleChunks.length > 0;

  updateControls();
  runSelfChecks();
}

function readChunkIdFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return params.has("chunk_id") ? params.get("chunk_id") : null;
}

function updateUrlForSelection(chunk) {
  const url = new URL(window.location.href);
  if (chunk.hasValidChunkId) {
    url.searchParams.set("chunk_id", chunk.chunkId);
  } else {
    url.searchParams.delete("chunk_id");
  }
  history.replaceState(null, "", url);
}

function getSourceReference(chunk) {
  return {
    chunkId: chunk.chunkId,
    pageStart: chunk.pageStart,
    pageEnd: chunk.pageEnd,
    sectionPath: chunk.sectionPath
  };
}

function runSelfChecks() {
  const failures = [];
  const rendered = [...elements.chunkList.querySelectorAll("article.chunk-card")];

  if (!state.loadError && rendered.length !== state.chunks.length) {
    failures.push(`Rendered count ${rendered.length} does not equal prepared chunk count ${state.chunks.length}.`);
  }

  for (const article of rendered) {
    const recordIndex = Number(article.dataset.recordIndex);
    const chunk = state.chunks.find((candidate) => candidate.originalIndex === recordIndex);
    if (!chunk) {
      failures.push(`Rendered element ${article.id} has no normalized record.`);
      continue;
    }
    if (chunk.hasValidChunkId && article.dataset.chunkId !== chunk.chunkId) {
      failures.push(`Rendered element ${article.id} does not preserve its data-chunk-id.`);
    }
    const enabledCopy = article.querySelector("button.copy-id-button:not(:disabled)");
    if (enabledCopy && !chunk.hasValidChunkId) {
      failures.push(`Enabled copy button found for chunk without a valid ID at line ${chunk.originalLineNumber}.`);
    }
  }

  const visibleDomOrder = rendered.filter((article) => !article.hidden).map((article) => article.dataset.recordIndex);
  const expectedVisibleOrder = state.visibleChunks.map((chunk) => String(chunk.originalIndex));
  if (visibleDomOrder.join("|") !== expectedVisibleOrder.join("|")) {
    failures.push("Visible chunks are not in expected order.");
  }

  const domIds = rendered.map((article) => article.id);
  if (new Set(domIds).size !== domIds.length) {
    failures.push("Duplicate DOM element IDs detected.");
  }

  const selectedCount = rendered.filter((article) => article.getAttribute("aria-selected") === "true").length;
  if (selectedCount > 1) {
    failures.push(`More than one chunk is selected (${selectedCount}).`);
  }

  if (failures.length > 0) {
    elements.diagnostics.hidden = false;
    elements.diagnostics.open = true;
    elements.diagnosticsOutput.textContent = failures.join("\n");
    console.error("Chunk browser self-check failures:", failures);
  } else {
    elements.diagnostics.hidden = true;
    elements.diagnostics.open = false;
    elements.diagnosticsOutput.textContent = "All runtime self-checks passed.";
    console.info("Chunk browser runtime self-checks passed.");
  }

  return failures;
}

function renderDatasetSummary() {
  const missingIds = state.chunks.filter((chunk) => !chunk.hasValidChunkId);
  const missingText = state.chunks.filter((chunk) => !chunk.hasDisplayText);
  const issueCount = state.malformedLines.length + missingIds.length + missingText.length + state.duplicateIds.size;

  if (issueCount === 0) {
    elements.errorSummary.hidden = true;
    return;
  }

  const container = document.createElement("div");
  const summary = document.createElement("p");
  summary.textContent = [
    `${state.chunks.length} valid chunks`,
    `${state.malformedLines.length} malformed lines`,
    `${missingIds.length} chunks missing chunk_id`,
    `${missingText.length} chunks missing displayable text`,
    `${state.duplicateIds.size} duplicate chunk_id values`
  ].join("; ") + ".";
  container.append(summary);

  const list = document.createElement("ul");
  if (state.malformedLines.length > 0) {
    const item = document.createElement("li");
    const lineList = state.malformedLines.map((entry) => entry.lineNumber).join(", ");
    item.textContent = `Malformed JSON on line(s): ${lineList}.`;
    list.append(item);
  }
  if (missingIds.length > 0) {
    const item = document.createElement("li");
    item.textContent = `Missing or invalid chunk_id on source line(s): ${missingIds.map((chunk) => chunk.originalLineNumber).join(", ")}.`;
    list.append(item);
  }
  if (missingText.length > 0) {
    const item = document.createElement("li");
    item.textContent = `Missing displayable text on source line(s): ${missingText.map((chunk) => chunk.originalLineNumber).join(", ")}.`;
    list.append(item);
  }
  for (const [id, occurrences] of state.duplicateIds) {
    const item = document.createElement("li");
    item.textContent = `Duplicate chunk_id “${id}” appears on source lines ${occurrences.map((chunk) => chunk.originalLineNumber).join(", ")}.`;
    list.append(item);
  }

  container.append(list);
  elements.errorSummaryContent.replaceChildren(container);
  elements.errorSummary.hidden = false;
}

function renderNotices() {
  const warnings = [];
  if (state.loadError) {
    warnings.push(`Load error: ${state.loadError}`);
  }
  if (state.urlWarning) {
    warnings.push(state.urlWarning);
  }

  if (warnings.length > 0) {
    elements.warningMessage.textContent = warnings.join(" ");
    elements.warningMessage.hidden = false;
  } else {
    elements.warningMessage.hidden = true;
    elements.warningMessage.textContent = "";
  }

  elements.noticeArea.hidden = elements.warningMessage.hidden && elements.errorSummary.hidden;
}

function clearSearch() {
  if (elements.searchInput.value === "") {
    return;
  }
  elements.searchInput.value = "";
  applySearch("");
  elements.searchInput.focus();
}

function navigateVisible(direction) {
  if (state.visibleChunks.length === 0) {
    return;
  }

  const currentIndex = state.visibleChunks.indexOf(state.selectedChunk);
  let targetIndex;
  if (currentIndex === -1) {
    targetIndex = direction > 0 ? 0 : state.visibleChunks.length - 1;
  } else {
    targetIndex = Math.min(Math.max(currentIndex + direction, 0), state.visibleChunks.length - 1);
  }

  const target = state.visibleChunks[targetIndex];
  selectChunk(target, { updateUrl: true, scroll: true, focus: true });
}

function updateControls() {
  const visibleIndex = state.visibleChunks.indexOf(state.selectedChunk);
  const noVisibleChunks = state.visibleChunks.length === 0;

  elements.previousChunk.disabled = noVisibleChunks || visibleIndex === 0;
  elements.nextChunk.disabled = noVisibleChunks || visibleIndex === state.visibleChunks.length - 1;

  if (visibleIndex === -1 && !noVisibleChunks) {
    elements.previousChunk.disabled = false;
    elements.nextChunk.disabled = false;
  }

  const canCopySelected = Boolean(state.selectedChunk?.hasValidChunkId);
  elements.copySelected.disabled = !canCopySelected;

  if (!state.selectedChunk) {
    elements.selectedChunkId.textContent = "None";
  } else if (state.selectedChunk.element.hidden) {
    const base = state.selectedChunk.hasValidChunkId
      ? state.selectedChunk.chunkId
      : `Missing chunk_id (line ${state.selectedChunk.originalLineNumber})`;
    elements.selectedChunkId.textContent = `${base} — hidden by search`;
  }
}

function handleGlobalKeydown(event) {
  if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey) {
    return;
  }

  const target = event.target;
  const isTypingTarget = target instanceof HTMLInputElement
    || target instanceof HTMLTextAreaElement
    || target instanceof HTMLSelectElement
    || target.isContentEditable;
  const isButton = target instanceof HTMLButtonElement;

  if (event.key === "/" && !isTypingTarget && !isButton) {
    event.preventDefault();
    elements.searchInput.focus();
    elements.searchInput.select();
    return;
  }

  if (event.key === "Escape") {
    if (elements.searchInput.value !== "") {
      event.preventDefault();
      clearSearch();
    }
    return;
  }

  if (isTypingTarget || isButton || hasActiveTextSelection()) {
    return;
  }

  if (event.key === "ArrowUp") {
    event.preventDefault();
    navigateVisible(-1);
  } else if (event.key === "ArrowDown") {
    event.preventDefault();
    navigateVisible(1);
  } else if (event.key === "Enter" && state.selectedChunk?.hasValidChunkId) {
    event.preventDefault();
    copyChunkId(state.selectedChunk, elements.copySelected);
  }
}

function parseFiniteNumber(value) {
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : null;
  }
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function isPlainObject(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function setOptionalDataAttribute(element, propertyName, value) {
  if (value !== null && value !== undefined && value !== "") {
    element.dataset[propertyName] = String(value);
  }
}

function createUniqueDomId(chunk) {
  const baseSource = chunk.hasValidChunkId ? chunk.chunkId : `missing-id-line-${chunk.originalLineNumber}`;
  const safe = String(baseSource)
    .normalize("NFKD")
    .replace(/[^A-Za-z0-9_-]+/g, "-")
    .replace(/^-+|-+$/g, "") || `record-${chunk.originalIndex + 1}`;

  let candidate = `chunk-${safe}`;
  let suffix = 1;
  while (state.domIdSet.has(candidate)) {
    suffix += 1;
    candidate = `chunk-${safe}-${suffix}`;
  }
  state.domIdSet.add(candidate);
  return candidate;
}

function hasActiveTextSelectionInside(element) {
  const selection = window.getSelection();
  if (!selection || selection.isCollapsed || selection.toString().length === 0) {
    return false;
  }
  return element.contains(selection.anchorNode) || element.contains(selection.focusNode);
}

function hasActiveTextSelection() {
  const selection = window.getSelection();
  return Boolean(selection && !selection.isCollapsed && selection.toString().length > 0);
}

function fallbackCopyText(text) {
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.inset = "-9999px auto auto -9999px";
  document.body.append(textarea);
  textarea.select();
  textarea.setSelectionRange(0, textarea.value.length);

  let copied = false;
  try {
    copied = document.execCommand("copy");
  } finally {
    textarea.remove();
  }
  return copied;
}

function showCopyConfirmation(button) {
  if (!button) {
    return;
  }
  const originalText = button.textContent;
  button.textContent = "Copied";
  window.setTimeout(() => {
    button.textContent = originalText;
  }, 1200);
}

function announce(message) {
  elements.liveRegion.textContent = "";
  window.setTimeout(() => {
    elements.liveRegion.textContent = message;
  }, 10);
}

// Expose these small hooks for future source-highlighting integrations and manual diagnostics.
window.chunkBrowser = {
  getSourceReference,
  runSelfChecks,
  getSelectedChunk: () => state.selectedChunk,
  getChunks: () => [...state.chunks]
};
