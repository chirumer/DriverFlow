// DriverFlow Cloud (mock) modal — fake file tree with multi-select.

import * as api from "../api.js";
import * as state from "../state.js";
import { showToast } from "./toast.js";

const openBtn = document.getElementById("btn-cloud");
const modal = document.getElementById("modal-cloud");
const treeEl = document.getElementById("cloud-tree");
const cancelBtn = document.getElementById("modal-cloud-cancel");
const importBtn = document.getElementById("modal-cloud-import");

const selected = new Set();
let tree = null;

openBtn.addEventListener("click", openModal);
cancelBtn.addEventListener("click", closeModal);
importBtn.addEventListener("click", doImport);

async function openModal() {
    selected.clear();
    modal.hidden = false;
    if (!tree) {
        try {
            tree = await api.getCloudTree();
        } catch (e) {
            showToast(`Cloud tree fetch failed: ${e.message}`, "error");
            tree = [];
        }
    }
    renderTree();
}

function closeModal() {
    modal.hidden = true;
}

async function doImport() {
    if (selected.size === 0) {
        showToast("Pick at least one file.", "warn");
        return;
    }
    importBtn.disabled = true;
    try {
        const res = await api.cloudSelect(Array.from(selected));
        const all = await api.listItems();
        state.setItems(all);
        showToast(`Imported ${res.items.length} item(s) from cloud.`);
        closeModal();
    } catch (e) {
        showToast(`Cloud import failed: ${e.message}`, "error");
    } finally {
        importBtn.disabled = false;
    }
}

function renderTree() {
    treeEl.innerHTML = "";
    for (const node of tree) treeEl.appendChild(renderNode(node));
}

function renderNode(node) {
    const wrap = document.createElement("div");
    const row = document.createElement("div");
    row.className = "cloud-node";

    if (node.kind === "dir") {
        row.classList.add("dir");
        const icon = document.createElement("span");
        icon.className = "icon";
        icon.textContent = "▾";
        row.appendChild(icon);
        const label = document.createElement("span");
        label.textContent = node.name;
        row.appendChild(label);

        const children = document.createElement("div");
        children.className = "cloud-children";
        for (const child of node.children || []) children.appendChild(renderNode(child));

        row.addEventListener("click", () => {
            const collapsed = children.classList.toggle("collapsed");
            icon.textContent = collapsed ? "▸" : "▾";
        });

        wrap.appendChild(row);
        wrap.appendChild(children);
    } else {
        row.classList.add("leaf");
        if (selected.has(node.path)) row.classList.add("selected");
        const icon = document.createElement("span");
        icon.className = "icon";
        icon.textContent = node.kind === "video" ? "🎬" : "🖼";
        row.appendChild(icon);
        const label = document.createElement("span");
        label.textContent = node.name;
        row.appendChild(label);
        row.addEventListener("click", () => {
            if (selected.has(node.path)) selected.delete(node.path);
            else selected.add(node.path);
            row.classList.toggle("selected");
        });
        wrap.appendChild(row);
    }
    return wrap;
}
