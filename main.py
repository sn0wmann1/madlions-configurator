"""
MADLIONS 60% Hall Effect Configurator — entry point.

Wires the bridge to a pywebview window that loads the web UI. Run:  python main.py
Also supports --crossfade RRGGBB for one-shot color transitions from wallpaper sync scripts.
"""

from __future__ import annotations

import os
import socket
import sys
import threading


def _run_crossfade(hex_color):
    """CLI mode: connect to the keyboard, crossfade from off to *hex_color*, disconnect."""
    import time
    from device.controller import DeviceController
    from device.protocol import NUM_SLOTS

    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        print(f"Invalid color: {hex_color!r} — use RRGGBB or #RRGGBB", file=sys.stderr)
        return 1

    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    ctrl = DeviceController()
    ctrl.auto_connect()
    if not ctrl.is_connected:
        print("Keyboard not found", file=sys.stderr)
        return 1

    target = [(r, g, b)] * NUM_SLOTS
    steps = 20
    step_delay = 0.5 / steps
    for i in range(1, steps + 1):
        t = i / steps
        ease = t * t * (3 - 2 * t)
        frame = [(int(r * ease), int(g * ease), int(b * ease))] * NUM_SLOTS
        ctrl.send_colors(frame)
        time.sleep(step_delay)

    ctrl.disconnect()
    return 0


if len(sys.argv) >= 3 and sys.argv[1] == "--crossfade":
    sys.exit(_run_crossfade(sys.argv[2]))


import webview

from bridge import Api
from tray import TrayController


def _base_dir():
    """Resolve the app's base directory, whether run from source or PyInstaller-frozen."""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


_UI_DIR = os.path.join(_base_dir(), "ui")

# Single-instance lock: the first instance binds this loopback port and listens; a second
# launch fails to bind, pokes the running instance (which restores its window) and exits.
_LOCK_PORT = 49613


def _acquire_single_instance(on_activate):
    """Return the held lock socket if we're the only instance, else None (another is running)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", _LOCK_PORT))   # no SO_REUSEADDR: a 2nd bind must fail
    except OSError:
        try:
            with socket.create_connection(("127.0.0.1", _LOCK_PORT), timeout=1):
                pass    # poke the running instance to surface its window
        except OSError:
            pass
        sock.close()
        return None
    sock.listen(5)

    def _serve():
        while True:
            try:
                conn, _ = sock.accept()
                conn.close()
                on_activate()
            except OSError:
                break

    threading.Thread(target=_serve, daemon=True).start()
    return sock


def main():
    # Enforce a single instance: a second launch restores the existing window and exits,
    # so the user can't end up with several copies open or minimized to the tray.
    holder = {}
    lock = _acquire_single_instance(lambda: _activate(holder.get("window")))
    if lock is None:
        return

    api = Api()
    window = webview.create_window(
        "MADLIONS 60 — Configurator",
        os.path.join(_UI_DIR, "index.html"),
        js_api=api,
        width=1240,
        height=760,
        min_size=(960, 640),
        background_color="#0a0a16",
    )
    # Closing the window minimizes to the system tray (like Discord/Steam) so the
    # host-rendered animation keeps streaming to the keyboard. The app fully quits only
    # via the tray "Quit" item.
    tray = TrayController(window, on_quit=api.shutdown)

    def _on_closing():
        # Returning False cancels the close. If the tray isn't available (or the user chose
        # Quit), allow the real close so they're never trapped without a way to exit.
        if tray.quitting or not tray.ready:
            return True
        tray.hide_to_tray()
        return False

    window.events.closing += _on_closing
    holder["window"] = window
    tray.start()
    webview.start()
    tray.stop()
    api.shutdown()


def _activate(window):
    """Bring the running instance's window back to the foreground (from tray/minimized)."""
    if window is None:
        return
    try:
        window.show()
        window.restore()
    except Exception:
        pass


if __name__ == "__main__":
    main()
