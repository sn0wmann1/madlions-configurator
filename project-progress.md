# MADLIONS Configurator — Project Progress

## 2026-07-19 — Fork & Foundation

### HID Protocol Reverse-Engineering
- [x] Capture keymap read/write protocol from hub.f.gg WebHID traffic
  - Read command: `12 00 [offset] [0x1c]` — 14 codes per page, 8 pages
  - Write command: `13 00 [byte_offset] [0x0E]` — 7 codes per half-page
- [x] Capture macro read protocol (`0c`/`0d`/`0e`/`0f` commands)
- [x] Build 88-entry HID keycode lookup table
- [x] Discover firmware-to-visual key mapping (non-linear, via golden template)

### Layout & Model Detection
- [x] Create 68-key MAD68 layout from MAD68 Pro reference (pixel-accurate positions)
- [x] Add MAD60 layout (61 keys) for fallback support
- [x] Auto-detect MAD60 (PID 0x1054) vs MAD68 (PID 0x1058) from device enumeration
- [x] Dynamic layout switching based on detected model
- [x] Window title reflects detected model

### Keymap System
- [x] 7-code sub-read format — reads all 112 entries without 14th code truncation
- [x] 7+7 split writes — 16 packets cover all 112 entries
- [x] Firmware-to-visual key mapping via golden template comparison
- [x] Golden template: factory-default keymap saved from web UI factory reset
- [x] `get_keymap()` returns codes at correct visual positions
- [x] `set_keymap({key_id: hid_code})` — partial remap with visual→firmware translation
- [x] `reset_key(key_id)` — restore single key from golden template
- [x] `reset_keymap_all()` — restore base layer (indices 0-67), preserve FN layers
- [ ] FN layer write support — mapping partially discovered, untested
- [ ] Macro write protocol — needs desktop driver HID capture

### RGB Subsystem
- [x] Crossfade transitions (0.5s smoothstep) for `set_all()` / `set_key_colors()`
- [x] Auto-RGB sync on app startup (reads wallpaper accent from `colors.json`)
- [x] Auto-reconnect detection (poll `find_rgb_interface()` every 2s)
- [x] RGB sync on reconnect (app startup + re-scan button + auto-reconnect)
- [x] Idle timeout: fade RGB to off after configurable N seconds of inactivity
- [x] Keypress wake: monitor `/dev/input/by-path/*kbd` via evdev/select
- [x] Fullscreen detection: skip idle fade when Hyprland window is fullscreen
- [x] CLI mode: `python main.py --crossfade RRGGBB` for wallpaper sync scripts

### GUI / Platform
- [x] Qt6 backend for Linux/Wayland (fixes GTK/Gdk crash on Hyprland)
- [x] Pre-init Qt backend before HID/socket/animation threads
- [x] `.desktop` launcher in `~/.local/share/applications/`
- [x] Launcher script in `~/.local/bin/madlions-configurator`

### KeyMap UI
- [x] New KeyMap tab with keyboard layout + clickable key grid
- [x] 7-row visual key grid (F-keys, QWERTY, numpad, media) matching web UI
- [x] Layer dropdown (Normal/FN1/FN2/FN3) below keyboard preview
- [x] Auto-refresh on layer change
- [x] Color-coded grid keys (media=green, modifiers=amber)
- [x] Click keyboard key → click grid key → instant remap
- [x] Reset selected key / reset all to factory defaults

### Boot / Wallpaper Sync (Dotfiles)
- [x] `fade-rgb.py`: OpenRGB retry logic (5 attempts with 1s delay)
- [x] `fade-rgb.py`: remove dedup check — always fade on sync
- [x] `fade-rgb.py`: instant set on boot, crossfade on wallpaper change
- [x] `wall-reset.sh`: always force-sync, removed `last_synced_accent` check
- [x] `hyprland.conf`: remove duplicate `openrgb --server` exec-once
- [x] MAD68 fade speed synced with OpenRGB (30ms/frame, was 100ms)
- [x] Govee BLE daemon + socket client (persistent connection, near-instant sync)

## 2026-07-20 — Stabilization & Polish

### Protocol Fixes
- [x] 14th code truncation bug fixed — 7-code sub-reads discover all entries
- [x] `reset_keymap_all` zeroed all FN layers — fixed to preserve indices 68+
- [x] `set_keymap` read-fallback bug — zeroes entire keymap on empty read

### RGB Idle Timeline
- [x] v1: JS-based idle timer (window-events only)
- [x] v2: Added fullscreen detection via Hyprland IPC
- [x] v3: Self-wake from HID crossfade writes fixed (flush + flag after fade)
- [x] v4: Physical keypress wake via evdev monitor (works unfocused)

### Keymap Iterator
- [x] v1: Legacy 13-code read (14th code truncated)
- [x] v2: 14th-code trailing byte hack (broken, wrong offset)
- [x] v3: 7-code sub-read format (correct, no truncation)
- [x] v4: 7+7 split write format (covers all 112 entries)

## Known Issues
- FN layer writes not reliable — use hub.f.gg web UI for FN bindings
- Chrome DevTools MCP steals OC CLI focus (Brave/Hyprland compositor behavior)
- Govee BLE daemon timing out on initial connect (BT adapter state)
- Keymap read `auto_connect()` needed before each read (stale backend)
