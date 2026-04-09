/**
 * app.js  –  Frontend JavaScript for Keystroke Logging Demonstration System
 * ==========================================================================
 * Educational / ethical demo only.  DO NOT use for malicious purposes.
 *
 * Responsibilities:
 *  - Login / logout with session token management (localStorage)
 *  - Start / stop / reset logging via REST API calls
 *  - Real-time keystroke feed via WebSocket (/ws/live)
 *  - Polling fallback for stats (every 5 s)
 *  - Tab switching: Live | Analysis | Storage
 *  - Load and display base64 chart images
 *  - CSV export
 *  - Change-password modal
 */

"use strict";

// ============================================================
// Config
// ============================================================
const API_BASE = "http://localhost:8000";
const WS_BASE  = "ws://localhost:8000";

// ============================================================
// State
// ============================================================
let sessionToken  = localStorage.getItem("kl_session_token") || null;
let wsConnection  = null;
let statsInterval = null;
let livePaused    = false;         // pause auto-scroll on hover

// ============================================================
// DOM helpers
// ============================================================
const $  = id => document.getElementById(id);
const el = (tag, cls, text) => {
  const e = document.createElement(tag);
  if (cls)  e.className   = cls;
  if (text) e.textContent = text;
  return e;
};

// ============================================================
// Toast notifications
// ============================================================
function showToast(msg, type = "info", duration = 3000) {
  const icons = { success: "✅", error: "❌", info: "ℹ️" };
  const container = $("toast-container");
  const toast = el("div", `toast ${type}`);
  toast.innerHTML = `<span>${icons[type] || "•"}</span> ${msg}`;
  container.appendChild(toast);
  setTimeout(() => { toast.style.opacity = "0"; toast.style.transition = "opacity 0.4s"; }, duration - 400);
  setTimeout(() => container.removeChild(toast), duration);
}

// ============================================================
// API helper
// ============================================================
async function api(method, path, body, raw = false) {
  const opts = {
    method,
    headers: {
      "Content-Type":   "application/json",
      "X-Session-Token": sessionToken || "",
    },
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(`${API_BASE}${path}`, opts);

  if (raw) return res;                            // for CSV download
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = data.detail || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return data;
}

// ============================================================
// Auth
// ============================================================
function showPage(page) {
  $("login-page").style.display     = page === "login"     ? "flex"  : "none";
  $("dashboard-page").classList.toggle("active", page === "dashboard");
}

$("login-form").addEventListener("submit", async e => {
  e.preventDefault();
  const pass    = $("password-input").value.trim();
  const errEl   = $("login-error");
  const btnEl   = $("login-btn");
  if (!pass) { errEl.textContent = "Please enter a password."; return; }

  errEl.textContent = "";
  btnEl.disabled    = true;
  btnEl.innerHTML   = '<span class="spinner"></span> Authenticating…';

  try {
    const data = await api("POST", "/api/login", { password: pass });
    sessionToken = data.token;
    localStorage.setItem("kl_session_token", sessionToken);
    showPage("dashboard");
    initDashboard();
  } catch (err) {
    errEl.textContent = err.message;
  } finally {
    btnEl.disabled  = false;
    btnEl.innerHTML = "🔓 Enter System";
  }
});

async function logout() {
  try { await api("POST", "/api/logout"); } catch (_) {}
  sessionToken = null;
  localStorage.removeItem("kl_session_token");
  stopWebSocket();
  clearInterval(statsInterval);
  showPage("login");
  showToast("Logged out successfully.", "info");
}

$("logout-btn").addEventListener("click", logout);

// ============================================================
// Boot: check existing session or show login
// ============================================================
(async function boot() {
  if (!sessionToken) { showPage("login"); return; }
  try {
    await api("GET", "/api/logger/status");   // validate token
    showPage("dashboard");
    initDashboard();
  } catch (_) {
    sessionToken = null;
    localStorage.removeItem("kl_session_token");
    showPage("login");
  }
})();

// ============================================================
// Dashboard initialisation
// ============================================================
function initDashboard() {
  refreshStatus();
  refreshTopKeys();
  statsInterval = setInterval(refreshStatus, 5000);
  connectWebSocket();
}

// ============================================================
// Logger Controls
// ============================================================
$("start-btn").addEventListener("click", async () => {
  try {
    await api("POST", "/api/logger/start");
    showToast("Keystroke logging STARTED.", "success");
    updateStatusUI(true);
    clearFeed();
    connectWebSocket();     // reconnect if needed
  } catch (err) { showToast(err.message, "error"); }
});

$("stop-btn").addEventListener("click", async () => {
  try {
    await api("POST", "/api/logger/stop");
    showToast("Keystroke logging STOPPED.", "info");
    updateStatusUI(false);
  } catch (err) { showToast(err.message, "error"); }
});

$("reset-btn").addEventListener("click", async () => {
  if (!confirm("Reset the live session? (Stored data is not deleted)")) return;
  try {
    await api("POST", "/api/logger/reset");
    clearFeed();
    updateCounters(0, 0);
    showToast("Session reset.", "info");
    updateStatusUI(false);
  } catch (err) { showToast(err.message, "error"); }
});

$("export-btn").addEventListener("click", async () => {
  try {
    const res = await api("GET", "/api/export/csv", null, true);
    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href     = url;
    a.download = "keylog_report.csv";
    a.click();
    URL.revokeObjectURL(url);
    showToast("CSV report downloaded!", "success");
  } catch (err) { showToast("Export failed: " + err.message, "error"); }
});

$("clear-storage-btn").addEventListener("click", async () => {
  if (!confirm("⚠️ This will permanently delete ALL stored keystroke data. Continue?")) return;
  try {
    await api("POST", "/api/logger/clear-storage");
    clearFeed();
    updateCounters(0, 0);
    showToast("All stored data deleted.", "success");
  } catch (err) { showToast(err.message, "error"); }
});

// ============================================================
// Status refresh
// ============================================================
async function refreshStatus() {
  try {
    const data = await api("GET", "/api/logger/status");
    updateStatusUI(data.running);
    updateCounters(data.total_live, data.kpm_live, data.stored_total);
  } catch (_) {}
}

function updateStatusUI(running) {
  const pill  = $("status-pill");
  const dot   = pill.querySelector(".status-dot");
  const start = $("start-btn");
  const stop  = $("stop-btn");

  if (running) {
    pill.className = "status-pill on";
    pill.querySelector(".status-text").textContent = "LOGGING ON";
    start.disabled = true;
    stop.disabled  = false;
  } else {
    pill.className = "status-pill off";
    pill.querySelector(".status-text").textContent = "LOGGING OFF";
    start.disabled = false;
    stop.disabled  = true;
  }
}

function updateCounters(totalLive, kpm, storedTotal) {
  if (totalLive !== undefined) $("count-live").textContent  = totalLive.toLocaleString();
  if (kpm       !== undefined) $("count-kpm").textContent   = kpm.toFixed(1);
  if (storedTotal !== undefined) $("count-stored").textContent = storedTotal.toLocaleString();
}

// ============================================================
// Live Feed (WebSocket)
// ============================================================
function connectWebSocket() {
  if (wsConnection && wsConnection.readyState !== WebSocket.CLOSED) return;
  const url = `${WS_BASE}/ws/live?token=${encodeURIComponent(sessionToken)}`;
  wsConnection = new WebSocket(url);

  wsConnection.onmessage = e => {
    const data = JSON.parse(e.data);
    if (data.heartbeat) return;
    appendToFeed(data);
    // bump live counter
    const cur = parseInt($("count-live").textContent.replace(/,/g, "")) || 0;
    $("count-live").textContent = (cur + 1).toLocaleString();
  };

  wsConnection.onerror  = _  => {};
  wsConnection.onclose  = _  => {};
}

function stopWebSocket() {
  if (wsConnection) { wsConnection.close(); wsConnection = null; }
}

function appendToFeed(record) {
  const feed = $("live-feed");
  // Remove placeholder on first keystroke
  const placeholder = feed.querySelector(".feed-placeholder");
  if (placeholder) placeholder.remove();

  const span = document.createElement("span");
  const key  = record.key || "?";

  if (key === "[SPACE]") {
    span.className   = "key-space";
    span.textContent = " ";
  } else if (record.is_special) {
    span.className   = "key-special";
    span.textContent = key;
  } else {
    span.className   = "key-normal";
    span.textContent = key;
  }

  feed.appendChild(span);

  // Keep the feed to last 1000 chars worth of spans to avoid DOM bloat
  const spans = feed.querySelectorAll("span");
  if (spans.length > 600) { for (let i = 0; i < 50; i++) spans[i].remove(); }

  if (!livePaused) feed.scrollTop = feed.scrollHeight;
}

function clearFeed() {
  $("live-feed").innerHTML = '<p class="feed-placeholder">⌨️ Press Start Logging and begin typing…</p>';
}

// Pause auto-scroll while user hovers the feed
$("live-feed").addEventListener("mouseenter", () => { livePaused = true; });
$("live-feed").addEventListener("mouseleave", () => { livePaused = false; $("live-feed").scrollTop = $("live-feed").scrollHeight; });

// ============================================================
// Top Keys Panel
// ============================================================
async function refreshTopKeys() {
  try {
    const stats = await api("GET", "/api/stats");
    const freq  = stats.key_freq || {};
    renderTopKeys(freq);
    updateCounters(undefined, stats.kpm_live, stats.total);
    $("count-session").textContent = stats.session_mins
      ? `${stats.session_mins} min`
      : "—";
  } catch (_) {}
}

function renderTopKeys(freq) {
  const sorted = Object.entries(freq).sort((a, b) => b[1] - a[1]).slice(0, 10);
  const maxCount = sorted.length ? sorted[0][1] : 1;
  const container = $("top-key-list");
  container.innerHTML = "";

  if (!sorted.length) {
    container.innerHTML = '<p style="color:var(--text-dim);font-size:.82rem;padding:.5rem">No data yet.</p>';
    return;
  }

  sorted.forEach(([key, count]) => {
    const item = el("div", "top-key-item");
    item.innerHTML = `
      <span class="key-label">${escHtml(key)}</span>
      <div class="key-bar-wrap"><div class="key-bar" style="width:${(count / maxCount * 100).toFixed(1)}%"></div></div>
      <span class="key-count">${count}</span>`;
    container.appendChild(item);
  });
}

// ============================================================
// Charts (Analysis Tab)
// ============================================================
$("load-charts-btn").addEventListener("click", loadCharts);

async function loadCharts() {
  const btn = $("load-charts-btn");
  btn.disabled  = true;
  btn.innerHTML = '<span class="spinner"></span> Generating…';

  try {
    const charts = await api("GET", "/api/charts");
    renderChart("chart-bar", charts.bar, "Key Frequency");
    renderChart("chart-kpm", charts.kpm, "Typing Speed (KPM)");
    renderChart("chart-pie", charts.pie, "Key Distribution");
    showToast("Charts loaded!", "success");
  } catch (err) {
    showToast("Chart error: " + err.message, "error");
  } finally {
    btn.disabled  = false;
    btn.innerHTML = "📊 Load Charts";
  }
}

function renderChart(containerId, b64, title) {
  const wrap = $(containerId);
  if (!b64) { wrap.innerHTML = `<div class="chart-placeholder">No data for "${title}"</div>`; return; }
  wrap.innerHTML = `<img src="data:image/png;base64,${b64}" alt="${title}" style="width:100%;border-radius:8px;padding:.5rem">`;
}

// ============================================================
// Recent Keystrokes Table (Storage Tab)
// ============================================================
$("load-table-btn").addEventListener("click", loadTable);

async function loadTable() {
  const btn = $("load-table-btn");
  btn.disabled  = true;
  btn.innerHTML = '<span class="spinner"></span> Loading…';

  try {
    const data  = await api("GET", "/api/keystrokes?n=100");
    const tbody = $("keystrokes-tbody");
    tbody.innerHTML = "";

    const records = [...(data.keystrokes || [])].reverse();   // newest first

    records.forEach(rec => {
      const tr = document.createElement("tr");
      const dt = new Date(rec.timestamp * 1000);
      tr.innerHTML = `
        <td>${dt.toLocaleTimeString()}.${String(dt.getMilliseconds()).padStart(3,"0")}</td>
        <td>${escHtml(rec.key || "?")}</td>
        <td><span class="${rec.is_special ? "badge-special" : "badge-normal"}">${rec.is_special ? "Special" : "Normal"}</span></td>`;
      tbody.appendChild(tr);
    });

    if (!records.length) {
      tbody.innerHTML = '<tr><td colspan="3" style="text-align:center;color:var(--text-dim);padding:1.5rem">No records found.</td></tr>';
    }
    showToast(`Loaded ${records.length} records.`, "info");
  } catch (err) {
    showToast("Failed to load records: " + err.message, "error");
  } finally {
    btn.disabled  = false;
    btn.innerHTML = "🔄 Refresh Records";
  }
}

// ============================================================
// Tab Switching
// ============================================================
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    $(btn.dataset.tab).classList.add("active");
    // Auto-load when switching tabs
    if (btn.dataset.tab === "tab-analysis") { refreshTopKeys(); }
    if (btn.dataset.tab === "tab-storage")  { loadTable(); }
  });
});

// ============================================================
// Change Password Modal
// ============================================================
$("change-pass-btn").addEventListener("click", () => {
  $("change-pass-modal").classList.add("open");
});
$("modal-close-btn").addEventListener("click", () => {
  $("change-pass-modal").classList.remove("open");
});

$("change-pass-form").addEventListener("submit", async e => {
  e.preventDefault();
  const oldPass = $("old-password").value.trim();
  const newPass = $("new-password").value.trim();
  const errEl   = $("change-pass-error");
  errEl.textContent = "";

  if (newPass.length < 6) {
    errEl.textContent = "New password must be at least 6 characters.";
    return;
  }

  try {
    await api("POST", "/api/change-password", { old_password: oldPass, new_password: newPass });
    $("change-pass-modal").classList.remove("open");
    $("change-pass-form").reset();
    showToast("Password changed successfully!", "success");
  } catch (err) {
    errEl.textContent = err.message;
  }
});

// ============================================================
// Utility
// ============================================================
function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}
