"""
Canonical 60% layout. ONE map shared by the UI grid, the keymap, and the lighting.

key_id == firmware slot index (0..59). Each entry: label, row, x (column offset in key
units), w (width in units). Slots 60..79 exist on the wire as padding and are not keys.

Kept in sync with the slot order used by the device protocol layer.
"""

from __future__ import annotations

# (label, key_id/slot, row, x_units, width_units)
KEYS = [
    # Row 0 — number row
    ("Esc", 0, 0, 0.0, 1), ("1", 1, 0, 1, 1), ("2", 2, 0, 2, 1), ("3", 3, 0, 3, 1),
    ("4", 4, 0, 4, 1), ("5", 5, 0, 5, 1), ("6", 6, 0, 6, 1), ("7", 7, 0, 7, 1),
    ("8", 8, 0, 8, 1), ("9", 9, 0, 9, 1), ("0", 10, 0, 10, 1), ("-", 11, 0, 11, 1),
    ("=", 12, 0, 12, 1), ("Bksp", 13, 0, 13, 2),
    # Row 1 — QWERTY
    ("Tab", 14, 1, 0, 1.5), ("Q", 15, 1, 1.5, 1), ("W", 16, 1, 2.5, 1),
    ("E", 17, 1, 3.5, 1), ("R", 18, 1, 4.5, 1), ("T", 19, 1, 5.5, 1),
    ("Y", 20, 1, 6.5, 1), ("U", 21, 1, 7.5, 1), ("I", 22, 1, 8.5, 1),
    ("O", 23, 1, 9.5, 1), ("P", 24, 1, 10.5, 1), ("[", 25, 1, 11.5, 1),
    ("]", 26, 1, 12.5, 1), ("\\", 27, 1, 13.5, 1.5),
    # Row 2 — home row
    ("Caps", 28, 2, 0, 1.75), ("A", 29, 2, 1.75, 1), ("S", 30, 2, 2.75, 1),
    ("D", 31, 2, 3.75, 1), ("F", 32, 2, 4.75, 1), ("G", 33, 2, 5.75, 1),
    ("H", 34, 2, 6.75, 1), ("J", 35, 2, 7.75, 1), ("K", 36, 2, 8.75, 1),
    ("L", 37, 2, 9.75, 1), (";", 38, 2, 10.75, 1), ("'", 39, 2, 11.75, 1),
    ("Enter", 40, 2, 12.75, 2.25),
    # Row 3 — shift row
    ("Shift", 41, 3, 0, 2.25), ("Z", 42, 3, 2.25, 1), ("X", 43, 3, 3.25, 1),
    ("C", 44, 3, 4.25, 1), ("V", 45, 3, 5.25, 1), ("B", 46, 3, 6.25, 1),
    ("N", 47, 3, 7.25, 1), ("M", 48, 3, 8.25, 1), (",", 49, 3, 9.25, 1),
    (".", 50, 3, 10.25, 1), ("/", 51, 3, 11.25, 1), ("Shift", 52, 3, 12.25, 2.75),
    # Row 4 — bottom row (8 keys, confirmed against the real MAD60)
    ("Ctrl", 53, 4, 0, 1.25), ("Win", 54, 4, 1.25, 1.25), ("Alt", 55, 4, 2.5, 1.25),
    ("Space", 56, 4, 3.75, 6.25), ("Alt", 57, 4, 10, 1.25), ("Menu", 58, 4, 11.25, 1.25),
    ("Ctrl", 59, 4, 12.5, 1.25), ("Fn", 60, 4, 13.75, 1.25),
]

NUM_KEYS = len(KEYS)        # 60 physical keys
NUM_SLOTS = 80              # wire length including padding


def as_dicts():
    """Layout for the frontend: list of {id, label, row, x, w}."""
    return [{"id": kid, "label": label, "row": row, "x": x, "w": w}
            for (label, kid, row, x, w) in KEYS]


# ── Actuation array index per key_id ────────────────────────────────────────────
# The Hall-Effect actuation array (protocol 03 96 0d) is a 14-column firmware matrix
# (index = row*14 + column). Rows 0-2 (key_ids 0-40) are identity. Row 2 has only 13
# keys, leaving one matrix column empty, which shifts the whole Shift row up by one.
# Row 4 (bottom) has wide gaps under the spacebar. Confirmed against FGG by setting
# individual keys and reading which array index changed (2026-06-02). This is a
# DIFFERENT index space than the RGB colour slots.
# Every entry below was directly measured against FGG (ruler capture 2026-06-02), not inferred.
_ACT_INDEX_OVERRIDES = {40: 41, 41: 42}                            # Enter->41 (idx40 gap); LShift->42
_ACT_INDEX_OVERRIDES.update({kid: kid + 2 for kid in range(42, 52)})  # Z..slash -> 44..53 (idx43 gap)
_ACT_INDEX_OVERRIDES[52] = 55                                      # Right Shift (idx54 gap)
_ACT_INDEX_OVERRIDES.update({
    53: 56,   # Left Ctrl
    54: 57,   # Left Win
    55: 58,   # Left Alt
    56: 62,   # Space
    57: 66,   # Right Alt
    58: 67,   # Menu
    59: 68,   # Right Ctrl
    60: 69,   # Win Fn
})


def actuation_index(key_id: int) -> int:
    """Map a visual key_id to its index in the firmware actuation array."""
    return _ACT_INDEX_OVERRIDES.get(int(key_id), int(key_id))


# ── (row, column) per key — used by the SOCD/advanced-key protocol ──────────────
# Advanced keys address a key as (physical row 0-4 top..bottom, 0-based column within
# that row). Confirmed against FGG (A+D / S+D / Q+D captures 2026-06-02).
_ROW_FIRST = {}
for (_lbl, _kid, _row, _x, _w) in KEYS:
    if _row not in _ROW_FIRST or _kid < _ROW_FIRST[_row]:
        _ROW_FIRST[_row] = _kid
KEY_RC = {kid: (row, kid - _ROW_FIRST[row]) for (_lbl, kid, row, _x, _w) in KEYS}


def socd_rc(key_id: int):
    """Return (row, column) for a key_id, as the SOCD/advanced-key protocol addresses it."""
    return KEY_RC[int(key_id)]


# Reverse maps for decoding read-back reports from the board.
_RC_KEY = {rc: kid for kid, rc in KEY_RC.items()}
_ACT_KEY_BY_INDEX = {actuation_index(kid): kid for (_l, kid, _r, _x, _w) in KEYS}


def key_from_rc(row: int, col: int):
    """Inverse of socd_rc: (row, col) -> key_id, or None if it isn't a real key."""
    return _RC_KEY.get((int(row), int(col)))


def key_from_actuation_index(index: int):
    """Inverse of actuation_index: firmware array index -> key_id, or None for gap slots."""
    return _ACT_KEY_BY_INDEX.get(int(index))
