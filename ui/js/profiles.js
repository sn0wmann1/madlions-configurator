// Profiles: snapshot the current lighting + calibration state, restore it later.

App.Profiles = {
  init() {
    App.$("profile-save").addEventListener("click", () => this.save());
  },

  async save() {
    const name = (App.$("profile-name").value || "").trim();
    if (!name) { App.status("name the profile first"); return; }
    const res = await App.api().save_profile(name);
    if (res.ok) { App.$("profile-name").value = ""; this.render(res.list); App.status(`profile saved · ${name}`); }
  },

  async load(name) {
    const res = await App.api().load_profile(name);
    if (res.ok) {
      App.hydrate(res.state);
      App.status(`profile loaded · ${name}`);
    }
  },

  async remove(name) {
    const res = await App.api().delete_profile(name);
    this.render(res.list);
    App.status(`profile deleted · ${name}`);
  },

  render(list) {
    App.state.profiles = list || [];
    const grid = App.$("profile-grid");
    grid.innerHTML = "";
    if (!App.state.profiles.length) {
      grid.innerHTML = `<div class="empty">no profiles yet — snapshot the current look above</div>`;
      return;
    }
    App.state.profiles.forEach((name) => {
      const card = document.createElement("div");
      card.className = "profile-card";
      card.innerHTML = `<h4>${name}</h4><div class="pc-actions">
        <button class="btn gold pc-load">load</button>
        <button class="btn danger pc-del">delete</button></div>`;
      card.querySelector(".pc-load").addEventListener("click", () => this.load(name));
      card.querySelector(".pc-del").addEventListener("click", () => this.remove(name));
      grid.appendChild(card);
    });
  },
};
