// Import: page-level drag/drop and the explicit "Import" button.

import * as api from "../api.js";
import * as state from "../state.js";
import { showToast } from "./toast.js";

const fileInput = document.getElementById("file-input");
const importBtn = document.getElementById("btn-import");

importBtn.addEventListener("click", () => fileInput.click());

fileInput.addEventListener("change", async () => {
    const files = Array.from(fileInput.files || []);
    if (!files.length) return;
    await uploadAndRefresh(files);
    fileInput.value = "";
});

let dragDepth = 0;
const isFileDrag = (e) =>
    Array.from(e.dataTransfer?.types || []).includes("Files");

window.addEventListener("dragenter", (e) => {
    if (!isFileDrag(e)) return;
    e.preventDefault();
    dragDepth += 1;
});
window.addEventListener("dragleave", () => {
    dragDepth = Math.max(0, dragDepth - 1);
});
window.addEventListener("dragover", (e) => {
    if (!isFileDrag(e)) return;
    e.preventDefault();
});
window.addEventListener("drop", async (e) => {
    if (!isFileDrag(e)) return;
    e.preventDefault();
    dragDepth = 0;
    const files = Array.from(e.dataTransfer.files || []);
    if (files.length) await uploadAndRefresh(files);
});

async function uploadAndRefresh(files) {
    try {
        const res = await api.uploadFiles(files);
        const added = (res.items || []).length;
        showToast(`Imported ${added} item${added === 1 ? "" : "s"}.`);
        const all = await api.listItems();
        state.setItems(all);
    } catch (e) {
        showToast(`Import failed: ${e.message}`, "error");
    }
}
