// Right-side model loader panel.

import * as api from "../api.js";
import * as state from "../state.js";
import { showToast } from "./toast.js";

const root = document.getElementById("models");
const toggleBtn = document.getElementById("btn-toggle-models");
const modelsSection = document.getElementById("models-section");

const MODELS = [
    { name: "dino", label: "Grounding DINO", load: api.loadDino },
    { name: "sam",  label: "SAM 2",          load: api.loadSam  },
];

let collapsed = false;
toggleBtn.addEventListener("click", () => {
    collapsed = !collapsed;
    root.style.display = collapsed ? "none" : "";
    toggleBtn.textContent = collapsed ? "+" : "−";
});

state.on("models:changed", render);
state.on("highlight:changed", render);

export async function init() {
    try {
        const status = await api.getModelsStatus();
        state.setModels(status);
    } catch (e) {
        showToast(`Models status fetch failed: ${e.message}`, "error");
    }
    render();
}

export function expand() {
    if (collapsed) toggleBtn.click();
}

function render() {
    root.innerHTML = "";
    for (const m of MODELS) {
        const btn = document.createElement("button");
        btn.className = "model-button";
        const loaded = !!state.state.models[m.name];
        if (loaded) btn.classList.add("loaded");
        if (state.state.highlightModel === m.name) btn.classList.add("highlighted");
        btn.dataset.modelName = m.name;
        btn.innerHTML = `<span>${m.label}</span><span>${loaded ? "✓ Loaded" : "Load"}</span>`;
        btn.disabled = loaded;
        btn.addEventListener("click", async () => {
            btn.disabled = true;
            const original = btn.innerHTML;
            btn.innerHTML = `<span>${m.label}</span><span>Loading…</span>`;
            try {
                const res = await m.load();
                state.setModels({ [m.name]: !!res.loaded, device: res.device });
                showToast(`${m.label} loaded (${res.took_seconds}s).`);
            } catch (e) {
                btn.disabled = false;
                btn.innerHTML = original;
                showToast(`${m.label} failed: ${e.message}`, "error");
            }
        });
        root.appendChild(btn);
    }
}
