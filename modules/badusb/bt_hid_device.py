"""
Bluetooth HID keyboard emulation for PiFlip Bad USB (wireless mode).

The Pi Zero 2W advertises itself as a Bluetooth keyboard, pairs with
the target device, then sends the same 8-byte HID reports as the wired
USB mode — so all existing payloads and DuckyScript work unchanged.

How it works:
  1. hciconfig makes the adapter discoverable + pairable
  2. L2CAP server sockets open on PSM 17 (control) and PSM 19 (interrupt)
  3. sdptool registers a HID keyboard SDP record so the target sees a keyboard
  4. Target connects → PiFlip sends 0xA1 HID INPUT reports over the interrupt channel

BlueZ config needed (done once by setup.sh):
  /etc/bluetooth/main.conf → Class = 0x000540   (keyboard device class)
  bluetoothd must run WITHOUT --noplugin=input  (default is fine)
"""
from __future__ import annotations

import logging
import socket
import struct
import subprocess
import time
from typing import Optional, Tuple

from modules.badusb.hid_device import (
    KEYCODES, CHAR_MAP,
    MOD_NONE, MOD_LCTRL, MOD_LSHIFT, MOD_LALT, MOD_LMETA,
)

log = logging.getLogger(__name__)

# L2CAP PSMs defined by the HID spec
HID_CTRL_PSM = 0x0011   # 17  — control channel
HID_INTR_PSM = 0x0013   # 19  — interrupt channel (where keystrokes go)

# Bluetooth HID INPUT report header byte
BT_HID_INPUT = 0xA1


class BTHIDDevice:
    """
    Bluetooth HID keyboard. Same interface as HIDDevice so ScriptRunner
    works with both wired USB and wireless BT without changes.
    """

    def __init__(self, adapter: str = 'hci0',
                 device_name: str = 'PiFlip Keyboard'):
        self._adapter = adapter
        self._name    = device_name
        self._ctrl_server: Optional[socket.socket] = None
        self._intr_server: Optional[socket.socket] = None
        self._ctrl_conn:   Optional[socket.socket] = None
        self._intr_conn:   Optional[socket.socket] = None
        self.connected = False

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------

    def _configure_adapter(self):
        """Put the adapter into discoverable + pairable keyboard mode."""
        cmds = [
            ['hciconfig', self._adapter, 'up'],
            ['hciconfig', self._adapter, 'piscan'],      # discoverable + connectable
            ['hciconfig', self._adapter, 'name', self._name],
            # 0x000540 = Major class: Peripheral, Minor: Keyboard
            ['hciconfig', self._adapter, 'class', '0x000540'],
        ]
        for cmd in cmds:
            result = subprocess.run(cmd, capture_output=True)
            if result.returncode != 0:
                log.warning('BT cmd failed: %s → %s', cmd, result.stderr.decode())

        # Make bluetoothctl pairable
        subprocess.run(
            ['bluetoothctl'],
            input=b'pairable on\ndiscoverable on\nquit\n',
            capture_output=True,
        )

    def _register_sdp(self):
        """Register HID keyboard SDP record via sdptool."""
        subprocess.run(['sdptool', 'del', '0x00010001'], capture_output=True)
        result = subprocess.run(
            ['sdptool', 'add', '--handle=0x00010001', 'HID'],
            capture_output=True,
        )
        if result.returncode != 0:
            log.warning('sdptool failed (continuing anyway): %s',
                        result.stderr.decode().strip())

    def _open_servers(self):
        """Open L2CAP server sockets for HID control + interrupt channels."""
        for s in [self._ctrl_server, self._intr_server]:
            if s:
                try:
                    s.close()
                except Exception:
                    pass

        self._ctrl_server = socket.socket(
            socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET, socket.BTPROTO_L2CAP)
        self._ctrl_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._ctrl_server.bind(('', HID_CTRL_PSM))
        self._ctrl_server.listen(1)

        self._intr_server = socket.socket(
            socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET, socket.BTPROTO_L2CAP)
        self._intr_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._intr_server.bind(('', HID_INTR_PSM))
        self._intr_server.listen(1)

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def advertise(self):
        """Configure adapter and open sockets. Call before wait_for_connection()."""
        self._configure_adapter()
        self._register_sdp()
        self._open_servers()
        log.info('BT HID keyboard advertising as "%s"', self._name)

    def wait_for_connection(self, timeout: int = 60) -> bool:
        """
        Block until a host connects on both channels, or timeout expires.
        Returns True on success.
        """
        self._ctrl_server.settimeout(timeout)
        self._intr_server.settimeout(timeout)
        try:
            log.info('Waiting for BT HID connection (timeout=%ds)...', timeout)
            self._ctrl_conn, addr = self._ctrl_server.accept()
            log.info('HID control channel connected from %s', addr)
            self._intr_conn, addr = self._intr_server.accept()
            log.info('HID interrupt channel connected from %s', addr)
            self.connected = True
            return True
        except socket.timeout:
            log.warning('BT HID connection timed out')
            return False
        except Exception as exc:
            log.error('BT HID connection error: %s', exc)
            return False

    def open(self):
        """Convenience: advertise + wait_for_connection (default 60s timeout)."""
        self.advertise()
        if not self.wait_for_connection(60):
            raise ConnectionError(
                'No Bluetooth host connected within 60 seconds.\n'
                'Make sure target device has Bluetooth on and\n'
                'is searching for new devices.'
            )

    def close(self):
        """Disconnect and clean up sockets."""
        self.connected = False
        for conn in [self._ctrl_conn, self._intr_conn,
                     self._ctrl_server, self._intr_server]:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
        self._ctrl_conn = self._intr_conn = None
        self._ctrl_server = self._intr_server = None
        # Stop advertising (best-effort — may not be available in test env)
        try:
            subprocess.run(
                ['bluetoothctl'],
                input=b'discoverable off\npairable off\nquit\n',
                capture_output=True,
            )
        except FileNotFoundError:
            pass
        log.info('BT HID keyboard disconnected')

    # ------------------------------------------------------------------
    # HID report sending
    # ------------------------------------------------------------------

    def _send_report(self, modifier: int, keycode: int) -> None:
        if not self.connected or self._intr_conn is None:
            raise ConnectionError('BT HID: not connected to a host')
        # 0xA1 = Bluetooth HID INPUT report header
        report = bytes([BT_HID_INPUT, modifier, 0, keycode, 0, 0, 0, 0, 0])
        self._intr_conn.send(report)

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
                log.debug('No BT keycode mapping for: %r', ch)

    def combo(self, *keys: str) -> None:
        """Press multiple keys simultaneously (e.g. Ctrl+Alt+T)."""
        if not self.connected or self._intr_conn is None:
            raise ConnectionError('BT HID: not connected to a host')
        modifier  = MOD_NONE
        keycodes  = []
        for key in keys:
            k = key.upper()
            if k in ('CTRL', 'LCTRL'):        modifier |= MOD_LCTRL
            elif k in ('SHIFT', 'LSHIFT'):    modifier |= MOD_LSHIFT
            elif k in ('ALT', 'LALT'):        modifier |= MOD_LALT
            elif k in ('GUI', 'WIN', 'LMETA'): modifier |= MOD_LMETA
            else:
                keycodes.append(KEYCODES.get(k, 0))

        payload = [BT_HID_INPUT, modifier, 0] + keycodes[:6]
        payload += [0] * max(0, 9 - len(payload))
        self._intr_conn.send(bytes(payload[:9]))
        time.sleep(0.01)
        self._key_up()
