let state = null;
let puzzleNames = {};
let selectedClueCell = null;
let pendingHint = null;
let autoTimer = null;
let feedbackTimer = null;

// Verdict modal target
let activeVerdictCell = null;

// Timer & pause state
let elapsedSeconds = 0;
let gameTimerInterval = null;
let isPaused = false;
let winShownForRun = false;

const $ = (id) => document.getElementById(id);

async function api(url, method = "GET", body = null) {
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Lỗi máy chủ");
  return data;
}

function showFeedback(text, type = "info", showApplyBtn = false, autoHideMs = 0) {
  if (feedbackTimer) {
    clearTimeout(feedbackTimer);
    feedbackTimer = null;
  }
  const banner = $("feedback-banner");
  banner.className = `feedback ${type}`;
  $("feedback-text").textContent = text;
  $("btn-apply-hint").classList.toggle("hidden", !showApplyBtn);
  if (autoHideMs > 0) {
    feedbackTimer = setTimeout(() => {
      hideFeedback();
    }, autoHideMs);
  }
}

function hideFeedback() {
  if (feedbackTimer) {
    clearTimeout(feedbackTimer);
    feedbackTimer = null;
  }
  $("feedback-banner").classList.add("hidden");
  $("btn-apply-hint").classList.add("hidden");
}

function stopAutoSolve() {
  if (autoTimer) {
    clearTimeout(autoTimer);
    autoTimer = null;
  }
  const btn = $("btn-auto");
  btn.textContent = "Auto Solve";
  btn.classList.remove("btn-danger");
  btn.classList.add("btn-plum");
}

// ------------------------------------------------------------------ Timer & Overlays
function formatTime(totalSeconds) {
  const mins = Math.floor(totalSeconds / 60);
  const secs = totalSeconds % 60;
  return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

function updateTimerDisplay() {
  const formatted = formatTime(elapsedSeconds);
  $("timer-display").textContent = formatted;
  $("pause-time-text").textContent = formatted;
}

function stopGameTimer() {
  if (gameTimerInterval) {
    clearInterval(gameTimerInterval);
    gameTimerInterval = null;
  }
}

function startGameTimer() {
  stopGameTimer();
  gameTimerInterval = setInterval(() => {
    if (!isPaused && state && !state.is_solved) {
      elapsedSeconds += 1;
      updateTimerDisplay();
    }
  }, 1000);
}

function resetGameTimer() {
  elapsedSeconds = 0;
  isPaused = false;
  winShownForRun = false;
  $("app-shell").classList.remove("blurred");
  $("pause-modal").classList.add("hidden");
  $("win-modal").classList.add("hidden");
  closeVerdictModal();
  updateTimerDisplay();
  startGameTimer();
}

function pauseGame() {
  if (!state || state.is_solved || isPaused) return;
  stopAutoSolve();
  closeVerdictModal();
  isPaused = true;
  updateTimerDisplay();
  $("app-shell").classList.add("blurred");
  $("pause-modal").classList.remove("hidden");
}

function resumeGame() {
  if (!isPaused) return;
  isPaused = false;
  $("app-shell").classList.remove("blurred");
  $("pause-modal").classList.add("hidden");
}

function showWinModal() {
  if (winShownForRun) return;
  winShownForRun = true;
  stopGameTimer();
  stopAutoSolve();
  closeVerdictModal();
  $("win-level-text").textContent =
    puzzleNames[state.puzzle_id] || state.puzzle_id;
  $("win-time-value").textContent = formatTime(elapsedSeconds);
  $("win-modal").classList.remove("hidden");
}

function closeWinModal() {
  $("win-modal").classList.add("hidden");
}

function openVerdictModal(ch) {
  if (isPaused || !state || state.is_solved) return;
  activeVerdictCell = ch.cell;
  const avatarUrl = `https://api.dicebear.com/9.x/big-smile/svg?seed=${encodeURIComponent(ch.name)}&backgroundColor=transparent`;
  $("verdict-modal-cell").textContent = ch.cell;
  const avatarEl = $("verdict-modal-avatar");
  avatarEl.style.display = "";
  avatarEl.src = avatarUrl;
  avatarEl.alt = ch.name;
  avatarEl.onerror = () => {
    avatarEl.style.display = "none";
  };
  $("verdict-modal-title").textContent = ch.name;
  $("verdict-modal-job").textContent = ch.job;
  $("verdict-modal").classList.remove("hidden");
}

function closeVerdictModal() {
  activeVerdictCell = null;
  $("verdict-modal").classList.add("hidden");
}

// ------------------------------------------------------------------ Puzzles
async function loadPuzzleList() {
  const data = await api("/api/puzzles");
  const container = $("puzzle-list");
  container.innerHTML = "";

  const groups = {};
  for (const p of data.puzzles) {
    if (!groups[p.group]) groups[p.group] = [];
    groups[p.group].push(p);
  }

  for (const [groupName, items] of Object.entries(groups)) {
    const title = document.createElement("div");
    title.className = "puzzle-group-title";
    title.textContent = groupName;
    container.appendChild(title);

    for (const p of items) {
      puzzleNames[p.id] = p.name;
      const btn = document.createElement("button");
      btn.className = "puzzle-item";
      btn.dataset.id = p.id;
      const diffLabels = {
        easy: "Easy",
        medium: "Med",
        hard: "Hard",
        expert: "Expert",
      };
      const diff = p.difficulty || "medium";
      btn.innerHTML = `
        <span>${p.name}</span>
        <span class="diff-badge diff-${diff}">${diffLabels[diff] || diff}</span>
      `;
      btn.onclick = () => selectPuzzle(p.id);
      container.appendChild(btn);
    }
  }

  if (data.puzzles.length > 0) {
    await selectPuzzle(data.puzzles[0].id);
  }
}

async function selectPuzzle(puzzleId) {
  stopAutoSolve();
  selectedClueCell = null;
  pendingHint = null;
  hideFeedback();

  state = await api("/api/load", "POST", { puzzle_id: puzzleId });

  document.querySelectorAll(".puzzle-item").forEach((el) => {
    el.classList.toggle("active", el.dataset.id === puzzleId);
  });

  resetGameTimer();
  renderAll();
}

// ------------------------------------------------------------------ Actions
async function submitVerdict(cell, verdict) {
  stopAutoSolve();
  pendingHint = null;
  closeVerdictModal();

  const res = await api("/api/verdict", "POST", { cell, verdict });
  state = res.state;

  if (res.result === "ACCEPTED") {
    // Do NOT auto-highlight referenced clues; only highlight when user clicks a card.
    selectedClueCell = null;
    hideFeedback();
    renderAll();
    if (state.is_solved) {
      showWinModal();
    }
  } else if (res.result === "NOT_PROVABLE") {
    showFeedback(
      `NOT_PROVABLE — Chưa đủ dữ kiện công khai để chứng minh ${cell} là ${verdict}.`,
      "warn",
      false,
      3000,
    );
    shakeCard(cell);
  } else if (res.result === "CONTRADICTED") {
    showFeedback(
      `CONTRADICTED — Phán đoán ${cell} là ${verdict} mâu thuẫn với các manh mối hiện có!`,
      "error",
      false,
      3000,
    );
    shakeCard(cell);
  } else {
    showFeedback(`${res.result}: ${res.message}`, "warn", false, 3000);
  }
}

function shakeCard(cell) {
  const card = document.querySelector(`.card[data-cell="${cell}"]`);
  if (!card) return;
  card.classList.remove("shake");
  void card.offsetWidth;
  card.classList.add("shake");
}

async function requestHint() {
  stopAutoSolve();
  const hint = await api("/api/hint", "POST");
  if (!hint.available) {
    showFeedback(hint.message, "warn", false);
    return;
  }
  pendingHint = hint;
  selectedClueCell = null;
  showFeedback(
    `Gợi ý (${hint.cell}): ${hint.message}`,
    "info",
    Boolean(hint.verdict),
  );
  renderBoard();
}

async function runSingleStep() {
  const res = await api("/api/step", "POST");
  state = res.state;
  pendingHint = null;
  selectedClueCell = null;
  renderAll();

  if (res.outcome === "SOLVED") {
    showFeedback(
      `Auto Solve hoàn thành trong ${formatTime(elapsedSeconds)} — Đã giải xong màn chơi!`,
      "success",
      false,
    );
    showWinModal();
  } else if (res.outcome === "STUCK") {
    showFeedback(
      "Agent dừng lại: STUCK (không có ô nào suy luận bắt buộc được).",
      "warn",
      false,
    );
  } else if (res.outcome === "INCONSISTENT") {
    showFeedback(
      "Agent dừng lại: INCONSISTENT (cơ sở tri thức mâu thuẫn).",
      "error",
      false,
    );
  }
  return res.outcome;
}

async function toggleAutoSolve() {
  if (autoTimer) {
    stopAutoSolve();
    showFeedback("Đã tạm dừng Auto Solve.", "info", false);
    return;
  }

  const btn = $("btn-auto");
  btn.textContent = "Stop";
  btn.classList.remove("btn-plum");
  btn.classList.add("btn-danger");

  const tick = async () => {
    if (isPaused) {
      stopAutoSolve();
      return;
    }
    const outcome = await runSingleStep();
    if (outcome === "RUNNING") {
      autoTimer = setTimeout(tick, 450);
    } else {
      stopAutoSolve();
    }
  };
  tick();
}

// ------------------------------------------------------------------ Render
function renderAll() {
  if (!state) return;
  $("current-level-title").textContent =
    puzzleNames[state.puzzle_id] || state.puzzle_id;
  const revealedCount = state.characters.filter((c) => c.revealed).length;
  $("progress-badge").textContent =
    `${revealedCount} / ${state.characters.length}`;

  const disabled = state.is_solved;
  $("btn-restart").disabled = false;
  $("btn-pause").disabled = disabled;
  $("btn-hint").disabled = disabled;
  $("btn-step").disabled = disabled;
  $("btn-auto").disabled = disabled;

  renderBoard();
  renderClues();
  renderTrace();
}

function renderBoard() {
  const grid = $("board-grid");
  const size = state.size;
  const cardWidth = size >= 5 ? 138 : size === 4 ? 162 : 178;
  grid.style.gridTemplateColumns = `24px repeat(${size}, ${cardWidth}px)`;
  grid.innerHTML = "";

  let highlighted = new Set();
  if (selectedClueCell) {
    const owner = state.characters.find((c) => c.cell === selectedClueCell);
    if (owner && owner.referenced_cells) {
      highlighted = new Set(owner.referenced_cells);
    }
  }

  grid.appendChild(document.createElement("div"));
  for (let c = 0; c < size; c++) {
    const lbl = document.createElement("div");
    lbl.className = "coord-label";
    lbl.textContent = String.fromCharCode(65 + c);
    grid.appendChild(lbl);
  }

  const charMap = {};
  for (const ch of state.characters) {
    charMap[ch.cell] = ch;
  }

  for (let r = 0; r < size; r++) {
    const rowLbl = document.createElement("div");
    rowLbl.className = "coord-label";
    rowLbl.textContent = String(r + 1);
    grid.appendChild(rowLbl);

    for (let c = 0; c < size; c++) {
      const cellId = `${String.fromCharCode(65 + c)}${r + 1}`;
      const ch = charMap[cellId];
      const card = document.createElement("div");
      card.className = "card";
      card.style.width = `${cardWidth}px`;
      card.dataset.cell = cellId;

      if (ch.revealed) {
        card.classList.add(
          "revealed",
          ch.status === "CRIMINAL" ? "criminal" : "innocent",
        );
        card.onclick = () => {
          selectedClueCell = selectedClueCell === cellId ? null : cellId;
          renderBoard();
          renderClues();
        };
      } else {
        card.classList.add("unrevealed");
        card.onclick = () => openVerdictModal(ch);
      }

      if (selectedClueCell === cellId) card.classList.add("selected-clue");
      if (highlighted.has(cellId)) card.classList.add("highlighted");
      if (
        selectedClueCell &&
        selectedClueCell !== cellId &&
        !highlighted.has(cellId)
      ) {
        card.classList.add("dimmed");
      }
      if (pendingHint && pendingHint.cell === cellId) {
        card.classList.add("hinted");
      }

      const avatarUrl = `https://api.dicebear.com/9.x/big-smile/svg?seed=${encodeURIComponent(ch.name)}&backgroundColor=transparent`;
      const statusBadgeHtml = ch.revealed
        ? `<span class="status-pill">${ch.status}</span>`
        : "";

      card.innerHTML = `
        <div>
          <div class="card-top">
            <span class="card-cell">${ch.cell}</span>
            ${statusBadgeHtml}
          </div>
          <div class="card-profile">
            <img class="card-avatar" src="${avatarUrl}" alt="${ch.name}"
                 onerror="this.style.display='none'" />
            <div>
              <div class="card-name">${ch.name}</div>
              <div class="card-job">${ch.job}</div>
            </div>
          </div>
        </div>
      `;

      if (ch.revealed) {
        const clueDiv = document.createElement("div");
        clueDiv.className = "card-clue";
        clueDiv.textContent = ch.clue || "(Không có manh mối)";
        card.appendChild(clueDiv);
      }

      grid.appendChild(card);
    }
  }
}

function renderClues() {
  const list = $("clue-list");
  list.innerHTML = "";
  for (const cl of state.clues) {
    const item = document.createElement("div");
    item.className = `clue-item ${selectedClueCell === cl.cell ? "active" : ""}`;
    item.innerHTML = `
      <div class="clue-item-head">
        <span>${cl.cell} — ${cl.name}</span>
        <span class="clue-count-pill">${cl.referenced_cells.length} ô</span>
      </div>
      <div class="clue-item-text">${cl.text}</div>
    `;
    item.onclick = () => {
      selectedClueCell = selectedClueCell === cl.cell ? null : cl.cell;
      renderBoard();
      renderClues();
    };
    list.appendChild(item);
  }
}

function renderTrace() {
  const list = $("trace-list");
  list.innerHTML = "";
  if (!state.trace || state.trace.length === 0) {
    list.innerHTML = `<div class="panel-hint">Chưa có bước suy luận tự động nào.</div>`;
    return;
  }
  for (const s of state.trace) {
    const div = document.createElement("div");
    div.className = "trace-item";
    div.innerHTML = `
      <div><strong>Bước ${s.step}:</strong> ${s.cell} → ${s.verdict} (${s.result})</div>
      ${s.clue ? `<div style="margin-top:4px;color:#6c698d;">Clue: ${s.clue}</div>` : ""}
    `;
    list.appendChild(div);
  }
}

async function restartCurrentPuzzle() {
  stopAutoSolve();
  selectedClueCell = null;
  pendingHint = null;
  hideFeedback();
  state = await api("/api/restart", "POST");
  resetGameTimer();
  renderAll();
}

// ------------------------------------------------------------------ Wiring
$("btn-restart").onclick = restartCurrentPuzzle;
$("btn-pause").onclick = pauseGame;
$("btn-resume").onclick = resumeGame;

$("btn-hint").onclick = requestHint;
$("btn-step").onclick = () => {
  stopAutoSolve();
  runSingleStep();
};
$("btn-auto").onclick = toggleAutoSolve;

$("btn-apply-hint").onclick = () => {
  if (pendingHint && pendingHint.cell && pendingHint.verdict) {
    submitVerdict(pendingHint.cell, pendingHint.verdict);
  }
};

// Verdict modal controls
$("btn-modal-innocent").onclick = () => {
  if (activeVerdictCell) submitVerdict(activeVerdictCell, "INNOCENT");
};
$("btn-modal-criminal").onclick = () => {
  if (activeVerdictCell) submitVerdict(activeVerdictCell, "CRIMINAL");
};
$("btn-modal-cancel").onclick = closeVerdictModal;
$("verdict-modal").onclick = (e) => {
  if (e.target === $("verdict-modal")) closeVerdictModal();
};

// Win modal controls
$("btn-win-restart").onclick = restartCurrentPuzzle;
$("btn-win-close").onclick = closeWinModal;
$("win-modal").onclick = (e) => {
  if (e.target === $("win-modal")) closeWinModal();
};

document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  if (!$("verdict-modal").classList.contains("hidden")) {
    closeVerdictModal();
  } else if (!$("win-modal").classList.contains("hidden")) {
    closeWinModal();
  } else if (isPaused) {
    resumeGame();
  }
});

document.querySelectorAll(".tab").forEach((tab) => {
  tab.onclick = () => {
    document
      .querySelectorAll(".tab, .tab-content")
      .forEach((el) => el.classList.remove("active"));
    tab.classList.add("active");
    $(`tab-${tab.dataset.tab}`).classList.add("active");
  };
});

loadPuzzleList();
