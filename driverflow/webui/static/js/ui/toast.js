// Tiny transient notifications.

let toastEl = null;
let timer = null;

export function showToast(message, level = "info", durationMs = 3500) {
    if (!toastEl) toastEl = document.getElementById("toast");
    if (!toastEl) return;
    toastEl.textContent = message;
    toastEl.classList.remove("error", "warn");
    if (level === "error") toastEl.classList.add("error");
    if (level === "warn")  toastEl.classList.add("warn");
    toastEl.hidden = false;
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => { toastEl.hidden = true; }, durationMs);
}
