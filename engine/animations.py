"""
Built-in animations, ported from the v3 tkinter GUI.

Each builder returns a frame function `f(t) -> list[(r,g,b)]` of length NUM_SLOTS.
Builders take `get_color()` returning the current base RGB so the live color slider
keeps affecting a running animation, exactly like the old GUI.

These are pure render functions — they never touch the device. The runtime pushes
their output through DeviceController (which applies brightness/calibration per frame).
"""

from __future__ import annotations

import colorsys
import math
import random

from . import layout

# Animations render in physical reading order (key_id 0..N-1), NOT firmware slot order.
# The runtime maps each key_id to its real slot before sending, so effects are spatially
# correct and gap-free regardless of the scrambled hardware matrix order.
N = layout.NUM_KEYS   # 61 physical keys


def _hsv(h, s, v):
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return int(r * 255), int(g * 255), int(b * 255)


def rainbow(get_color):
    def f(t):
        return [_hsv((i / N + t * 0.25) % 1, 1, 1) for i in range(N)]
    return f


def breathing(get_color):
    def f(t):
        r, g, b = get_color()
        br = (math.sin(t * 2) + 1) / 2
        return [(int(r * br), int(g * br), int(b * br))] * N
    return f


def color_cycle(get_color):
    def f(t):
        return [_hsv(t * 0.1 % 1, 1, 1)] * N
    return f


def strobe(get_color):
    def f(t):
        r, g, b = get_color()
        c = (r, g, b) if int(t * 8) % 2 == 0 else (0, 0, 0)
        return [c] * N
    return f


def ripple(get_color):
    def f(t):
        r, g, b = get_color()
        out = []
        for i in range(N):
            br = max(0.0, math.sin(t * 5 - i * 0.35))
            out.append((int(r * br), int(g * br), int(b * br)))
        return out
    return f


def fire(get_color):
    heat = [0.0] * N
    ignite_start = N - 8   # bottom row (last 8 keys in reading order) ignites
    def f(t):
        for i in range(ignite_start, N):
            heat[i] = min(1.0, heat[i] + random.random() * 0.6)
        new = heat[:]
        for i in range(1, ignite_start):
            new[i] = (heat[i] * 0.4 + heat[i + 1] * 0.45 + heat[i - 1] * 0.05) * 0.985
        new[0] = (heat[0] * 0.4 + heat[1] * 0.45) * 0.985
        heat[:] = new
        r, g, b = get_color()
        if r == 0 and g == 0 and b == 0:
            r, g, b = 255, 80, 0
        out = []
        for h in heat:
            if h < 0.3:
                s = h / 0.3
                out.append((int(r * s * 0.6), int(g * s * 0.3), int(b * s * 0.3)))
            elif h < 0.7:
                s = (h - 0.3) / 0.4
                out.append((int(r * (0.6 + s * 0.4)),
                            int(g * (0.3 + s * 0.5)),
                            int(b * (0.3 + s * 0.3))))
            else:
                s = (h - 0.7) / 0.3
                out.append((min(255, int(r + (255 - r) * s * 0.8)),
                            min(255, int(g + (255 - g) * s * 0.7)),
                            min(255, int(b + (255 - b) * s * 0.5))))
        return out
    return f


def sparkle(get_color):
    sparks = [0.0] * N
    def f(t):
        r, g, b = get_color()
        dim = (r // 8, g // 8, b // 8)
        for i in range(N):
            sparks[i] = 1.0 if random.random() < 0.04 else max(0.0, sparks[i] - 0.07)
        return [(int(r * s), int(g * s), int(b * s)) if s > 0.05 else dim for s in sparks]
    return f


def matrix(get_color):
    cr, cg, cb = get_color()
    if cr == 0 and cg == 0 and cb == 0:
        cr, cg, cb = 0, 255, 0
    positions = [random.uniform(0, N) for _ in range(8)]
    speeds = [random.uniform(0.4, 1.0) for _ in range(8)]
    trail = 14
    last_t = [0.0]
    def f(t):
        dt = max(0.0, min(t - last_t[0], 0.5))
        last_t[0] = t
        for ci in range(len(positions)):
            positions[ci] = (positions[ci] + speeds[ci] * dt * 15) % N
        bmap = [0.0] * N
        cmap = [(0, 0, 0)] * N
        for ci in range(len(positions)):
            head = int(positions[ci])
            for tr in range(trail):
                idx = (head - tr) % N
                br = max(0.0, 1.0 - tr / trail)
                if tr == 0:
                    col = (min(255, cr + int((255 - cr) * 0.75)),
                           min(255, cg + int((255 - cg) * 0.75)),
                           min(255, cb + int((255 - cb) * 0.75)))
                else:
                    col = (int(cr * br), int(cg * br), int(cb * br))
                if br > bmap[idx]:
                    bmap[idx] = br
                    cmap[idx] = col
        return cmap
    return f


def plasma(get_color):
    def f(t):
        out = []
        for i in range(N):
            v = (math.sin(i * 0.3 + t * 1.5) +
                 math.sin(i * 0.15 - t * 1.1) +
                 math.sin(i * 0.6 + t * 0.7)) / 3.0
            out.append(_hsv((v + 1) / 2, 1.0, 1.0))
        return out
    return f


def wave_sweep(get_color):
    def f(t):
        r, g, b = get_color()
        center = (t * 12) % (N + 20) - 10
        width = 8
        out = []
        for i in range(N):
            br = max(0.0, 1.0 - abs(i - center) / width)
            out.append((int(r * br), int(g * br), int(b * br)))
        return out
    return f


def comet(get_color):
    tail = 20
    def f(t):
        r, g, b = get_color()
        head = (t * 20) % N
        out = []
        for i in range(N):
            behind = (head - i) % N
            if behind == 0:
                out.append((min(255, r + 60), min(255, g + 60), min(255, b + 60)))
            elif behind < tail:
                decay = math.exp(-behind / 6.0)
                out.append((int(r * decay), int(g * decay), int(b * decay)))
            else:
                out.append((0, 0, 0))
        return out
    return f


def heartbeat(get_color):
    def pulse(t):
        phase = math.fmod(t * 0.8, 1.0)
        p1 = math.exp(-((phase) ** 2) / 0.002)
        p2 = math.exp(-((phase - 0.18) ** 2) / 0.003) * 0.6
        return min(1.0, p1 + p2)
    def f(t):
        r, g, b = get_color()
        br = pulse(t)
        return [(int(r * br), int(g * br), int(b * br))] * N
    return f


def glitch_noise(get_color):
    def f(t):
        r, g, b = get_color()
        out = []
        for i in range(N):
            n = math.sin(i * 127.1 + t * 311.7) * math.sin(i * 269.5 - t * 183.3)
            br = (n + 1) / 2
            out.append((int(r * br), int(g * br), int(b * br)))
        return out
    return f


def aurora(get_color):
    def f(t):
        out = []
        for i in range(N):
            h1 = (math.sin(i * 0.08 + t * 0.3) + 1) / 2
            h2 = (math.sin(i * 0.05 - t * 0.2 + 1.5) + 1) / 2
            blend = (math.sin(i * 0.12 + t * 0.15) + 1) / 2
            hue = h1 * (1 - blend) + (h2 * 0.75 + 0.55) * blend
            sat = 0.6 + 0.4 * (math.sin(i * 0.2 + t * 0.4) + 1) / 2
            val = 0.7 + 0.3 * (math.sin(i * 0.07 - t * 0.25) + 1) / 2
            out.append(_hsv(hue % 1.0, sat, val))
        return out
    return f


def ember_drift(get_color):
    glow = [random.random() * 0.3 for _ in range(N)]
    def f(t):
        r, g, b = get_color()
        for i in range(N):
            if random.random() < 0.06:
                glow[i] = min(1.0, glow[i] + random.uniform(0.4, 1.0))
        new = glow[:]
        for i in range(N):
            spread = 0.0
            if i > 0:
                spread += glow[i - 1] * 0.18
            if i < N - 1:
                spread += glow[i + 1] * 0.18
            new[i] = glow[i] * 0.92 + spread
        glow[:] = new
        return [(int(r * g2), int(g * g2), int(b * g2)) for g2 in glow]
    return f


def crossfade(get_color):
    def f(t):
        r, g, b = get_color()
        hue = (t * 0.04) % 1.0
        tr, tg, tb = _hsv(hue, 0.8, 1.0)
        out = []
        for i in range(N):
            phase = (math.sin(i * 0.2 + t * 0.8) + 1) / 2
            out.append((
                int(r + (tr - r) * phase),
                int(g + (tg - g) * phase),
                int(b + (tb - b) * phase),
            ))
        return out
    return f


# name -> builder. Order is the display order in the UI.
BUILDERS = {
    "Rainbow wave": rainbow,
    "Breathing": breathing,
    "Color cycle": color_cycle,
    "Strobe": strobe,
    "Ripple": ripple,
    "Fire": fire,
    "Sparkle": sparkle,
    "Matrix": matrix,
    "Plasma": plasma,
    "Wave sweep": wave_sweep,
    "Comet": comet,
    "Heartbeat": heartbeat,
    "Glitch noise": glitch_noise,
    "Aurora": aurora,
    "Ember drift": ember_drift,
    "Crossfade": crossfade,
}


def names():
    return list(BUILDERS.keys())
