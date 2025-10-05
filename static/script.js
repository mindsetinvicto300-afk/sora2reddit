function clearSharedEntries() {
  if (!sharedList) return;
  sharedList.innerHTML = "";
}
const CODES_ENDPOINT = "/api/codes";
const MANUAL_SCAN_ENDPOINT = "/api/scan";
const POLL_INTERVAL = 5000;

const codesList = document.getElementById("codes-list");
const statusIndicator = document.getElementById("status-indicator");
const lastUpdateSpan = document.getElementById("last-update");
const rescanButton = document.getElementById("rescan-btn");
const inlineScanButton = document.getElementById("scan-inline");
const soundToggle = document.getElementById("sound-toggle");
const template = document.getElementById("code-row-template");
const emptyHint = document.getElementById("empty-hint");
const statTotal = document.getElementById("stat-total");
const statLatest = document.getElementById("stat-latest");
const shareForm = document.getElementById("share-form");
const shareCodesInput = document.getElementById("share-codes");
const shareNoteInput = document.getElementById("share-note");
const shareFeedback = document.getElementById("share-feedback");
const sharedList = document.getElementById("shared-codes");
const clearSharedButton = document.getElementById("clear-shared");

const state = {
  codes: new Map(),
  lastFetchedAt: 0,
  audioContext: null,
};

function formatTimestamp(epochSeconds) {
  if (!epochSeconds) return "Unknown";
  const date = new Date(epochSeconds * 1000);
  return date.toLocaleString();
}

function createRow(entry) {
  const fragment = template.content.cloneNode(true);
  const li = fragment.querySelector("li");
  const codeEl = li.querySelector(".code");
  const authorEl = li.querySelector(".author span");
  const permalinkEl = li.querySelector(".permalink");
  const timestampEl = li.querySelector(".timestamp");
  const timestampTextEl = timestampEl.querySelector("span");
  const copyButton = li.querySelector(".copy-btn");

  codeEl.textContent = entry.code;
  permalinkEl.href = entry.permalink || "#";
  permalinkEl.textContent = entry.permalink ? "View on Reddit" : "No link";
  authorEl.textContent = entry.author ? `u/${entry.author}` : "unknown";
  timestampEl.dateTime = new Date(entry.first_seen * 1000).toISOString();
  timestampTextEl.textContent = formatTimestamp(entry.first_seen);

  copyButton.addEventListener("click", () => copyCode(entry.code, copyButton));

  return li;
}

async function copyCode(code, button) {
  try {
    await navigator.clipboard.writeText(code);
    button.textContent = "Copied";
    setTimeout(() => {
      button.textContent = "Copy";
    }, 1500);
  } catch (error) {
    console.error("Clipboard write failed", error);
    button.textContent = "Failed";
    setTimeout(() => {
      button.textContent = "Copy";
    }, 1500);
  }
}

function renderCodes(codes) {
  codesList.innerHTML = "";
  // Show only last 5 codes
  const lastFiveCodes = codes.slice(0, 5);
  lastFiveCodes.forEach((entry) => {
    const row = createRow(entry);
    codesList.appendChild(row);
  });
  toggleEmptyState(codes.length > 0);
}

function rememberCodes(codes) {
  const newEntries = [];
  codes.forEach((entry, idx) => {
    if (!state.codes.has(entry.code)) {
      newEntries.push(entry);
    } else {
      const existing = state.codes.get(entry.code);
      if (existing && entry.first_seen < existing.first_seen) {
        state.codes.set(entry.code, entry);
      }
      return;
    }
    state.codes.set(entry.code, entry);
  });
  const sorted = Array.from(state.codes.values()).sort(
    (a, b) => b.first_seen - a.first_seen,
  );
  renderCodes(sorted);
  updateStats(sorted);
  return newEntries;
}

function updateStatus(text, isActive = false) {
  const textSpan = statusIndicator.querySelector("span:last-child");
  if (textSpan) {
    textSpan.textContent = text;
  } else {
    statusIndicator.textContent = text;
  }
  statusIndicator.classList.toggle("active", isActive);
}

function toggleEmptyState(hasCodes) {
  if (!emptyHint) return;
  emptyHint.style.display = hasCodes ? "none" : "flex";
}

function updateLastUpdate(epoch) {
  state.lastFetchedAt = epoch;
  const textSpan = lastUpdateSpan.querySelector("span");
  const target = textSpan || lastUpdateSpan;

  if (!epoch) {
    target.textContent = "Never";
    return;
  }
  target.textContent = formatTimestamp(epoch);
}

function updateStats(sorted) {
  if (!statTotal || !statLatest) return;
  statTotal.textContent = sorted.length.toString();
  if (sorted.length) {
    const latest = sorted[0];
    statLatest.textContent = latest.code;
    statLatest.setAttribute("title", `Seen ${formatTimestamp(latest.first_seen)}`);
  } else {
    statLatest.textContent = "Waiting…";
    statLatest.removeAttribute("title");
  }
}

function ensureAudioContext() {
  if (state.audioContext) return state.audioContext;
  try {
    state.audioContext = new AudioContext();
  } catch (err) {
    console.warn("Unable to initialize audio context", err);
  }
  return state.audioContext;
}

function playChime() {
  if (!soundToggle.checked) return;
  const ctx = ensureAudioContext();
  if (!ctx) return;
  const duration = 0.2;
  const oscillator = ctx.createOscillator();
  const gain = ctx.createGain();

  oscillator.type = "sine";
  oscillator.frequency.value = 880;
  gain.gain.setValueAtTime(0.0, ctx.currentTime);
  gain.gain.linearRampToValueAtTime(0.3, ctx.currentTime + 0.01);
  gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);

  oscillator.connect(gain);
  gain.connect(ctx.destination);
  oscillator.start();
  oscillator.stop(ctx.currentTime + duration);
}

async function fetchCodes() {
  updateStatus("Syncing…", true);
  try {
    const response = await fetch(CODES_ENDPOINT);
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`);
    }
    const data = await response.json();
    const newEntries = rememberCodes(data.codes || []);
    if (newEntries.length) {
      playChime();
    }
    updateLastUpdate(data.fetched_at || 0);
    updateStatus("Listening", true);
  } catch (error) {
    console.error("Fetching codes failed", error);
    updateStatus("Error", false);
  }
}

async function triggerManualScan() {
  updateStatus("Scanning…", true);
  setScanButtonsDisabled(true);
  try {
    const response = await fetch(MANUAL_SCAN_ENDPOINT, { method: "POST" });
    if (!response.ok) {
      throw new Error(`Scan failed: ${response.status}`);
    }
    const data = await response.json();
    const newEntries = rememberCodes(data.codes || []);
    if (newEntries.length) {
      playChime();
    }
    updateLastUpdate(data.fetched_at || 0);
    updateStatus("Listening", true);
  } catch (error) {
    console.error("Manual scan failed", error);
    updateStatus("Error", false);
  } finally {
    setScanButtonsDisabled(false);
  }
}

function setScanButtonsDisabled(disabled) {
  if (rescanButton) {
    rescanButton.disabled = disabled;
  }
  if (inlineScanButton) {
    inlineScanButton.disabled = disabled;
  }
}

async function shareCodes(event) {
  event.preventDefault();
  if (!shareCodesInput) return;
  const rawCodes = shareCodesInput.value
    .split(/[,\n\s]+/)
    .map((code) => code.trim().toUpperCase())
    .filter(Boolean);
  if (!rawCodes.length) {
    updateShareFeedback("Enter at least one code.", true);
    return;
  }
  const uniqueCodes = Array.from(new Set(rawCodes));
  const note = (shareNoteInput?.value || "").trim();

  // Add codes to the community dropbox
  appendSharedEntries(uniqueCodes, note);

  updateShareFeedback("Codes shared successfully!", false);
  shareCodesInput.value = "";
  if (shareNoteInput) shareNoteInput.value = "";
}

function updateShareFeedback(message, isError) {
  if (!shareFeedback) return;
  shareFeedback.textContent = message;
  shareFeedback.style.color = isError
    ? "rgba(239, 68, 68, 0.9)"
    : "rgba(34, 197, 94, 0.9)";
}

function appendSharedEntries(codes, note) {
  if (!sharedList) return;
  const timestamp = new Date();
  codes.forEach((code) => {
    const li = document.createElement("li");
    li.className = "shared-entry";
    li.innerHTML = `
      <strong>${code}</strong>
      <span>${timestamp.toLocaleTimeString()}</span>
      ${note ? `<span>${note}</span>` : ""}
    `;
    sharedList.prepend(li);
  });
  while (sharedList.children.length > 8) {
    sharedList.removeChild(sharedList.lastChild);
  }
}

function init() {
  fetchCodes();
  setInterval(fetchCodes, POLL_INTERVAL);
  if (rescanButton) {
    rescanButton.addEventListener("click", triggerManualScan);
  }
  if (inlineScanButton) {
    inlineScanButton.addEventListener("click", triggerManualScan);
  }
  if (shareForm) {
    shareForm.addEventListener("submit", shareCodes);
  }
  if (clearSharedButton) {
    clearSharedButton.addEventListener("click", clearSharedEntries);
  }
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) {
      fetchCodes();
    }
  });
}

toggleEmptyState(false);
updateStats([]);

window.addEventListener("DOMContentLoaded", init);
