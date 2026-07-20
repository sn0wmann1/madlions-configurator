// Boot, navigation, the Lighting section, and shared state-hydration helpers.

const SWATCHES = ["#ff2d2d", "#ff7a18", "#ffd23f", "#3cf06b", "#19e0d6", "#2f7bff",
                  "#7a3cff", "#ff3cc7", "#ff1f6b", "#ffffff", "#5a5a5a", "#000000"];

const VIEW_META = {
  lighting:   ["Lighting", "Per-key colour across the board"],
  animations: ["Effects", "Built-in lighting animations"],
  editor:     ["Editor", "Paint your own keyframe animations"],
  performance:["Performance", "Hall Effect actuation & rapid trigger"],
  keymap:     ["KeyMap", "Read and remap key bindings"],
  profiles:   ["Profiles", "Snapshot and restore complete looks"],
  settings:   ["Settings", "Calibration, key mapping and device"],
};

// ── navigation ───────────────────────────────────────────────
App.go = function (view) {
  App.qsa(".nav-item").forEach((n) => n.classList.toggle("active", n.dataset.view === view));
  App.qsa(".view").forEach((v) => v.classList.toggle("active", v.id === "view-" + view));
  const m = VIEW_META[view] || [view, ""];
  App.$("view-title").textContent = m[0];
  App.$("view-sub").textContent = m[1];
  if (view === "editor" && App.Editor.board) App.Editor.loadActiveToBoard();
};

// ── shared helpers ───────────────────────────────────────────
App.buildSwatches = function (container, onPick) {
  container.innerHTML = "";
  SWATCHES.forEach((hex) => {
    const sw = document.createElement("div");
    sw.className = "swatch";
    sw.style.background = hex;
    sw.style.color = hex;
    sw.addEventListener("click", () => { const c = App.fromHex(hex); onPick(c.r, c.g, c.b); });
    container.appendChild(sw);
  });
};

App.renderDevice = function (status) {
  const dot = App.$("conn-dot"), state = App.$("device-state"), meta = App.$("device-meta");
  dot.className = "conn"; state.className = "device-state";
  if (!status || !status.connected) { dot.classList.add("off"); state.classList.add("off"); state.textContent = "offline"; meta.textContent = "no device"; }
  else if (status.mock) { dot.classList.add("mock"); state.classList.add("mock"); state.textContent = "mock"; meta.textContent = "no keyboard — simulated"; }
  else { dot.classList.add("ok"); state.classList.add("ok"); state.textContent = "live"; meta.textContent = (status.info && status.info.product) || "MADLIONS 60"; }
};

App.refreshLibraries = function (customs) {
  if (customs) App.state.customs = customs;
  const sel = App.$("ed-load");
  sel.innerHTML = `<option value="">load…</option>` +
    App.state.customs.map((n) => `<option value="${n}">${n}</option>`).join("");
  if (App.Effects && App.Effects.setCustoms) App.Effects.setCustoms(App.state.customs);
};

App.refreshBoardFromState = function () {
  const kc = App.state.keyColors || {};
  for (const k of App.state.layout) {
    const c = kc[k.id] || [0, 0, 0];
    App.Lighting.board.paint(k.id, c[0], c[1], c[2]);
  }
};

App.hydrate = function (st) {
  if (!st) return;
  App.state.keyColors = st.key_colors || App.state.keyColors || {};
  App.refreshBoardFromState();
  if (st.current_color) { App.state.color = { r: st.current_color[0], g: st.current_color[1], b: st.current_color[2] }; App.Lighting.picker.setRGB(...st.current_color); }
  if (typeof st.brightness === "number") { App.$("brightness").value = st.brightness; App.$("brightnessv").textContent = st.brightness.toFixed(2); }
  if (typeof st.speed === "number") { App.$("speed").value = st.speed; App.$("speedv").textContent = st.speed.toFixed(1); }
  App.state.mapped = !!st.mapped;
  App.$("mapwarn").textContent = st.mapped ? "" : "keys not mapped — Settings > mapping wizard";
  App.setActiveAnim(st.animation || null);
  App.refreshLibraries(st.custom_animations || []);
  App.Profiles.render(st.profiles || []);
  App.renderDevice(st.status);
  App.Settings.applyState(st);
};

// ── Lighting section ─────────────────────────────────────────
App.Lighting = {
  board: null,
  picker: null,

  init() {
    this.board = new Board("keyboard", "select");
    this.board.render(App.state.layout);
    this.board.onSelect = (id, isSel) => { if (isSel) this.applySelected(); this.updateHint(); };
    this.picker = new Picker(App.$("picker"), (r, g, b) => this.onColor(r, g, b));
    this.picker.setRGB(255, 0, 0);
    App.buildSwatches(App.$("swatches"), (r, g, b) => { this.picker.setRGB(r, g, b); this.onColor(r, g, b); this.applyDefault(); });

    App.$("apply-sel").addEventListener("click", () => this.applySelected());
    App.$("apply-all").addEventListener("click", () => this.applyAll());
    App.$("select-all").addEventListener("click", () => { this.board.selectAll(); this.updateHint(); });
    App.$("clear-sel").addEventListener("click", () => { this.board.clearSelection(); this.updateHint(); });
    App.$("brightness").addEventListener("input", (e) => {
      const v = +e.target.value; App.$("brightnessv").textContent = v.toFixed(2); App.api().set_brightness(v);
    });
  },

  onColor(r, g, b) {
    App.state.color = { r, g, b };
    App.api().set_current_color([r, g, b]);
    if (this.board.selected.size) this.applySelected();
  },

  applyDefault() { this.board.selected.size ? this.applySelected() : this.applyAll(); },

  async applySelected() {
    const sel = this.board.selected;
    if (!sel.size) { App.status("no keys selected — click keys first"); return; }
    const c = App.state.color, updates = {};
    App.state.keyColors = App.state.keyColors || {};
    for (const id of sel) { updates[id] = [c.r, c.g, c.b]; App.state.keyColors[id] = [c.r, c.g, c.b]; this.board.paint(id, c.r, c.g, c.b); }
    const res = await App.api().set_key_colors(updates);
    App.setActiveAnim(null);
    this.report(res, `applied ${App.toHex(c.r, c.g, c.b)} · ${sel.size} keys`);
  },

  async applyAll() {
    const c = App.state.color;
    App.state.keyColors = {};
    App.state.layout.forEach((k) => { App.state.keyColors[k.id] = [c.r, c.g, c.b]; this.board.paint(k.id, c.r, c.g, c.b); });
    const res = await App.api().set_all([c.r, c.g, c.b]);
    App.setActiveAnim(null);
    this.report(res, `applied ${App.toHex(c.r, c.g, c.b)} · all keys`);
  },

  report(res, ok) {
    if (res && res.status) App.renderDevice(res.status);
    App.status(res && res.ok === false ? "write failed — running in mock?" : ok);
  },

  updateHint() {
    const n = this.board.selected.size;
    App.$("selhint").textContent = n ? `${n} key${n === 1 ? "" : "s"} selected` : "click keys to select · or paint all";
  },
};

// ── boot ─────────────────────────────────────────────────────
async function boot() {
  App.state.layout = await App.api().get_layout();
  App.state.layout.forEach((k) => { App.state.keyById[k.id] = k; });

  App.Lighting.init();
  App.Editor.init();
  App.Performance.init();
  App.Profiles.init();
  App.KeyMap.init();
  App.Settings.init();
  App.Effects.build(await App.api().get_animations());

  App.qsa(".nav-item").forEach((n) => n.addEventListener("click", () => App.go(n.dataset.view)));
  App.$("reconnect").addEventListener("click", async () => App.renderDevice(await App.api().reconnect()));
  App.$("stop-anim").addEventListener("click", () => App.Effects.stop());
  App.$("speed").addEventListener("input", (e) => { const v = +e.target.value; App.$("speedv").textContent = v.toFixed(1); App.Effects.setSpeed(v); });

  // ── Idle timeout: fade RGB off after inactivity ──────────────────────
  let idleTimer = null, idleOff = false, idleSeconds = 30;
  App.$("idle-timeout").addEventListener("input", (e) => {
    idleSeconds = +e.target.value;
    App.$("idle-timeoutv").textContent = idleSeconds + "s";
    App.api().set_idle_timeout(idleSeconds);
  });
  function resetIdle() {
    clearTimeout(idleTimer);
    if (idleOff) { App.api().idle_fade_on(); idleOff = false; }
    if (idleSeconds > 0) idleTimer = setTimeout(() => { App.api().idle_fade_off(); idleOff = true; }, idleSeconds * 1000);
  }
  ["pointermove","pointerdown","keydown","wheel"].forEach(e => document.addEventListener(e, resetIdle, {passive:true}));
  resetIdle();

  App.hydrate(await App.api().get_state());
  App.status("ready");
}

window.addEventListener("pywebviewready", boot);
