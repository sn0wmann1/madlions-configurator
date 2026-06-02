"""
Physical-key -> firmware-slot mapping.

The wire protocol addresses 80 slots, but the slot order does NOT match the
left-to-right/top-to-bottom layout (the bottom rows, in particular, live in slots
that were assumed to be padding). The true mapping can only be learned against the
real board, so it is discovered with the in-app mapping wizard and persisted here.

Stored as {key_id: slot}. key_id is the stable on-screen layout index (engine.layout).
Default is identity (key_id == slot) until the wizard saves a real map.
"""

from __future__ import annotations

import json
import os

from . import layout

_MAP_FILE = os.path.join(os.path.expanduser("~"), ".madlions", "key_map.json")


def default_map() -> dict:
    """Identity mapping: every physical key_id points at the same-numbered slot."""
    return {k["id"]: k["id"] for k in layout.as_dicts()}


def load() -> dict:
    """Load the saved {key_id: slot} map, falling back to identity for missing keys."""
    m = default_map()
    try:
        with open(_MAP_FILE) as f:
            saved = json.load(f)
        for k, v in saved.items():
            kid = int(k)
            if kid in m and isinstance(v, int) and 0 <= v < layout.NUM_SLOTS:
                m[kid] = v
    except Exception:
        pass
    return m


def save(mapping: dict):
    """Persist a {key_id: slot} map."""
    os.makedirs(os.path.dirname(_MAP_FILE), exist_ok=True)
    clean = {str(int(k)): int(v) for k, v in mapping.items()}
    with open(_MAP_FILE, "w") as f:
        json.dump(clean, f, indent=2)


def is_mapped() -> bool:
    """True if a non-identity map has been saved (i.e. the wizard has been run)."""
    return os.path.exists(_MAP_FILE)
