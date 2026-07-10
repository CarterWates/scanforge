const state = {
  jobId: null,
  scanId: null,
  poll: null,
  results: [],
  sortField: "port",
  sortAsc: true,
};

const form = document.querySelector("#scan-form");
const startButton = document.querySelector("#start-button");
const scanTitle = document.querySelector("#scan-title");
const progressMetric = document.querySelector("#metric-progress");
const openMetric = document.querySelector("#metric-open");
const durationMetric = document.querySelector("#metric-duration");
const stateMetric = document.querySelector("#metric-state");
const progressBar = document.querySelector("#progress-bar");
const resultsBody = document.querySelector("#results-body");
const searchInput = document.querySelector("#result-search");
const stateFilter = document.querySelector("#state-filter");
const historyList = document.querySelector("#history-list");
const toast = document.querySelector("#toast");
const jsonLink = document.querySelector("#json-link");
const csvLink = document.querySelector("#csv-link");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(form);
  await startScan({
    target: data.get("target"),
    ports: data.get("ports"),
    timeout: Number(data.get("timeout")),
    concurrency: Number(data.get("concurrency")),
    max_targets: Number(data.get("max_targets")),
    banner: data.get("banner") === "on",
    allow_large_scan: data.get("allow_large_scan") === "on",
  });
});

document.querySelector("#refresh-history").addEventListener("click", loadHistory);
searchInput.addEventListener("input", renderResults);
stateFilter.addEventListener("change", renderResults);
document.querySelectorAll("th[data-sort]").forEach((header) => {
  header.addEventListener("click", () => {
    const field = header.dataset.sort;
    state.sortAsc = state.sortField === field ? !state.sortAsc : true;
    state.sortField = field;
    renderResults();
  });
});

async function startScan(payload) {
  startButton.disabled = true;
  setExports(null);
  try {
    const response = await fetch("/api/scans", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const body = await response.json();
    if (!response.ok) throw new Error(body.error || "Scan failed to start.");
    state.jobId = body.job_id;
    state.results = [];
    scanTitle.textContent = `${payload.target} · ${payload.ports}`;
    stateMetric.textContent = "Running";
    renderResults();
    pollJob();
  } catch (error) {
    showToast(error.message);
    startButton.disabled = false;
  }
}

async function pollJob() {
  clearTimeout(state.poll);
  if (!state.jobId) return;
  try {
    const response = await fetch(`/api/scans/${state.jobId}`);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Unable to read scan status.");
    updateCurrentScan(payload);
    if (payload.status === "running") {
      state.poll = setTimeout(pollJob, 350);
    } else {
      startButton.disabled = false;
      await loadHistory();
    }
  } catch (error) {
    showToast(error.message);
    startButton.disabled = false;
  }
}

function updateCurrentScan(payload) {
  state.results = payload.results || [];
  state.scanId = payload.scan_id;
  const total = payload.total_checks || 0;
  const completed = payload.completed_checks || 0;
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0;
  const summary = payload.summary || {};
  progressMetric.textContent = `${completed} / ${total}`;
  openMetric.textContent = summary.open_ports ?? countOpen(state.results);
  durationMetric.textContent = `${(summary.duration_seconds ?? 0).toFixed(3)}s`;
  stateMetric.textContent = titleCase(payload.status);
  progressBar.style.width = `${pct}%`;
  setExports(payload.scan_id);
  if (payload.error) showToast(payload.error);
  renderResults();
}

function renderResults() {
  const query = searchInput.value.trim().toLowerCase();
  const desiredState = stateFilter.value;
  const rows = [...state.results]
    .filter((row) => desiredState === "all" || row.state === desiredState)
    .filter((row) => {
      if (!query) return true;
      return [row.target, row.port, row.state, row.banner, row.error]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(query);
    })
    .sort((a, b) => compareValues(a[state.sortField], b[state.sortField]));

  if (!state.sortAsc) rows.reverse();
  if (rows.length === 0) {
    resultsBody.innerHTML = '<tr><td colspan="6" class="empty">No matching results.</td></tr>';
    return;
  }
  resultsBody.innerHTML = rows.map((row) => `
    <tr>
      <td>${escapeHtml(row.target)}</td>
      <td>${row.port}</td>
      <td><span class="state ${row.state}">${escapeHtml(row.state)}</span></td>
      <td>${Number(row.latency_ms).toFixed(2)} ms</td>
      <td>${escapeHtml(row.banner || "")}</td>
      <td>${escapeHtml(row.error || "")}</td>
    </tr>
  `).join("");
}

async function loadHistory() {
  try {
    const response = await fetch("/api/history");
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Unable to load history.");
    renderHistory(payload.history || []);
  } catch (error) {
    showToast(error.message);
  }
}

function renderHistory(items) {
  if (items.length === 0) {
    historyList.innerHTML = '<p class="empty">No saved scans yet.</p>';
    return;
  }
  historyList.innerHTML = items.map((item) => `
    <article class="history-item">
      <h3>${escapeHtml(item.target_spec)}</h3>
      <div class="history-meta">
        <span>${escapeHtml(item.port_spec)} · ${item.total_checks} checks</span>
        <span>${item.open_ports} open · ${Number(item.duration_seconds).toFixed(3)}s</span>
        <span>${escapeHtml(item.created_at)}</span>
      </div>
      <div class="history-actions">
        <button class="mini-button" type="button" data-view="${item.id}">View</button>
        <button class="mini-button" type="button" data-rerun="${item.id}">Rerun</button>
        <a class="mini-button" href="/api/history/${item.id}/export.json">JSON</a>
        <a class="mini-button" href="/api/history/${item.id}/export.csv">CSV</a>
      </div>
    </article>
  `).join("");
  historyList.querySelectorAll("[data-view]").forEach((button) => {
    button.addEventListener("click", () => viewHistory(button.dataset.view));
  });
  historyList.querySelectorAll("[data-rerun]").forEach((button) => {
    button.addEventListener("click", () => rerunHistory(button.dataset.rerun));
  });
}

async function viewHistory(scanId) {
  try {
    const response = await fetch(`/api/history/${scanId}`);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Unable to load report.");
    state.results = payload.report.results || [];
    state.scanId = payload.id;
    scanTitle.textContent = `${payload.options.target} · ${payload.options.ports}`;
    updateSummaryFromReport(payload.report, payload.id);
    renderResults();
  } catch (error) {
    showToast(error.message);
  }
}

async function rerunHistory(scanId) {
  try {
    const response = await fetch(`/api/history/${scanId}/rerun`, { method: "POST" });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Unable to rerun scan.");
    state.jobId = payload.job_id;
    startButton.disabled = true;
    pollJob();
  } catch (error) {
    showToast(error.message);
  }
}

function updateSummaryFromReport(report, scanId) {
  const summary = report.summary;
  progressMetric.textContent = `${summary.total_checks} / ${summary.total_checks}`;
  openMetric.textContent = summary.open_ports;
  durationMetric.textContent = `${Number(summary.duration_seconds).toFixed(3)}s`;
  stateMetric.textContent = "Saved";
  progressBar.style.width = "100%";
  setExports(scanId);
}

function setExports(scanId) {
  [jsonLink, csvLink].forEach((link) => link.classList.toggle("disabled", !scanId));
  if (!scanId) return;
  jsonLink.href = `/api/history/${scanId}/export.json`;
  csvLink.href = `/api/history/${scanId}/export.csv`;
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("visible");
  setTimeout(() => toast.classList.remove("visible"), 3600);
}

function countOpen(rows) {
  return rows.filter((row) => row.state === "open").length;
}

function compareValues(a, b) {
  if (typeof a === "number" && typeof b === "number") return a - b;
  return String(a ?? "").localeCompare(String(b ?? ""));
}

function titleCase(value) {
  if (!value) return "Idle";
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

loadHistory();
