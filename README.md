# MADLIONS 60 Configurator

A desktop app to fully configure the **MADLIONS 60% Hall Effect** keyboard — per-key RGB,
animations (built-in and your own), Hall-Effect performance tuning, and profiles — without the
official web app.

It talks to the keyboard directly over USB HID (userspace, no drivers, no admin), and reads the
board's current state back so the UI reflects what's actually stored on the device.

> Not affiliated with or endorsed by MADLIONS. Built by observing the keyboard's own HID protocol
> for interoperability; no vendor code is included. Use at your own risk (see the disclaimer below).

## Features

- **Lighting** — per-key colour with a live picker, swatches, brightness, and a guided
  **white-balance** calibrator (floods the board white and tunes R/G/B live).
- **Effects** — 15 built-in animations plus any custom ones you make.
- **Editor** — paint your own keyframe animations on a timeline: drag-to-paint, click-to-toggle,
  per-frame hold/easing (with an accurate in-app preview), multi-frame select for bulk edits,
  undo/redo, and continuous autosave.
- **Performance (Hall Effect)** — per-key actuation depth, rapid trigger, performance toggles
  (Swap WASD / Win-lock / Mac / NKRO / false-touch), and **SOCD / snap-tap** (e.g. A+D for
  strafing). All read back from the board on open.
- **Profiles** — snapshot and restore complete looks (lighting, white balance, and more).
- **Key-mapping wizard** — the firmware's slot order is not the visual order; map it once per board.
- **Minimize to tray** — closing the window keeps animations streaming (the app keeps running in
  the system tray, like Discord/Steam); quit fully from the tray menu.

## Supported hardware

- MADLIONS 60% Hall Effect keyboard (USB VID `0x373B`, PID `0x1054`).

Everything has been verified against one physical unit. A different firmware revision of the same
model will very likely work, but the per-key index maps were measured on real hardware — if
something looks off, run the key-mapping wizard and re-check.

> Key remap / Fn-layer / macros are intentionally **not** implemented here — set those in the
> official FGG web app. They live in the keyboard's onboard flash and this app never writes that
> region, so they coexist with the colours and Hall-Effect settings configured here.

## Requirements

- Python 3.11+
- Windows (primary target; uses the Edge WebView2 runtime, preinstalled on Windows 10/11)

Install dependencies:

```
pip install -r requirements.txt
```

## Running

```
python main.py
```

or double-click **`MADLIONS.bat`** (use `MADLIONS-debug.bat` to see a console for troubleshooting).

If `hidapi` can't open the device on Windows, you may need to assign the WinUSB driver to the
RGB/config interface with [Zadig](https://zadig.akeo.ie/).

## First-time setup

1. **Key mapping** (Settings > "run mapping wizard") — teaches the app your board's slot order so
   per-key control is correct. Saved to `~/.madlions/`.
2. **White balance** (Settings > "calibrate white") — if white looks teal/pink, tune R/G/B until
   it reads neutral. Note: balanced white is dimmer than full blast, which is a property of the
   LEDs, not a bug.

User data (calibration, key map, profiles, custom animations, editor autosave) lives in
`~/.madlions/`.

## Building a standalone .exe

A PyInstaller spec is included. Build with:

```
pip install pyinstaller
pyinstaller madlions.spec
```

The one-file executable is written to `dist/MADLIONS60.exe`. It bundles the web frontend, the
`hidapi` native library, the pywebview WebView2 loader, and the tray icon; the target machine
still needs the Edge WebView2 runtime (preinstalled on Windows 10/11).

## Project layout

```
device/    HID protocol + connect/read/write (the only layer that builds report bytes)
engine/    models, animation runtime, profile/animation storage, layout
ui/        web frontend (HTML/CSS/JS) served in a pywebview window
bridge.py  pywebview js_api: the methods the frontend calls into Python
main.py    wires it together, single-instance + tray
```

## License

Licensed under the **PolyForm Noncommercial License 1.0.0** — see [`LICENSE`](LICENSE). You may
use, modify, and share it for any **noncommercial** purpose (personal use, hobby projects,
research, education, etc.). Commercial use — including selling it or charging for it — is not
permitted. Keep the copyright notice in any copies.

## Disclaimer

Not affiliated with, endorsed by, or supported by MADLIONS. Provided "as is", without warranty of
any kind; the author is not liable for any damage or loss arising from its use.

This app only sends **documented configuration reports** (lighting and Hall-Effect settings) to the
keyboard. It never writes firmware, bootloader, or flash regions, so it cannot brick the device the
way a bad firmware flash could — the worst case is wrong settings, which you can change back here or
in the vendor software. Even so, use it at your own risk.
