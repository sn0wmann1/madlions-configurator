// WebHID capture logger — paste into the vendor web app's DevTools console.
// Captures BOTH directions:
//   OUT      sendReport(id, data)            host -> keyboard (writes)
//   FEAT-OUT sendFeatureReport(id, data)     host -> keyboard (feature write)
//   FEAT-IN  receiveFeatureReport(id)        keyboard -> host (feature read response)
//   IN       'inputreport' event             keyboard -> host (replies to queries)
// Each line is printed to the console AND POSTed to the local beacon
// (python tools/webhid_beacon.py), which appends it to tools/webhid_capture.log.
(() => {
  const BEACON = "http://127.0.0.1:8765";
  const hex = (d) => {
    if (!d) return "";
    const u8 = ArrayBuffer.isView(d)
      ? new Uint8Array(d.buffer, d.byteOffset, d.byteLength)
      : new Uint8Array(d);
    return [...u8].map((b) => b.toString(16).padStart(2, "0")).join(" ");
  };
  const emit = (line) => {
    console.log(line);
    try { fetch(BEACON, { method: "POST", body: line, keepalive: true }); } catch (e) {}
  };

  // ── Outbound writes ───────────────────────────────────────────────
  for (const m of ["sendReport", "sendFeatureReport"]) {
    const orig = HIDDevice.prototype[m];
    HIDDevice.prototype[m] = function (id, data) {
      emit((m === "sendReport" ? "OUT" : "FEAT-OUT") + " id=" + id + "  " + hex(data));
      return orig.call(this, id, data);
    };
  }

  // ── Feature-report reads (host asks, keyboard answers in the resolved value) ──
  const rfr = HIDDevice.prototype.receiveFeatureReport;
  HIDDevice.prototype.receiveFeatureReport = function (id) {
    const p = rfr.call(this, id);
    return p.then((dv) => { emit("FEAT-IN id=" + id + "  " + hex(dv)); return dv; });
  };

  // ── Inbound input reports (the keyboard's replies to query commands) ──
  const attach = (dev) => {
    if (!dev || dev.__logged) return;
    dev.__logged = true;
    dev.addEventListener("inputreport", (e) => {
      emit("IN id=" + e.reportId + "  " + hex(e.data));
    });
  };
  // Attach to devices already opened, and to any opened after this point.
  if (navigator.hid && navigator.hid.getDevices) {
    navigator.hid.getDevices().then((ds) => ds.forEach(attach));
  }
  const openOrig = HIDDevice.prototype.open;
  HIDDevice.prototype.open = function () {
    attach(this);
    return openOrig.apply(this, arguments);
  };

  emit("logger installed (OUT / FEAT-OUT / FEAT-IN / IN)");
})();
