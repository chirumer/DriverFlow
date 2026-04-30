// Right-side tools panel. Renders from /api/tools/registry, gates buttons
// on (model loaded) AND (input kind present on working item), and routes
// submit to either a generic params form or a tool-specific descriptor.

import * as api from "../api.js";
import * as state from "../state.js";
import { showToast } from "./toast.js";
import * as modelPanel from "./model-panel.js";
import { addLoadingCard, replaceLoadingCard } from "./data-workspace.js";
import { activateRefineCanvas, deactivateRefineCanvas } from "./refine-canvas.js";

const toolsRoot = document.getElementById("tools");
const paramsRoot = document.getElementById("tool-params");

let toolDescriptors = [];
let activeToolName = null;

state.on("models:changed", render);
state.on("working:changed", () => { activeToolName = null; clearParams(); render(); });
state.on("tools:changed", () => { toolDescriptors = state.state.toolDescriptors; render(); });

document.addEventListener("click", (e) => {
    // Any click anywhere clears the model highlight (per spec).
    if (state.state.highlightModel !== null) {
        // Only clear when the click is not on the highlighted button itself
        // (so the button click can still trigger its own load handler).
        const isModelButton = e.target.closest('.model-button.highlighted');
        if (!isModelButton) {
            state.setHighlightModel(null);
        } else {
            state.setHighlightModel(null);
        }
    }
});

export async function init() {
    try {
        const tools = await api.getToolRegistry();
        toolDescriptors = tools;
        state.setToolDescriptors(tools);
    } catch (e) {
        showToast(`Tool registry fetch failed: ${e.message}`, "error");
    }
    render();
}

function applicableTools() {
    const wi = state.state.workingItem;
    const mediaType = wi ? wi.media_type : null;
    if (!mediaType) return [];
    return toolDescriptors.filter((t) => t.media_types.includes(mediaType));
}

function evalGate(tool) {
    const wi = state.state.workingItem;
    if (!wi) return { enabled: false, reason: "No working item." };
    if (tool.requires_model && !state.state.models[tool.requires_model]) {
        const label = tool.requires_model.toUpperCase();
        return { enabled: false, reason: `Load ${label} first.`, missingModel: tool.requires_model };
    }
    if (tool.requires_input_kind) {
        const kinds = wi.versions || [];
        if (!kinds.includes(tool.requires_input_kind)) {
            return { enabled: false, reason: `Needs ${tool.requires_input_kind} version.` };
        }
    }
    return { enabled: true };
}

function clearParams() { paramsRoot.innerHTML = ""; deactivateRefineCanvas(); }

function render() {
    toolsRoot.innerHTML = "";
    const applicable = applicableTools();
    if (state.state.workingItem == null) {
        const p = document.createElement("p");
        p.className = "hint";
        p.textContent = "Select a working item.";
        toolsRoot.appendChild(p);
        return;
    }
    if (applicable.length === 0) {
        const p = document.createElement("p");
        p.className = "hint";
        p.textContent = "No tools available for this media type.";
        toolsRoot.appendChild(p);
        return;
    }
    for (const tool of applicable) {
        const gate = evalGate(tool);
        const btn = document.createElement("button");
        btn.className = "tool-button";
        if (activeToolName === tool.name) btn.classList.add("active");
        btn.innerHTML = `<span>${tool.label}</span>` +
            (gate.enabled ? "" : `<span class="reason">${gate.reason}</span>`);
        if (!gate.enabled && !gate.missingModel) btn.disabled = true;
        btn.addEventListener("click", () => onToolClick(tool, gate));
        toolsRoot.appendChild(btn);
    }
}

function onToolClick(tool, gate) {
    if (!gate.enabled && gate.missingModel) {
        state.setHighlightModel(gate.missingModel);
        modelPanel.expand();
        return;
    }
    if (!gate.enabled) {
        showToast(gate.reason, "warn");
        return;
    }
    activeToolName = tool.name;
    render();
    showParamsFor(tool);
}

function showParamsFor(tool) {
    clearParams();

    if (tool.name === "refine") {
        activateRefineCanvas(async (points, labels) => {
            await runWithLoading(tool, { points, labels });
            deactivateRefineCanvas();
            activeToolName = null;
            render();
        });
        return;
    }

    const form = document.createElement("form");
    const values = {};
    for (const param of tool.params) {
        if (param.type === "points" || param.type === "labels") continue;
        const field = document.createElement("div");
        field.className = "field";

        const label = document.createElement("label");
        label.textContent = param.label || param.name;
        field.appendChild(label);

        if (param.type === "string") {
            const input = document.createElement("input");
            input.type = "text";
            input.placeholder = param.placeholder || "";
            input.value = param.default || "";
            input.addEventListener("input", () => { values[param.name] = input.value; });
            values[param.name] = input.value;
            field.appendChild(input);
        } else if (param.type === "number") {
            const wrap = document.createElement("div");
            const input = document.createElement("input");
            input.type = "range";
            input.min = String(param.min);
            input.max = String(param.max);
            input.step = String(param.step);
            input.value = String(param.default);
            const row = document.createElement("div");
            row.className = "row";
            row.innerHTML = `<span>${param.min} – ${param.max}</span>` +
                `<span class="value">${parseFloat(input.value).toFixed(2)}</span>`;
            input.addEventListener("input", () => {
                values[param.name] = parseFloat(input.value);
                row.querySelector(".value").textContent = parseFloat(input.value).toFixed(2);
            });
            values[param.name] = parseFloat(input.value);
            wrap.appendChild(input);
            wrap.appendChild(row);
            field.appendChild(wrap);
        }

        form.appendChild(field);
    }

    const submit = document.createElement("button");
    submit.type = "button";
    submit.className = "btn btn-primary";
    submit.textContent = `Run ${tool.label}`;
    submit.addEventListener("click", async () => {
        submit.disabled = true;
        try {
            await runWithLoading(tool, values);
        } finally {
            submit.disabled = false;
            activeToolName = null;
            clearParams();
            render();
        }
    });
    form.appendChild(submit);

    paramsRoot.appendChild(form);
}

async function runWithLoading(tool, params) {
    const wi = state.state.workingItem;
    if (!wi) return;
    const loadingId = addLoadingCard(tool);
    state.setRunningTool(tool.name);
    try {
        const body = { item_id: wi.id, ...params };
        const res = await api.runTool(tool.name, body);
        replaceLoadingCard(loadingId, res.version);
        // Refresh whole items list so sidebars stay in sync.
        const all = await api.listItems();
        state.setItems(all);
        // Update working item to point at the new version.
        const updated = state.state.itemIndex.get(wi.id);
        if (updated) state.setWorkingItem(updated, res.version.id);
        state.emit("version:added", { itemId: wi.id, versionId: res.version.id });
        showToast(`${tool.label} complete.`);
    } catch (e) {
        replaceLoadingCard(loadingId, null, e.message);
        showToast(`${tool.label} failed: ${e.message}`, "error");
    } finally {
        state.setRunningTool(null);
    }
}
