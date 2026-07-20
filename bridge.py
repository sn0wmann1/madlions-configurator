"""
pywebview js_api bridge: the methods the web frontend calls into Python.

The frontend NEVER touches HID. It calls `pywebview.api.<method>(...)`; every device
write happens here through DeviceController (which serializes writes and applies
calibration). Static color edits and animations both flow through the same controller.

Physical keys are addressed by key_id (the stable on-screen layout index). Because the
firmware's slot order is not the visual order, every push translates key_id -> slot via
the discovered keymap (engine.keymap), learned with the in-app mapping wizard.
"""

from __future__ import annotations

import time

from device import protocol
from device.controller import DeviceController
from engine import animations, custom_anim, keymap, layout, profile_store
from engine.animation_runtime import AnimationRuntime

NUM_SLOTS = layout.NUM_SLOTS
NUM_KEYS = layout.NUM_KEYS
IDLE = [0, 0, 0]      # unset keys are off (a dim non-zero value renders as cyan after white balance)


class Api:
    def __init__(self):
        self.controller = DeviceController()
        self.controller.auto_connect()
        self.slot_for_key = keymap.load()                  # {key_id: slot}
        self.runtime = AnimationRuntime(self.controller, self._perkey_to_wire)
        self.key_colors = {k["id"]: list(IDLE) for k in layout.as_dicts()}
        self.current_color = [255, 0, 0]
        # Hall Effect: per-key actuation depth, raw 0.01mm units, keyed by visual key_id.
        # Empty = every key at the firmware default (3.54mm).
        self.actuation = {}
        # Hall Effect: per-key rapid trigger {key_id: {enable, reset(mm), rapid(mm)}}.
        self.rapid_trigger = {}
        # Global performance flags (defaults match firmware: NKRO on, rest off, false-touch on).
        self.perf = {"swap_wasd": False, "mac": False, "win_lock": False,
                     "six_key": False, "false_touch": True}
        # SOCD / snap-tap bindings, in slot order. Each: {key1, key2, mode, travel_mm, quick_trigger}.
        self.socd = []

        # Auto RGB sync + reconnect detection
        self._sync_rgb_on_connect()
        self._was_connected = self.controller.is_connected
        self._start_auto_reconnect()

    # ── Status / metadata ──────────────────────────────────────────────────────
    def _start_auto_reconnect(self):
        """Poll for keyboard disconnect/reconnect and auto-sync RGB."""
        import threading, time
        from device.hid_device import find_rgb_interface
        def _poll():
            while True:
                time.sleep(2)
                try:
                    real_present = find_rgb_interface() is not None
                    was = self._was_connected
                    if not was and real_present:
                        self._was_connected = True
                        self.controller.auto_connect()
                        self._sync_rgb_on_connect()
                    elif was and not real_present:
                        self._was_connected = False
                except Exception:
                    pass
        t = threading.Thread(target=_poll, daemon=True)
        t.start()

    def _sync_rgb_on_connect(self):
        """Apply the current wallpaper accent color to the keyboard on startup."""
        try:
            import json, colorsys, os
            colors_file = os.path.expanduser("~/.cache/skwd-wall/colors.json")
            if not os.path.exists(colors_file):
                return
            with open(colors_file) as f:
                data = json.load(f)
            accent = data.get("accent", "").lstrip("#")
            if len(accent) < 6:
                return
            r = int(accent[0:2], 16) / 255.0
            g = int(accent[2:4], 16) / 255.0
            b = int(accent[4:6], 16) / 255.0
            h, l, s = colorsys.rgb_to_hls(r, g, b)
            rl, gl, bl = colorsys.hls_to_rgb(h, 0.45, 0.90)
            ri, gi, bi = int(rl * 255), int(gl * 255), int(bl * 255)
            # Use instant push, not crossfade (avoids animation runtime at startup)
            target = (ri, gi, bi)
            target_wire = [target] * NUM_SLOTS
            for kid in self.key_colors:
                self.key_colors[kid] = list(target)
            self.controller.send_colors(target_wire)
        except Exception:
            pass

    def get_status(self):
        return self.controller.status()

    def reconnect(self):
        self.controller.auto_connect()
        if self.controller.is_connected:
            self._sync_rgb_on_connect()
        return self.controller.status()

    # ── RGB idle timeout (fade off when inactive) ──────────────────────────
    _idle_timeout = 0
    _idle_color = None

    def set_idle_timeout(self, seconds):
        self._idle_timeout = int(seconds)

    def get_idle_timeout(self):
        return self._idle_timeout

    def idle_fade_off(self):
        if self.runtime.running:
            self.runtime.halt()
        self._crossfade_wire(self._wire(), [(0, 0, 0)] * NUM_SLOTS, 1.5)

    def idle_fade_on(self):
        self._sync_rgb_on_connect()

    def is_fullscreen(self):
        """Check if any Hyprland window is fullscreen (for movie/game detection)."""
        try:
            import subprocess, json
            clients = json.loads(subprocess.run(
                ["hyprctl", "-j", "clients"], capture_output=True, text=True, timeout=2
            ).stdout)
            if isinstance(clients, list):
                for c in clients:
                    if c.get("fullscreen", 0) > 0 or c.get("fakeFullscreen", False):
                        return True
        except Exception:
            pass
        return False

    def get_layout(self):
        return layout.as_dicts()

    def get_animations(self):
        return animations.names()

    def get_state(self):
        return {
            "key_colors": {str(k): v for k, v in self.key_colors.items()},
            "current_color": self.current_color,
            "brightness": self.controller.cal.brightness,
            "calibration": self.controller.cal.to_dict(),
            "animation": self.runtime.current,
            "speed": self.runtime.speed,
            "status": self.controller.status(),
            "mapped": keymap.is_mapped(),
            "custom_animations": profile_store.list_animations(),
            "profiles": profile_store.list_profiles(),
            "keymap": self.get_keymap(),
        }

    # ── Wire build (key_id -> slot) ────────────────────────────────────────────
    def _perkey_to_wire(self, per_key):
        """Map a per-key list (indexed by key_id) into the 80-slot wire array."""
        wire = [(0, 0, 0)] * NUM_SLOTS
        for kid in range(min(NUM_KEYS, len(per_key))):
            slot = self.slot_for_key.get(kid, kid)
            if 0 <= slot < NUM_SLOTS:
                wire[slot] = tuple(per_key[kid])
        return wire

    def _wire(self):
        """Build the 80-slot array from the per-key static colors."""
        per_key = [tuple(self.key_colors.get(kid, (0, 0, 0))) for kid in range(NUM_KEYS)]
        return self._perkey_to_wire(per_key)

    def _crossfade_wire(self, current_wire, target_wire, duration=0.5):
        """Smoothly crossfade all slots from current_wire to target_wire using
        smoothstep easing. Blocks during the transition (duration < 0.5s)."""
        steps = 20
        step_delay = duration / steps
        for i in range(1, steps + 1):
            t = i / steps
            ease = t * t * (3 - 2 * t)  # smoothstep
            frame = []
            for cur, tgt in zip(current_wire, target_wire):
                frame.append((
                    int(cur[0] + (tgt[0] - cur[0]) * ease),
                    int(cur[1] + (tgt[1] - cur[1]) * ease),
                    int(cur[2] + (tgt[2] - cur[2]) * ease),
                ))
            self.controller.send_colors(frame)
            time.sleep(step_delay)

    def _push(self):
        ok = self.controller.send_colors(self._wire())
        return {"ok": ok, "status": self.controller.status()}

    # ── Static color control ────────────────────────────────────────────────────
    def set_current_color(self, rgb):
        self.current_color = [int(rgb[0]), int(rgb[1]), int(rgb[2])]
        return True

    def set_key_colors(self, updates):
        """Apply colors to specific physical keys (by key_id) with a crossfade transition."""
        self.runtime.halt()
        current_wire = self._wire()
        new_colors = dict(self.key_colors)
        for k, rgb in updates.items():
            kid = int(k)
            if kid in new_colors:
                new_colors[kid] = [int(rgb[0]), int(rgb[1]), int(rgb[2])]
        saved = self.key_colors
        self.key_colors = new_colors
        target_wire = self._wire()
        self.key_colors = saved
        self._crossfade_wire(current_wire, target_wire)
        self.key_colors = new_colors
        return {"ok": True, "status": self.controller.status()}

    def set_all(self, rgb):
        self.runtime.halt()
        current_wire = self._wire()
        target = (int(rgb[0]), int(rgb[1]), int(rgb[2]))
        target_wire = [target] * NUM_SLOTS
        self._crossfade_wire(current_wire, target_wire)
        for kid in self.key_colors:
            self.key_colors[kid] = list(target)
        return {"ok": True, "status": self.controller.status()}

    # ── Animations ──────────────────────────────────────────────────────────────
    def play_animation(self, name):
        builder = animations.BUILDERS.get(name)
        if builder is None:
            return {"ok": False, "error": f"unknown animation {name!r}"}
        fn = builder(lambda: tuple(self.current_color))
        self.runtime.play(fn, name)
        return {"ok": True, "animation": name}

    def stop_animation(self):
        self.runtime.halt()
        return self._push()

    def shutdown(self):
        """Called when the window is closing. We only stop our render thread cleanly; we do
        NOT push a colour. The proper "keep animating after close" behaviour needs the board's
        ONBOARD effect engine (see play_onboard_effect) — host-rendered effects can't persist
        because nothing is left to stream frames once the process exits."""
        try:
            self.runtime.halt()
        except Exception:
            pass

    def set_speed(self, value):
        self.runtime.speed = float(value)
        return True

    # ── Custom (keyframe) animations ────────────────────────────────────────────
    def list_custom_animations(self):
        return profile_store.list_animations()

    def get_custom_animation(self, name):
        try:
            return {"ok": True, "animation": profile_store.load_animation(name)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def save_custom_animation(self, anim):
        """Persist an Animation dict (name, fps, loop, frames[]) to the library."""
        name = (anim.get("name") or "untitled").strip()
        anim["name"] = name
        profile_store.save_animation(name, anim)
        return {"ok": True, "name": name, "list": profile_store.list_animations()}

    def delete_custom_animation(self, name):
        import os
        try:
            from engine.profile_store import _ANIM_DIR, _safe_name
            os.remove(os.path.join(_ANIM_DIR, f"{_safe_name(name)}.json"))
        except Exception:
            pass
        return {"ok": True, "list": profile_store.list_animations()}

    def play_custom_animation(self, name):
        try:
            anim = profile_store.load_animation(name)
        except Exception as e:
            return {"ok": False, "error": str(e)}
        fn = custom_anim.build(anim, get_speed=lambda: self.runtime.speed)
        self.runtime.play(fn, f"custom:{name}")
        return {"ok": True, "animation": name}

    def preview_custom_animation(self, anim):
        """Play an unsaved Animation dict straight from the editor."""
        fn = custom_anim.build(anim, get_speed=lambda: self.runtime.speed)
        self.runtime.play(fn, f"preview:{anim.get('name', 'untitled')}")
        return {"ok": True}

    def save_editor_draft(self, anim):
        """Autosave the editor's working animation so unsaved work survives a crash/close."""
        try:
            profile_store.save_draft(anim)
        except Exception:
            pass
        return {"ok": True}

    def get_editor_draft(self):
        """Return the last autosaved editor draft, or None."""
        return profile_store.load_draft()

    # ── Profiles ────────────────────────────────────────────────────────────────
    def list_profiles(self):
        return profile_store.list_profiles()

    def save_profile(self, name):
        """Snapshot the current lighting + calibration state into a named profile."""
        name = (name or "Default").strip()
        anim = self.runtime.current
        data = {
            "name": name,
            "lighting": {
                "mode": "animation" if anim else "static",
                "animation": anim,                       # built-in name, "custom:..", or None
                "current_color": list(self.current_color),
                "per_key_colors": {str(k): v for k, v in self.key_colors.items()},
            },
            "calibration": self.controller.cal.to_dict(),
            "meta": {"keys": NUM_KEYS},
        }
        profile_store.save_profile(name, data)
        return {"ok": True, "name": name, "list": profile_store.list_profiles()}

    def load_profile(self, name):
        try:
            data = profile_store.load_profile(name)
        except Exception as e:
            return {"ok": False, "error": str(e)}
        cal = data.get("calibration", {})
        self.controller.set_calibration(
            r=cal.get("r"), g=cal.get("g"), b=cal.get("b"),
            order=cal.get("order"), brightness=cal.get("brightness"), save=True,
        )
        light = data.get("lighting", {})
        if light.get("current_color"):
            self.current_color = [int(c) for c in light["current_color"]]
        for k, v in (light.get("per_key_colors") or {}).items():
            kid = int(k)
            if kid in self.key_colors:
                self.key_colors[kid] = [int(v[0]), int(v[1]), int(v[2])]
        anim = light.get("animation")
        if anim and anim.startswith("custom:"):
            self.play_custom_animation(anim.split("custom:", 1)[1])
        elif anim in animations.BUILDERS:
            self.play_animation(anim)
        else:
            self.runtime.halt()
            self._push()
        return {"ok": True, "state": self.get_state()}

    def delete_profile(self, name):
        import os
        try:
            from engine.profile_store import _PROFILE_DIR, _safe_name
            os.remove(os.path.join(_PROFILE_DIR, f"{_safe_name(name)}.json"))
        except Exception:
            pass
        return {"ok": True, "list": profile_store.list_profiles()}

    # ── Brightness / calibration ──────────────────────────────────────────────
    def set_brightness(self, value):
        self.controller.set_calibration(brightness=float(value))
        if not self.runtime.running:
            self._push()
        return True

    def get_calibration(self):
        return self.controller.cal.to_dict()

    def set_calibration(self, r=None, g=None, b=None, order=None):
        self.controller.set_calibration(r=r, g=g, b=b, order=order)
        if not self.runtime.running:
            self._push()
        return self.controller.cal.to_dict()

    def send_raw_channel(self, rgb):
        """White-balance helper: fill all keys with a raw (uncalibrated) color."""
        self.runtime.halt()
        c = (int(rgb[0]), int(rgb[1]), int(rgb[2]))
        ok = self.controller.send_colors([c] * NUM_SLOTS, raw=True)
        return {"ok": ok}

    def white_preview(self, r=None, g=None, b=None):
        """White-balance wizard: optionally update the R/G/B multipliers, then flood the whole
        board with CALIBRATED white so the user sees the result live while tuning. Does NOT
        touch the stored per-key colours, so their lighting is untouched when the wizard ends."""
        if r is not None or g is not None or b is not None:
            self.controller.set_calibration(r=r, g=g, b=b)
        self.runtime.halt()
        ok = self.controller.send_colors([(255, 255, 255)] * NUM_SLOTS)
        return {"ok": ok, "calibration": self.controller.cal.to_dict()}

    def white_done(self):
        """Leave the white-balance wizard: restore the user's actual per-key lighting."""
        return self._push()

    # ── Hall Effect: actuation point (CONFIRMED protocol) ───────────────────────
    def get_actuation(self):
        """Per-key actuation in mm for keys set away from the default (3.54mm)."""
        return {str(k): protocol.raw_to_mm(v) for k, v in self.actuation.items()}

    def _push_actuation(self):
        """Translate the per-key (key_id) actuation map into firmware indices and send."""
        depths = {layout.actuation_index(k): v for k, v in self.actuation.items()}
        return self.controller.send_actuation(depths)

    def set_actuation(self, key_id, mm):
        """Set one key's actuation depth (mm) and push the full array. key_id = visual id."""
        self.actuation[int(key_id)] = protocol.mm_to_raw(mm)
        ok = self._push_actuation()
        return {"ok": ok, "key": int(key_id), "mm": protocol.raw_to_mm(self.actuation[int(key_id)])}

    def set_actuation_keys(self, key_ids, mm):
        """Set actuation depth (mm) for a list of key_ids in one push."""
        raw = protocol.mm_to_raw(mm)
        for kid in key_ids:
            self.actuation[int(kid)] = raw
        ok = self._push_actuation()
        return {"ok": ok, "mm": protocol.raw_to_mm(raw), "count": len(key_ids)}

    def set_actuation_all(self, mm):
        """Set every key's actuation depth (mm) and push."""
        raw = protocol.mm_to_raw(mm)
        self.actuation = {k["id"]: raw for k in layout.as_dicts()}
        ok = self._push_actuation()
        return {"ok": ok, "mm": protocol.raw_to_mm(raw)}

    # ── Hall Effect: rapid trigger (CONFIRMED protocol) ─────────────────────────
    @staticmethod
    def _rt_raw(mm):
        return max(1, min(400, int(round(float(mm) * 100))))

    def get_rapid_trigger(self):
        return {str(k): v for k, v in self.rapid_trigger.items()}

    def _push_rapid_trigger(self):
        per_index = {}
        for kid, s in self.rapid_trigger.items():
            per_index[layout.actuation_index(kid)] = (
                1 if s.get("enable", True) else 0,
                self._rt_raw(s.get("reset", 0.5)),
                self._rt_raw(s.get("rapid", 0.5)),
            )
        return self.controller.send_rapid_trigger(per_index)

    def set_rapid_trigger(self, key_id, enable=True, reset_mm=0.5, rapid_mm=0.5):
        """Set one key's rapid-trigger config (enable + reset/rapid travel mm) and push."""
        self.rapid_trigger[int(key_id)] = {
            "enable": bool(enable), "reset": float(reset_mm), "rapid": float(rapid_mm)}
        ok = self._push_rapid_trigger()
        return {"ok": ok, "key": int(key_id), "config": self.rapid_trigger[int(key_id)]}

    def set_rapid_trigger_keys(self, key_ids, enable=True, reset_mm=0.5, rapid_mm=0.5):
        """Set rapid-trigger config for a list of key_ids in one push."""
        cfg = {"enable": bool(enable), "reset": float(reset_mm), "rapid": float(rapid_mm)}
        for kid in key_ids:
            self.rapid_trigger[int(kid)] = dict(cfg)
        ok = self._push_rapid_trigger()
        return {"ok": ok, "config": cfg, "count": len(key_ids)}

    def set_rapid_trigger_all(self, enable=True, reset_mm=0.5, rapid_mm=0.5):
        """Set every key's rapid-trigger config and push."""
        cfg = {"enable": bool(enable), "reset": float(reset_mm), "rapid": float(rapid_mm)}
        self.rapid_trigger = {k["id"]: dict(cfg) for k in layout.as_dicts()}
        ok = self._push_rapid_trigger()
        return {"ok": ok, "config": cfg}

    # ── Performance flags (global toggles, CONFIRMED) ───────────────────────────
    def get_perf(self):
        return dict(self.perf)

    # ── Advanced key: SOCD / snap-tap (CONFIRMED) ──────────────────────────────
    _SOCD_MODES = {"last": protocol.SOCD_LAST_INPUT, "key1": protocol.SOCD_ABS_KEY1,
                   "key2": protocol.SOCD_ABS_KEY2, "neutral": protocol.SOCD_NEUTRAL}

    # The firmware list FGG exposes holds up to this many advanced-key bindings.
    _SOCD_MAX = 20

    def get_socd(self):
        """Current SOCD bindings, in slot order (what the UI renders)."""
        return [dict(b) for b in self.socd]

    def _push_one_socd(self, slot, b):
        m = self._SOCD_MODES.get(str(b.get("mode", "last")).lower(), protocol.SOCD_LAST_INPUT)
        rc1, rc2 = layout.socd_rc(b["key1"]), layout.socd_rc(b["key2"])
        travel_raw = max(1, min(400, int(round(float(b.get("travel_mm", 0.5)) * 100))))
        return self.controller.send_socd(
            rc1, rc2, m, travel_raw, bool(b.get("quick_trigger", True)), int(slot))

    def set_socd(self, bindings):
        """Replace the whole SOCD list and push it to the board.

        bindings: list of {key1, key2, mode?, travel_mm?, quick_trigger?} (visual key_ids).
        Slots are assigned by list order. Slots beyond the new list length are cleared, so the
        board always matches the UI exactly.
        """
        new = []
        for b in (bindings or [])[:self._SOCD_MAX]:
            new.append({
                "key1": int(b["key1"]),
                "key2": int(b["key2"]),
                "mode": str(b.get("mode", "last")).lower(),
                "travel_mm": float(b.get("travel_mm", 0.5)),
                "quick_trigger": bool(b.get("quick_trigger", True)),
            })
        ok = True
        for slot, b in enumerate(new):
            ok = self._push_one_socd(slot, b) and ok
        # Clear any slots the old list used beyond the new length.
        for slot in range(len(new), max(len(self.socd), len(new))):
            self.controller.send_socd_clear(slot)
        if ok:
            self.socd = new
        return {"ok": ok, "socd": self.get_socd()}

    def clear_socd(self, slot=None):
        """Delete one SOCD binding by index, or all when slot is None."""
        if slot is None:
            for s in range(len(self.socd)):
                self.controller.send_socd_clear(s)
            self.socd = []
            return {"ok": True, "socd": []}
        idx = int(slot)
        if 0 <= idx < len(self.socd):
            remaining = self.socd[:idx] + self.socd[idx + 1:]
            return self.set_socd(remaining)
        return {"ok": False, "socd": self.get_socd()}

    def set_perf(self, opts):
        """Update global performance toggles and push. opts: dict of any of
        swap_wasd / mac / win_lock / six_key / false_touch -> bool."""
        for k in self.perf:
            if isinstance(opts, dict) and k in opts:
                self.perf[k] = bool(opts[k])
        ok1 = self.controller.send_perf_flags(
            self.perf["swap_wasd"], self.perf["mac"], self.perf["win_lock"], self.perf["six_key"])
        ok2 = self.controller.send_false_touch(self.perf["false_touch"])
        return {"ok": bool(ok1 and ok2), "perf": dict(self.perf)}

    # ── Key mapping (read/write onboard keymap via cmd 12/13) ─────────────────
    _fw_to_key = None
    _key_to_fw = None

    def _load_mapping(self):
        if self._fw_to_key is not None:
            return
        import json, os
        path = os.path.join(os.path.dirname(__file__), "engine", "keymap_mapping.json")
        try:
            with open(path) as f:
                data = json.load(f)
            self._fw_to_key = {int(k): v for k, v in data.get("fw_to_key", {}).items()}
            self._key_to_fw = {int(k): v for k, v in data.get("key_to_fw", {}).items()}
        except Exception:
            self._fw_to_key = {}
            self._key_to_fw = {}

    def get_keymap(self):
        """Read keymap mapped to visual key_ids via firmware→visual mapping."""
        self._load_mapping()
        codes = self._read_keymap_raw()
        result = {}
        for kid in range(layout.NUM_KEYS):
            fw = self._key_to_fw.get(kid, kid)
            result[kid] = codes[fw] if fw < len(codes) else 0
        return result

    def _write_keymap_pages(self, codes_112):
        """Write 112 keycodes using 7+7 split per page (16 packets total).
        Two 7-code writes per page cover all 14 codes without truncation."""
        import time
        ok = True
        codes = list(codes_112) + [0] * (112 - len(codes_112))
        codes = codes[:112]
        idx = 0
        for page in range(8):
            for half_offset in (0, 14):  # byte offset: 0 then 14 (7 codes × 2 bytes)
                pkt = bytearray(protocol.REPORT_LEN)
                pkt[1] = protocol.CMD_KEYMAP_WRITE
                pkt[2] = 0x00
                pkt[3] = (page * protocol.KEYMAP_PAGE_SIZE + half_offset) & 0xFF
                pkt[4] = 0x0E  # 14 bytes = 7 codes
                pkt[5] = 0x00
                for k in range(7):
                    code = codes[idx] if idx < len(codes) else 0
                    pkt[6 + k * 2] = code & 0xFF
                    pkt[7 + k * 2] = (code >> 8) & 0xFF
                    idx += 1
                if not self.controller._send_packets([pkt]):
                    ok = False
                time.sleep(0.05)
        return ok

    def set_keymap(self, remaps):
        """Write key remaps. remaps = {key_id: hid_code}. Maps visual→firmware, preserves others."""
        self._load_mapping()
        import time
        current = self._read_keymap_raw()
        full = list(current) + [0] * (112 - len(current))
        full = full[:112]
        for kid, code in remaps.items():
            fw = self._key_to_fw.get(int(kid), int(kid))
            if 0 <= fw < 112:
                full[fw] = code
        return self._write_keymap_pages(full)

    def reset_key(self, key_id):
        """Reset a single key to factory default from golden template."""
        import json, os
        kid = int(key_id)
        path = os.path.join(os.path.dirname(__file__), "engine", "keymap_golden.json")
        try:
            with open(path) as f:
                golden = json.load(f)
            self._load_mapping()
            fw = self._key_to_fw.get(kid, kid)
            if fw < len(golden):
                return self.set_keymap({kid: golden[fw]})
        except Exception:
            pass
        return False

    def reset_keymap_all(self):
        """Write the full factory-default keymap from golden template (all 112 entries)."""
        import json, os, time
        path = os.path.join(os.path.dirname(__file__), "engine", "keymap_golden.json")
        try:
            with open(path) as f:
                golden = json.load(f)
        except Exception:
            return False
        full = list(golden) + [0] * (112 - len(golden))
        full = full[:112]
        return self._write_keymap_pages(full)

    def _read_keymap_raw(self):
        """Read all 112 keymap entries using 7-code sub-reads."""
        import time
        self.controller.auto_connect()
        codes = []
        for page in range(8):
            for half in (0, 7):
                byte_off = page * protocol.KEYMAP_PAGE_SIZE + half * 2
                pkt = bytearray(protocol.REPORT_LEN)
                pkt[1] = protocol.CMD_KEYMAP
                pkt[2] = 0x00
                pkt[3] = byte_off & 0xFF
                pkt[4] = 0x0E
                pkt[5] = 0x00
                self.controller.backend.write(pkt)
                time.sleep(0.03)
                resp = self.controller.backend.read(64)
                if resp:
                    for k in range(min(7, (len(resp) - 5) // 2)):
                        b = 5 + k * 2
                        if b + 1 < len(resp):
                            codes.append(resp[b] | (resp[b + 1] << 8))
                else:
                    codes.extend([0] * 7)
        return codes

    # ── Read-back from the board (CONFIRMED) ────────────────────────────────────
    _SOCD_MODE_NAMES = {v: k for k, v in _SOCD_MODES.items()}

    def sync_from_device(self):
        """Read the live Hall-Effect state off the keyboard and replace our caches.

        Populates actuation, rapid trigger, perf toggles and SOCD from what's actually
        stored on the board, so the UI reflects reality (including anything set in FGG).
        Silently leaves a cache untouched if that read is unavailable (e.g. mock device).
        Returns a summary of what was read.
        """
        read = {"actuation": False, "rapid_trigger": False, "perf": False, "socd": False}

        perf = self.controller.read_perf()
        if perf is not None:
            self.perf.update(perf)
            read["perf"] = True
        ft = self.controller.read_false_touch()
        if ft is not None:
            self.perf["false_touch"] = ft

        socd = self.controller.read_socd()
        if socd is not None:
            parsed = []
            for b in socd:
                k1 = layout.key_from_rc(*b["key1_rc"])
                k2 = layout.key_from_rc(*b["key2_rc"])
                if k1 is None or k2 is None:
                    continue
                parsed.append({
                    "key1": k1, "key2": k2,
                    "mode": self._SOCD_MODE_NAMES.get(b["mode"], "last"),
                    "travel_mm": protocol.raw_to_mm(b["travel_raw"]),
                    "quick_trigger": bool(b["quick_trigger"]),
                })
            self.socd = parsed
            read["socd"] = True

        act = self.controller.read_actuation()
        if act is not None:
            self.actuation = {}
            for idx, raw in act.items():
                kid = layout.key_from_actuation_index(idx)
                # Only keep real keys whose depth differs from the firmware default.
                if kid is not None and raw and raw != protocol.ACTUATION_DEFAULT_RAW:
                    self.actuation[kid] = raw
            read["actuation"] = True

        rt = self.controller.read_rapid_trigger()
        if rt is not None:
            self.rapid_trigger = {}
            for idx, (en, reset, rapid) in rt.items():
                kid = layout.key_from_actuation_index(idx)
                if kid is not None:
                    self.rapid_trigger[kid] = {
                        "enable": bool(en),
                        "reset": protocol.raw_to_mm(reset),
                        "rapid": protocol.raw_to_mm(rapid),
                    }
            read["rapid_trigger"] = True

        return {
            "read": read,
            "perf": dict(self.perf),
            "socd": self.get_socd(),
            "actuation": self.get_actuation(),
            "rapid_trigger": self.get_rapid_trigger(),
        }

    # ── Key-mapping wizard ───────────────────────────────────────────────────────
    def get_key_map(self):
        return {str(k): v for k, v in self.slot_for_key.items()}

    def identify_slot(self, slot):
        """Light exactly one firmware slot (bright, uncalibrated), everything else off."""
        self.runtime.halt()
        slot = int(slot)
        wire = [(0, 0, 0)] * NUM_SLOTS
        if 0 <= slot < NUM_SLOTS:
            wire[slot] = (255, 255, 255)
        ok = self.controller.send_colors(wire, raw=True)
        return {"ok": ok, "slot": slot}

    def save_key_map(self, mapping):
        """Persist a {key_id: slot} map from the wizard, then re-apply current colors."""
        clean = {}
        for k, v in mapping.items():
            kid, slot = int(k), int(v)
            if kid in self.key_colors and 0 <= slot < NUM_SLOTS:
                clean[kid] = slot
        keymap.save(clean)
        self.slot_for_key = keymap.load()
        self._push()
        return {"ok": True, "count": len(clean)}

    def cancel_identify(self):
        """Leave the wizard: restore the current per-key colors."""
        return self._push()
