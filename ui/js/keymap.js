// KeyMap view: read/write keyboard key mappings with FN layer support
App.KeyMap = {
  board: null,
  selectedIdx: null,
  allCodes: {},
  currentLayer: 0,

  init() {
    this.board = new Board("keyboard-keymap", "keymap");
    this.board.render(App.state.layout);

    App.$("km-apply").addEventListener("click", () => this.applyRemap());
    App.$("km-reset-key").addEventListener("click", () => this.resetKey());
    App.$("km-reset-all").addEventListener("click", () => this.resetAll());
    App.$("km-read").addEventListener("click", () => this.refresh());
    App.$("km-layer").addEventListener("change", () => this.refresh());

    this.buildGrid();
  },

  buildGrid() {
    const rows = [
      // F-keys row
      ["Esc","F1","F2","F3","F4","F5","F6","F7","F8","F9","F10","F11","F12","PrtSc","ScrLk","Pause"],
      // Number row + extras
      ["`","1","2","3","4","5","6","7","8","9","0","-","=","Bksp","Ins","Home","PgUp","NumLock","Num/","Num*","Num-"],
      // QWERTY row
      ["Tab","Q","W","E","R","T","Y","U","I","O","P","[","]","\\","Del","End","PgDn","Num7","Num8","Num9","Num+"],
      // Home row
      ["Caps","A","S","D","F","G","H","J","K","L",";","'","Enter","Num4","Num5","Num6"],
      // Shift row
      ["LShift","Z","X","C","V","B","N","M",",",".","/","RShift","↑","Num1","Num2","Num3","NumEnter"],
      // Bottom row
      ["LCtrl","LWin","LAlt","Space","RAlt","RWin","Menu","RCtrl","←","↓","→","Num0","Num."],
      // Media keys
      ["VolUp","VolDown","Mute","Play","Stop","Prev","Next","Media","Mail","Calc","Search"],
    ];

    const codes = {
      A:0x04,B:0x05,C:0x06,D:0x07,E:0x08,F:0x09,G:0x0A,H:0x0B,I:0x0C,J:0x0D,K:0x0E,L:0x0F,M:0x10,
      N:0x11,O:0x12,P:0x13,Q:0x14,R:0x15,S:0x16,T:0x17,U:0x18,V:0x19,W:0x1A,X:0x1B,Y:0x1C,Z:0x1D,
      "1":0x1E,"2":0x1F,"3":0x20,"4":0x21,"5":0x22,"6":0x23,"7":0x24,"8":0x25,"9":0x26,"0":0x27,
      Enter:0x28,Esc:0x29,Bksp:0x2A,Tab:0x2B,Space:0x2C,"-":0x2D,"=":0x2E,"[":0x2F,"]":0x30,"\\":0x31,
      ";":0x33,"'":0x34,"`":0x35,",":0x36,".":0x37,"/":0x38,
      Caps:0x39,F1:0x3A,F2:0x3B,F3:0x3C,F4:0x3D,F5:0x3E,F6:0x3F,F7:0x40,F8:0x41,F9:0x42,
      F10:0x43,F11:0x44,F12:0x45,PrtSc:0x46,ScrLk:0x47,Pause:0x48,
      Ins:0x49,Home:0x4A,PgUp:0x4B,Del:0x4C,End:0x4D,PgDn:0x4E,"→":0x4F,"←":0x50,"↓":0x51,"↑":0x52,
      Menu:0x65,
      LCtrl:0xE0,LShift:0xE1,LAlt:0xE2,LWin:0xE3,RCtrl:0xE4,RShift:0xE5,RAlt:0xE6,RWin:0xE7,Fn:0x00,
      NumLock:0x53,"Num/":0x54,"Num*":0x55,"Num-":0x56,"Num+":0x57,"NumEnter":0x58,"Num1":0x59,"Num2":0x5A,"Num3":0x5B,"Num4":0x5C,"Num5":0x5D,"Num6":0x5E,"Num7":0x5F,"Num8":0x60,"Num9":0x61,"Num0":0x62,"Num.":0x63,
      Play:0xCD,Stop:0xB7,Prev:0xB6,Next:0xB5,VolUp:0xE9,VolDown:0xEA,Mute:0xE2,
      Media:0x83,Mail:0x8A,Calc:0x92,Search:0x65,
    };

    const grid = App.$("km-grid");
    grid.innerHTML = "";
    rows.forEach((row, ri) => {
      const div = document.createElement("div");
      div.className = "km-row";
      row.forEach(name => {
        const code = codes[name];
        if (code === undefined) return;
        const k = document.createElement("span");
        k.className = "km-key";
        if (ri === 6) k.classList.add("km-media");
        else if (["LCtrl","LShift","LAlt","LWin","RCtrl","RShift","RAlt","RWin"].includes(name)) k.classList.add("km-mod");
        else if (name === "Fn") k.classList.add("km-special");
        k.textContent = name;
        k.dataset.code = code;
        k.addEventListener("click", () => this.pickGrid(code, name));
        div.appendChild(k);
      });
      grid.appendChild(div);
    });
  },

  pickGrid(code, name) {
    if (this.selectedIdx === null) { App.status("click a keyboard key first"); return; }
    const layer = parseInt(App.$("km-layer").value) || 0;
    if (layer > 0) {
      App.api().set_fn_binding(layer, this.selectedIdx, code).then(() => this.refresh());
    } else {
      App.api().set_keymap({[this.selectedIdx]: code}).then(() => this.refresh());
    }
    App.status(`mapped key ${this.selectedIdx} → ${name}`);
  },

  async refresh() {
    this.currentLayer = parseInt(App.$("km-layer").value) || 0;
    if (this.currentLayer === 0) {
      this.allCodes = await App.api().get_keymap();
    } else {
      const layers = await App.api().get_fn_layers();
      this.allCodes = layers[["normal","fn1","fn2","fn3"][this.currentLayer]] || {};
    }
    this.renderBoard();
    const names = ["Normal","FN1","FN2","FN3"];
    App.status(`keymap loaded · ${names[this.currentLayer]}`);
  },

  renderBoard() {
    this.board.clearSelection();
    this.board.clearMarks("remapped");
    for (let idx = 0; idx < App.state.layout.length; idx++) {
      const code = this.allCodes[idx] || 0;
      if (code !== 0 && this.currentLayer > 0) {
        this.board.mark(idx, "remapped");
        this.board.paint(idx, 50, 28, 8);
      } else if (code !== 0 && this.currentLayer === 0) {
        this.board.paint(idx, 60, 30, 10);
      } else {
        this.board.paint(idx, 26, 26, 32);
      }
    }
  },

  selectIndex(idx) {
    this.selectedIdx = idx;
    const lbl = App.state.layout[idx]?.label || `idx ${idx}`;
    App.$("km-sel").textContent = `selected: ${lbl.replace(/<br>/,' ')}`;
  },

  async applyRemap() {
    // handled by pickGrid now
  },

  async resetKey() {
    if (this.selectedIdx === null) { App.status("click a key first"); return; }
    await App.api().reset_key(this.selectedIdx);
    await this.refresh();
    App.status("key reset");
  },

  async resetAll() {
    if (!confirm("Reset entire keymap to factory defaults?")) return;
    await App.api().reset_keymap_all();
    await this.refresh();
    App.status("all keys reset to factory defaults");
  },
};
