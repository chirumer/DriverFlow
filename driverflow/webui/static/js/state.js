// Tiny reactive store + event bus shared across UI modules.

export const state = {
    items: [],
    itemIndex: new Map(),               // id -> item
    selectedItemIds: new Set(),         // sidebar multi-select
    filters: {
        media: { image: true, video: true },
        sources: ["raw", "processed", "exported"],
    },
    models: { dino: false, sam: false, device: null },
    workingItem: null,                  // {id, name, media_type, currentVersionId}
    highlightModel: null,               // "dino" | "sam" | null
    toolDescriptors: [],                // from /api/tools/registry
    runningToolName: null,
};

const listeners = new Map();

export function on(eventName, fn) {
    if (!listeners.has(eventName)) listeners.set(eventName, new Set());
    listeners.get(eventName).add(fn);
    return () => listeners.get(eventName).delete(fn);
}

export function emit(eventName, payload) {
    const set = listeners.get(eventName);
    if (!set) return;
    for (const fn of set) {
        try { fn(payload); } catch (e) { console.error(`[state:${eventName}]`, e); }
    }
}

export function setItems(items) {
    state.items = items;
    state.itemIndex = new Map(items.map((i) => [i.id, i]));
    emit("items:changed", { items });
}

export function setModels(s) {
    Object.assign(state.models, s);
    emit("models:changed", { models: state.models });
}

export function setWorkingItem(item, versionId = null) {
    if (item) {
        state.workingItem = {
            id: item.id,
            name: item.name,
            media_type: item.media_type,
            currentVersionId: versionId,
            versions: item.version_kinds || [],
        };
    } else {
        state.workingItem = null;
    }
    emit("working:changed", { workingItem: state.workingItem });
}

export function setItem(updatedItem) {
    state.itemIndex.set(updatedItem.id, updatedItem);
    const idx = state.items.findIndex((i) => i.id === updatedItem.id);
    if (idx >= 0) state.items[idx] = updatedItem;
    if (state.workingItem && state.workingItem.id === updatedItem.id) {
        state.workingItem.name = updatedItem.name;
        state.workingItem.versions = updatedItem.version_kinds || [];
    }
    emit("items:changed", { items: state.items });
    emit("working:changed", { workingItem: state.workingItem });
}

export function setHighlightModel(name) {
    state.highlightModel = name;
    emit("highlight:changed", { highlightModel: name });
}

export function setToolDescriptors(descriptors) {
    state.toolDescriptors = descriptors;
    emit("tools:changed", { toolDescriptors: descriptors });
}

export function setRunningTool(name) {
    state.runningToolName = name;
    emit("tool-running:changed", { name });
}

// Working item is "dirty" if it has any non-raw versions and has not been exported.
export function isWorkingDirty() {
    const wi = state.workingItem;
    if (!wi) return false;
    const item = state.itemIndex.get(wi.id);
    if (!item) return false;
    const kinds = item.version_kinds || [];
    const hasDerived = kinds.some((k) => k !== "raw");
    const wasExported = (item.sources || []).includes("exported");
    return hasDerived && !wasExported;
}
