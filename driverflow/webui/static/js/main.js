// Entrypoint — pulls in every UI module so their side-effects register.

import * as api from "./api.js";
import * as state from "./state.js";

import "./ui/import.js";
import "./ui/sidebar.js";
import "./ui/workspace.js";
import "./ui/data-workspace.js";
import "./ui/cloud-mock.js";
import * as modelPanel from "./ui/model-panel.js";
import * as toolsPanel from "./ui/tools.js";

(async function init() {
    try {
        const items = await api.listItems();
        state.setItems(items);
    } catch (e) {
        console.error("[init] items:", e);
    }
    await modelPanel.init();
    await toolsPanel.init();
})();
