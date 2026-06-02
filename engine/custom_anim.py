"""
Custom (keyframe) animation playback.

A custom animation is the `Animation` model: ordered frames, each with a per-key color
map and a duration. Playback walks a real-time clock across the timeline, interpolating
each key's color from the current frame toward the next with an easing curve.

Like the built-ins, the frame function returns a per-key list (length NUM_KEYS, indexed
by key_id); the runtime maps it to slots. Keys absent from a frame are treated as off.
"""

from __future__ import annotations

import time

from . import layout

N = layout.NUM_KEYS
_OFF = (0, 0, 0)


def _ease(frac, kind):
    f = max(0.0, min(1.0, frac))
    if kind == "ease-in":
        return f * f
    if kind == "ease-out":
        return 1 - (1 - f) * (1 - f)
    if kind == "ease-in-out":
        return 3 * f * f - 2 * f * f * f
    return f   # linear / hold handled by caller


def _frame_to_list(colors):
    """Resolve a frame's {key_id: [r,g,b]} map into a length-N per-key list."""
    out = [_OFF] * N
    for k, rgb in colors.items():
        kid = int(k)
        if 0 <= kid < N:
            out[kid] = (int(rgb[0]), int(rgb[1]), int(rgb[2]))
    return out


def _lerp(a, b, f):
    return (
        int(a[0] + (b[0] - a[0]) * f),
        int(a[1] + (b[1] - a[1]) * f),
        int(a[2] + (b[2] - a[2]) * f),
    )


def build(anim: dict, get_speed=lambda: 1.0):
    """
    Build a frame function f(t) -> per-key list for the given Animation dict.

    The runtime's `t` is ignored; playback uses a wall clock scaled by get_speed() so
    frame durations are honored in real milliseconds. Falls back to a static single
    frame when there is only one, and to all-off when there are none.
    """
    frames = anim.get("frames") or []
    loop = anim.get("loop", True)
    if not frames:
        return lambda t: [_OFF] * N

    lists = [_frame_to_list(fr.get("colors", {})) for fr in frames]
    durations = [max(1, int(fr.get("duration_ms", 100))) for fr in frames]
    easings = [fr.get("easing", "linear") for fr in frames]
    total = sum(durations)
    start = time.monotonic()

    if len(frames) == 1:
        only = lists[0]
        return lambda t: only

    def f(t):
        elapsed = (time.monotonic() - start) * 1000.0 * max(0.05, get_speed())
        pos = (elapsed % total) if loop else min(elapsed, total - 0.001)
        # locate the active segment
        acc = 0.0
        for i, dur in enumerate(durations):
            if pos < acc + dur or i == len(durations) - 1:
                local = (pos - acc) / dur
                nxt = (i + 1) % len(lists) if loop else min(i + 1, len(lists) - 1)
                if easings[i] == "hold" or nxt == i:
                    return lists[i]
                fe = _ease(local, easings[i])
                cur, nx = lists[i], lists[nxt]
                return [_lerp(cur[k], nx[k], fe) for k in range(N)]
            acc += dur
        return lists[-1]

    return f
