// Confirmation modal helper.

export function confirmModal({ title, body, okLabel = "Replace", cancelLabel = "Cancel" }) {
    return new Promise((resolve) => {
        const modal = document.getElementById("modal-confirm");
        const titleEl = document.getElementById("modal-confirm-title");
        const bodyEl  = document.getElementById("modal-confirm-body");
        const okBtn   = document.getElementById("modal-confirm-ok");
        const noBtn   = document.getElementById("modal-confirm-cancel");
        if (title) titleEl.textContent = title;
        if (body)  bodyEl.textContent  = body;
        okBtn.textContent = okLabel;
        noBtn.textContent = cancelLabel;
        modal.hidden = false;

        const cleanup = () => {
            modal.hidden = true;
            okBtn.removeEventListener("click", onOk);
            noBtn.removeEventListener("click", onNo);
        };
        const onOk = () => { cleanup(); resolve(true); };
        const onNo = () => { cleanup(); resolve(false); };
        okBtn.addEventListener("click", onOk);
        noBtn.addEventListener("click", onNo);
    });
}
