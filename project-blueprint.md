# MADLIONS Configurator — Project Blueprint

## Architecture

```
main.py          ← Entry point (CLI --crossfade | GUI via pywebview)
bridge.py        ← pywebview js_api: Python methods exposed to frontend
│
├── device/
│   ├── protocol.py     ← HID report builders (cmd 12/13 for keymap, 07 for RGB, 02/03 for HE)
│   ├── hid_device.py   ← Raw HID I/O, device enumeration (multi-PID support)
│   ├── controller.py   ← Serialized gateway: calibration, lock, send/read
│   └── mock_device.py  ← Mock backend for testing without hardware
│
├── engine/
│   ├── layout.py       ← Keyboard layouts (MAD60 61-key, MAD68 68-key), auto-detection
│   ├── animations.py   ← 15 built-in animations (rainbow, breathing, fire, etc.)
│   ├── animation_runtime.py  ← Daemon thread: render frames, push via controller
│   ├── custom_anim.py  ← Keyframe animation builder (from editor JSON)
│   ├── keymap.py       ← Load/save slot→key mapping (from mapping wizard)
│   ├── profile_store.py ← JSON storage for profiles and custom animations
│   ├── keymap_golden.json   ← Factory-default keymap (112 entries, 105 active)
│   └── keymap_mapping.json  ← Firmware index → visual key_id translation table
│
├── ui/
│   ├── index.html      ← Single-page app shell
│   ├── css/style.css   ← Global styles + KeyMap grid styles
│   └── js/
│       ├── app.js      ← Boot, navigation, shared helpers, idle timer
│       ├── board.js    ← Keyboard renderer (select/paint/keymap modes)
│       ├── color.js    ← HSV <-> RGB, HEX helpers
│       ├── effects.js  ← Built-in animations gallery
│       ├── editor.js   ← Keyframe animation editor (timeline)
│       ├── performance.js ← Hall Effect (actuation, rapid trigger, SOCD)
│       ├── profiles.js ← Profile snapshot/restore
│       ├── settings.js ← White balance, mapping wizard, device info
│       └── keymap.js   ← KeyMap: visual grid, layer selector, remap flow
│
└── tools/
    ├── webhid_beacon.py  ← Local server to capture WebHID writes from browser
    └── webhid_logger.js  ← Console script: intercepts HIDDevice.prototype methods
```

## Key Protocols

### RGB Control (cmd 07)
```
Write: 07 42 [chunk 0-4] [sub 0x00/0x08] [8 keys] [RGB×8]
Commit: 07 41 01 00 90 FF 00 EE D2
```
- 10 packets (5 chunks × 2 subs) per full update
- 80 slots, 8 keys per packet

### Keymap Read (cmd 12)
```
Request:  12 00 [byte_offset] [size 0x0E] 00
Response: 12 00 [byte_offset] [size 0x0E] [7×2 byte codes...]
```
- 7 codes per read (14 bytes), 16 reads for full 112-entry keymap
- Byte offset: `page*0x1C + half*2` (where half is 0 or 7)
- Response codes start at byte 5 of the 32-byte input report

### Keymap Write (cmd 13)
```
Write: 13 00 [byte_offset] [size 0x0E] 00 [7×2 byte codes...]
```
- Same framing as read, mirrored 7+7 split format
- 16 packets total (2 per page × 8 pages)

### HE Config (cmd 02/03 with subcmd 96)
```
Read:  02 96 [opcode] [params...]
Write: 03 96 [opcode] [params...]
```
- Opcodes: 0x0D (actuation), 0x0E (rapid trigger), 0x11 (perf flags), 0x1D (false touch), 0x20 (SOCD)

### Keymap Structure
```
Base layer:  fw[0]  — fw[67]  (68 physical key mappings)
FN1 layer:   fw[68] — fw[87]  (20 entries, specific key subset)
FN2 layer:   fw[88] — fw[99]  (~12 entries)
FN3 layer:   fw[100]—fw[111] (~12 entries)
```

## Firmware Index Mapping

The firmware stores keycodes in matrix order (non-linear relative to visual layout).
Translation is done via `keymap_mapping.json`:

```
fw[0]=Esc, fw[1]=1, ..., fw[12]==, fw[13]=Bksp,
fw[14]=Ins, fw[15]=Tab, fw[16]=Q, ..., fw[27]=],
fw[28]=\, fw[29]=Del, fw[30]=Caps, ..., fw[41]=',
fw[42]=gap(0), fw[43]=Enter, fw[44]=PgUp, fw[45]=LShift,
fw[46]=gap, fw[47]=Z, fw[48]=X, ..., fw[56]=/,
fw[57]=RShift, fw[58]=↑, fw[59]=PgDn, fw[60]=LCtrl,
fw[61]=LWin, fw[62]=LAlt, fw[63-65]=gaps, fw[66]=Space,
fw[67]=gap, fw[68]=gap, fw[69]=RAlt
```

Key gaps (0x0000) at indices 42, 46, 63-65, 67-68 correspond to
firmware matrix positions that don't map to physical keys.

## Idle Timeout Pipeline
```
JS idle timer → set_timeout(30s) → idle_fade_off()
                                    ├── halt animation runtime
                                    ├── crossfade to black (1.5s)
                                    ├── flush kbd events
                                    └── set _idle_off = True

evdev monitor thread → select() on /dev/input/by-path/*kbd
                    → on event + _idle_off: idle_fade_on()
                                    ├── _sync_rgb_on_connect()
                                    └── set _idle_off = False

JS activity events (pointer/key/wheel) → resetIdle() → idle_fade_on()
```

## RGB Sync Pipeline
```
App start → _sync_rgb_on_connect()
          → read ~/.cache/skwd-wall/colors.json
          → HLS transform accent → vibrant LED color
          → send_colors (instant, no crossfade)

Reconnect → auto_connect() → _sync_rgb_on_connect()
Physical reconnect → poll thread (2s) → find_rgb_interface()
                  → auto_connect() → _sync_rgb_on_connect()
```
