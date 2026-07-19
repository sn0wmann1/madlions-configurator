"""
MADLIONS keyboard layouts — one map shared by the UI grid, the keymap, and the
lighting. Each entry: (label, key_id, row, x_units, width_units).

Automatic layout selection is NOT implemented yet; the active layout is hard-coded
to MAD68 (68 keys). For MAD60 (61 keys) replace KEYS below.
"""

from __future__ import annotations

KEYS = [
    # Row 0 — number row (15 keys: standard 60% + Ins in right column)
    ("Esc", 0, 0, 0.0, 1), ("1", 1, 0, 1, 1), ("2", 2, 0, 2, 1),
    ("3", 3, 0, 3, 1), ("4", 4, 0, 4, 1), ("5", 5, 0, 5, 1),
    ("6", 6, 0, 6, 1), ("7", 7, 0, 7, 1), ("8", 8, 0, 8, 1),
    ("9", 9, 0, 9, 1), ("0", 10, 0, 10, 1), ("-", 11, 0, 11, 1),
    ("=", 12, 0, 12, 1), ("Bksp", 13, 0, 13, 2),
    ("Ins", 14, 0, 15.75, 1),

    # Row 1 — QWERTY (15 keys: standard + Del)
    ("Tab", 15, 1, 0, 1.5),
    ("Q", 16, 1, 1.5, 1), ("W", 17, 1, 2.5, 1), ("E", 18, 1, 3.5, 1),
    ("R", 19, 1, 4.5, 1), ("T", 20, 1, 5.5, 1), ("Y", 21, 1, 6.5, 1),
    ("U", 22, 1, 7.5, 1), ("I", 23, 1, 8.5, 1), ("O", 24, 1, 9.5, 1),
    ("P", 25, 1, 10.5, 1), ("[", 26, 1, 11.5, 1), ("]", 27, 1, 12.5, 1),
    ("\\", 28, 1, 13.5, 1.5),
    ("Del", 29, 1, 15.75, 1),

    # Row 2 — home row (14 keys: standard + PgUp)
    ("Caps", 30, 2, 0, 1.75),
    ("A", 31, 2, 1.75, 1), ("S", 32, 2, 2.75, 1), ("D", 33, 2, 3.75, 1),
    ("F", 34, 2, 4.75, 1), ("G", 35, 2, 5.75, 1), ("H", 36, 2, 6.75, 1),
    ("J", 37, 2, 7.75, 1), ("K", 38, 2, 8.75, 1), ("L", 39, 2, 9.75, 1),
    (";", 40, 2, 10.75, 1), ("'", 41, 2, 11.75, 1),
    ("Enter", 42, 2, 12.75, 2.25),
    ("PgUp", 43, 2, 15.75, 1),

    # Row 3 — shift row (14 keys: standard, RShift shortened, + ↑ / PgDn)
    ("Shift", 44, 3, 0, 2.25),
    ("Z", 45, 3, 2.25, 1), ("X", 46, 3, 3.25, 1), ("C", 47, 3, 4.25, 1),
    ("V", 48, 3, 5.25, 1), ("B", 49, 3, 6.25, 1), ("N", 50, 3, 7.25, 1),
    ("M", 51, 3, 8.25, 1), (",", 52, 3, 9.25, 1), (".", 53, 3, 10.25, 1),
    ("/", 54, 3, 11.25, 1), ("Shift", 55, 3, 12.25, 1.75),
    ("↑", 56, 3, 14, 1),
    ("PgDn", 57, 3, 15.75, 1),

    # Row 4 — bottom row (10 keys: 3 mods left, space, 3 mods right, 3 arrows)
    ("Ctrl", 58, 4, 0, 1.25), ("Win", 59, 4, 1.25, 1.25),
    ("Alt", 60, 4, 2.5, 1.25),
    ("Space", 61, 4, 3.75, 6.25),
    ("Alt", 62, 4, 10, 1.25), ("Fn", 63, 4, 11.25, 1.25),
    ("Ctrl", 64, 4, 12.5, 1.25),
    ("←", 65, 4, 13.75, 1), ("↓", 66, 4, 14.75, 1), ("→", 67, 4, 15.75, 1),
]

NUM_KEYS = len(KEYS)        # 68 physical keys
NUM_SLOTS = 80              # wire length including padding


def as_dicts():
    """Layout for the frontend: list of {id, label, row, x, w}."""
    return [{"id": kid, "label": label, "row": row, "x": x, "w": w}
            for (label, kid, row, x, w) in KEYS]


# ── Actuation array index per key_id ────────────────────────────────────────────
# TODO: measure these on real MAD68 hardware via FGG like the MAD60 mappings below.
# For now all keys use identity mapping (actuation_index(key_id) == key_id), which
# means Hall-Effect actuation / rapid-trigger read-back will NOT match the firmware
# matrix. The RGB pipeline is unaffected.
_ACT_INDEX_OVERRIDES = {}


def actuation_index(key_id: int) -> int:
    """Map a visual key_id to its index in the firmware actuation array."""
    return _ACT_INDEX_OVERRIDES.get(int(key_id), int(key_id))


# ── (row, column) per key — used by the SOCD/advanced-key protocol ──────────────
# Advanced keys address a key as (physical row 0-4 top..bottom, 0-based column within
# that row). Computed automatically from the visual layout; this is approximate and
# SHOULD be confirmed against real hardware captures before relying on SOCD writes.
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
