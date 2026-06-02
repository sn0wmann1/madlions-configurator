// HSV colour picker component (SV plane + hue strip + hex/RGB readout).
// Pure DOM/CSS, no canvas. Instantiated for the Lighting dock and the Editor dock.

class Picker {
  constructor(container, onChange) {
    this.onChange = onChange;
    this.h = 0; this.s = 1; this.v = 1;
    container.classList.add("picker");
    container.innerHTML = `
      <div class="sv-plane"><div class="sv-cursor"></div></div>
      <div class="hue"><div class="hue-cursor"></div></div>
      <div class="readout">
        <div class="swatch-lg"></div>
        <input class="hex-in" maxlength="7" value="#FF0000" />
      </div>
      <div class="rgb-mini"><span class="rm-r"></span><span class="rm-g"></span><span class="rm-b"></span></div>`;
    this.sv = container.querySelector(".sv-plane");
    this.svCur = container.querySelector(".sv-cursor");
    this.hue = container.querySelector(".hue");
    this.hueCur = container.querySelector(".hue-cursor");
    this.swatch = container.querySelector(".swatch-lg");
    this.hex = container.querySelector(".hex-in");
    this.rm = {
      r: container.querySelector(".rm-r"),
      g: container.querySelector(".rm-g"),
      b: container.querySelector(".rm-b"),
    };
    this._bind();
    this._render();
  }

  _bind() {
    const dragSV = (e) => {
      const rect = this.sv.getBoundingClientRect();
      this.s = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
      this.v = Math.max(0, Math.min(1, 1 - (e.clientY - rect.top) / rect.height));
      this._emit();
    };
    const dragHue = (e) => {
      const rect = this.hue.getBoundingClientRect();
      this.h = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
      this._emit();
    };
    this._attachDrag(this.sv, dragSV);
    this._attachDrag(this.hue, dragHue);
    this.hex.addEventListener("change", () => {
      const c = App.fromHex(this.hex.value);
      if (c) this.setRGB(c.r, c.g, c.b, true);
      else App.status("invalid hex");
    });
  }

  _attachDrag(el, handler) {
    let down = false;
    el.addEventListener("pointerdown", (e) => { down = true; el.setPointerCapture(e.pointerId); handler(e); });
    el.addEventListener("pointermove", (e) => { if (down) handler(e); });
    el.addEventListener("pointerup", () => { down = false; });
  }

  _emit() { this._render(); const c = this.getRGB(); if (this.onChange) this.onChange(c.r, c.g, c.b); }

  _render() {
    const hueRGB = App.hsv2rgb(this.h, 1, 1);
    const hueHex = App.toHex(hueRGB.r, hueRGB.g, hueRGB.b);
    this.sv.style.background =
      `linear-gradient(to top, #000, transparent), linear-gradient(to right, #fff, ${hueHex})`;
    this.svCur.style.left = this.s * 100 + "%";
    this.svCur.style.top = (1 - this.v) * 100 + "%";
    this.hueCur.style.left = this.h * 100 + "%";
    const c = this.getRGB();
    const hex = App.toHex(c.r, c.g, c.b);
    this.swatch.style.background = hex;
    this.swatch.style.setProperty("--kglow", `rgba(${c.r},${c.g},${c.b},0.6)`);
    if (document.activeElement !== this.hex) this.hex.value = hex;
    this.rm.r.textContent = "R" + c.r; this.rm.g.textContent = "G" + c.g; this.rm.b.textContent = "B" + c.b;
  }

  getRGB() { return App.hsv2rgb(this.h, this.s, this.v); }

  setRGB(r, g, b, emit) {
    const hsv = App.rgb2hsv(r, g, b);
    this.h = hsv.h; this.s = hsv.s; this.v = hsv.v;
    this._render();
    if (emit && this.onChange) this.onChange(r, g, b);
  }
}
window.Picker = Picker;
