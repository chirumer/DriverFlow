// Data workspace — version cards for the working item.
//
// Cards are pluggable via a registry keyed by version kind. Loading cards
// are added before a tool call and replaced inline once the response lands.

import * as state from "../state.js";
import { previewUrl } from "../api.js";

const cardsRoot = document.getElementById("dw-cards");

const RENDERERS = {
    raw:        renderMediaCard,
    detected:   renderImageCard,
    segmented:  renderImageCard,
    refined:    renderImageCard,
};

state.on("working:changed", render);
state.on("items:changed", render);

let nextLoadingId = 0;
const loadingCards = new Map();   // tempId -> element

export function addLoadingCard(tool) {
    const tempId = `loading-${++nextLoadingId}`;
    const el = document.createElement("div");
    el.className = "dw-card loading";
    el.dataset.tempId = tempId;
    el.innerHTML = `
        <div class="spinner"></div>
        <div class="dw-meta">Running ${tool.label}…</div>
    `;
    cardsRoot.appendChild(el);
    loadingCards.set(tempId, el);
    el.scrollIntoView({ behavior: "smooth", block: "nearest" });
    return tempId;
}

export function replaceLoadingCard(tempId, version, errorText = null) {
    const el = loadingCards.get(tempId);
    if (!el) return;
    if (errorText) {
        el.classList.remove("loading");
        el.innerHTML = `<div class="dw-kind">Error</div><div class="dw-meta">${escapeHtml(errorText)}</div>`;
        loadingCards.delete(tempId);
        return;
    }
    el.remove();
    loadingCards.delete(tempId);
    // The full re-render in render() picks up the new version from items[].
    render();
}

export function render() {
    cardsRoot.innerHTML = "";
    const wi = state.state.workingItem;
    if (!wi) {
        cardsRoot.innerHTML = '<p class="hint">No working item.</p>';
        return;
    }
    const item = state.state.itemIndex.get(wi.id);
    if (!item) return;

    const versions = item.versions || [];
    for (const v of versions) {
        const renderer = RENDERERS[v.kind] || renderImageCard;
        const card = renderer(v, item);
        cardsRoot.appendChild(card);
    }

    // Re-attach any in-flight loading cards (tools.js adds them mid-run).
    for (const el of loadingCards.values()) cardsRoot.appendChild(el);
}

function renderMediaCard(version, item) {
    const el = baseCard(version, item);
    if (item.media_type === "video") {
        const v = document.createElement("video");
        v.src = previewUrl(item.id, version.id);
        v.muted = true;
        v.preload = "metadata";
        el.appendChild(v);
    } else {
        const img = document.createElement("img");
        img.alt = version.kind;
        img.src = previewUrl(item.id, version.id);
        el.appendChild(img);
    }
    addMeta(el, version, item);
    return el;
}

function renderImageCard(version, item) {
    const el = baseCard(version, item);
    const img = document.createElement("img");
    img.alt = version.kind;
    img.src = previewUrl(item.id, version.id);
    el.appendChild(img);
    addMeta(el, version, item);
    return el;
}

function baseCard(version, item) {
    const wi = state.state.workingItem;
    const el = document.createElement("div");
    el.className = "dw-card";
    el.draggable = true;
    const isActive = wi && (
        (wi.currentVersionId === version.id) ||
        (wi.currentVersionId == null && version.kind === "raw" && (item.versions || [])[0]?.id === version.id)
    );
    if (isActive) el.classList.add("active");
    el.addEventListener("dragstart", (e) => {
        e.dataTransfer.setData(
            "application/x-driverflow-version",
            JSON.stringify({ itemId: item.id, versionId: version.id }),
        );
        e.dataTransfer.effectAllowed = "copy";
    });
    el.addEventListener("click", () => {
        state.state.workingItem.currentVersionId = version.id;
        state.emit("working:changed", { workingItem: state.state.workingItem });
    });
    return el;
}

function addMeta(el, version, item) {
    const kind = document.createElement("div");
    kind.className = "dw-kind";
    kind.textContent = prettyKind(version.kind);
    el.appendChild(kind);

    const meta = document.createElement("div");
    meta.className = "dw-meta";
    meta.textContent = summarize(version);
    el.appendChild(meta);
}

function prettyKind(kind) {
    return ({
        raw: "Raw",
        detected: "Detected (boxes)",
        segmented: "Segmented (masks)",
        refined: "Refined",
    })[kind] || kind;
}

function summarize(v) {
    const s = v.summary || {};
    if (v.kind === "detected") return `${s.n_boxes ?? 0} boxes — ${s.prompt || ""}`;
    if (v.kind === "segmented") return `${s.n_masks ?? 0} masks`;
    if (v.kind === "refined") return `${s.n_points ?? 0} clicks · ${s.n_masks ?? 0} masks`;
    return "";
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}
