# MADLIONS Configurator — Project Progress & Completed Features

> Fork of [MemoryHazy313/madlions-configurator](https://github.com/MemoryHazy313/madlions-configurator) adding MAD68 support, keymap editing, and Linux/Wayland improvements.

---

## 🛠️ 1. HID Protocol Reverse-Engineering

| Protocol | Read Command | Write Command | Status |
|---|---|---|---|
| RGB Lighting | `07 42` + `07 41` commit | Same | Confirmed working |
| Keymap | `12 00 [offset] 0x0E` (7-code sub-reads) | `13 00 [offset] 0x0E` (7+7 split) | Confirmed working |
| HE Config (actuation/RT/SOCD/perf) | `02 96 [opcode]` | `03 96 [opcode]` | Confirmed working |
| Macros | `0c`/`0d`/`0e`/`0f` | Unknown | Read understood, write needs capture |
| FN Layers | Stored at fw[68-111] | `13 00` (same write) | Mapping partially discovered |

---

## 📐 2. Implementation Checklist

### [x] Phase 1: Core Fork Setup
- [x] Fork from MemoryHazy313/madlions-configurator
- [x] MAD68 PID (0x1058) added to device enumeration
- [x] 68-key layout with pixel-accurate positions from MAD68 Pro reference
- [x] Auto-detect MAD60 (0x1054) vs MAD68 (0x1058) from device PID
- [x] Dynamic layout switching based on detected model
- [x] Window title shows detected model (60/68)

### [x] Phase 2: Keymap Protocol
- [x] Capture keymap read/write from hub.f.gg WebHID traffic
- [x] Implement 7-code sub-read format (no 14th code truncation)
- [x] Implement 7+7 split write format (covers all 112 entries)
- [x] Build 88-entry HID keycode lookup table
- [x] Firmware-to-visual key mapping via golden template
- [x] Golden template: save factory-default keymap from web UI factory reset
- [x] `get_keymap()` returns codes at correct visual positions
- [x] `set_keymap({key_id: hid_code})` — partial remap with visual→firmware translation
- [x] `reset_key(key_id)` — restore single key from golden template
- [x] `reset_keymap_all()` — restore base layer (0-67), preserve FN layers (68+)

### [x] Phase 3: KeyMap UI
- [x] New KeyMap tab with keyboard layout + visual key grid
- [x] 7-row clickable key grid (F-keys, QWERTY, numpad, media) matching web UI
- [x] Color-coded keys: media (green), modifiers (amber)
- [x] Layer dropdown (Normal/FN1/FN2/FN3) below keyboard preview
- [x] Auto-refresh on layer change
- [x] Click keyboard key → click grid key → instant remap
- [x] Reset selected key / reset all to factory defaults
- [x] Click-only selection (no drag-select in KeyMap mode)

### [x] Phase 4: RGB Subsystem
- [x] Smooth crossfade transitions (0.5s smoothstep) for `set_all()` / `set_key_colors()`
- [x] Auto-RGB sync on app startup (reads wallpaper accent from `colors.json`)
- [x] Auto-reconnect detection (poll `find_rgb_interface()` every 2s)
- [x] RGB sync on reconnect (startup + re-scan button + auto-reconnect)
- [x] Idle timeout: fade RGB to off after configurable N seconds
- [x] Keypress wake: monitor `/dev/input/by-path/*kbd` via evdev/select
- [x] Fullscreen detection: skip idle fade when Hyprland window is fullscreen
- [x] CLI mode: `python main.py --crossfade RRGGBB` for wallpaper sync scripts
- [x] MAD68 fade speed synced with OpenRGB (30ms/frame, was 100ms)

### [x] Phase 5: Linux/Wayland Support
- [x] Qt6 backend for pywebview (fixes GTK/Gdk crash on Hyprland)
- [x] Pre-init Qt before HID/socket/animation threads
- [x] `.desktop` launcher in `~/.local/share/applications/`
- [x] Launcher script in `~/.local/bin/madlions-configurator`

### [ ] Phase 6: FN Layers & Macros
- [ ] FN layer write support — mapping partially discovered, untested
- [ ] Macro write protocol — needs desktop driver HID capture
- [ ] FN layer UI: show bindings per key on layer switch (like web UI)

### [ ] Phase 7: Boot/Wallpaper Sync (Dotfiles)
- [x] `fade-rgb.py`: OpenRGB retry logic (5 attempts with 1s delay)
- [x] `fade-rgb.py`: remove dedup check — always fade on sync
- [x] `fade-rgb.py`: instant set on boot, crossfade on wallpaper change
- [x] `wall-reset.sh`: always force-sync, removed `last_synced_accent` check
- [x] `hyprland.conf`: remove duplicate `openrgb --server` exec-once
- [ ] Govee BLE daemon — persistent connection, currently unstable

---

## 🔧 3. Protocol Bugs Fixed

| Bug | Root Cause | Fix |
|---|---|---|
| 14th code truncated in keymap read | HID IN report limited to 32 bytes | 7-code sub-read format (2 reads per page) |
| 14th code missing in keymap write | 13 codes per write doesn't cover 14 | 7+7 split writes (7 codes per packet) |
| Keymap writes zeroed FN layers | `reset_keymap_all` wrote all 112 entries | Preserve indices 68+ from current state |
| Stale keymap read | `auto_connect()` needed before each read | Reconnect in `_read_keymap_raw()` |
| Idle self-wake | Crossfade HID writes trigger input events | Flush kbd events after fade, set flag last |

---

## 📊 Known Issues

- FN layer writes not reliable — use hub.f.gg web UI for FN bindings
- Chrome DevTools MCP steals OC CLI focus (Brave/Hyprland compositor behavior)
- Govee BLE daemon timing out on initial connect (BT adapter state)
- Right-side keyboard layout spacing needs refinement
