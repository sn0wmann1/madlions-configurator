// Settings: white balance, channel order, device info, and the key-mapping wizard.

const NUM_SLOTS = 80;

App.Settings = {
  init() {
    // White-balance sliders live inside the calibrate-white wizard. Dragging floods the board
    // with calibrated white and updates live, so the user tunes by looking at the keyboard.
    ["r", "g", "b"].forEach((ch) => {
      const el = App.$("cal-" + ch);
      el.addEventListener("input", () => {
        const v = +el.value;
        App.$("cal-" + ch + "v").textContent = v.toFixed(2);
        const arg = { r: undefined, g: undefined, b: undefined };
        arg[ch] = v;
        App.api().white_preview(arg.r, arg.g, arg.b);
      });
    });
    App.$("wb-start").addEventListener("click", async () => {
      App.$("wb-overlay").hidden = false;
      await App.api().white_preview();
      App.status("white balance — watch the keyboard, tune until it looks neutral white");
    });
    App.$("wb-reset").addEventListener("click", async () => {
      ["r", "g", "b"].forEach((ch) => { App.$("cal-" + ch).value = 1; App.$("cal-" + ch + "v").textContent = "1.00"; });
      await App.api().white_preview(1, 1, 1);
    });
    App.$("wb-done").addEventListener("click", async () => {
      App.$("wb-overlay").hidden = true;
      await App.api().white_done();
      App.status("white balance saved");
    });
    App.qsa(".order .mini").forEach((b) => {
      b.addEventListener("click", () => {
        const order = b.dataset.order.split(",").map(Number);
        App.api().set_calibration(undefined, undefined, undefined, order);
        App.qsa(".order .mini").forEach((x) => x.classList.remove("active"));
        b.classList.add("active");
        App.status("channel order · " + b.textContent);
      });
    });

    App.$("map-keys").addEventListener("click", () => this.start());
    App.$("wiz-skip").addEventListener("click", () => this.advance(1));
    App.$("wiz-back").addEventListener("click", () => this.advance(-1));
    App.$("wiz-finish").addEventListener("click", () => this.finish());
    App.$("wiz-cancel").addEventListener("click", () => this.cancel());
  },

  applyState(st) {
    if (st.calibration) {
      const c = st.calibration;
      [["r", c.r], ["g", c.g], ["b", c.b]].forEach(([ch, v]) => {
        App.$("cal-" + ch).value = v; App.$("cal-" + ch + "v").textContent = (+v).toFixed(2);
      });
    }
    App.$("map-state").textContent = st.mapped ? "mapped · saved to disk" : "not mapped yet — run the wizard";
    if (st.status && st.status.info) {
      const i = st.status.info;
      App.$("device-info").textContent =
        `product   ${i.product}\nvendor    0x${(i.vid || 0).toString(16)}\nproduct id 0x${(i.pid || 0).toString(16)}\nusage     0x${(i.usage_page || 0).toString(16)}\nmode      ${st.status.mock ? "mock" : "live"}`;
    }
  },

  // ── mapping wizard ──────────────────────────────────────────
  async start() {
    App.go("settings");
    App.Lighting.board.clearSelection();
    App.Lighting.board.clearMarks("done");
    App.go("lighting");   // wizard maps on the Lighting board
    App.state.mapping = { slot: 0, map: {} };
    document.querySelector(".board-hero").classList.add("mapping");
    App.$("map-overlay").hidden = false;
    App.$("wiz-total").textContent = NUM_SLOTS - 1;
    App.$("wiz-keys").textContent = App.state.layout.length;
    await this.light();
  },

  async light() {
    const m = App.state.mapping;
    App.$("wiz-slot").textContent = m.slot;
    App.$("wiz-mapped").textContent = Object.keys(m.map).length;
    await App.api().identify_slot(m.slot);
  },

  mapAssign(keyId) {
    const m = App.state.mapping;
    for (const k of Object.keys(m.map)) if (m.map[k] === m.slot) delete m.map[k];
    m.map[keyId] = m.slot;
    App.Lighting.board.mark(keyId, "done");
    this.advance(1);
  },

  async advance(dir) {
    const m = App.state.mapping;
    m.slot = Math.max(0, Math.min(NUM_SLOTS - 1, m.slot + dir));
    await this.light();
    if (Object.keys(m.map).length >= App.state.layout.length)
      App.$("wiz-hint").textContent = "all keys mapped — click finish & save";
  },

  async finish() {
    const res = await App.api().save_key_map(App.state.mapping.map);
    this._close();
    App.status(`key map saved · ${res.count} keys`);
    App.hydrate(await App.api().get_state());
  },

  async cancel() {
    await App.api().cancel_identify();
    this._close();
    App.status("mapping cancelled");
  },

  _close() {
    App.state.mapping = null;
    App.$("map-overlay").hidden = true;
    document.querySelector(".board-hero").classList.remove("mapping");
    App.Lighting.board.clearMarks("done");
    App.refreshBoardFromState();
  },
};
