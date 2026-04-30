// Center preview area. Owns the working item, drop logic, replace warning,
// beforeunload guard, and download button.

import * as state from "../state.js";
import { downloadExport, previewUrl } from "../api.js";
import { showToast } from "./toast.js";
import { confirmModal } from "./modal.js";

const previewEl = document.getElementById("preview");
const nameEl = document.getElementById("working-name");
const exportBtn = document.getElementById("btn-export");

state.on("working:changed", render);
state.on("items:changed", render);
state.on("version:added", ({ itemId, versionId }) => {
    if (!state.state.workingItem || state.state.workingItem.id !== itemId) return;
    state.state.workingItem.currentVersionId = versionId;
    render();
});

previewEl.addEventListener("dragover", (e) => {
    if (!isItemDrag(e)) return;
    e.preventDefault();
    previewEl.classList.add("dragover");
});
previewEl.addEventListener("dragleave", () => previewEl.classList.remove("dragover"));
previewEl.addEventListener("drop", async (e) => {
    if (!isItemDrag(e)) return;
    e.preventDefault();
    previewEl.classList.remove("dragover");

    const idsRaw = e.dataTransfer.getData("application/x-driverflow-item-ids");
    if (idsRaw) {
        const ids = JSON.parse(idsRaw);
        if (ids.length !== 1) {
            showToast("Drag one item at a time.", "warn");
            return;
        }
        await tryReplaceWorkingItem(ids[0]);
        return;
    }

    const versionRaw = e.dataTransfer.getData("application/x-driverflow-version");
    if (versionRaw) {
        const { itemId, versionId } = JSON.parse(versionRaw);
        if (state.state.workingItem && state.state.workingItem.id === itemId) {
            state.state.workingItem.currentVersionId = versionId;
            state.emit("working:changed", { workingItem: state.state.workingItem });
        }
    }
});

exportBtn.addEventListener("click", async () => {
    const wi = state.state.workingItem;
    if (!wi) return;
    try {
        await downloadExport(wi.id, wi.currentVersionId);
        // Refresh sources so item appears under "exported".
        const list = await (await fetch("/api/items")).json();
        state.setItems(list.items || []);
    } catch (e) {
        // toast already shown in api.js
    }
});

window.addEventListener("beforeunload", (e) => {
    if (!state.isWorkingDirty()) return;
    e.preventDefault();
    e.returnValue = "Unsaved work will be lost.";
    return e.returnValue;
});

function isItemDrag(e) {
    return Array.from(e.dataTransfer.types || []).some((t) =>
        t === "application/x-driverflow-item-ids" || t === "application/x-driverflow-version"
    );
}

async function tryReplaceWorkingItem(newItemId) {
    if (state.isWorkingDirty()) {
        const ok = await confirmModal({
            title: "Replace working item?",
            body: "Replacing will lose any unsaved changes on the current item. Continue?",
            okLabel: "Replace",
        });
        if (!ok) return;
    }
    const item = state.state.itemIndex.get(newItemId);
    if (!item) return;
    state.setWorkingItem(item, null);
}

function render() {
    const wi = state.state.workingItem;
    if (!wi) {
        nameEl.textContent = "No item selected";
        previewEl.innerHTML = `
            <div class="empty-state">
                <p>Drag an image or video here, or pick one from the sidebar.</p>
            </div>`;
        exportBtn.disabled = true;
        return;
    }

    nameEl.textContent = wi.name + (wi.currentVersionId ? "" : " (raw)");
    exportBtn.disabled = false;

    previewEl.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = "preview-canvas-wrap";
    const url = withCacheBuster(previewUrl(wi.id, wi.currentVersionId));
    if (wi.media_type === "video") {
        const v = document.createElement("video");
        v.src = url;
        v.controls = true;
        v.style.maxHeight = "600px";
        wrap.appendChild(v);
    } else {
        const img = document.createElement("img");
        img.id = "preview-img";
        img.alt = wi.name;
        img.src = url;
        wrap.appendChild(img);
    }
    previewEl.appendChild(wrap);
}

function withCacheBuster(url) {
    const sep = url.includes("?") ? "&" : "?";
    return `${url}${sep}t=${Date.now()}`;
}

export function getPreviewWrap() {
    return previewEl.querySelector(".preview-canvas-wrap");
}

export function getPreviewImage() {
    return document.getElementById("preview-img");
}
