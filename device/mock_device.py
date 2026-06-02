"""
Mock backend: same interface as HidBackend, no hardware required.

Lets the whole UI/engine run with no keyboard plugged in. Decodes incoming
color packets back into an 80-slot color array so a simulated render is possible.
"""

from __future__ import annotations

from . import protocol


class MockBackend:
    is_mock = True

    def __init__(self):
        self._open = False
        # Last decoded per-slot colors, so callers can render a simulated board.
        self.slots = [(0, 0, 0)] * protocol.NUM_SLOTS
        self.last_committed = False

    @property
    def connected(self) -> bool:
        return self._open

    @property
    def info(self) -> dict | None:
        if not self._open:
            return None
        return {
            "manufacturer": "MADLIONS (mock)",
            "product": "60% Hall Effect (mock)",
            "interface_number": -1,
            "usage_page": protocol.RGB_USAGE_PAGE,
            "vid": protocol.VID,
            "pid": protocol.PID,
        }

    def open(self):
        self._open = True

    def write(self, data: bytes) -> int:
        if not self._open:
            raise RuntimeError("Mock device is not open.")
        if len(data) >= 6 and data[1] == protocol.REPORT_ID:
            if data[2] == protocol.CMD_SET_COLORS:
                chunk, sub = data[3], data[4]
                base = (chunk * len(protocol.SUB_OFFSETS) + (1 if sub else 0)) * protocol.KEYS_PER_PACKET
                for k in range(protocol.KEYS_PER_PACKET):
                    idx = base + k
                    if 0 <= idx < protocol.NUM_SLOTS:
                        self.slots[idx] = (data[6 + k * 3], data[7 + k * 3], data[8 + k * 3])
            elif data[2] == protocol.CMD_COMMIT:
                self.last_committed = True
        return len(data)

    def read(self, length: int = 64) -> bytes:
        # The mock has no real device to query; reads return nothing so the controller's
        # read_* helpers report "unavailable" and callers keep their in-memory state.
        return b""

    def close(self):
        self._open = False
