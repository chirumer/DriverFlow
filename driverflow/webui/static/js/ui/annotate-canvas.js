// Bounding-box drawing canvas for the Annotate tool.

import { getPreviewImage, getPreviewWrap } from "./workspace.js";
import { showToast } from "./toast.js";

let canvas = null;
let ctrlBar = null;
let boxes = [];      // {x1, y1, x2, y2, label}
let draft = null;
let activeSubmit = null;
let resizeObserver = null;
let syncLayout = null;

export function activateAnnotateCanvas(onSubmit) {
    deactivateAnnotateCanvas();
    const img = getPreviewImage();
    const wrap = getPreviewWrap();
    if (!img || !wrap) return;

    activeSubmit = onSubmit;
    boxes = [];

    const start = () => {
        if (!img.naturalWidth) return;
        canvas = document.createElement("canvas");
        canvas.width = img.naturalWidth;
        canvas.height = img.naturalHeight;
        wrap.appendChild(canvas);
        canvas.addEventListener("pointerdown", onPointerDown);
        canvas.addEventListener("pointermove", onPointerMove);
        canvas.addEventListener("pointerup", onPointerUp);
        canvas.addEventListener("pointercancel", cancelDraft);
        installResize(img);
        mountControls();
        redraw();
    };

    if (img.complete && img.naturalWidth) {
        start();
    } else {
        img.addEventListener("load", start, { once: true });
    }
}

export function deactivateAnnotateCanvas() {
    if (canvas) {
        canvas.remove();
        canvas = null;
    }
    if (ctrlBar) {
        ctrlBar.remove();
        ctrlBar = null;
    }
    if (resizeObserver) {
        resizeObserver.disconnect();
        resizeObserver = null;
    }
    if (syncLayout) {
        window.removeEventListener("resize", syncLayout);
        syncLayout = null;
    }
    boxes = [];
    draft = null;
    activeSubmit = null;
}

function installResize(img) {
    syncLayout = () => {
        if (!canvas) return;
        canvas.style.width = `${img.clientWidth}px`;
        canvas.style.height = `${img.clientHeight}px`;
        canvas.style.left = `${img.offsetLeft}px`;
        canvas.style.top = `${img.offsetTop}px`;
    };
    syncLayout();
    resizeObserver = new ResizeObserver(syncLayout);
    resizeObserver.observe(img);
    window.addEventListener("resize", syncLayout);
}

function mountControls() {
    ctrlBar = document.createElement("div");
    ctrlBar.style.cssText =
        "margin-top: 0.6rem; padding: 0.6rem; border: 1px solid var(--border); border-radius: 6px; background: var(--bg-card); display: flex; gap: 0.6rem; align-items: center; flex-wrap: wrap;";
    ctrlBar.innerHTML = `
        <label class="annotate-label">Class <input type="text" id="annotate-label" placeholder="e.g. car" autocomplete="off"></label>
        <button type="button" class="btn btn-ghost mini" id="annotate-undo">Undo</button>
        <button type="button" class="btn btn-ghost mini" id="annotate-clear">Clear</button>
        <span id="annotate-status" style="margin-left:auto; font-size:0.8rem; color: var(--text-muted);">0 boxes</span>
        <button type="button" class="btn btn-primary" id="annotate-submit">Submit</button>
        <button type="button" class="btn btn-ghost" id="annotate-cancel">Cancel</button>
    `;
    document.getElementById("tool-params").appendChild(ctrlBar);

    document.getElementById("annotate-label").focus();
    document.getElementById("annotate-undo").addEventListener("click", () => {
        if (boxes.length) boxes.pop();
        redraw();
        updateStatus();
    });
    document.getElementById("annotate-clear").addEventListener("click", () => {
        boxes = [];
        draft = null;
        redraw();
        updateStatus();
    });
    document.getElementById("annotate-cancel").addEventListener("click", deactivateAnnotateCanvas);
    document.getElementById("annotate-submit").addEventListener("click", submit);
}

function currentLabel() {
    return (document.getElementById("annotate-label")?.value || "").trim();
}

function canvasPoint(e) {
    const rect = canvas.getBoundingClientRect();
    const sx = canvas.width / rect.width;
    const sy = canvas.height / rect.height;
    return {
        x: Math.round((e.clientX - rect.left) * sx),
        y: Math.round((e.clientY - rect.top) * sy),
    };
}

function onPointerDown(e) {
    if (!canvas) return;
    const label = currentLabel();
    if (!label) {
        showToast("Enter a class label before drawing.", "warn");
        document.getElementById("annotate-label")?.focus();
        return;
    }
    e.preventDefault();
    canvas.setPointerCapture(e.pointerId);
    const p = canvasPoint(e);
    draft = { x1: p.x, y1: p.y, x2: p.x, y2: p.y, label };
    redraw();
}

function onPointerMove(e) {
    if (!draft || !canvas) return;
    e.preventDefault();
    const p = canvasPoint(e);
    draft.x2 = p.x;
    draft.y2 = p.y;
    redraw();
}

function onPointerUp(e) {
    if (!draft || !canvas) return;
    e.preventDefault();
    const p = canvasPoint(e);
    draft.x2 = p.x;
    draft.y2 = p.y;
    const box = normalizeBox(draft);
    draft = null;
    if (box && box.x2 - box.x1 >= 4 && box.y2 - box.y1 >= 4) {
        boxes.push(box);
    }
    redraw();
    updateStatus();
}

function cancelDraft() {
    draft = null;
    redraw();
}

function normalizeBox(box) {
    const x1 = Math.max(0, Math.min(canvas.width, Math.min(box.x1, box.x2)));
    const y1 = Math.max(0, Math.min(canvas.height, Math.min(box.y1, box.y2)));
    const x2 = Math.max(0, Math.min(canvas.width, Math.max(box.x1, box.x2)));
    const y2 = Math.max(0, Math.min(canvas.height, Math.max(box.y1, box.y2)));
    if (x2 <= x1 || y2 <= y1) return null;
    return { x1, y1, x2, y2, label: box.label };
}

function redraw() {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (const box of boxes) drawBox(ctx, box, "rgba(47, 129, 247, 0.95)");
    if (draft) drawBox(ctx, normalizeBox(draft), "rgba(210, 153, 34, 0.95)");
}

function drawBox(ctx, box, strokeStyle) {
    if (!box) return;
    const w = box.x2 - box.x1;
    const h = box.y2 - box.y1;
    ctx.lineWidth = 3;
    ctx.strokeStyle = strokeStyle;
    ctx.strokeRect(box.x1, box.y1, w, h);

    const label = box.label;
    ctx.font = "14px sans-serif";
    const metrics = ctx.measureText(label);
    const labelW = Math.ceil(metrics.width) + 10;
    const labelH = 22;
    const ly = Math.max(0, box.y1 - labelH);
    ctx.fillStyle = strokeStyle;
    ctx.fillRect(box.x1, ly, labelW, labelH);
    ctx.fillStyle = "black";
    ctx.fillText(label, box.x1 + 5, ly + 15);
}

function updateStatus() {
    const el = document.getElementById("annotate-status");
    if (el) el.textContent = `${boxes.length} box${boxes.length === 1 ? "" : "es"}`;
}

async function submit() {
    if (boxes.length === 0) {
        showToast("Draw at least one box.", "warn");
        return;
    }
    const submitBtn = document.getElementById("annotate-submit");
    if (submitBtn) submitBtn.disabled = true;
    try {
        if (activeSubmit) await activeSubmit(boxes);
    } finally {
        if (submitBtn) submitBtn.disabled = false;
    }
}
