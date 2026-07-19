"""
MAD68 (68-key) layout — pixel-verified against the MAD68 Pro reference.

Each entry: (label, key_id, row, x_units, width_units).
Positions derived from the MAD68 Pro KEY_LAYOUT (44px key pitch).
"""

from __future__ import annotations

KEYS = [
    # Row 0 — number row (15 keys)
    ("Esc", 0, 0, 0.7, 1), ("1", 1, 0, 1.7, 1), ("2", 2, 0, 2.8, 1),
    ("3", 3, 0, 3.9, 1), ("4", 4, 0, 4.9, 1), ("5", 5, 0, 6.0, 1),
    ("6", 6, 0, 7.1, 1), ("7", 7, 0, 8.2, 1), ("8", 8, 0, 9.2, 1),
    ("9", 9, 0, 10.3, 1), ("0", 10, 0, 11.4, 1), ("-", 11, 0, 12.4, 1),
    ("=", 12, 0, 13.5, 1), ("Bksp", 13, 0, 14.5, 1.7),
    ("Ins", 14, 0, 16.4, 1),

    # Row 1 — QWERTY (15 keys)
    ("Tab", 15, 1, 0.7, 1.5),
    ("Q", 16, 1, 2.3, 1), ("W", 17, 1, 3.3, 1), ("E", 18, 1, 4.4, 1),
    ("R", 19, 1, 5.4, 1), ("T", 20, 1, 6.5, 1), ("Y", 21, 1, 7.5, 1),
    ("U", 22, 1, 8.6, 1), ("I", 23, 1, 9.6, 1), ("O", 24, 1, 10.7, 1),
    ("P", 25, 1, 11.7, 1), ("[", 26, 1, 12.8, 1), ("]", 27, 1, 13.8, 1),
    ("\\", 28, 1, 14.9, 1.4),
    ("Del", 29, 1, 16.4, 1),

    # Row 2 — home row (14 keys)
    ("Caps", 30, 2, 0.7, 1.8),
    ("A", 31, 2, 2.6, 1), ("S", 32, 2, 3.6, 1), ("D", 33, 2, 4.7, 1),
    ("F", 34, 2, 5.7, 1), ("G", 35, 2, 6.8, 1), ("H", 36, 2, 7.8, 1),
    ("J", 37, 2, 8.9, 1), ("K", 38, 2, 9.9, 1), ("L", 39, 2, 11.0, 1),
    (";", 40, 2, 12.0, 1), ("'", 41, 2, 13.1, 1),
    ("Enter", 42, 2, 14.1, 2.2),
    ("PgUp", 43, 2, 16.4, 1),

    # Row 3 — shift row (14 keys)
    ("Shift", 44, 3, 0.7, 2.1),
    ("Z", 45, 3, 2.8, 1), ("X", 46, 3, 3.9, 1), ("C", 47, 3, 4.9, 1),
    ("V", 48, 3, 6.0, 1), ("B", 49, 3, 7.0, 1), ("N", 50, 3, 8.1, 1),
    ("M", 51, 3, 9.1, 1), (",", 52, 3, 10.2, 1), (".", 53, 3, 11.2, 1),
    ("/", 54, 3, 12.3, 1), ("Shift", 55, 3, 13.4, 1.8),
    ("↑", 56, 3, 15.3, 1),
    ("PgDn", 57, 3, 16.4, 1),

    # Row 4 — bottom row (10 keys)
    ("Ctrl", 58, 4, 0.7, 1.2), ("Win", 59, 4, 2.0, 1.2),
    ("Alt", 60, 4, 3.3, 1.2),
    ("Space", 61, 4, 4.7, 6.3),
    ("AltGr", 62, 4, 11.1, 1), ("Fn", 63, 4, 12.1, 1),
    ("Ctrl", 64, 4, 13.2, 1),
    ("←", 65, 4, 14.2, 1), ("↓", 66, 4, 15.3, 1), ("→", 67, 4, 16.4, 1),
]

NUM_KEYS = len(KEYS)        # 68 physical keys
NUM_SLOTS = 80              # wire length including padding


def as_dicts():
    """Layout for the frontend: list of {id, label, row, x, w}."""
    return [{"id": kid, "label": label, "row": row, "x": x, "w": w}
            for (label, kid, row, x, w) in KEYS]


# ── Actuation array index per key_id ────────────────────────────────────────────
# TODO: measure these on real MAD68 hardware.
_ACT_INDEX_OVERRIDES = {}


def actuation_index(key_id: int) -> int:
    return _ACT_INDEX_OVERRIDES.get(int(key_id), int(key_id))


# ── (row, column) per key — used by the SOCD/advanced-key protocol ──────────────
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
