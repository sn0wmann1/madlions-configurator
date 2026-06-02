// Built-in effects gallery. Cards trigger play_animation; the active card is marked.
// Colour-based effects read the current colour the backend already holds (set from Lighting).

App.Effects = {
  names: [],          // built-in animation names
  customs: [],        // user-saved custom animation names

  // decorative gradient per card so the gallery has life without faking a live preview
  _grad(i, n) {
    const a = Math.round((i / Math.max(1, n)) * 360);
    return `linear-gradient(115deg, hsl(${a} 70% 22%), transparent 60%), ` +
           `radial-gradient(120% 80% at 90% 120%, hsl(${(a + 60) % 360} 65% 30% / .6), transparent)`;
  },

  build(names) {
    this.names = names || [];
    this.render();
  },

  // Custom animations live in the same gallery; built-ins play via play_animation,
  // customs via play_custom_animation. Refreshed whenever the library changes.
  setCustoms(customs) {
    this.customs = customs || [];
    this.render();
  },

  _card(name, i, n, isCustom) {
    const card = document.createElement("div");
    card.className = "fx-card" + (isCustom ? " fx-custom" : "");
    card.dataset.name = name;
    if (isCustom) card.dataset.custom = "1";
    card.innerHTML = `<div class="fx-bgline" style="background:${this._grad(i, n)}"></div>` +
                     (isCustom ? `<span class="fx-tag">custom</span>` : "") +
                     `<span class="fx-name">${name}</span>` +
                     (isCustom ? `<button class="fx-del" title="delete" data-del="${name}">remove</button>` : "");
    card.addEventListener("click", (e) => {
      if (e.target.closest("[data-del]")) { this.remove(name); return; }
      this.play(name, isCustom);
    });
    return card;
  },

  render() {
    const grid = App.$("fx-grid");
    grid.innerHTML = "";
    const total = this.names.length + this.customs.length;
    this.customs.forEach((name, i) => grid.appendChild(this._card(name, i, total, true)));
    this.names.forEach((name, i) => grid.appendChild(this._card(name, this.customs.length + i, total, false)));
    App.setActiveAnim(App.state.activeAnim);
  },

  async play(name, isCustom) {
    if (isCustom) await App.api().play_custom_animation(name);
    else await App.api().play_animation(name);
    App.setActiveAnim(name);
    App.status(`playing · ${name}`);
  },

  async remove(name) {
    const res = await App.api().delete_custom_animation(name);
    if (res && res.list) { App.refreshLibraries(res.list); App.status(`removed · ${name}`); }
  },

  async stop() {
    await App.api().stop_animation();
    App.setActiveAnim(null);
    App.refreshBoardFromState();
    App.status("stopped");
  },

  setSpeed(v) { App.api().set_speed(v); },
};

// Reflect the currently-playing effect across gallery + editor without redundant calls.
// The runtime reports customs as "custom:<name>"; match cards on the bare name.
App.setActiveAnim = function (name) {
  App.state.activeAnim = name;
  const bare = typeof name === "string" && name.startsWith("custom:") ? name.slice(7) : name;
  App.qsa(".fx-card").forEach((c) => c.classList.toggle("active", c.dataset.name === bare));
};
