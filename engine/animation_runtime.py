"""
Animation runtime: a single daemon thread that renders frames and pushes them to
the device on a fixed tick. All device writes go through DeviceController, whose lock
keeps these pushes from colliding with UI writes.

Frame functions render in physical key order (a list indexed by key_id, length NUM_KEYS).
`to_wire` translates that into the 80-slot wire array via the discovered keymap, so
animations are spatially correct regardless of the scrambled hardware matrix order.

fps is capped; full-board per-key updates can hit the USB report-rate ceiling, so the
real device's limit should be measured and TARGET_FPS lowered if frames are dropped.
"""

from __future__ import annotations

import threading
import time

TARGET_FPS = 30
_TICK = 1.0 / TARGET_FPS


class AnimationRuntime(threading.Thread):
    def __init__(self, controller, to_wire):
        super().__init__(daemon=True)
        self.controller = controller
        self.to_wire = to_wire          # per_key_list -> 80-slot wire list
        self._fn = None
        self._name = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self.speed = 1.0
        self.start()

    @property
    def current(self):
        return self._name

    @property
    def running(self) -> bool:
        return self._fn is not None and not self._stop.is_set()

    def play(self, fn, name):
        self._stop.clear()
        with self._lock:
            self._fn = fn
            self._name = name

    def halt(self):
        self._stop.set()
        with self._lock:
            self._fn = None
            self._name = None

    def run(self):
        t = 0.0
        while True:
            with self._lock:
                fn = self._fn
            if fn and not self._stop.is_set():
                try:
                    self.controller.send_colors(self.to_wire(fn(t)))
                except Exception:
                    pass
                t += 0.04 * max(0.1, self.speed)
            time.sleep(_TICK)
