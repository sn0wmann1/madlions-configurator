// KeyMap view: read/write keyboard key mappings
App.KeyMap = {
  board: null,
  selectedIdx: null,
  allCodes: {},

  init() {
    this.board = new Board("keyboard-keymap", "select");
    this.board.render(App.state.layout);
    this.board.onSelect = (id, isSel) => {
      if (isSel) this.selectIndex(id);
    };

    App.$("km-apply").addEventListener("click", () => this.applyRemap());
    App.$("km-reset-key").addEventListener("click", () => this.resetKey());
    App.$("km-reset-all").addEventListener("click", () => this.resetAll());
    App.$("km-read").addEventListener("click", () => this.refresh());

    this.buildTargetSelect();
  },

  buildTargetSelect() {
    const sel = App.$("km-target");
    sel.innerHTML = '<option value="0">— select key —</option>';
    // Standard keys
    const keys = [
      "", "Esc","F1","F2","F3","F4","F5","F6","F7","F8","F9","F10","F11","F12",
      "PrtSc","ScrLk","Pause","","","","","","","","","","","","","","","",
      "`","1","2","3","4","5","6","7","8","9","0","-","=","Bksp",
      "Tab","Q","W","E","R","T","Y","U","I","O","P","[","]","\\",
      "Caps","A","S","D","F","G","H","J","K","L",";","'","Enter",
      "LShift","Z","X","C","V","B","N","M",",",".","/","RShift",
      "LCtrl","LWin","LAlt","Space","RAlt","Fn","RCtrl","←","↓","→",
      "Ins","Home","PgUp","Del","End","PgDn","↑","Menu",
    ];
    keys.forEach((name, code) => {
      if (name) {
        const opt = document.createElement("option");
        opt.value = code ? code.toString() : "0";
        opt.textContent = name;
        sel.appendChild(opt);
      }
    });
  },

  async refresh() {
    App.$("km-mapwarn").textContent = App.state.mapped ? "" : "keys not mapped — run Settings > mapping wizard first";
    if (!App.state.mapped) { App.status("run mapping wizard first"); return; }
    this.allCodes = await App.api().get_keymap();
    this.renderBoard();
    App.status("keymap loaded");
  },

  renderBoard() {
    this.board.clearSelection();
    this.board.clearMarks("remapped");
    for (let idx = 0; idx < App.state.layout.length; idx++) {
      const code = this.allCodes[idx] || 0;
      if (code !== 0) {
        this.board.mark(idx, "remapped");
      }
      // Paint key with color indicator
      if (code === 0) {
        this.board.paint(idx, 30, 30, 36);
      } else {
        this.board.paint(idx, 60, 30, 10);
      }
    }
  },

  selectIndex(idx) {
    this.selectedIdx = idx;
    App.$("km-apply").textContent = `apply remap to ${App.state.layout[idx]?.label || idx}`;
    const code = this.allCodes[idx] || 0;
    App.$("km-target").value = code.toString();
  },

  async applyRemap() {
    if (this.selectedIdx === null) { App.status("click a key first"); return; }
    const target = parseInt(App.$("km-target").value) || 0;
    const remaps = {};
    remaps[this.selectedIdx] = target;
    await App.api().set_keymap(remaps);
    await this.refresh();
    App.status(`key ${this.selectedIdx} remapped`);
  },

  async resetKey() {
    if (this.selectedIdx === null) { App.status("click a key first"); return; }
    await App.api().reset_key(this.selectedIdx);
    await this.refresh();
    App.status(`key ${this.selectedIdx} reset to default`);
  },

  async resetAll() {
    if (!confirm("Reset entire keymap to factory defaults?")) return;
    await App.api().reset_keymap_all();
    await this.refresh();
    App.status("all keys reset to default");
  },
};
