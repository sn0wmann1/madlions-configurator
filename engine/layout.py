"""
MADLIONS keyboard layouts — auto-selected based on connected device PID.

MAD60 (PID 0x1054): 61 keys, standard 60% layout
MAD68 (PID 0x1058): 68 keys, 65% layout with arrows and nav cluster
"""

from __future__ import annotations

# ── MAD60 (61 keys) ──────────────────────────────────────────────────────────
KEYS_MAD60 = [
    ("Esc", 0, 0, 0.0, 1), ("1", 1, 0, 1, 1), ("2", 2, 0, 2, 1), ("3", 3, 0, 3, 1),
    ("4", 4, 0, 4, 1), ("5", 5, 0, 5, 1), ("6", 6, 0, 6, 1), ("7", 7, 0, 7, 1),
    ("8", 8, 0, 8, 1), ("9", 9, 0, 9, 1), ("0", 10, 0, 10, 1), ("-", 11, 0, 11, 1),
    ("=", 12, 0, 12, 1), ("Bksp", 13, 0, 13, 2),
    ("Tab", 14, 1, 0, 1.5), ("Q", 15, 1, 1.5, 1), ("W", 16, 1, 2.5, 1),
    ("E", 17, 1, 3.5, 1), ("R", 18, 1, 4.5, 1), ("T", 19, 1, 5.5, 1),
    ("Y", 20, 1, 6.5, 1), ("U", 21, 1, 7.5, 1), ("I", 22, 1, 8.5, 1),
    ("O", 23, 1, 9.5, 1), ("P", 24, 1, 10.5, 1), ("[", 25, 1, 11.5, 1),
    ("]", 26, 1, 12.5, 1), ("\\", 27, 1, 13.5, 1.5),
    ("Caps", 28, 2, 0, 1.75), ("A", 29, 2, 1.75, 1), ("S", 30, 2, 2.75, 1),
    ("D", 31, 2, 3.75, 1), ("F", 32, 2, 4.75, 1), ("G", 33, 2, 5.75, 1),
    ("H", 34, 2, 6.75, 1), ("J", 35, 2, 7.75, 1), ("K", 36, 2, 8.75, 1),
    ("L", 37, 2, 9.75, 1), (";", 38, 2, 10.75, 1), ("'", 39, 2, 11.75, 1),
    ("Enter", 40, 2, 12.75, 2.25),
    ("Shift", 41, 3, 0, 2.25), ("Z", 42, 3, 2.25, 1), ("X", 43, 3, 3.25, 1),
    ("C", 44, 3, 4.25, 1), ("V", 45, 3, 5.25, 1), ("B", 46, 3, 6.25, 1),
    ("N", 47, 3, 7.25, 1), ("M", 48, 3, 8.25, 1), (",", 49, 3, 9.25, 1),
    (".", 50, 3, 10.25, 1), ("/", 51, 3, 11.25, 1), ("Shift", 52, 3, 12.25, 2.75),
    ("Ctrl", 53, 4, 0, 1.25), ("Win", 54, 4, 1.25, 1.25), ("Alt", 55, 4, 2.5, 1.25),
    ("Space", 56, 4, 3.75, 6.25), ("Alt", 57, 4, 10, 1.25), ("Menu", 58, 4, 11.25, 1.25),
    ("Ctrl", 59, 4, 12.5, 1.25), ("Fn", 60, 4, 13.75, 1.25),
]

# ── MAD68 (68 keys) — pixel-verified against MAD68 Pro reference ───────────
KEYS_MAD68 = [
    # Row 0 — number row (15 keys)
    ("Esc", 0, 0, 0.68, 1.0),
    ("1!", 1, 0, 1.73, 1.0),
    ("2@", 2, 0, 2.8, 1.0),
    ("3#", 3, 0, 3.86, 1.0),
    ("4$", 4, 0, 4.93, 1.0),
    ("5%", 5, 0, 6.0, 1.0),
    ("6^", 6, 0, 7.07, 1.0),
    ("7&", 7, 0, 8.16, 1.0),
    ("8*", 8, 0, 9.23, 1.0),
    ("9(", 9, 0, 10.3, 1.0),
    ("0)", 10, 0, 11.36, 1.0),
    ("-_", 11, 0, 12.43, 1.0),
    ("=+", 12, 0, 13.5, 1.0),
    ("Bksp", 13, 0, 14.55, 1.73),
    ("Ins", 14, 0, 16.36, 1.0),

    # Row 1 — QWERTY (15 keys)
    ("Tab", 15, 1, 0.68, 1.55),
    ("Q", 16, 1, 2.27, 1.0),
    ("W", 17, 1, 3.32, 1.0),
    ("E", 18, 1, 4.36, 1.0),
    ("R", 19, 1, 5.41, 1.0),
    ("T", 20, 1, 6.45, 1.0),
    ("Y", 21, 1, 7.52, 1.0),
    ("U", 22, 1, 8.57, 1.0),
    ("I", 23, 1, 9.61, 1.0),
    ("O", 24, 1, 10.66, 1.0),
    ("P", 25, 1, 11.73, 1.0),
    ("[{", 26, 1, 12.77, 1.0),
    ("]}", 27, 1, 13.84, 1.0),
    ("\\|", 28, 1, 14.91, 1.39),
    ("Del", 29, 1, 16.36, 1.0),

    # Row 2 — home row (14 keys)
    ("Caps", 30, 2, 0.68, 1.84),
    ("A", 31, 2, 2.57, 1.0),
    ("S", 32, 2, 3.64, 1.0),
    ("D", 33, 2, 4.68, 1.0),
    ("F", 34, 2, 5.73, 1.0),
    ("G", 35, 2, 6.77, 1.0),
    ("H", 36, 2, 7.84, 1.0),
    ("J", 37, 2, 8.89, 1.0),
    ("K", 38, 2, 9.93, 1.0),
    ("L", 39, 2, 10.98, 1.0),
    (";:", 40, 2, 12.05, 1.0),
    ("'\"", 41, 2, 13.09, 1.0),
    ("Enter", 42, 2, 14.14, 2.16),
    ("PG ▲", 43, 2, 16.36, 1.0),

    # Row 3 — shift row (14 keys)
    ("Shift", 44, 3, 0.68, 2.09),
    ("Z", 45, 3, 2.84, 1.0),
    ("X", 46, 3, 3.89, 1.0),
    ("C", 47, 3, 4.93, 1.0),
    ("V", 48, 3, 6.0, 1.0),
    ("B", 49, 3, 7.05, 1.0),
    ("N", 50, 3, 8.09, 1.0),
    ("M", 51, 3, 9.14, 1.0),
    (",<", 52, 3, 10.18, 1.0),
    (".>", 53, 3, 11.25, 1.0),
    ("/?", 54, 3, 12.32, 1.0),
    ("Shift", 55, 3, 13.39, 1.84),
    ("↑", 56, 3, 15.3, 1.0),
    ("PG ▼", 57, 3, 16.36, 1.0),

    # Row 4 — bottom row (10 keys)
    ("Ctrl", 58, 4, 0.68, 1.25),
    ("Win", 59, 4, 2.0, 1.25),
    ("Alt", 60, 4, 3.34, 1.25),
    ("Space", 61, 4, 4.66, 6.34),
    ("Alt", 62, 4, 11.09, 1.0),
    ("Fn", 63, 4, 12.14, 1.0),
    ("Ctrl", 64, 4, 13.18, 1.0),
    ("←", 65, 4, 14.23, 1.0),
    ("↓", 66, 4, 15.3, 1.0),
    ("→", 67, 4, 16.36, 1.0),
]

NUM_KEYS_MAD68 = len(KEYS_MAD68)
NUM_KEYS_MAD60 = len(KEYS_MAD60)

# Auto-detect model from connected keyboard PID (default to MAD68)
import os, json as _json
_CAL_FILE = os.path.join(os.path.expanduser("~"), ".madlions", "madlions_cal.json")

def _detect_model():
    """Check connected keyboard PID, or fall back to last known model."""
    try:
        from device.hid_device import enumerate_interfaces
        for dev in enumerate_interfaces():
            pid = dev.get("product_id", 0)
            if pid == 0x1058:
                return "MAD68"
            elif pid == 0x1054:
                return "MAD60"
    except Exception:
        pass
    # Fall back to saved calibration's last model, or MAD68
    try:
        if os.path.exists(_CAL_FILE):
            with open(_CAL_FILE) as f:
                data = _json.load(f)
            return data.get("model", "MAD68")
    except Exception:
        pass
    return "MAD68"

_MODEL = _detect_model()
KEYS = KEYS_MAD68 if _MODEL == "MAD68" else KEYS_MAD60
NUM_KEYS = len(KEYS)
NUM_SLOTS = 80

# Rebuild the RC maps for the active layout
_ROW_FIRST = {}
for (_lbl, _kid, _row, _x, _w) in KEYS:
    if _row not in _ROW_FIRST or _kid < _ROW_FIRST[_row]:
        _ROW_FIRST[_row] = _kid
KEY_RC = {kid: (row, kid - _ROW_FIRST[row]) for (_lbl, kid, row, _x, _w) in KEYS}
_RC_KEY = {rc: kid for kid, rc in KEY_RC.items()}


def as_dicts():
    return [{"id": kid, "label": label, "row": row, "x": x, "w": w}
            for (label, kid, row, x, w) in KEYS]


_ACT_INDEX_OVERRIDES = {}


def actuation_index(key_id: int) -> int:
    return _ACT_INDEX_OVERRIDES.get(int(key_id), int(key_id))


def socd_rc(key_id: int):
    return KEY_RC[int(key_id)]


def key_from_rc(row: int, col: int):
    return _RC_KEY.get((int(row), int(col)))


def key_from_actuation_index(index: int):
    _ACT_KEY_BY_INDEX = {actuation_index(kid): kid for (_l, kid, _r, _x, _w) in KEYS}
    return _ACT_KEY_BY_INDEX.get(int(index))
