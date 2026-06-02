"""
Data models. Dataclasses serialized to JSON for profiles.

These cover the full feature set from the build plan; only the lighting fields are
wired up in the current phase. HE / keymap fields exist so profiles round-trip cleanly
once Phase 0 captures land, but nothing writes them to the device yet.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional

RGB = tuple  # (int, int, int)


@dataclass
class Binding:
    type: str = "key"            # "key" | "macro" | "layer" | "media"
    value: str = ""
    mod_tap: Optional[str] = None


@dataclass
class Layer:
    name: str = "base"
    bindings: dict = field(default_factory=dict)   # key_id -> Binding


@dataclass
class Keymap:
    layers: list = field(default_factory=lambda: [Layer(name="base"), Layer(name="fn")])


@dataclass
class Frame:
    duration_ms: int = 100
    colors: dict = field(default_factory=dict)     # key_id -> [r,g,b]
    easing: str = "linear"


@dataclass
class Animation:
    id: str = ""
    name: str = ""
    fps: int = 30
    loop: bool = True
    frames: list = field(default_factory=list)     # list[Frame]


@dataclass
class LightingState:
    mode: str = "static"                           # "static" | "animation"
    per_key_colors: dict = field(default_factory=dict)   # key_id -> [r,g,b]
    animation_id: Optional[str] = None
    white_balance: dict = field(default_factory=lambda: {"r": 1.0, "g": 1.0, "b": 1.0})


@dataclass
class RapidTrigger:
    enabled: bool = False
    sensitivity: float = 0.2


@dataclass
class SnapTap:
    enabled: bool = False
    mode: str = "last"                             # "last" | "neutral"
    key_pairs: list = field(default_factory=list)


@dataclass
class HESettings:
    global_actuation: float = 1.5
    rapid_trigger: RapidTrigger = field(default_factory=RapidTrigger)
    snap_tap: SnapTap = field(default_factory=SnapTap)
    per_key_overrides: dict = field(default_factory=dict)


@dataclass
class Profile:
    name: str = "Default"
    keymap: Keymap = field(default_factory=Keymap)
    lighting: LightingState = field(default_factory=LightingState)
    he: HESettings = field(default_factory=HESettings)
    meta: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)
