// Keyboard renderer. A Board renders the layout into a container and exposes
// per-key painting + (in select mode) a selection set. The Editor uses paint mode.
// Pointer drag is supported: drag to paint many keys, or drag to select/deselect a run.
// While the mapping wizard is active, any board click routes to the wizard instead.

const UNIT = 42, ROW_H = 46, PAD = 20;

class Board {
  constructor(containerId, mode) {
    this.el = App.$(containerId);
    this.mode = mode;              // "select" | "paint"
    this.keyEls = {};
    this.selected = new Set();     // this board's own selection (select mode)
    this.onPaint = null;           // paint mode: (keyId) => void
    this.onSelect = null;          // select mode: (keyId, isSelected) => void
    this.onStrokeStart = null;     // paint mode: called once when a drag/click begins
    this._stroke = false;          // a pointer drag is in progress
    this._selValue = true;         // during a select-drag: are we selecting or deselecting
    // End any drag when the pointer is released anywhere.
    document.addEventListener("pointerup", () => { this._stroke = false; });
  }

  render(layout) {
    this.el.innerHTML = "";
    this.keyEls = {};
    let maxX = 0, maxRow = 0;
    for (const k of layout) {
      const el = document.createElement("div");
      el.className = "key";
      el.dataset.id = k.id;
      el.style.left = (PAD + k.x * UNIT) + "px";
      el.style.top = (PAD + k.row * ROW_H) + "px";
      el.style.width = (k.w * UNIT - 4) + "px";
      el.style.height = (ROW_H - 5) + "px";
      el.innerHTML = `<span class="klbl">${k.label}</span>`;
      el.addEventListener("pointerdown", (e) => { e.preventDefault(); this._begin(k.id); });
      el.addEventListener("pointerenter", () => { if (this._stroke) this._continue(k.id); });
      this.el.appendChild(el);
      this.keyEls[k.id] = el;
      maxX = Math.max(maxX, k.x + k.w);
      maxRow = Math.max(maxRow, k.row);
    }
    this.el.style.width = (PAD * 2 + maxX * UNIT) + "px";
    this.el.style.height = (PAD * 2 + (maxRow + 1) * ROW_H - 5) + "px";
  }

  _begin(id) {
    if (App.state.mapping) { App.Settings.mapAssign(id); return; }   // wizard: single assign, no drag
    if (this.mode === "keymap") { App.KeyMap.selectIndex(id); return; }  // keymap: click-only, no drag
    if (this.mode === "paint") {
      this._stroke = true;
      if (this.onStrokeStart) this.onStrokeStart(id);   // owner decides paint-vs-erase for the stroke
      if (this.onPaint) this.onPaint(id);
      return;
    }
    // select mode: the drag selects if the first key was unselected, else deselects
    this._stroke = true;
    this._selValue = !this.selected.has(id);
    this._applySelect(id, this._selValue);
  }

  _continue(id) {
    if (App.state.mapping) return;
    if (this.mode === "paint") { if (this.onPaint) this.onPaint(id); return; }
    this._applySelect(id, this._selValue);
  }

  _applySelect(id, want) {
    const el = this.keyEls[id];
    const has = this.selected.has(id);
    if (want === has) return;                 // no change
    if (want) { this.selected.add(id); el.classList.add("sel"); }
    else { this.selected.delete(id); el.classList.remove("sel"); }
    if (this.onSelect) this.onSelect(id, want);
  }

  selectAll() { Object.keys(this.keyEls).forEach((id) => { this.selected.add(+id); this.keyEls[id].classList.add("sel"); }); }
  clearSelection() { this.selected.clear(); this.clearMarks("sel"); }

  paint(id, r, g, b) {
    const el = this.keyEls[id];
    if (!el) return;
    el.style.setProperty("--kc", App.toHex(r, g, b));
    if (Math.max(r, g, b) > 24) {
      el.classList.add("lit");
      el.style.setProperty("--kt", App.lum(r, g, b) < 140 ? "#fff" : "#111");
      el.style.setProperty("--kglow", `rgba(${r},${g},${b},0.65)`);
    } else {
      el.classList.remove("lit");
    }
  }

  clearMarks(cls) { Object.values(this.keyEls).forEach((e) => e.classList.remove(cls)); }
  mark(id, cls) { const e = this.keyEls[id]; if (e) e.classList.add(cls); }
}
window.Board = Board;
