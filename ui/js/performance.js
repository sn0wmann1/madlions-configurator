// Performance section: per-key Hall Effect actuation + rapid trigger.
// Select keys on the grid, set values, apply to selection or all. Writes live to the board.

App.Performance = {
  board: null,

  init() {
    this.board = new Board("keyboard-perf", "select");
    this.board.render(App.state.layout);
    this.board.onSelect = () => this.updateHint();

    App.$("perf-select-all").addEventListener("click", () => { this.board.selectAll(); this.updateHint(); });
    App.$("perf-clear").addEventListener("click", () => { this.board.clearSelection(); this.updateHint(); });

    // live value readouts on the sliders
    ["act-mm", "rt-rapid", "rt-reset"].forEach((id) => {
      const el = App.$(id), out = App.$(id + "v");
      const upd = () => { out.textContent = (+el.value).toFixed(2); };
      el.addEventListener("input", upd); upd();
    });

    App.$("act-apply-sel").addEventListener("click", () => this.applyActuation(false));
    App.$("act-apply-all").addEventListener("click", () => this.applyActuation(true));
    App.$("rt-apply-sel").addEventListener("click", () => this.applyRT(false));
    App.$("rt-apply-all").addEventListener("click", () => this.applyRT(true));

    // Pull the live on-board state first, then build the controls from it.
    this.syncThenInit();
    this.updateHint();
  },

  async syncThenInit() {
    try {
      const s = await App.api().sync_from_device();
      if (s && s.read) {
        const got = Object.entries(s.read).filter(([, v]) => v).map(([k]) => k);
        if (got.length) App.status("read from keyboard: " + got.join(", "));
      }
    } catch (_) {}
    this.initSocd();
    this.initToggles();
  },

  selIds() { return [...this.board.selected]; },

  async applyActuation(all) {
    const mm = +App.$("act-mm").value;
    let res, label;
    if (all) { res = await App.api().set_actuation_all(mm); label = "all keys"; }
    else {
      const ids = this.selIds();
      if (!ids.length) { App.status("select keys first (or use apply to all)"); return; }
      res = await App.api().set_actuation_keys(ids, mm); label = ids.length + " keys";
    }
    App.status(res && res.ok === false ? "write failed — is FGG holding the keyboard?"
      : `actuation ${mm.toFixed(2)} mm -> ${label}`);
  },

  async applyRT(all) {
    const enable = App.$("rt-enable").checked;
    const rapid = +App.$("rt-rapid").value, reset = +App.$("rt-reset").value;
    let res, label;
    if (all) { res = await App.api().set_rapid_trigger_all(enable, reset, rapid); label = "all keys"; }
    else {
      const ids = this.selIds();
      if (!ids.length) { App.status("select keys first (or use apply to all)"); return; }
      res = await App.api().set_rapid_trigger_keys(ids, enable, reset, rapid); label = ids.length + " keys";
    }
    App.status(res && res.ok === false ? "write failed — is FGG holding the keyboard?"
      : `rapid trigger ${enable ? "on" : "off"}, trigger ${rapid.toFixed(2)} / reset ${reset.toFixed(2)} -> ${label}`);
  },

  updateHint() {
    const n = this.board.selected.size;
    App.$("perf-hint").textContent = n
      ? `${n} key${n === 1 ? "" : "s"} selected — apply below`
      : "select keys, then apply (or use apply to all)";
  },

  // ── Snap tap (SOCD) ─────────────────────────────────────────────
  socd: [],

  keyName(id) { return this._names ? this._names[id] : String(id); },

  buildKeyNames() {
    // Disambiguate duplicate labels (Shift/Ctrl/Alt/Win appear twice) by left/right.
    const byLabel = {};
    App.state.layout.forEach((k) => { (byLabel[k.label] = byLabel[k.label] || []).push(k); });
    const names = {};
    Object.values(byLabel).forEach((arr) => {
      if (arr.length === 1) { names[arr[0].id] = arr[0].label; return; }
      arr.sort((a, b) => a.x - b.x);
      arr.forEach((k, i) => { names[k.id] = `${k.label} (${i === 0 ? "L" : "R"})`; });
    });
    this._names = names;
  },

  async initSocd() {
    this.buildKeyNames();
    const opts = App.state.layout
      .map((k) => `<option value="${k.id}">${this.keyName(k.id)}</option>`).join("");
    const k1 = App.$("socd-k1"), k2 = App.$("socd-k2");
    k1.innerHTML = opts; k2.innerHTML = opts;
    k1.value = "29"; k2.value = "31";   // sensible default: A + D
    App.$("socd-add").addEventListener("click", () => this.addSocd());
    App.$("socd-list").addEventListener("click", (e) => {
      const btn = e.target.closest("[data-del]");
      if (btn) this.removeSocd(+btn.dataset.del);
    });
    try {
      const cur = await App.api().get_socd();
      this.socd = Array.isArray(cur) ? cur : [];
    } catch (_) { this.socd = []; }
    this.renderSocd();
  },

  renderSocd() {
    const el = App.$("socd-list");
    if (!this.socd.length) { el.innerHTML = `<p class="note socd-empty">No pairs yet.</p>`; return; }
    const modeLbl = { last: "last input", key1: "always 1st", key2: "always 2nd", neutral: "neutral" };
    el.innerHTML = this.socd.map((b, i) => `
      <div class="socd-row">
        <span class="socd-keys">${this.keyName(b.key1)} <span class="socd-amp">+</span> ${this.keyName(b.key2)}</span>
        <span class="socd-mode">${modeLbl[b.mode] || b.mode}</span>
        <button class="icon-btn" data-del="${i}" title="remove">remove</button>
      </div>`).join("");
  },

  async addSocd() {
    const k1 = +App.$("socd-k1").value, k2 = +App.$("socd-k2").value;
    const mode = App.$("socd-mode").value;
    if (k1 === k2) { App.status("pick two different keys"); return; }
    if (this.socd.some((b) => (b.key1 === k1 && b.key2 === k2) || (b.key1 === k2 && b.key2 === k1))) {
      App.status("that pair is already bound"); return;
    }
    const next = this.socd.concat([{ key1: k1, key2: k2, mode, travel_mm: 0.5, quick_trigger: true }]);
    const res = await App.api().set_socd(next);
    if (res && res.ok) { this.socd = res.socd; this.renderSocd(); App.status(`SOCD: ${this.keyName(k1)} + ${this.keyName(k2)} added`); }
    else App.status("write failed — is FGG holding the keyboard?");
  },

  async removeSocd(idx) {
    const res = await App.api().clear_socd(idx);
    if (res && res.ok) { this.socd = res.socd; this.renderSocd(); App.status("SOCD pair removed"); }
    else App.status("write failed — is FGG holding the keyboard?");
  },

  // ── Global performance toggles ──────────────────────────────────
  _toggleMap: {
    "perf-swap": "swap_wasd", "perf-winlock": "win_lock", "perf-mac": "mac",
    "perf-sixkey": "six_key", "perf-falsetouch": "false_touch",
  },

  async initToggles() {
    try {
      const p = await App.api().get_perf();
      Object.entries(this._toggleMap).forEach(([id, key]) => {
        const el = App.$(id); if (el && p && key in p) el.checked = !!p[key];
      });
    } catch (_) {}
    Object.keys(this._toggleMap).forEach((id) => {
      App.$(id).addEventListener("change", () => this.applyToggles());
    });
  },

  async applyToggles() {
    const opts = {};
    Object.entries(this._toggleMap).forEach(([id, key]) => { opts[key] = App.$(id).checked; });
    const res = await App.api().set_perf(opts);
    App.status(res && res.ok === false ? "write failed — is FGG holding the keyboard?" : "performance toggles applied");
  },
};
