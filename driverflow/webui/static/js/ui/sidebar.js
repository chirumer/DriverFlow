// Left sidebar: pluggable section registry. Each section lists items
// (filtered by source + media type) and makes each entry draggable.

import * as state from "../state.js";
import { thumbUrl } from "../api.js";

const SECTIONS = [
    { id: "raw",       label: "Raw Media",      source: "raw" },
    { id: "processed", label: "Processed",      source: "processed" },
    { id: "exported",  label: "Exported",       source: "exported" },
];

const root = document.getElementById("sidebar-sections");
const mediaFilters = document.querySelectorAll('#filter-media input[type="checkbox"]');

mediaFilters.forEach((cb) => {
    cb.addEventListener("change", () => {
        state.state.filters.media[cb.value] = cb.checked;
        render();
    });
});

state.on("items:changed", render);
state.on("working:changed", render);

export function render() {
    root.innerHTML = "";
    for (const section of SECTIONS) {
        const wrap = document.createElement("div");
        wrap.className = "sidebar-section";

        const header = document.createElement("div");
        header.className = "section-header";
        header.textContent = section.label;
        wrap.appendChild(header);

        const list = document.createElement("div");
        list.className = "section-items";
        wrap.appendChild(list);

        const items = filterFor(section.source);
        if (items.length === 0) {
            const empty = document.createElement("div");
            empty.className = "sidebar-empty";
            empty.textContent = "—";
            list.appendChild(empty);
        } else {
            for (const item of items) list.appendChild(renderItem(item));
        }
        root.appendChild(wrap);
    }
}

function filterFor(source) {
    const { media } = state.state.filters;
    return state.state.items.filter((item) => {
        if (!media[item.media_type]) return false;
        if (source === "raw") return true;
        if (source === "processed") return (item.sources || []).includes("processed");
        if (source === "exported")  return (item.sources || []).includes("exported");
        return true;
    });
}

function renderItem(item) {
    const el = document.createElement("div");
    el.className = "sidebar-item";
    el.draggable = true;
    el.dataset.itemId = item.id;
    if (state.state.selectedItemIds.has(item.id)) el.classList.add("selected");

    const img = document.createElement("img");
    img.className = "thumb";
    img.alt = "";
    img.src = thumbUrl(item.id);
    el.appendChild(img);

    const name = document.createElement("div");
    name.className = "name";
    name.textContent = item.name;
    name.title = item.name;
    el.appendChild(name);

    const badges = document.createElement("div");
    badges.className = "badges";
    badges.textContent = item.media_type === "video" ? "🎬" : "🖼";
    el.appendChild(badges);

    el.addEventListener("click", (e) => {
        if (e.shiftKey) {
            if (state.state.selectedItemIds.has(item.id)) {
                state.state.selectedItemIds.delete(item.id);
            } else {
                state.state.selectedItemIds.add(item.id);
            }
            render();
        } else {
            state.state.selectedItemIds.clear();
            state.state.selectedItemIds.add(item.id);
            state.emit("working:replace-request", { itemId: item.id });
        }
    });

    el.addEventListener("dragstart", (e) => {
        let ids;
        if (state.state.selectedItemIds.has(item.id) && state.state.selectedItemIds.size > 1) {
            ids = Array.from(state.state.selectedItemIds);
        } else {
            ids = [item.id];
        }
        e.dataTransfer.setData("application/x-driverflow-item-ids", JSON.stringify(ids));
        e.dataTransfer.effectAllowed = "copy";
    });

    return el;
}
