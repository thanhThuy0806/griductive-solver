let state = null;
let puzzleNames = {};
let selectedClueCell = null;
let pendingHint = null;
let autoTimer = null;

const $ = (id) => document.getElementById(id);

async function api(url, method = "GET", body = null) {
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Lỗi máy chủ");
  return data;
}

function showFeedback(text, type = "info", showApplyBtn = false) {
  const banner = $("feedback-banner");
  banner.className = `feedback ${type}`;
  $("feedback-text").textContent = text;
  $("btn-apply-hint").classList.toggle("hidden", !showApplyBtn);
}

function hideFeedback() {
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

  renderAll();
}

// ------------------------------------------------------------------ Actions
async function submitVerdict(cell, verdict) {
  stopAutoSolve();
  pendingHint = null;

  const res = await api("/api/verdict", "POST", { cell, verdict });
  state = res.state;

  if (res.result === "ACCEPTED") {
    selectedClueCell = cell;
    if (state.is_solved) {
      showFeedback(
        "Hoàn thành! Tất cả nhân vật đã được suy luận chính xác.",
        "success",
        false,
      );
    } else {
      showFeedback(`Chính xác! ${cell} là ${verdict}.`, "success", false);
    }
    renderAll();
  } else if (res.result === "NOT_PROVABLE") {
    showFeedback(
      `NOT_PROVABLE — Chưa đủ dữ kiện công khai để chứng minh ${cell} là ${verdict}.`,
      "warn",
      false,
    );
    shakeCard(cell);
  } else if (res.result === "CONTRADICTED") {
    showFeedback(
      `CONTRADICTED — Phán đoán ${cell} là ${verdict} mâu thuẫn với các manh mối hiện có!`,
      "error",
      false,
    );
    shakeCard(cell);
  } else {
    showFeedback(`${res.result}: ${res.message}`, "warn", false);
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
  renderAll();

  if (res.outcome === "SOLVED") {
    showFeedback(
      "Auto Solve hoàn thành — Đã giải xong màn chơi!",
      "success",
      false,
    );
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

      const statusText = ch.revealed ? ch.status : "UNKNOWN";
      const avatarUrl = `https://api.dicebear.com/9.x/big-smile/svg?seed=${encodeURIComponent(ch.name)}&backgroundColor=transparent`;

      card.innerHTML = `
        <div>
          <div class="card-top">
            <span class="card-cell">${ch.cell}</span>
            <span class="status-pill">${statusText}</span>
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
      } else {
        const actions = document.createElement("div");
        actions.className = "card-actions";

        const btnInn = document.createElement("button");
        btnInn.className = "act-btn act-innocent";
        btnInn.textContent = "Innocent";
        btnInn.onclick = (e) => {
          e.stopPropagation();
          submitVerdict(cellId, "INNOCENT");
        };

        const btnCrim = document.createElement("button");
        btnCrim.className = "act-btn act-criminal";
        btnCrim.textContent = "Criminal";
        btnCrim.onclick = (e) => {
          e.stopPropagation();
          submitVerdict(cellId, "CRIMINAL");
        };

        actions.appendChild(btnInn);
        actions.appendChild(btnCrim);
        card.appendChild(actions);
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

// ------------------------------------------------------------------ Wiring
$("btn-restart").onclick = async () => {
  stopAutoSolve();
  selectedClueCell = null;
  pendingHint = null;
  hideFeedback();
  state = await api("/api/restart", "POST");
  renderAll();
};

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
