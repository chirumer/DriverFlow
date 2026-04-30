// Click-collection canvas overlay for the Refine tool.
//
// Mounts on top of the preview image, lets the user place positive/negative
// points, and submits {points, labels} when the user clicks Submit.

import { getPreviewImage, getPreviewWrap } from "./workspace.js";

let canvas = null;
let ctrlBar = null;
let clicks = [];     // {x, y, label}
let activeSubmit = null;
let resizeObserver = null;

export function activateRefineCanvas(onSubmit) {
    deactivateRefineCanvas();
    const img = getPreviewImage();
    const wrap = getPreviewWrap();
    if (!img || !wrap) return;

    activeSubmit = onSubmit;
    clicks = [];

    const start = () => {
        if (!img.naturalWidth) return;
        canvas = document.createElement("canvas");
        canvas.width = img.naturalWidth;
        canvas.height = img.naturalHeight;
        wrap.appendChild(canvas);
        canvas.addEventListener("click", onClick);
        redraw();
        installResize(img);
        mountControls();
    };
    if (img.complete && img.naturalWidth) {
        start();
    } else {
        img.addEventListener("load", start, { once: true });
    }
}

export function deactivateRefineCanvas() {
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
    clicks = [];
    activeSubmit = null;
}

function installResize(img) {
    const sync = () => {
        if (!canvas) return;
        canvas.style.width = `${img.clientWidth}px`;
        canvas.style.height = `${img.clientHeight}px`;
        canvas.style.left = `${img.offsetLeft}px`;
        canvas.style.top = `${img.offsetTop}px`;
    };
    sync();
    resizeObserver = new ResizeObserver(sync);
    resizeObserver.observe(img);
    window.addEventListener("resize", sync);
}

function selectedLabel() {
    const radio = document.querySelector('input[name="refine-label"]:checked');
    return radio ? parseInt(radio.value, 10) : 1;
}

function onClick(e) {
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const sx = canvas.width / rect.width;
    const sy = canvas.height / rect.height;
    const x = Math.round((e.clientX - rect.left) * sx);
    const y = Math.round((e.clientY - rect.top) * sy);
    clicks.push({ x, y, label: selectedLabel() });
    redraw();
    updateStatus();
}

function redraw() {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (const c of clicks) {
        ctx.beginPath();
        ctx.arc(c.x, c.y, 8, 0, 2 * Math.PI);
        ctx.fillStyle = c.label === 1 ? "rgba(40, 220, 80, 0.9)" : "rgba(240, 60, 60, 0.9)";
        ctx.fill();
        ctx.lineWidth = 2;
        ctx.strokeStyle = "white";
        ctx.stroke();
    }
}

function mountControls() {
    ctrlBar = document.createElement("div");
    ctrlBar.style.cssText =
        "margin-top: 0.6rem; padding: 0.6rem; border: 1px solid var(--border); border-radius: 6px; background: var(--bg-card); display: flex; gap: 0.6rem; align-items: center; flex-wrap: wrap;";
    ctrlBar.innerHTML = `
        <label><input type="radio" name="refine-label" value="1" checked> Positive</label>
        <label><input type="radio" name="refine-label" value="0"> Negative</label>
        <button type="button" class="btn btn-ghost mini" id="refine-undo">Undo</button>
        <span id="refine-status" style="margin-left:auto; font-size:0.8rem; color: var(--text-muted);">0 clicks</span>
        <button type="button" class="btn btn-primary" id="refine-submit">Submit</button>
        <button type="button" class="btn btn-ghost" id="refine-cancel">Cancel</button>
    `;
    document.getElementById("tool-params").appendChild(ctrlBar);

    document.getElementById("refine-undo").addEventListener("click", () => {
        if (clicks.length) clicks.pop();
        redraw();
        updateStatus();
    });
    document.getElementById("refine-cancel").addEventListener("click", deactivateRefineCanvas);
    document.getElementById("refine-submit").addEventListener("click", submit);
}

function updateStatus() {
    const el = document.getElementById("refine-status");
    if (el) el.textContent = `${clicks.length} click${clicks.length === 1 ? "" : "s"}`;
}

async function submit() {
    if (clicks.length === 0) return;
    const points = clicks.map((c) => [c.x, c.y]);
    const labels = clicks.map((c) => c.label);
    const submitBtn = document.getElementById("refine-submit");
    if (submitBtn) submitBtn.disabled = true;
    try {
        if (activeSubmit) await activeSubmit(points, labels);
    } finally {
        if (submitBtn) submitBtn.disabled = false;
    }
}
