"""
Keyboard HID protocol — the ONLY module that constructs raw report bytes.

Each builder is annotated CONFIRMED (verified against the real keyboard) or GUESSED.
Nothing in ui/ or engine/ may build device bytes; they go through device.controller,
which calls into here.
"""

from __future__ import annotations

# ── Device identity (CONFIRMED) ────────────────────────────────────────────────
VID = 0x373B
PID = 0x1054          # MADLIONS 60%
PID_MAD68 = 0x1058    # MADLIONS 68%
SUPPORTED_PIDS = (PID, PID_MAD68)
RGB_USAGE_PAGE = 0xFF60   # the RGB-control interface enumerates with this usage page

# ── Geometry ────────────────────────────────────────────────────────────────────
NUM_SLOTS = 80            # 0..59 physical keys, 60..79 padding (always black)
KEYS_PER_PACKET = 8
NUM_CHUNKS = 5
SUB_OFFSETS = (0x00, 0x08)

# ── Report framing (CONFIRMED) ──────────────────────────────────────────────────
REPORT_LEN = 33           # 1 hidapi prefix byte + 32 payload bytes
REPORT_ID = 0x07
CMD_SET_COLORS = 0x42
CMD_COMMIT = 0x41

RGB = tuple  # (int, int, int)


def _clamp8(v: int) -> int:
    return 0 if v < 0 else 255 if v > 255 else int(v)


def build_color_packets(slots):
    """
    Build the 10 set-color packets for an 80-slot color list.

    `slots` is an iterable of (r, g, b). It is padded with black / truncated to
    exactly NUM_SLOTS. Returns a list of 10 `bytes` objects, in send order.
    Colors must already be calibrated/brightness-adjusted by the caller.
    """
    padded = (list(slots) + [(0, 0, 0)] * NUM_SLOTS)[:NUM_SLOTS]
    packets = []
    idx = 0
    for chunk in range(NUM_CHUNKS):
        for sub in SUB_OFFSETS:
            pkt = bytearray(REPORT_LEN)
            pkt[0] = 0x00            # hidapi report-ID prefix
            pkt[1] = REPORT_ID
            pkt[2] = CMD_SET_COLORS
            pkt[3] = chunk
            pkt[4] = sub
            pkt[5] = KEYS_PER_PACKET
            for k in range(KEYS_PER_PACKET):
                r, g, b = padded[idx]
                pkt[6 + k * 3] = _clamp8(r)
                pkt[7 + k * 3] = _clamp8(g)
                pkt[8 + k * 3] = _clamp8(b)
                idx += 1
            packets.append(bytes(pkt))
    return packets


def build_commit_packet():
    """Build the commit/apply packet sent once after the color packets."""
    pkt = bytearray(REPORT_LEN)
    pkt[0] = 0x00
    pkt[1] = REPORT_ID
    pkt[2] = CMD_COMMIT
    pkt[3] = 0x01
    pkt[5] = 0x90
    pkt[6] = 0xFF
    pkt[8] = 0xEE
    pkt[9] = 0xD2
    return bytes(pkt)


# ── Performance flags — CONFIRMED (FGG WebHID capture 2026-06-02) ──────────────
# Two single-report commands. 03 96 11 carries four global flags; 03 96 1d is the
# False-touch-prevention toggle. (FGG follows each with a 02 96 13 read-back we skip.)
OP_PERF_FLAGS = 0x11
OP_FALSE_TOUCH = 0x1D


def build_perf_flags(swap_wasd=False, mac=False, win_lock=False, six_key=False):
    """03 96 11: Swap WASD / MAC / Win lock / rollover. six_key=True -> 6-key (byte=0), else NKRO (1)."""
    pkt = bytearray(REPORT_LEN)
    pkt[1] = CMD_CONFIG
    pkt[2] = SUBCMD_HE
    pkt[3] = OP_PERF_FLAGS
    pkt[5] = 1 if swap_wasd else 0
    pkt[6] = 1 if mac else 0
    pkt[7] = 1 if win_lock else 0
    pkt[8] = 0 if six_key else 1
    return bytes(pkt)


def build_false_touch(enabled=True):
    """03 96 1d: False touch prevention mode."""
    pkt = bytearray(REPORT_LEN)
    pkt[1] = CMD_CONFIG
    pkt[2] = SUBCMD_HE
    pkt[3] = OP_FALSE_TOUCH
    pkt[4] = 1 if enabled else 0
    return bytes(pkt)


# ── Advanced key: SOCD (snap-tap) — CONFIRMED (FGG WebHID capture 2026-06-02) ──
# Command 03 96 20, one report per binding slot. Keys addressed as (row, col).
OP_ADV_KEY = 0x20
SOCD_LAST_INPUT = 0x02       # last-key-wins (snap-tap / null-bind, for strafing)
SOCD_ABS_KEY1 = 0x03         # key1 always wins
SOCD_ABS_KEY2 = 0x04         # key2 always wins
SOCD_NEUTRAL = 0x05          # both -> neither
SOCD_TRAVEL_DEFAULT = 354    # what FGG sends when "quick trigger" is off (3.54mm)


def build_socd(key1_rc, key2_rc, mode=SOCD_LAST_INPUT, travel_raw=50,
               quick_trigger=True, slot=0):
    """
    Build one SOCD ("Sappy Tnappy") binding report. key1_rc/key2_rc are (row, col)
    tuples (see engine.layout.socd_rc). mode is one of SOCD_*. quick_trigger enables
    the rapid-trigger travel (travel_raw, 0.01mm); when off, FGG sends travel 354.
    Byte-identical to FGG for the captured A+D / S+D / Q+D / W+S cases.
    """
    k1r, k1c = key1_rc
    k2r, k2c = key2_rc
    travel = travel_raw if quick_trigger else SOCD_TRAVEL_DEFAULT
    pkt = bytearray(REPORT_LEN)
    pkt[1] = CMD_CONFIG          # 03
    pkt[2] = SUBCMD_HE           # 96
    pkt[3] = OP_ADV_KEY          # 20
    # data[3] (pkt[4]) is constant 0; the binding slot lives in data[6] AND data[8].
    pkt[6] = 0x03                # data[5] — constant
    pkt[7] = slot & 0xFF         # data[6] binding slot
    pkt[8] = mode & 0xFF         # data[7]
    pkt[9] = slot & 0xFF         # data[8] binding slot (mirror)
    pkt[10] = (travel >> 8) & 0xFF   # data[9]  travel hi
    pkt[11] = travel & 0xFF          # data[10] travel lo
    pkt[13] = 0x01 if quick_trigger else 0x00   # data[12] quick-trigger enable
    pkt[14] = k1r & 0xFF         # data[13] key1 row
    pkt[15] = k1c & 0xFF         # data[14] key1 col
    pkt[16] = k2r & 0xFF         # data[15] key2 row
    pkt[17] = k2c & 0xFF         # data[16] key2 col
    return bytes(pkt)


def build_socd_clear(slot=0):
    """Clear (delete) the SOCD binding at a slot — zero params, slot in data[6]/data[8]."""
    pkt = bytearray(REPORT_LEN)
    pkt[1] = CMD_CONFIG
    pkt[2] = SUBCMD_HE
    pkt[3] = OP_ADV_KEY
    pkt[6] = 0x03
    pkt[7] = slot & 0xFF     # data[6] slot
    pkt[9] = slot & 0xFF     # data[8] slot
    return bytes(pkt)


# ============================================================================
# Key remapping protocol — CAPTURED from hub.f.gg WebHID traffic (2026-07-19)
# Command 12 00: reads/writes the onboard keymap (112 entries, 2B HID usage codes
# LE, in 28-byte pages of 14 codes each). The write variant uses the same framing
# with non-zero payload (inferred — the web app only reads; writes are done by the
# desktop driver, but the protocol is expected to mirror the read format).
# ============================================================================

CMD_KEYMAP = 0x12
KEYMAP_PAGE_SIZE = 0x1C          # 28 bytes per page
KEYMAP_ENTRIES_PER_PAGE = 14     # 14 × 2-byte HID usage codes per page
KEYMAP_WRITE_CODES = 13          # HID OUT report fits 13 codes (26B) + 6B header = 32B
KEYMAP_TOTAL_ENTRIES = 112       # covers all layers (Normal + FN1/FN2/FN3)
KEYMAP_TOTAL_PAGES = KEYMAP_TOTAL_ENTRIES // KEYMAP_ENTRIES_PER_PAGE  # 8

CMD_MACRO_COUNT = 0x0C           # read: response byte 1 = number of macro slots (16)
CMD_MACRO_INFO = 0x0D            # read macro metadata
CMD_MACRO_PAGE = 0x0E            # read macro pages (0x1c byte chunks)
CMD_MACRO_PAGE2 = 0x0F           # another macro read variant

# Standard HID keyboard usage codes (selection — full table in HID Usage Tables spec)
HID_KEYCODES = {
    # Letters
    "A": 0x04, "B": 0x05, "C": 0x06, "D": 0x07, "E": 0x08, "F": 0x09, "G": 0x0A,
    "H": 0x0B, "I": 0x0C, "J": 0x0D, "K": 0x0E, "L": 0x0F, "M": 0x10, "N": 0x11,
    "O": 0x12, "P": 0x13, "Q": 0x14, "R": 0x15, "S": 0x16, "T": 0x17, "U": 0x18,
    "V": 0x19, "W": 0x1A, "X": 0x1B, "Y": 0x1C, "Z": 0x1D,
    # Numbers
    "1": 0x1E, "2": 0x1F, "3": 0x20, "4": 0x21, "5": 0x22,
    "6": 0x23, "7": 0x24, "8": 0x25, "9": 0x26, "0": 0x27,
    # Modifiers / special
    "Enter": 0x28, "Esc": 0x29, "Bksp": 0x2A, "Tab": 0x2B, "Space": 0x2C,
    "-": 0x2D, "=": 0x2E, "[": 0x2F, "]": 0x30, "\\": 0x31,
    ";": 0x33, "'": 0x34, "`": 0x35, ",": 0x36, ".": 0x37, "/": 0x38,
    "Caps": 0x39, "F1": 0x3A, "F2": 0x3B, "F3": 0x3C, "F4": 0x3D,
    "F5": 0x3E, "F6": 0x3F, "F7": 0x40, "F8": 0x41, "F9": 0x42,
    "F10": 0x43, "F11": 0x44, "F12": 0x45,
    "PrtSc": 0x46, "ScrLk": 0x47, "Pause": 0x48,
    "Ins": 0x49, "Home": 0x4A, "PgUp": 0x4B, "Del": 0x4C,
    "End": 0x4D, "PgDn": 0x4E, "→": 0x4F, "←": 0x50, "↓": 0x51, "↑": 0x52,
    # System (modifier keys)
    "LCtrl": 0xE0, "LShift": 0xE1, "LAlt": 0xE2, "LWin": 0xE3,
    "RCtrl": 0xE4, "RShift": 0xE5, "RAlt": 0xE6, "RWin": 0xE7,
    "Menu": 0x65, "Fn": 0xFF,  # Fn is internal, not standard HID
}

# Reverse map
HID_CODE_TO_KEY = {v: k for k, v in HID_KEYCODES.items()}


def keycode_from_name(name: str) -> int:
    """Return the HID usage code for a key name, or None if unknown."""
    return HID_KEYCODES.get(name)


def key_name_from_code(code: int) -> str | None:
    """Return the key name for a HID usage code, or None."""
    return HID_CODE_TO_KEY.get(code)


def build_keymap_read(offset: int) -> bytes:
    """Build a keymap page read request at *offset* (0, 0x1c, ..., 0xc4)."""
    pkt = bytearray(REPORT_LEN)
    pkt[1] = CMD_KEYMAP           # 12
    pkt[2] = 0x00                 # sub
    pkt[3] = offset & 0xFF        # offset (single byte, pages every 0x1c)
    pkt[4] = KEYMAP_PAGE_SIZE     # 0x1c
    pkt[5] = 0x00                 # reserved
    return bytes(pkt)


def parse_keymap_page(resp: bytes) -> list[int]:
    """Parse a keymap read response into a list of 14 HID usage codes.
    Returns empty list if the response isn't a valid keymap page."""
    if not resp or len(resp) < 7 or resp[0] != CMD_KEYMAP or resp[3] != KEYMAP_PAGE_SIZE:
        return []
    codes = []
    for k in range(KEYMAP_ENTRIES_PER_PAGE):
        b = 5 + k * 2
        if b + 1 < len(resp):
            codes.append(resp[b] | (resp[b + 1] << 8))
    return codes


def build_keymap_write(offset: int, codes: list[int]) -> bytes:
    """Build a keymap page write. Inferred from read response format.
    Writes up to 13 codes (26 bytes) to fit in the 33-byte HID OUT report."""
    pkt = bytearray(REPORT_LEN)
    pkt[1] = CMD_KEYMAP           # 12
    pkt[2] = 0x00                 # sub
    pkt[3] = offset & 0xFF        # offset
    pkt[4] = KEYMAP_PAGE_SIZE     # 0x1c
    pkt[5] = 0x00                 # reserved
    for k in range(min(KEYMAP_WRITE_CODES, len(codes))):
        code = codes[k] & 0xFFFF
        pkt[6 + k * 2] = code & 0xFF
        pkt[7 + k * 2] = (code >> 8) & 0xFF
    return bytes(pkt)


# ── Macros — CAPTURED (read only, writes inferred) ──────────────────────────
MACRO_COUNT = 16
MACRO_PAGE_SIZE = 0x1C


def build_macro_count_read() -> bytes:
    pkt = bytearray(REPORT_LEN)
    pkt[1] = CMD_MACRO_COUNT      # 0c
    return bytes(pkt)


def build_macro_info_read() -> bytes:
    pkt = bytearray(REPORT_LEN)
    pkt[1] = CMD_MACRO_INFO       # 0d
    return bytes(pkt)


def build_macro_page_read(offset: int) -> bytes:
    pkt = bytearray(REPORT_LEN)
    pkt[1] = CMD_MACRO_PAGE       # 0e
    pkt[3] = offset & 0xFF
    pkt[4] = (offset >> 8) & 0xFF
    pkt[5] = MACRO_PAGE_SIZE      # 0x1c
    return bytes(pkt)


# ── Actuation point — CONFIRMED (decoded from captured WebHID traffic) ──
ACTUATION_DEFAULT_RAW = 354        # 3.54 mm, FGG per-key default
ACTUATION_SLOTS = 77               # indices 0..76
ACTUATION_REAL = 70                # 0..69 carry depths; 70..76 are zero padding
_ACT_STARTS = (0, 11, 22, 33, 44, 55, 66)
ACT_MIN_MM, ACT_MAX_MM = 0.1, 3.54
CMD_CONFIG = 0x03
SUBCMD_HE = 0x96
OP_ACTUATION = 0x0D


def mm_to_raw(mm: float) -> int:
    """Actuation depth in mm -> raw 0.01mm units, clamped to the device range."""
    mm = max(ACT_MIN_MM, min(ACT_MAX_MM, float(mm)))
    return int(round(mm * 100))


def raw_to_mm(raw: int) -> float:
    return round(raw / 100.0, 2)


def build_actuation_packets(depths_raw: dict):
    """
    Build the 7-chunk per-key actuation write, byte-identical to what FGG sends.

    `depths_raw` maps key index (visual reading order, 0..) -> raw depth (0.01mm units).
    Real keys not listed default to 354 (3.54mm); slots 70..76 are zero. Returns 7 reports
    (33 bytes each, hidapi report-0 prefixed). The final chunk's flag (0x02) applies the change.
    """
    arr = [ACTUATION_DEFAULT_RAW] * ACTUATION_REAL + [0] * (ACTUATION_SLOTS - ACTUATION_REAL)
    for idx, val in depths_raw.items():
        if 0 <= int(idx) < ACTUATION_SLOTS:
            arr[int(idx)] = int(val)

    packets = []
    last = len(_ACT_STARTS) - 1
    for ci, start in enumerate(_ACT_STARTS):
        flag = 0x01 if ci == 0 else (0x02 if ci == last else 0x00)
        pkt = bytearray(REPORT_LEN)
        pkt[0] = 0x00            # hidapi report-number prefix (report id 0)
        pkt[1] = CMD_CONFIG
        pkt[2] = SUBCMD_HE
        pkt[3] = OP_ACTUATION
        pkt[7] = start
        pkt[8] = 0x0b            # 11 entries per chunk
        pkt[9] = flag
        for k in range(11):
            idx = start + k
            v = arr[idx] if idx < ACTUATION_SLOTS else 0
            pkt[10 + k * 2] = (v >> 8) & 0xFF
            pkt[11 + k * 2] = v & 0xFF
        packets.append(bytes(pkt))
    return packets


# ── Rapid trigger — CONFIRMED (FGG WebHID capture 2026-06-02) ──────────────────
# Command 03 96 0e. 18 chunks, 4 entries/chunk, indices 0..71 (same key matrix as
# actuation). Each entry is 5 bytes: enable(1) + reset_travel(2 BE) + rapid_travel(2 BE),
# travels in 0.01 mm. Per-key default = 01 00 32 00 32 (on, 0.50, 0.50). Last chunk applies.
OP_RAPID_TRIGGER = 0x0E
RT_SLOTS = 72
RT_KEY_REGION = 70           # 0..69 carry entries; 70,71 are zero
_RT_STARTS = tuple(range(0, RT_SLOTS, 4))   # 0,4,...,68  -> 18 chunks
RT_DEFAULT = (1, 50, 50)     # enable, reset(0.50), rapid(0.50)


def build_rapid_trigger_packets(per_index: dict):
    """
    Build the 18-chunk rapid-trigger write (byte-identical to FGG).

    `per_index` maps actuation/key index -> (enable, reset_raw, rapid_raw) where the
    travels are raw 0.01mm units. Real-key region (0..69) defaults to RT_DEFAULT; slots
    70,71 are zero. Returns 18 reports (33 bytes each, report-0 prefixed).
    """
    arr = [RT_DEFAULT if i < RT_KEY_REGION else (0, 0, 0) for i in range(RT_SLOTS)]
    for idx, entry in per_index.items():
        if 0 <= int(idx) < RT_SLOTS:
            en, reset, rapid = entry
            arr[int(idx)] = (int(en) & 0xFF, int(reset), int(rapid))

    packets = []
    last = len(_RT_STARTS) - 1
    for ci, start in enumerate(_RT_STARTS):
        flag = 0x01 if ci == 0 else (0x02 if ci == last else 0x00)
        pkt = bytearray(REPORT_LEN)
        pkt[0] = 0x00
        pkt[1] = CMD_CONFIG
        pkt[2] = SUBCMD_HE
        pkt[3] = OP_RAPID_TRIGGER
        pkt[7] = start
        pkt[8] = 0x04
        pkt[9] = flag
        for e in range(4):
            en, reset, rapid = arr[start + e]
            b = 10 + e * 5
            pkt[b] = en & 0xFF
            pkt[b + 1] = (reset >> 8) & 0xFF
            pkt[b + 2] = reset & 0xFF
            pkt[b + 3] = (rapid >> 8) & 0xFF
            pkt[b + 4] = rapid & 0xFF
        packets.append(bytes(pkt))
    return packets


# ── Read-back (CONFIRMED, FGG replug capture 2026-06-02) ──────────────────────────
# Reading uses the SAME opcode as writing but with the leading command byte 0x02 (read)
# instead of 0x03 (write/config). The host sends the chunk/slot header with a zero payload
# and the board replies with an input report carrying the same header + the stored data.
# (Read requests carry zeros, so the reply is never an echo — unlike 0x03 writes, which the
# board echoes back verbatim as an ACK.)
CMD_READ = 0x02

# How many advanced-key (SOCD) slots the firmware exposes; FGG reads 0..19.
SOCD_READ_SLOTS = 20
# Read chunking differs slightly from writes: actuation reads 12 entries/chunk over 6 chunks.
_ACT_READ_STARTS = (0x00, 0x0c, 0x18, 0x24, 0x30, 0x3c)
_ACT_READ_COUNT = 0x0c


def _read_pkt(opcode):
    pkt = bytearray(REPORT_LEN)
    pkt[1] = CMD_READ
    pkt[2] = SUBCMD_HE
    pkt[3] = opcode
    return pkt


def build_actuation_read(start):
    pkt = _read_pkt(OP_ACTUATION)
    pkt[7] = start & 0xFF
    pkt[8] = _ACT_READ_COUNT
    return bytes(pkt)


def build_rapid_trigger_read(start):
    pkt = _read_pkt(OP_RAPID_TRIGGER)
    pkt[7] = start & 0xFF
    pkt[8] = 0x04
    return bytes(pkt)


def build_perf_read():
    return bytes(_read_pkt(OP_PERF_FLAGS))


def build_false_touch_read():
    return bytes(_read_pkt(OP_FALSE_TOUCH))


def build_socd_read(slot):
    pkt = _read_pkt(OP_ADV_KEY)
    pkt[6] = 0x01            # data[5] — constant for SOCD reads
    pkt[7] = slot & 0xFF     # data[6] slot
    pkt[9] = slot & 0xFF     # data[8] slot
    return bytes(pkt)


def _resp_data(resp):
    """A read response is the raw input report (no hidapi prefix): data[0]=0x02, [1]=0x96, ..."""
    return resp if resp else b""


def is_read_response(resp, opcode):
    d = _resp_data(resp)
    return len(d) >= 3 and d[0] == CMD_READ and d[1] == SUBCMD_HE and d[2] == opcode


def parse_actuation_chunk(resp):
    """-> {array_index: raw} for one actuation read response, or {} if not parseable.

    NOTE: read responses have NO flag byte (unlike writes); entries begin right after the
    start+count header at data[8]. Confirmed against the FGG replug capture.
    """
    d = _resp_data(resp)
    if not is_read_response(d, OP_ACTUATION):
        return {}
    start, count = d[6], d[7]
    out = {}
    for k in range(count):
        b = 8 + k * 2
        if b + 1 < len(d):
            out[start + k] = (d[b] << 8) | d[b + 1]
    return out


def parse_rapid_trigger_chunk(resp):
    """-> {array_index: (enable, reset_raw, rapid_raw)} for one RT read response.

    Like actuation reads, entries begin at data[8] (no flag byte).
    """
    d = _resp_data(resp)
    if not is_read_response(d, OP_RAPID_TRIGGER):
        return {}
    start, count = d[6], d[7]
    out = {}
    for e in range(count):
        b = 8 + e * 5
        if b + 4 < len(d):
            out[start + e] = (d[b], (d[b + 1] << 8) | d[b + 2], (d[b + 3] << 8) | d[b + 4])
    return out


def parse_perf(resp):
    """-> {swap_wasd, mac, win_lock, six_key} from a 02 96 11 response, or None."""
    d = _resp_data(resp)
    if not is_read_response(d, OP_PERF_FLAGS):
        return None
    return {
        "swap_wasd": bool(d[4]),
        "mac": bool(d[5]),
        "win_lock": bool(d[6]),
        "six_key": d[7] == 0,     # rollover byte: 1 = NKRO, 0 = 6-key
    }


def parse_false_touch(resp):
    """-> bool false-touch enabled, from a 02 96 1d response, or None."""
    d = _resp_data(resp)
    if not is_read_response(d, OP_FALSE_TOUCH):
        return None
    return bool(d[3])


def parse_socd(resp):
    """
    Parse one 02 96 20 slot response.
    -> {slot, mode, travel_raw, quick_trigger, key1_rc, key2_rc} for a populated slot,
       or {"slot": n, "empty": True} for an empty/cleared slot, or None if not a SOCD response.
    """
    d = _resp_data(resp)
    if not is_read_response(d, OP_ADV_KEY):
        return None
    slot = d[6]
    mode = d[7]
    k1r, k1c, k2r, k2c = d[13], d[14], d[15], d[16]
    empty = (mode == 0) or (k1r == 0xFF) or (k1r == 0 and k1c == 0 and k2r == 0 and k2c == 0)
    if empty:
        return {"slot": slot, "empty": True}
    return {
        "slot": slot,
        "mode": mode,
        "travel_raw": (d[9] << 8) | d[10],
        "quick_trigger": bool(d[12]),
        "key1_rc": (k1r, k1c),
        "key2_rc": (k2r, k2c),
    }


def build_snap_tap(enabled, mode, key_pair):
    """Alias for build_socd. Kept for compatibility."""
    raise NotImplementedError("Use build_socd / build_socd_clear instead")


def build_macro(key_id, macro):
    """TODO: implement macro write protocol (captured reads only so far)."""
    raise NotImplementedError("Macro write protocol not yet implemented")


def build_onboard_save():
    """TODO: implement onboard flash save command."""
    raise NotImplementedError("Onboard save protocol not yet implemented")
