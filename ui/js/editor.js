// Custom animation editor: paint per-key colours into keyframes, scrub a timeline,
// preview in-app (with real easing) or play on the keyboard, save/load to the library.
// Extras: undo/redo (Ctrl+Z / Ctrl+Shift+Z), multi-frame select for bulk hold/easing edits,
// drag-to-paint, and continuous autosave so unsaved work survives a crash/close.

App.Editor = {
  board: null,
  picker: null,
  paintColor: { r: 255, g: 0, b: 0 },
  selFrames: new Set([0]),     // selected frame indices (for bulk edits); always includes active
  undoStack: [],
  redoStack: [],
  _rt: null,                   // throttle for re-render during a paint stroke
  _save_t: null,               // debounce for autosave

  init() {
    this.board = new Board("keyboard-edit", "paint");
    this.board.render(App.state.layout);
    this.board.onPaint = (id) => this.paintKey(id);
    // One undo entry per stroke; the stroke erases if it began on a key already showing the
    // active colour (so a click toggles it off / fixes a misclick), otherwise it paints.
    this.board.onStrokeStart = (id) => { this.pushUndo(); this._beginStroke(id); };
    this.picker = new Picker(App.$("picker-edit"), (r, g, b) => { this.paintColor = { r, g, b }; });
    this.picker.setRGB(255, 0, 0);
    App.buildSwatches(App.$("swatches-edit"), (r, g, b) => { this.paintColor = { r, g, b }; this.picker.setRGB(r, g, b); });
    this._wire();
    this._wireShortcuts();
    this.restoreDraftOrReset();
  },

  model() { return App.state.editor; },
  activeFrame() { return this.model().frames[this.model().active]; },

  // ── draft / autosave ─────────────────────────────────────────
  async restoreDraftOrReset() {
    let d = null;
    try { d = await App.api().get_editor_draft(); } catch (_) {}
    if (d && Array.isArray(d.frames) && d.frames.length && d.frames.some((f) => f.colors && Object.keys(f.colors).length)) {
      App.state.editor = { name: d.name || "", loop: d.loop !== false, active: 0, frames: d.frames };
      App.$("anim-name").value = d.name || "";
      App.$("anim-loop").checked = d.loop !== false;
      this.selFrames = new Set([0]);
      this.renderFrames();
      this.loadActiveToBoard();
      App.status("restored your in-progress animation");
    } else {
      this.reset();
    }
  },

  _payload() {
    const m = this.model();
    return { name: (App.$("anim-name").value || "untitled").trim(), fps: 30, loop: m.loop, frames: m.frames };
  },

  autosave() {
    clearTimeout(this._save_t);
    this._save_t = setTimeout(() => { try { App.api().save_editor_draft(this._payload()); } catch (_) {} }, 600);
  },

  reset() {
    App.state.editor = { name: "", loop: true, active: 0,
      frames: [{ duration_ms: 160, easing: "linear", colors: {} }] };
    App.$("anim-name").value = "";
    App.$("anim-loop").checked = true;
    this.selFrames = new Set([0]);
    this.renderFrames();
    this.loadActiveToBoard();
    this.autosave();
  },

  // ── undo / redo ──────────────────────────────────────────────
  snapshot() {
    const m = this.model();
    return JSON.stringify({ name: App.$("anim-name").value, loop: App.$("anim-loop").checked, active: m.active, frames: m.frames });
  },
  pushUndo() {
    this.undoStack.push(this.snapshot());
    if (this.undoStack.length > 80) this.undoStack.shift();
    this.redoStack = [];
  },
  _applySnap(s) {
    const d = JSON.parse(s);
    const frames = (d.frames && d.frames.length) ? d.frames : [{ duration_ms: 160, easing: "linear", colors: {} }];
    App.state.editor = { name: d.name || "", loop: d.loop !== false, active: Math.min(d.active || 0, frames.length - 1), frames };
    App.$("anim-name").value = d.name || "";
    App.$("anim-loop").checked = d.loop !== false;
    this.selFrames = new Set([App.state.editor.active]);
    this.renderFrames();
    this.loadActiveToBoard();
    this.autosave();
  },
  undo() { if (!this.undoStack.length) return; this.redoStack.push(this.snapshot()); this._applySnap(this.undoStack.pop()); App.status("undo"); },
  redo() { if (!this.redoStack.length) return; this.undoStack.push(this.snapshot()); this._applySnap(this.redoStack.pop()); App.status("redo"); },

  _wireShortcuts() {
    document.addEventListener("keydown", (e) => {
      if (!App.$("view-editor").classList.contains("active")) return;
      const tag = (e.target.tagName || "").toLowerCase();
      if (tag === "input" || tag === "select" || tag === "textarea") return;
      const k = (e.key || "").toLowerCase();
      if ((e.ctrlKey || e.metaKey) && k === "z") { e.preventDefault(); e.shiftKey ? this.redo() : this.undo(); }
      else if ((e.ctrlKey || e.metaKey) && k === "y") { e.preventDefault(); this.redo(); }
    });
  },

  // ── painting ─────────────────────────────────────────────────
  _beginStroke(firstId) {
    const cur = this.activeFrame().colors[firstId], c = this.paintColor;
    // erase mode when the first key already holds the active colour (click-to-toggle-off)
    this._strokeErase = !!(cur && cur[0] === c.r && cur[1] === c.g && cur[2] === c.b);
  },
  paintKey(id) {
    if (this._strokeErase) {
      delete this.activeFrame().colors[id];
      this.board.paint(id, 0, 0, 0);
    } else {
      const c = this.paintColor;
      this.activeFrame().colors[id] = [c.r, c.g, c.b];
      this.board.paint(id, c.r, c.g, c.b);
    }
    this._scheduleRender();
  },
  _scheduleRender() {
    clearTimeout(this._rt);
    this._rt = setTimeout(() => { this.renderFrames(); this.autosave(); }, 110);
  },

  loadActiveToBoard() {
    const colors = this.activeFrame().colors;
    for (const k of App.state.layout) {
      const c = colors[k.id] || [0, 0, 0];
      this.board.paint(k.id, c[0], c[1], c[2]);
    }
    App.$("frame-dur").value = this.activeFrame().duration_ms;
    App.$("frame-ease").value = this.activeFrame().easing;
  },

  // ── frame selection ──────────────────────────────────────────
  setActive(i) {
    this.model().active = i;
    this.selFrames = new Set([i]);
    this.renderFrames();
    this.loadActiveToBoard();
  },
  frameClick(i, e) {
    const m = this.model();
    if (e.shiftKey) {
      const a = Math.min(m.active, i), b = Math.max(m.active, i);
      this.selFrames = new Set();
      for (let k = a; k <= b; k++) this.selFrames.add(k);
      m.active = i;
      this.renderFrames();
      this.loadActiveToBoard();
    } else if (e.ctrlKey || e.metaKey) {
      if (this.selFrames.has(i) && this.selFrames.size > 1) this.selFrames.delete(i);
      else this.selFrames.add(i);
      m.active = i;
      this.renderFrames();
      this.loadActiveToBoard();
    } else {
      this.setActive(i);
    }
  },
  _targetFrames() {
    const m = this.model();
    if (this.selFrames.size > 1) return [...this.selFrames].map((i) => m.frames[i]).filter(Boolean);
    return [this.activeFrame()];
  },

  renderFrames() {
    const wrap = App.$("frames");
    wrap.innerHTML = "";
    const m = this.model();
    m.frames.forEach((fr, i) => {
      const cell = document.createElement("div");
      cell.className = "frame-cell" + (i === m.active ? " active" : "") + (this.selFrames.has(i) ? " selected" : "");
      const mini = document.createElement("div");
      mini.className = "frame-mini";
      for (const k of App.state.layout) {
        const c = fr.colors[k.id];
        if (!c || Math.max(...c) <= 8) continue;
        const d = document.createElement("div");
        d.className = "frame-dot";
        d.style.left = (4 + k.x * 6) + "px";
        d.style.top = (6 + k.row * 9) + "px";
        d.style.width = (k.w * 6 - 1) + "px";
        d.style.height = "7px";
        d.style.background = App.toHex(c[0], c[1], c[2]);
        mini.appendChild(d);
      }
      cell.appendChild(mini);
      const cap = document.createElement("div");
      cap.className = "frame-cap";
      cap.innerHTML = `<span>#${i + 1}</span><span>${fr.duration_ms}ms</span>`;
      cell.appendChild(cap);
      cell.addEventListener("click", (e) => this.frameClick(i, e));
      wrap.appendChild(cell);
    });
  },

  _wire() {
    App.$("frame-add").addEventListener("click", () => {
      this.pushUndo();
      const m = this.model();
      m.frames.splice(m.active + 1, 0, { duration_ms: 160, easing: "linear", colors: {} });
      this.setActive(m.active + 1);
      this.autosave();
    });
    App.$("frame-dup").addEventListener("click", () => {
      this.pushUndo();
      const m = this.model(), src = this.activeFrame();
      m.frames.splice(m.active + 1, 0, { duration_ms: src.duration_ms, easing: src.easing, colors: { ...src.colors } });
      this.setActive(m.active + 1);
      this.autosave();
    });
    App.$("frame-del").addEventListener("click", () => {
      this.pushUndo();
      const m = this.model();
      if (m.frames.length <= 1) { this.activeFrame().colors = {}; this.setActive(0); this.autosave(); return; }
      m.frames.splice(m.active, 1);
      this.setActive(Math.max(0, m.active - 1));
      this.autosave();
    });
    // hold/easing apply to ALL selected frames (or the active one)
    App.$("frame-dur").addEventListener("change", (e) => {
      this.pushUndo();
      const v = Math.max(20, +e.target.value | 0);
      this._targetFrames().forEach((fr) => { fr.duration_ms = v; });
      this.renderFrames();
      this.autosave();
    });
    App.$("frame-ease").addEventListener("change", (e) => {
      this.pushUndo();
      this._targetFrames().forEach((fr) => { fr.easing = e.target.value; });
      this.autosave();
    });
    App.$("anim-loop").addEventListener("change", (e) => { this.pushUndo(); this.model().loop = e.target.checked; this.autosave(); });

    App.$("ed-preview").addEventListener("click", () => this._previewLocal());
    App.$("ed-play").addEventListener("click", () => this.playOnKeyboard());
    App.$("ed-stop").addEventListener("click", () => { this._stopLocal(); App.api().stop_animation(); });
    App.$("ed-save").addEventListener("click", () => this.save());
    App.$("ed-new").addEventListener("click", () => { this.pushUndo(); this.reset(); });
    App.$("ed-load").addEventListener("change", (e) => { if (e.target.value) this.load(e.target.value); });
  },

  // ── easing (matches engine/custom_anim.py so the preview is accurate) ──
  _ease(f, kind) {
    f = Math.max(0, Math.min(1, f));
    if (kind === "ease-in") return f * f;
    if (kind === "ease-out") return 1 - (1 - f) * (1 - f);
    if (kind === "ease-in-out") return 3 * f * f - 2 * f * f * f;
    return f;
  },
  _lerp(a, b, f) {
    return [Math.round(a[0] + (b[0] - a[0]) * f), Math.round(a[1] + (b[1] - a[1]) * f), Math.round(a[2] + (b[2] - a[2]) * f)];
  },

  // in-app preview: interpolate between frames with the real easing, no device writes
  _previewLocal() {
    this._stopLocal();
    const m = this.model(), frames = m.frames;
    if (frames.length < 2) { this.loadActiveToBoard(); return; }
    const durs = frames.map((f) => Math.max(20, f.duration_ms));
    const eas = frames.map((f) => f.easing || "linear");
    const total = durs.reduce((a, b) => a + b, 0);
    const loop = m.loop !== false;
    const colorOf = (fr, id) => (fr.colors && fr.colors[id]) ? fr.colors[id] : [0, 0, 0];
    const start = performance.now();
    const tick = () => {
      let pos = performance.now() - start;
      pos = loop ? (pos % total) : Math.min(pos, total - 0.001);
      let acc = 0, i = 0;
      for (i = 0; i < durs.length; i++) { if (pos < acc + durs[i] || i === durs.length - 1) break; acc += durs[i]; }
      const local = (pos - acc) / durs[i];
      const nxt = loop ? (i + 1) % frames.length : Math.min(i + 1, frames.length - 1);
      const hold = eas[i] === "hold" || nxt === i;
      for (const k of App.state.layout) {
        const c = hold ? colorOf(frames[i], k.id)
          : this._lerp(colorOf(frames[i], k.id), colorOf(frames[nxt], k.id), this._ease(local, eas[i]));
        this.board.paint(k.id, c[0], c[1], c[2]);
      }
      this._raf = requestAnimationFrame(tick);
    };
    this._raf = requestAnimationFrame(tick);
    App.status("previewing in editor (with easing)");
  },
  _stopLocal() { if (this._raf) cancelAnimationFrame(this._raf); this._raf = null; this.loadActiveToBoard(); },

  async playOnKeyboard() {
    this._stopLocal();
    await App.api().preview_custom_animation(this._payload());
    App.status("playing custom on keyboard");
  },

  async save() {
    const p = this._payload();
    const res = await App.api().save_custom_animation(p);
    if (res.ok) { App.refreshLibraries(res.list); App.status(`saved · ${res.name}`); }
  },

  async load(name) {
    const res = await App.api().get_custom_animation(name);
    if (!res.ok) { App.status("load failed"); return; }
    this.pushUndo();
    const a = res.animation;
    App.state.editor = { name: a.name || name, loop: a.loop !== false, active: 0,
      frames: (a.frames && a.frames.length) ? a.frames : [{ duration_ms: 160, easing: "linear", colors: {} }] };
    App.$("anim-name").value = a.name || name;
    App.$("anim-loop").checked = a.loop !== false;
    this.selFrames = new Set([0]);
    this.renderFrames();
    this.loadActiveToBoard();
    App.$("ed-load").value = "";
    this.autosave();
    App.status(`loaded · ${name}`);
  },
};
