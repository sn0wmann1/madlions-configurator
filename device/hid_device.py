"""
Real HID backend: connect/disconnect and raw report writes to the keyboard.

Backends only do raw HID I/O and enumeration. They never build report bytes
(that is protocol.py) and never serialize writes (that is the controller).
"""

from __future__ import annotations

import hid

from . import protocol


class DeviceNotFound(RuntimeError):
    pass


def enumerate_interfaces():
    """Return all HID interfaces for supported keyboard models (all PIDs)."""
    devs = []
    for pid in protocol.SUPPORTED_PIDS:
        devs.extend(hid.enumerate(protocol.VID, pid))
    return devs


def find_rgb_interface():
    """Return the descriptor of the RGB-control interface, or None if absent."""
    for dev in enumerate_interfaces():
        if dev.get("usage_page") == protocol.RGB_USAGE_PAGE:
            return dev
    return None


class HidBackend:
    """Holds a persistent open handle to the RGB interface."""

    is_mock = False

    def __init__(self):
        self._h = None
        self._info = None

    @property
    def connected(self) -> bool:
        return self._h is not None

    @property
    def info(self) -> dict | None:
        return self._info

    def open(self):
        """Open the RGB interface. Raises DeviceNotFound if it isn't present/openable."""
        if self._h is not None:
            return
        dev = find_rgb_interface()
        if dev is None:
            raise DeviceNotFound(
                f"MADLIONS keyboard RGB interface not found "
                f"(VID={protocol.VID:04x} PID={protocol.PID:04x} "
                f"usage_page={protocol.RGB_USAGE_PAGE:04x})."
            )
        h = hid.device()
        h.open_path(dev["path"])
        h.set_nonblocking(1)
        self._h = h
        self._info = {
            "manufacturer": dev.get("manufacturer_string"),
            "product": dev.get("product_string"),
            "interface_number": dev.get("interface_number"),
            "usage_page": dev.get("usage_page"),
            "vid": dev.get("vendor_id", protocol.VID),
            "pid": dev.get("product_id", protocol.PID),
        }

    def write(self, data: bytes) -> int:
        if self._h is None:
            raise DeviceNotFound("Device is not open.")
        return self._h.write(data)

    def read(self, length: int = 64) -> bytes:
        """Non-blocking read of one input report (the handle is opened non-blocking).

        Returns the raw report bytes (no hidapi prefix for report id 0) or b'' if nothing
        is queued. The controller polls this after sending a read request.
        """
        if self._h is None:
            raise DeviceNotFound("Device is not open.")
        data = self._h.read(length)
        return bytes(data) if data else b""

    def close(self):
        if self._h is not None:
            try:
                self._h.close()
            finally:
                self._h = None
                self._info = None
