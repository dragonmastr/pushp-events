const form = document.getElementById("sendForm");
const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");
const statusText = document.getElementById("statusText");
const totalCount = document.getElementById("totalCount");
const sentCount = document.getElementById("sentCount");
const failedCount = document.getElementById("failedCount");
const skippedCount = document.getElementById("skippedCount");
const currentEmail = document.getElementById("currentEmail");
const startedAt = document.getElementById("startedAt");
const finishedAt = document.getElementById("finishedAt");
const logLink = document.getElementById("logLink");

let pollTimer = null;

function setStatus(payload) {
  statusText.textContent = `${payload.status || "idle"} ${payload.message || ""}`.trim();
  totalCount.textContent = payload.total ?? 0;
  sentCount.textContent = payload.sent ?? 0;
  failedCount.textContent = payload.failed ?? 0;
  skippedCount.textContent = payload.skipped ?? 0;
  currentEmail.textContent = payload.current || "-";
  startedAt.textContent = payload.started_at || "-";
  finishedAt.textContent = payload.finished_at || "-";

  if (payload.log_path) {
    logLink.hidden = false;
    logLink.href = `/download-log?path=${encodeURIComponent(payload.log_path)}`;
  }
}

async function fetchStatus() {
  const res = await fetch("/status");
  const data = await res.json();
  setStatus(data);

  if (data.status !== "running") {
    stopPolling();
    startBtn.disabled = false;
  }
}

function startPolling() {
  if (pollTimer) return;
  pollTimer = setInterval(fetchStatus, 2000);
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  startBtn.disabled = true;
  logLink.hidden = true;

  const formData = new FormData(form);
  const res = await fetch("/start", {
    method: "POST",
    body: formData,
  });

  const data = await res.json();
  if (!data.ok) {
    statusText.textContent = data.error || "Failed to start.";
    startBtn.disabled = false;
    return;
  }

  statusText.textContent = "Job started...";
  startPolling();
  fetchStatus();
});

stopBtn.addEventListener("click", async () => {
  await fetch("/stop", { method: "POST" });
  fetchStatus();
});

fetchStatus();
