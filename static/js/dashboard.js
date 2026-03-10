"use strict";

// ── POLLING INTERVALS ─────────────────────────────────────────
const STATS_INTERVAL    = 8000;   // ms
const SENSOR_INTERVAL   = 3000;
const INVENTORY_INTERVAL = 10000;
const ACTIVITY_INTERVAL  = 10000;

// ── CLOCK ─────────────────────────────────────────────────────
function tickClock() {
  const el = document.getElementById("clock");
  if (el) {
    const now = new Date();
    el.textContent = now.toLocaleTimeString();
  }
}
setInterval(tickClock, 1000);
tickClock();

// ── FETCH HELPERS ─────────────────────────────────────────────
async function apiFetch(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

async function apiPost(path, body = {}) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res.json();
}

function setConnectionBadge(ok) {
  const el = document.getElementById("connection-badge");
  if (!el) return;
  if (ok) {
    el.textContent = "● Live";
    el.className = "badge badge--ok";
  } else {
    el.textContent = "● Offline";
    el.className = "badge badge--err";
  }
}

// ── TOAST ─────────────────────────────────────────────────────
let _toastTimer = null;
function showToast(msg, duration = 3000) {
  const el = document.getElementById("toast");
  if (!el) return;
  el.textContent = msg;
  el.classList.remove("hidden");
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => el.classList.add("hidden"), duration);
}

// ── STATS ─────────────────────────────────────────────────────
async function loadStats() {
  try {
    const d = await apiFetch("/api/stats");
    document.getElementById("stat-total").textContent     = d.total_gallons    ?? "—";
    document.getElementById("stat-active").textContent    = d.active_gallons   ?? "—";
    document.getElementById("stat-defective").textContent = d.defective_gallons ?? "—";
    document.getElementById("stat-refills").textContent   = d.total_refills    ?? "—";
    setConnectionBadge(true);
  } catch {
    setConnectionBadge(false);
  }
}

// ── SENSOR ────────────────────────────────────────────────────
function setSensorCard(cardId, valueId, value, text, state) {
  const card = document.getElementById(cardId);
  const val  = document.getElementById(valueId);
  if (!card || !val) return;
  val.textContent = text;
  card.classList.remove("active", "warning", "error");
  if (state) card.classList.add(state);
}

async function loadSensor() {
  try {
    const d = await apiFetch("/api/sensor");

    const psi = d.pressure_psi != null ? `${d.pressure_psi} PSI` : "N/A";
    const pressureState = d.leak_detected ? "error" : (d.pressure_psi != null ? "active" : "");
    setSensorCard("sc-pressure", "sv-pressure", d.pressure_psi, psi, pressureState);

    const dist = d.distance_cm != null ? `${d.distance_cm} cm` : "N/A";
    setSensorCard("sc-distance", "sv-distance", d.distance_cm, dist, d.distance_cm != null ? "active" : "");

    setSensorCard("sc-valve",    "sv-valve",    d.valve_open,
                  d.valve_open ? "OPEN" : "CLOSED",
                  d.valve_open ? "warning" : "active");

    setSensorCard("sc-conveyor", "sv-conveyor",  d.conveyor_running,
                  d.conveyor_running ? "RUNNING" : "STOPPED",
                  d.conveyor_running ? "active" : "");

    setSensorCard("sc-leak",     "sv-leak",      d.leak_detected,
                  d.leak_detected ? "⚠ LEAK" : "OK",
                  d.leak_detected ? "error" : "active");

    const wfState = d.workflow_state ?? "IDLE";
    const wfClass = wfState === "IDLE" ? "" : wfState === "COMPLETE" ? "active" : "warning";
    setSensorCard("sc-workflow", "sv-workflow", wfState, wfState, wfClass);

    const updated = document.getElementById("sensor-updated");
    if (updated) updated.textContent = d.last_updated ?? "—";

  } catch {
    // no-op — connection badge already handled in loadStats
  }
}

// ── INVENTORY TABLE ───────────────────────────────────────────
async function loadInventory() {
  try {
    const items = await apiFetch("/api/inventory");
    const tbody = document.getElementById("inventory-tbody");
    if (!tbody) return;

    if (!items.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="empty-row">No gallons found</td></tr>';
      return;
    }

    tbody.innerHTML = items.map(g => {
      const status = g.status ?? "active";
      const badgeCls = status === "defective" ? "status-badge--defective" : "status-badge--active";
      return `<tr>
        <td>${escHtml(g.inventory_id ?? "")}</td>
        <td>${escHtml(g.name ?? "")}</td>
        <td><span class="status-badge ${badgeCls}">${escHtml(status)}</span></td>
        <td>${g.refills ?? 0}</td>
        <td>${g.defects ?? 0}</td>
        <td>
          <button class="btn btn--green" onclick="remoteRefill('${escHtml(g.inventory_id)}')">Refill</button>
          <button class="btn btn--red"   onclick="remoteDefect('${escHtml(g.inventory_id)}')">Defect</button>
        </td>
      </tr>`;
    }).join("");
  } catch (e) {
    const tbody = document.getElementById("inventory-tbody");
    if (tbody) tbody.innerHTML = '<tr><td colspan="6" class="empty-row">Error loading data</td></tr>';
  }
}

// ── ACTIVITY FEED ─────────────────────────────────────────────
const ACTIVITY_ICONS = {
  ADD:    "➕",  REFILL: "💧",  DEFECT: "⚠️",
  SCAN:   "🔍",  FIX:    "🔧",  DELETE: "🗑️",
};

async function loadActivity() {
  try {
    const logs = await apiFetch("/api/activity");
    const feed = document.getElementById("activity-feed");
    if (!feed) return;

    if (!logs.length) {
      feed.innerHTML = '<li class="activity-item activity-item--empty">No activity yet</li>';
      return;
    }

    feed.innerHTML = logs.map(l => {
      const type = (l.activity_type ?? "OTHER").toUpperCase();
      const icon = ACTIVITY_ICONS[type] ?? "📌";
      const typeCls = `activity-type--${type in ACTIVITY_ICONS ? type : "OTHER"}`;
      const ts = l.timestamp ? l.timestamp.split(".")[0] : "";
      return `<li class="activity-item">
        <span class="activity-type ${typeCls}">${icon} ${escHtml(type)}</span>
        <span class="activity-desc">${escHtml(l.description ?? "")}</span>
        <span class="activity-time">${escHtml(ts)}</span>
      </li>`;
    }).join("");
  } catch {
    // ignore
  }
}

// ── REMOTE ACTIONS ────────────────────────────────────────────
async function remoteRefill(id) {
  if (!confirm(`Mark refill for ${id}?`)) return;
  try {
    const res = await apiPost(`/api/inventory/${encodeURIComponent(id)}/refill`);
    showToast(res.success ? `✅ Refill recorded for ${id}` : `❌ ${res.message}`);
    loadInventory();
    loadStats();
    loadActivity();
  } catch {
    showToast("❌ Request failed");
  }
}

async function remoteDefect(id) {
  if (!confirm(`Report defect for ${id}?`)) return;
  try {
    const res = await apiPost(`/api/inventory/${encodeURIComponent(id)}/defect`);
    showToast(res.success ? `⚠️ Defect reported for ${id}` : `❌ ${res.message}`);
    loadInventory();
    loadStats();
    loadActivity();
  } catch {
    showToast("❌ Request failed");
  }
}

// ── SECURITY: HTML ESCAPE ─────────────────────────────────────
function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// ── INIT & POLLING ────────────────────────────────────────────
function init() {
  loadStats();
  loadSensor();
  loadInventory();
  loadActivity();

  setInterval(loadStats,     STATS_INTERVAL);
  setInterval(loadSensor,    SENSOR_INTERVAL);
  setInterval(loadInventory, INVENTORY_INTERVAL);
  setInterval(loadActivity,  ACTIVITY_INTERVAL);
}

document.addEventListener("DOMContentLoaded", init);
