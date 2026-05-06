const downloads = [
  {
    platform: "Windows",
    format: ".zip",
    version: "v1.0.0",
    size: "Pack local",
    description: "Archive de demonstration telechargeable directement depuis le repo Git.",
    url: "./downloads/ai-agent-windows.zip",
    label: "Télécharger pour Windows",
    filename: "ai-agent-windows.zip",
  },
  {
    platform: "macOS",
    format: ".zip",
    version: "v1.0.0",
    size: "Pack local",
    description: "Archive de demonstration telechargeable directement depuis le repo Git.",
    url: "./downloads/ai-agent-macos.zip",
    label: "Télécharger pour macOS",
    filename: "ai-agent-macos.zip",
  },
  {
    platform: "Linux",
    format: ".zip",
    version: "v1.0.0",
    size: "Pack local",
    description: "Archive de demonstration telechargeable directement depuis le repo Git.",
    url: "./downloads/ai-agent-linux.zip",
    label: "Télécharger pour Linux",
    filename: "ai-agent-linux.zip",
  },
];

const versionNode = document.getElementById("currentVersion");
const updatedNode = document.getElementById("lastUpdated");
const grid = document.getElementById("downloadGrid");

function renderDownloads() {
  grid.innerHTML = "";

  downloads.forEach((item) => {
    const card = document.createElement("article");
    card.className = "download-card";
    card.innerHTML = `
      <span class="download-badge">${item.platform} ${item.format}</span>
      <h3>${item.label}</h3>
      <p>${item.description}</p>
      <div class="download-meta">
        <span>${item.version}</span>
        <span>${item.size}</span>
      </div>
      <a class="download-button" href="${item.url}" download="${item.filename}">${item.label}</a>
    `;
    grid.appendChild(card);
  });

  if (downloads[0]) {
    versionNode.textContent = downloads[0].version;
  }

  updatedNode.textContent = new Date().toISOString().slice(0, 10);
}

renderDownloads();

const widget = document.getElementById("widget");
const dragHandle = document.getElementById("dragHandle");
const powerSwitch = document.getElementById("powerSwitch");
const widgetStatus = document.getElementById("widgetStatus");

let isOn = true;
let isDragging = false;
let pendingDrag = false;
let dragPointerId = null;
let offsetX = 0;
let offsetY = 0;
let startX = 0;
let startY = 0;
const dragThreshold = 6;

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function setPowerState(nextValue) {
  isOn = nextValue;
  widget.classList.toggle("off", !isOn);
  widgetStatus.textContent = isOn ? "On" : "Off";
}

function resetDragState() {
  pendingDrag = false;
  isDragging = false;
  dragPointerId = null;
}

powerSwitch.addEventListener("click", () => {
  setPowerState(!isOn);
});

dragHandle.addEventListener("pointerdown", (event) => {
  if (event.target.closest("button")) {
    return;
  }

  const rect = widget.getBoundingClientRect();
  pendingDrag = true;
  isDragging = false;
  dragPointerId = event.pointerId;
  startX = event.clientX;
  startY = event.clientY;
  offsetX = event.clientX - rect.left;
  offsetY = event.clientY - rect.top;
  widget.style.left = `${rect.left}px`;
  widget.style.top = `${rect.top}px`;
  widget.style.right = "auto";
  widget.style.bottom = "auto";
  dragHandle.setPointerCapture(event.pointerId);
});

dragHandle.addEventListener("pointermove", (event) => {
  if (event.pointerId !== dragPointerId) {
    return;
  }

  if (pendingDrag) {
    const movedX = Math.abs(event.clientX - startX);
    const movedY = Math.abs(event.clientY - startY);
    if (movedX < dragThreshold && movedY < dragThreshold) {
      return;
    }
    pendingDrag = false;
    isDragging = true;
  }

  if (!isDragging) {
    return;
  }

  const nextLeft = clamp(event.clientX - offsetX, 0, window.innerWidth - widget.offsetWidth);
  const nextTop = clamp(event.clientY - offsetY, 0, window.innerHeight - widget.offsetHeight);

  widget.style.left = `${nextLeft}px`;
  widget.style.top = `${nextTop}px`;
});

dragHandle.addEventListener("pointerup", (event) => {
  if (event.pointerId !== dragPointerId) {
    return;
  }

  if (dragHandle.hasPointerCapture(event.pointerId)) {
    dragHandle.releasePointerCapture(event.pointerId);
  }
  resetDragState();
});

dragHandle.addEventListener("pointercancel", (event) => {
  if (event.pointerId !== dragPointerId) {
    return;
  }
  resetDragState();
});

dragHandle.addEventListener("lostpointercapture", () => {
  resetDragState();
});

setPowerState(true);
