"""
System-tray integration.

Closing the window MINIMIZES the app to the Windows tray (like Discord / Steam /
Spotify) instead of quitting, so the host-rendered animation keeps streaming to the
keyboard. The user restores the window or quits for real from the tray icon.

Uses pystray (tray icon + menu) and Pillow (to draw the icon). The tray runs on its own
daemon thread; pywebview owns the main thread. Menu callbacks call window methods, which
pywebview marshals to the GUI thread.
"""

from __future__ import annotations

import threading

import pystray
from PIL import Image, ImageDraw

# Accent used for the tray glyph (matches the app's signal accent).
_ACCENT = (233, 162, 59, 255)
_TILE = (16, 18, 22, 255)
_EDGE = (62, 68, 78, 255)


def _make_icon_image(size: int = 64) -> Image.Image:
    """A dark rounded tile with a bright 'M' — recognisable at 16px in the tray."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = max(2, size // 32)
    d.rounded_rectangle([pad, pad, size - pad - 1, size - pad - 1],
                        radius=size // 5, fill=_TILE, outline=_EDGE, width=max(1, size // 32))
    # Bold "M" as a single polyline, scaled to the tile.
    s = size / 64.0
    pts = [(18 * s, 47 * s), (18 * s, 17 * s), (32 * s, 33 * s),
           (46 * s, 17 * s), (46 * s, 47 * s)]
    d.line(pts, fill=_ACCENT, width=max(2, int(5 * s)), joint="curve")
    return img


class TrayController:
    def __init__(self, window, on_quit=None):
        self.window = window
        self.on_quit = on_quit
        self._quitting = False
        self._ready = threading.Event()
        self.icon = pystray.Icon(
            "madlions",
            _make_icon_image(),
            "MADLIONS 60 Configurator",
            menu=pystray.Menu(
                pystray.MenuItem("Show MADLIONS", self._show, default=True),
                pystray.MenuItem("Quit", self._quit),
            ),
        )

    # ── lifecycle ──────────────────────────────────────────────────────────────
    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        # setup is called once the tray icon is live; flag readiness so the close
        # handler knows the tray is available (and won't trap the user otherwise).
        def _setup(icon):
            icon.visible = True
            self._ready.set()
        try:
            self.icon.run(setup=_setup)
        except Exception:
            # If the tray backend fails, mark ready so closing falls back to a real quit.
            self._ready.set()

    @property
    def ready(self) -> bool:
        return self._ready.is_set()

    @property
    def quitting(self) -> bool:
        return self._quitting

    # ── actions ──────────────────────────────────────────────────────────────
    def hide_to_tray(self):
        try:
            self.window.hide()
        except Exception:
            pass

    def _show(self, icon=None, item=None):
        try:
            self.window.show()
        except Exception:
            pass

    def _quit(self, icon=None, item=None):
        self._quitting = True
        if self.on_quit:
            try:
                self.on_quit()
            except Exception:
                pass
        try:
            self.icon.stop()
        except Exception:
            pass
        try:
            self.window.destroy()
        except Exception:
            pass

    def stop(self):
        try:
            self.icon.stop()
        except Exception:
            pass
