"""
MAD68 (68-key) layout — pixel-verified against the MAD68 Pro reference.

Each entry: (label, key_id, row, x_units, width_units).
Positions derived from the MAD68 Pro KEY_LAYOUT (44px key pitch).
"""

from __future__ import annotations

KEYS = [
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
    ("PG ↑", 43, 2, 16.36, 1.0),

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
    ("PG ↓", 57, 3, 16.36, 1.0),

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

NUM_KEYS = len(KEYS)
NUM_SLOTS = 80


def as_dicts():
    return [{"id": kid, "label": label, "row": row, "x": x, "w": w}
            for (label, kid, row, x, w) in KEYS]


_ACT_INDEX_OVERRIDES = {}


def actuation_index(key_id: int) -> int:
    return _ACT_INDEX_OVERRIDES.get(int(key_id), int(key_id))


_ROW_FIRST = {}
for (_lbl, _kid, _row, _x, _w) in KEYS:
    if _row not in _ROW_FIRST or _kid < _ROW_FIRST[_row]:
        _ROW_FIRST[_row] = _kid
KEY_RC = {kid: (row, kid - _ROW_FIRST[row]) for (_lbl, kid, row, _x, _w) in KEYS}


def socd_rc(key_id: int):
    return KEY_RC[int(key_id)]


_RC_KEY = {rc: kid for kid, rc in KEY_RC.items()}
_ACT_KEY_BY_INDEX = {actuation_index(kid): kid for (_l, kid, _r, _x, _w) in KEYS}


def key_from_rc(row: int, col: int):
    return _RC_KEY.get((int(row), int(col)))


def key_from_actuation_index(index: int):
    return _ACT_KEY_BY_INDEX.get(int(index))
