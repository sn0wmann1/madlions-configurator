"""
Profile + custom-animation persistence as JSON on disk.

Profiles and custom animations live under a per-user data dir so they survive a
PyInstaller-frozen install. Built-in animations are code (engine/animations.py);
only user-saved custom animations are stored here.
"""

from __future__ import annotations

import json
import os

_APP_DIR = os.path.join(os.path.expanduser("~"), ".madlions")
_PROFILE_DIR = os.path.join(_APP_DIR, "profiles")
_ANIM_DIR = os.path.join(_APP_DIR, "animations")
_DRAFT_FILE = os.path.join(_APP_DIR, "editor_draft.json")


def _ensure_dirs():
    os.makedirs(_PROFILE_DIR, exist_ok=True)
    os.makedirs(_ANIM_DIR, exist_ok=True)


def _safe_name(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_ " else "_" for c in name).strip() or "untitled"


def list_profiles():
    _ensure_dirs()
    return [os.path.splitext(f)[0] for f in os.listdir(_PROFILE_DIR) if f.endswith(".json")]


def save_profile(name: str, data: dict):
    _ensure_dirs()
    with open(os.path.join(_PROFILE_DIR, f"{_safe_name(name)}.json"), "w") as f:
        json.dump(data, f, indent=2)


def load_profile(name: str) -> dict:
    with open(os.path.join(_PROFILE_DIR, f"{_safe_name(name)}.json")) as f:
        return json.load(f)


def list_animations():
    _ensure_dirs()
    return [os.path.splitext(f)[0] for f in os.listdir(_ANIM_DIR) if f.endswith(".json")]


def save_animation(name: str, data: dict):
    _ensure_dirs()
    with open(os.path.join(_ANIM_DIR, f"{_safe_name(name)}.json"), "w") as f:
        json.dump(data, f, indent=2)


def load_animation(name: str) -> dict:
    with open(os.path.join(_ANIM_DIR, f"{_safe_name(name)}.json")) as f:
        return json.load(f)


# ── Editor draft (autosave) ──────────────────────────────────────────────────────
# The editor continuously persists its working animation here so unsaved frame-by-frame
# work survives a crash, power loss, or accidental close.
def save_draft(data: dict):
    os.makedirs(_APP_DIR, exist_ok=True)
    with open(_DRAFT_FILE, "w") as f:
        json.dump(data, f)


def load_draft():
    try:
        with open(_DRAFT_FILE) as f:
            return json.load(f)
    except Exception:
        return None
