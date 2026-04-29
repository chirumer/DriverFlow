let selectedFile = null;
let lastDetections = null;
let lastImageWidth = null;
let lastImageHeight = null;

const uploadZone = document.getElementById("upload-zone");
const fileInput = document.getElementById("file-input");
const previewContainer = document.getElementById("preview-container");
const preview = document.getElementById("preview");
const textPromptInput = document.getElementById("text-prompt");
const boxSlider = document.getElementById("box-threshold");
const textSlider = document.getElementById("text-threshold");
const boxVal = document.getElementById("box-val");
const textVal = document.getElementById("text-val");
const detectBtn = document.getElementById("detect-btn");
const loadingDiv = document.getElementById("loading");
const resultsDiv = document.getElementById("results");
const emptyState = document.getElementById("empty-state");
const annotatedImg = document.getElementById("annotated-img");
const summaryBody = document.getElementById("summary-body");
const downloadBtn = document.getElementById("download-btn");

uploadZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    uploadZone.classList.add("dragover");
});

uploadZone.addEventListener("dragleave", () => {
    uploadZone.classList.remove("dragover");
});

uploadZone.addEventListener("drop", (e) => {
    e.preventDefault();
    uploadZone.classList.remove("dragover");
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
});

uploadZone.addEventListener("click", () => {
    fileInput.click();
});

fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) {
        handleFile(fileInput.files[0]);
    }
});

boxSlider.addEventListener("input", (e) => {
    boxVal.textContent = parseFloat(e.target.value).toFixed(2);
});

textSlider.addEventListener("input", (e) => {
    textVal.textContent = parseFloat(e.target.value).toFixed(2);
});

detectBtn.addEventListener("click", runDetection);

downloadBtn.addEventListener("click", downloadYolo);

function handleFile(file) {
    if (!file.type.startsWith("image/")) {
        alert("Please select an image file");
        return;
    }

    selectedFile = file;

    const reader = new FileReader();
    reader.onload = (e) => {
        preview.src = e.target.result;
        previewContainer.hidden = false;
    };
    reader.readAsDataURL(file);

    detectBtn.disabled = false;
}

async function runDetection() {
    if (!selectedFile) {
        alert("Please select an image first");
        return;
    }

    if (!textPromptInput.value.trim()) {
        alert("Please enter a text prompt");
        return;
    }

    const formData = new FormData();
    formData.append("image", selectedFile);
    formData.append("text_prompt", textPromptInput.value);
    formData.append("box_threshold", parseFloat(boxSlider.value));
    formData.append("text_threshold", parseFloat(textSlider.value));

    showLoading(true);

    try {
        const response = await fetch("/api/detect", {
            method: "POST",
            body: formData,
        });

        if (!response.ok) {
            const error = await response.text();
            throw new Error(`Detection failed: ${error}`);
        }

        const data = await response.json();
        renderResults(data);

    } catch (error) {
        alert(`Error: ${error.message}`);
    } finally {
        showLoading(false);
    }
}

function showLoading(show) {
    loadingDiv.hidden = !show;
}

function renderResults(data) {
    lastDetections = data.detections;
    lastImageWidth = data.image_width;
    lastImageHeight = data.image_height;

    annotatedImg.src = `data:image/jpeg;base64,${data.annotated_image_b64}`;

    summaryBody.innerHTML = "";
    data.class_counts.forEach((row) => {
        const tr = document.createElement("tr");
        const confidence = (row.avg_confidence * 100).toFixed(1);
        tr.innerHTML = `
            <td>${escapeHtml(row.class)}</td>
            <td>${row.count}</td>
            <td>${confidence}%</td>
        `;
        summaryBody.appendChild(tr);
    });

    resultsDiv.hidden = false;
    emptyState.hidden = true;
    downloadBtn.hidden = false;
}

async function downloadYolo() {
    if (!lastDetections) {
        alert("No detections to download");
        return;
    }

    try {
        const response = await fetch("/api/download_yolo", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                detections: lastDetections,
                image_width: lastImageWidth,
                image_height: lastImageHeight,
            }),
        });

        if (!response.ok) {
            throw new Error("Download failed");
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "driverflow_annotations.zip";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

    } catch (error) {
        alert(`Error downloading: ${error.message}`);
    }
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}
