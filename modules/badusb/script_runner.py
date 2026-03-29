"""
DuckyScript-inspired payload runner.
Parses .duck files and executes them via HIDDevice.

Supported commands:
  DELAY <ms>           - Wait N milliseconds
  STRING <text>        - Type a string
  ENTER                - Press Enter
  TAB                  - Press Tab
  SPACE                - Press Space
  BACKSPACE            - Press Backspace
  ESC / ESCAPE         - Press Escape
  DELETE               - Press Delete
  UP / DOWN / LEFT / RIGHT  - Arrow keys
  HOME / END / INSERT / PAGEUP / PAGEDOWN
  F1..F12              - Function keys
  GUI <key>            - Windows key + key (e.g. GUI r)
  CTRL <key>           - Ctrl + key
  SHIFT <key>          - Shift + key
  ALT <key>            - Alt + key
  CTRL-ALT <key>       - Ctrl+Alt+key
  CTRL-SHIFT <key>     - Ctrl+Shift+key
  ALT-SHIFT <key>      - Alt+Shift+key
  REM / #              - Comment (ignored)
  REPEAT <n>           - Repeat previous command n times
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

from modules.badusb.hid_device import HIDDevice, MOD_LCTRL, MOD_LSHIFT, MOD_LALT, MOD_LMETA

log = logging.getLogger(__name__)

SIMPLE_KEYS = {
    'ENTER', 'TAB', 'SPACE', 'BACKSPACE', 'ESC', 'ESCAPE',
    'DELETE', 'UP', 'DOWN', 'LEFT', 'RIGHT',
    'HOME', 'END', 'INSERT', 'PAGEUP', 'PAGEDOWN',
    'CAPSLOCK',
    'F1', 'F2', 'F3', 'F4', 'F5', 'F6',
    'F7', 'F8', 'F9', 'F10', 'F11', 'F12',
}


class ScriptRunner:
    def __init__(self, hid: HIDDevice, default_delay_ms: int = 0) -> None:
        self._hid = hid
        self._default_delay = default_delay_ms
        self._last_action: Optional[tuple] = None  # for REPEAT

    def run_file(self, path: str) -> None:
        content = Path(path).read_text(encoding='utf-8')
        self.run_script(content)

    def run_script(self, script: str) -> None:
        lines = script.splitlines()
        for line in lines:
            line = line.strip()
            if not line or line.startswith('REM') or line.startswith('#'):
                continue
            self._execute(line)
            if self._default_delay:
                time.sleep(self._default_delay / 1000.0)

    def _execute(self, line: str) -> None:
        parts = line.split(' ', 1)
        cmd = parts[0].upper()
        arg = parts[1] if len(parts) > 1 else ''

        action = None

        if cmd == 'DELAY':
            ms = int(arg) if arg.isdigit() else 100
            action = ('delay', ms)
            time.sleep(ms / 1000.0)

        elif cmd == 'STRING':
            action = ('string', arg)
            self._hid.type_string(arg)

        elif cmd == 'DEFAULTDELAY' or cmd == 'DEFAULT_DELAY':
            self._default_delay = int(arg) if arg.isdigit() else 0

        elif cmd in SIMPLE_KEYS:
            action = ('key', cmd)
            self._hid.press_key(cmd)

        elif cmd == 'GUI' or cmd == 'WINDOWS':
            action = ('combo', 'GUI', arg)
            self._hid.combo('GUI', arg)

        elif cmd == 'CTRL':
            action = ('combo', 'CTRL', arg)
            self._hid.combo('CTRL', arg)

        elif cmd == 'SHIFT':
            action = ('combo', 'SHIFT', arg)
            self._hid.combo('SHIFT', arg)

        elif cmd == 'ALT':
            action = ('combo', 'ALT', arg)
            self._hid.combo('ALT', arg)

        elif cmd == 'CTRL-ALT':
            action = ('combo', 'CTRL', 'ALT', arg)
            self._hid.combo('CTRL', 'ALT', arg)

        elif cmd == 'CTRL-SHIFT':
            action = ('combo', 'CTRL', 'SHIFT', arg)
            self._hid.combo('CTRL', 'SHIFT', arg)

        elif cmd == 'ALT-SHIFT':
            action = ('combo', 'ALT', 'SHIFT', arg)
            self._hid.combo('ALT', 'SHIFT', arg)

        elif cmd == 'REPEAT':
            count = int(arg) if arg.isdigit() else 1
            for _ in range(count):
                if self._last_action:
                    self._execute_action(self._last_action)
            return  # don't update last_action for REPEAT itself

        else:
            log.warning('Unknown DuckyScript command: %r', cmd)

        if action:
            self._last_action = action

    def _execute_action(self, action: tuple) -> None:
        kind = action[0]
        if kind == 'delay':
            time.sleep(action[1] / 1000.0)
        elif kind == 'string':
            self._hid.type_string(action[1])
        elif kind == 'key':
            self._hid.press_key(action[1])
        elif kind == 'combo':
            self._hid.combo(*action[1:])
