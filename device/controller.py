"""
DeviceController — the single, serialized gateway to the keyboard.

Hard rules enforced here:
  - ALL device writes pass through one lock, so the animation thread and the UI
    can never interleave and corrupt a report.
  - Raw bytes come only from protocol.py.

It wraps a backend (HidBackend or MockBackend) so the rest of the app is identical
whether or not hardware is present. Calibration (white balance / brightness / channel
order) is applied here, just before packets are built.
"""

from __future__ import annotations

import json
import os
import threading

from . import protocol
from .hid_device import HidBackend, DeviceNotFound, find_rgb_interface
from .mock_device import MockBackend

# Calibration lives in the per-user app dir (not next to the exe), so it stays writable
# when the app is frozen and installed under Program Files.
_CAL_FILE = os.path.join(os.path.expanduser("~"), ".madlions", "madlions_cal.json")


class Calibration:
    """Host-side color correction. Compatible with the old madlions_cal.json format."""

    def __init__(self, r=1.0, g=1.0, b=1.0, order=(0, 1, 2), brightness=1.0):
        self.r = r
        self.g = g
        self.b = b
        self.order = list(order)
        self.brightness = brightness

    def apply(self, rgb):
        r = min(255, int(rgb[0] * self.brightness * self.r))
        g = min(255, int(rgb[1] * self.brightness * self.g))
        b = min(255, int(rgb[2] * self.brightness * self.b))
        ch = (r, g, b)
        return ch[self.order[0]], ch[self.order[1]], ch[self.order[2]]

    def to_dict(self):
        return {"r": self.r, "g": self.g, "b": self.b, "order": self.order,
                "brightness": self.brightness}

    @classmethod
    def load(cls):
        try:
            with open(_CAL_FILE) as f:
                d = json.load(f)
            return cls(
                r=float(d.get("r", 1.0)),
                g=float(d.get("g", 1.0)),
                b=float(d.get("b", 1.0)),
                order=list(d.get("order", [0, 1, 2])),
                brightness=float(d.get("brightness", 1.0)),
            )
        except Exception:
            return cls()

    def save(self):
        try:
            os.makedirs(os.path.dirname(_CAL_FILE), exist_ok=True)
            with open(_CAL_FILE, "w") as f:
                json.dump(self.to_dict(), f)
        except Exception:
            pass


class DeviceController:
    def __init__(self, backend=None):
        self.backend = backend
        self.cal = Calibration.load()
        self._lock = threading.Lock()

    # ── Connection ──────────────────────────────────────────────────────────
    def auto_connect(self):
        """Use the real keyboard if its RGB interface is present and openable, else mock.

        Falls back to mock if the device is present but can't be opened (e.g. another app
        such as the FGG web configurator currently holds it), so the UI still runs.
        """
        backend = HidBackend() if find_rgb_interface() is not None else MockBackend()
        try:
            with self._lock:
                backend.open()
            self.backend = backend
        except Exception:
            self.backend = MockBackend()
            with self._lock:
                self.backend.open()
        return self.is_connected

    def use_mock(self):
        self.disconnect()
        self.backend = MockBackend()
        with self._lock:
            self.backend.open()

    def disconnect(self):
        if self.backend is not None:
            with self._lock:
                self.backend.close()

    @property
    def is_connected(self) -> bool:
        return self.backend is not None and self.backend.connected

    @property
    def is_mock(self) -> bool:
        return bool(self.backend and getattr(self.backend, "is_mock", False))

    def status(self) -> dict:
        return {
            "connected": self.is_connected,
            "mock": self.is_mock,
            "info": self.backend.info if self.backend else None,
        }

    # ── Writes (serialized) ───────────────────────────────────────────────────
    def send_colors(self, slots, *, raw=False) -> bool:
        """
        Push an 80-slot color list to the board. Applies calibration unless raw=True
        (raw is for the white-balance wizard, which must show true LED output).
        Returns True on success.
        """
        if not self.is_connected:
            return False
        if not raw:
            slots = [self.cal.apply(c) for c in slots]
        packets = protocol.build_color_packets(slots)
        commit = protocol.build_commit_packet()
        with self._lock:
            try:
                for pkt in packets:
                    self.backend.write(pkt)
                self.backend.write(commit)
                return True
            except (DeviceNotFound, OSError):
                return False

    def send_actuation(self, depths_raw) -> bool:
        """Push the per-key actuation array (raw 0.01mm units, key_index->raw). Serialized."""
        if not self.is_connected:
            return False
        packets = protocol.build_actuation_packets(depths_raw)
        return self._send_packets(packets)

    def send_rapid_trigger(self, per_index) -> bool:
        """Push the per-key rapid-trigger array ({index: (enable, reset_raw, rapid_raw)})."""
        if not self.is_connected:
            return False
        return self._send_packets(protocol.build_rapid_trigger_packets(per_index))

    def send_perf_flags(self, swap_wasd, mac, win_lock, six_key) -> bool:
        if not self.is_connected:
            return False
        return self._send_packets([protocol.build_perf_flags(swap_wasd, mac, win_lock, six_key)])

    def send_false_touch(self, enabled) -> bool:
        if not self.is_connected:
            return False
        return self._send_packets([protocol.build_false_touch(enabled)])

    def send_socd(self, key1_rc, key2_rc, mode, travel_raw, quick_trigger, slot=0) -> bool:
        if not self.is_connected:
            return False
        return self._send_packets([protocol.build_socd(
            key1_rc, key2_rc, mode, travel_raw, quick_trigger, slot)])

    def send_socd_clear(self, slot=0) -> bool:
        if not self.is_connected:
            return False
        return self._send_packets([protocol.build_socd_clear(slot)])

    def _send_packets(self, packets) -> bool:
        with self._lock:
            try:
                for pkt in packets:
                    self.backend.write(pkt)
                return True
            except (DeviceNotFound, OSError):
                return False

    # ── Reads (serialized request/response) ───────────────────────────────────
    def _request(self, out_report, opcode, *, timeout=0.4):
        """Write a read request, then poll for the matching read response.

        Matches on the read opcode (02 96 <opcode>); ignores write-echo/ACK input reports
        (those start 03) and unrelated reports. Returns the response bytes or None.
        """
        import time
        if self.is_mock:
            return None        # mock has nothing to read; don't burn the timeout per request
        with self._lock:
            try:
                self.backend.write(out_report)
            except (DeviceNotFound, OSError):
                return None
            deadline = time.time() + timeout
            while time.time() < deadline:
                try:
                    data = self.backend.read(64)
                except (DeviceNotFound, OSError):
                    return None
                if data and protocol.is_read_response(data, opcode):
                    return data
                if not data:
                    time.sleep(0.004)
        return None

    def read_perf(self):
        """-> {swap_wasd, mac, win_lock, six_key} or None if unavailable."""
        if not self.is_connected:
            return None
        return protocol.parse_perf(self._request(protocol.build_perf_read(), protocol.OP_PERF_FLAGS))

    def read_false_touch(self):
        if not self.is_connected:
            return None
        return protocol.parse_false_touch(
            self._request(protocol.build_false_touch_read(), protocol.OP_FALSE_TOUCH))

    def read_socd(self):
        """-> list of populated bindings in slot order: {slot, mode, travel_raw, quick_trigger,
        key1_rc, key2_rc}. Empty/cleared slots are skipped. None if device unavailable."""
        if not self.is_connected:
            return None
        out = []
        answered = False
        for slot in range(protocol.SOCD_READ_SLOTS):
            resp = self._request(protocol.build_socd_read(slot), protocol.OP_ADV_KEY)
            parsed = protocol.parse_socd(resp) if resp else None
            if parsed is None:
                continue
            answered = True
            if not parsed.get("empty"):
                out.append(parsed)
        return out if answered else None

    def read_actuation(self):
        """-> {array_index: raw} merged across chunks, or None if unavailable."""
        if not self.is_connected:
            return None
        merged = {}
        for start in protocol._ACT_READ_STARTS:
            resp = self._request(protocol.build_actuation_read(start), protocol.OP_ACTUATION)
            if resp:
                merged.update(protocol.parse_actuation_chunk(resp))
        return merged or None

    def read_rapid_trigger(self):
        """-> {array_index: (enable, reset_raw, rapid_raw)} merged across chunks, or None."""
        if not self.is_connected:
            return None
        merged = {}
        for start in protocol._RT_STARTS:
            resp = self._request(protocol.build_rapid_trigger_read(start), protocol.OP_RAPID_TRIGGER)
            if resp:
                merged.update(protocol.parse_rapid_trigger_chunk(resp))
        return merged or None

    # ── Calibration ───────────────────────────────────────────────────────────
    def set_calibration(self, *, r=None, g=None, b=None, order=None, brightness=None,
                        save=True):
        if r is not None:
            self.cal.r = r
        if g is not None:
            self.cal.g = g
        if b is not None:
            self.cal.b = b
        if order is not None:
            self.cal.order = list(order)
        if brightness is not None:
            self.cal.brightness = brightness
        if save:
            self.cal.save()
