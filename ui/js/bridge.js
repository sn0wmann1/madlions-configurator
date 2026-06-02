// Shared core: global App namespace, bridge access, colour math, small helpers.
// Every module hangs off window.App. The frontend only ever calls pywebview.api.

const App = {
  state: {
    layout: [],
    keyById: {},
    selected: new Set(),
    color: { r: 255, g: 0, b: 0 },
    activeAnim: null,
    mapping: null,           // wizard session, else null
    editor: null,            // { name, loop, frames:[{duration_ms,colors,easing}], active }
    customs: [],
    profiles: [],
    mapped: false,
  },

  api() { return window.pywebview.api; },
  $(id) { return document.getElementById(id); },
  qsa(s) { return Array.from(document.querySelectorAll(s)); },
  status(msg) { const el = App.$("statusbar"); if (el) el.textContent = msg; },
};
window.App = App;

// ── colour utilities ───────────────────────────────────────────
App.clamp8 = (v) => Math.max(0, Math.min(255, Math.round(v)));
App.toHex = (r, g, b) =>
  "#" + [r, g, b].map((v) => App.clamp8(v).toString(16).padStart(2, "0")).join("").toUpperCase();
App.fromHex = (h) => {
  h = (h || "").replace("#", "").trim();
  if (h.length !== 6) return null;
  const r = parseInt(h.slice(0, 2), 16), g = parseInt(h.slice(2, 4), 16), b = parseInt(h.slice(4, 6), 16);
  return [r, g, b].some(isNaN) ? null : { r, g, b };
};
App.lum = (r, g, b) => 0.299 * r + 0.587 * g + 0.114 * b;

App.hsv2rgb = (h, s, v) => {
  let r, g, b;
  const i = Math.floor(h * 6), f = h * 6 - i;
  const p = v * (1 - s), q = v * (1 - f * s), t = v * (1 - (1 - f) * s);
  switch (i % 6) {
    case 0: r = v; g = t; b = p; break;
    case 1: r = q; g = v; b = p; break;
    case 2: r = p; g = v; b = t; break;
    case 3: r = p; g = q; b = v; break;
    case 4: r = t; g = p; b = v; break;
    default: r = v; g = p; b = q; break;
  }
  return { r: Math.round(r * 255), g: Math.round(g * 255), b: Math.round(b * 255) };
};
App.rgb2hsv = (r, g, b) => {
  r /= 255; g /= 255; b /= 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b), d = max - min;
  let h = 0;
  if (d) {
    if (max === r) h = ((g - b) / d) % 6;
    else if (max === g) h = (b - r) / d + 2;
    else h = (r - g) / d + 4;
    h /= 6; if (h < 0) h += 1;
  }
  return { h, s: max ? d / max : 0, v: max };
};
