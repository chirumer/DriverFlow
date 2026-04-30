// Thin fetch wrapper. One function per endpoint.

import { showToast } from "./ui/toast.js";

async function _checkOk(resp) {
    if (!resp.ok) {
        let detail = `${resp.status} ${resp.statusText}`;
        try {
            const body = await resp.json();
            if (body && body.detail) detail = body.detail;
        } catch (_) { /* leave detail */ }
        throw new Error(detail);
    }
    return resp;
}

export async function uploadFiles(files) {
    const fd = new FormData();
    for (const f of files) fd.append("files", f);
    const resp = await fetch("/api/import/upload", { method: "POST", body: fd });
    await _checkOk(resp);
    return resp.json();
}

export async function getCloudTree() {
    const resp = await fetch("/api/import/cloud_tree");
    await _checkOk(resp);
    return (await resp.json()).tree;
}

export async function cloudSelect(paths) {
    const resp = await fetch("/api/import/cloud_select", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ paths }),
    });
    await _checkOk(resp);
    return resp.json();
}

export async function listItems() {
    const resp = await fetch("/api/items");
    await _checkOk(resp);
    return (await resp.json()).items;
}

export async function getModelsStatus() {
    const resp = await fetch("/api/models/status");
    await _checkOk(resp);
    return resp.json();
}

export async function loadDino() {
    const resp = await fetch("/api/models/load_dino", { method: "POST" });
    await _checkOk(resp);
    return resp.json();
}

export async function loadSam() {
    const resp = await fetch("/api/models/load_sam", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
    });
    await _checkOk(resp);
    return resp.json();
}

export async function getToolRegistry() {
    const resp = await fetch("/api/tools/registry");
    await _checkOk(resp);
    return (await resp.json()).tools;
}

export async function runTool(name, body) {
    const resp = await fetch(`/api/tools/${encodeURIComponent(name)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    await _checkOk(resp);
    return resp.json();
}

export function exportUrl(itemId, versionId = null) {
    const v = versionId ? `?version=${encodeURIComponent(versionId)}` : "";
    return `/api/export/${encodeURIComponent(itemId)}${v}`;
}

export function previewUrl(itemId, versionId = null) {
    const v = versionId ? `?version=${encodeURIComponent(versionId)}` : "";
    return `/api/preview/${encodeURIComponent(itemId)}${v}`;
}

export function thumbUrl(itemId) {
    return `/api/preview/thumb/${encodeURIComponent(itemId)}`;
}

export async function downloadExport(itemId, versionId = null) {
    const url = exportUrl(itemId, versionId);
    const resp = await fetch(url);
    if (!resp.ok) {
        const text = await resp.text();
        showToast(text || "Export failed", "error");
        throw new Error(text);
    }
    const cd = resp.headers.get("Content-Disposition") || "";
    const m = cd.match(/filename="?([^"]+)"?/);
    const filename = m ? m[1] : `driverflow-${itemId}.bin`;
    const blob = await resp.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(a.href);
}
