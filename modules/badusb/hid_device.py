"""
USB HID keyboard emulation via Linux gadget (/dev/hidg0).
Requires the dwc2 + libcomposite kernel gadget to be configured (see setup.sh).
Writes 8-byte HID keyboard reports directly to the character device.
"""
from __future__ import annotations

import logging
import struct
import time

log = logging.getLogger(__name__)

# HID modifier bitmask values
MOD_NONE    = 0x00
MOD_LCTRL   = 0x01
MOD_LSHIFT  = 0x02
MOD_LALT    = 0x04
MOD_LMETA   = 0x08   # Windows/Super key
MOD_RCTRL   = 0x10
MOD_RSHIFT  = 0x20
MOD_RALT    = 0x40
MOD_RMETA   = 0x80

# Selected HID keycodes (US layout subset)
KEYCODES: dict[str, int] = {
    'NONE': 0x00, 'A': 0x04, 'B': 0x05, 'C': 0x06, 'D': 0x07,
    'E': 0x08, 'F': 0x09, 'G': 0x0A, 'H': 0x0B, 'I': 0x0C,
    'J': 0x0D, 'K': 0x0E, 'L': 0x0F, 'M': 0x10, 'N': 0x11,
    'O': 0x12, 'P': 0x13, 'Q': 0x14, 'R': 0x15, 'S': 0x16,
    'T': 0x17, 'U': 0x18, 'V': 0x19, 'W': 0x1A, 'X': 0x1B,
    'Y': 0x1C, 'Z': 0x1D,
    '1': 0x1E, '2': 0x1F, '3': 0x20, '4': 0x21, '5': 0x22,
    '6': 0x23, '7': 0x24, '8': 0x25, '9': 0x26, '0': 0x27,
    'ENTER': 0x28, 'ESC': 0x29, 'BACKSPACE': 0x2A, 'TAB': 0x2B,
    'SPACE': 0x2C, 'MINUS': 0x2D, 'EQUAL': 0x2E,
    'LEFTBRACE': 0x2F, 'RIGHTBRACE': 0x30,
    'BACKSLASH': 0x31, 'SEMICOLON': 0x33, 'APOSTROPHE': 0x34,
    'GRAVE': 0x35, 'COMMA': 0x36, 'DOT': 0x37, 'SLASH': 0x38,
    'CAPSLOCK': 0x39,
    'F1': 0x3A, 'F2': 0x3B, 'F3': 0x3C, 'F4': 0x3D, 'F5': 0x3E,
    'F6': 0x3F, 'F7': 0x40, 'F8': 0x41, 'F9': 0x42, 'F10': 0x43,
    'F11': 0x44, 'F12': 0x45,
    'INSERT': 0x49, 'HOME': 0x4A, 'PAGEUP': 0x4B,
    'DELETE': 0x4C, 'END': 0x4D, 'PAGEDOWN': 0x4E,
    'RIGHT': 0x4F, 'LEFT': 0x50, 'DOWN': 0x51, 'UP': 0x52,
    'GUI': 0xE3,   # Windows key (Left GUI)
    'CTRL': 0xE0, 'SHIFT': 0xE1, 'ALT': 0xE2,
}

# Characters requiring SHIFT on US layout
SHIFT_CHARS = '!@#$%^&*()_+{}|:"<>?~ABCDEFGHIJKLMNOPQRSTUVWXYZ'

CHAR_MAP: dict[str, tuple[int, int]] = {}

for _c, _k in [
    (' ', 'SPACE'), ('\n', 'ENTER'), ('\t', 'TAB'),
    ('a', 'A'), ('b', 'B'), ('c', 'C'), ('d', 'D'), ('e', 'E'),
    ('f', 'F'), ('g', 'G'), ('h', 'H'), ('i', 'I'), ('j', 'J'),
    ('k', 'K'), ('l', 'L'), ('m', 'M'), ('n', 'N'), ('o', 'O'),
    ('p', 'P'), ('q', 'Q'), ('r', 'R'), ('s', 'S'), ('t', 'T'),
    ('u', 'U'), ('v', 'V'), ('w', 'W'), ('x', 'X'), ('y', 'Y'),
    ('z', 'Z'),
    ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'),
    ('6', '6'), ('7', '7'), ('8', '8'), ('9', '9'), ('0', '0'),
    ('-', 'MINUS'), ('=', 'EQUAL'), ('[', 'LEFTBRACE'), (']', 'RIGHTBRACE'),
    ('\\', 'BACKSLASH'), (';', 'SEMICOLON'), ("'", 'APOSTROPHE'),
    ('`', 'GRAVE'), (',', 'COMMA'), ('.', 'DOT'), ('/', 'SLASH'),
]:
    CHAR_MAP[_c] = (MOD_NONE, KEYCODES[_k])

for _c, _k in [
    ('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D'), ('E', 'E'),
    ('F', 'F'), ('G', 'G'), ('H', 'H'), ('I', 'I'), ('J', 'J'),
    ('K', 'K'), ('L', 'L'), ('M', 'M'), ('N', 'N'), ('O', 'O'),
    ('P', 'P'), ('Q', 'Q'), ('R', 'R'), ('S', 'S'), ('T', 'T'),
    ('U', 'U'), ('V', 'V'), ('W', 'W'), ('X', 'X'), ('Y', 'Y'),
    ('Z', 'Z'),
    ('!', '1'), ('@', '2'), ('#', '3'), ('$', '4'), ('%', '5'),
    ('^', '6'), ('&', '7'), ('*', '8'), ('(', '9'), (')', '0'),
    ('_', 'MINUS'), ('+', 'EQUAL'), ('{', 'LEFTBRACE'), ('}', 'RIGHTBRACE'),
    ('|', 'BACKSLASH'), (':', 'SEMICOLON'), ('"', 'APOSTROPHE'),
    ('~', 'GRAVE'), ('<', 'COMMA'), ('>', 'DOT'), ('?', 'SLASH'),
]:
    CHAR_MAP[_c] = (MOD_LSHIFT, KEYCODES[_k])


class HIDDevice:
    def __init__(self, device_path: str = '/dev/hidg0') -> None:
        self._path = device_path
        self._fd = None

    def open(self) -> None:
        try:
            self._fd = open(self._path, 'wb', buffering=0)
            log.info('HID device opened: %s', self._path)
        except FileNotFoundError:
            raise FileNotFoundError(
                f'{self._path} not found.\n'
                'Run setup.sh first to configure the USB HID gadget.\n'
                'Requires Raspberry Pi Zero 2W with OTG cable.'
            )
        except PermissionError:
            raise PermissionError(
                f'Permission denied on {self._path}. Run as root or add udev rule.'
            )

    def close(self) -> None:
        if self._fd:
            self._fd.close()
            self._fd = None

    def _send_report(self, modifier: int, keycode: int) -> None:
        report = struct.pack('8B', modifier, 0, keycode, 0, 0, 0, 0, 0)
        self._fd.write(report)

    def _key_up(self) -> None:
        self._send_report(0, 0)

    def press_key(self, key: str, modifier: int = MOD_NONE) -> None:
        code = KEYCODES.get(key.upper(), 0)
        self._send_report(modifier, code)
        time.sleep(0.005)
        self._key_up()
        time.sleep(0.005)

    def type_string(self, text: str, delay_ms: int = 50) -> None:
        for ch in text:
            if ch in CHAR_MAP:
                mod, code = CHAR_MAP[ch]
                self._send_report(mod, code)
                time.sleep(delay_ms / 1000.0)
                self._key_up()
                time.sleep(delay_ms / 1000.0)
            else:
                log.debug('No keycode mapping for character: %r', ch)

    def combo(self, *keys: str) -> None:
        """Press multiple keys simultaneously (e.g. Ctrl+Alt+Del)."""
        modifier = MOD_NONE
        keycodes = []
        for key in keys:
            k = key.upper()
            if k in ('CTRL', 'LCTRL'):
                modifier |= MOD_LCTRL
            elif k in ('SHIFT', 'LSHIFT'):
                modifier |= MOD_LSHIFT
            elif k in ('ALT', 'LALT'):
                modifier |= MOD_LALT
            elif k in ('GUI', 'WIN', 'LMETA'):
                modifier |= MOD_LMETA
            else:
                keycodes.append(KEYCODES.get(k, 0))

        report = [modifier, 0] + keycodes[:6] + [0] * max(0, 6 - len(keycodes))
        self._fd.write(struct.pack('8B', *report[:8]))
        time.sleep(0.01)
        self._key_up()
