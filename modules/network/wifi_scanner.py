"""
WiFi scanner — lists nearby networks with SSID, BSSID, channel,
signal strength (dBm), and security type.
Uses iwlist (no extra packages) or nmcli as fallback.
"""
from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger(__name__)


@dataclass
class WiFiNetwork:
    ssid:     str = ''
    bssid:    str = ''
    channel:  int = 0
    freq_ghz: float = 0.0
    signal_dbm: int = -100
    quality:  int = 0          # 0-100
    security: str = 'OPEN'
    mode:     str = ''

    @property
    def signal_bar(self) -> str:
        bars = int(self.quality / 25)
        return '█' * bars + '░' * (4 - bars)

    def summary(self) -> str:
        ssid = (self.ssid or '<hidden>')[:16].ljust(16)
        sig  = f'{self.signal_dbm:4d}dBm'
        ch   = f'Ch{self.channel:2d}'
        sec  = self.security[:8].ljust(8)
        return f'{ssid} {sig} {ch} {sec}'


class WiFiScanner:
    def __init__(self, interface: str = 'wlan0') -> None:
        self._iface = interface

    def interface_available(self) -> bool:
        try:
            r = subprocess.run(['iwconfig', self._iface],
                               capture_output=True, text=True, timeout=3)
            return r.returncode == 0
        except FileNotFoundError:
            return False

    def scan(self) -> list[WiFiNetwork]:
        networks = self._scan_iwlist()
        if not networks:
            networks = self._scan_nmcli()
        networks.sort(key=lambda n: n.signal_dbm, reverse=True)
        return networks

    # -----------------------------------------------------------------------
    # iwlist scan (no extra deps)
    # -----------------------------------------------------------------------

    def _scan_iwlist(self) -> list[WiFiNetwork]:
        try:
            result = subprocess.run(
                ['sudo', 'iwlist', self._iface, 'scan'],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode != 0:
                return []
            return self._parse_iwlist(result.stdout)
        except FileNotFoundError:
            return []
        except subprocess.TimeoutExpired:
            log.warning('iwlist scan timed out')
            return []

    def _parse_iwlist(self, output: str) -> list[WiFiNetwork]:
        networks = []
        current: Optional[WiFiNetwork] = None

        for line in output.splitlines():
            line = line.strip()

            if line.startswith('Cell '):
                if current:
                    networks.append(current)
                current = WiFiNetwork()
                m = re.search(r'Address: ([0-9A-F:]{17})', line)
                if m:
                    current.bssid = m.group(1)

            if not current:
                continue

            if 'ESSID:' in line:
                m = re.search(r'ESSID:"(.*?)"', line)
                current.ssid = m.group(1) if m else ''

            elif 'Channel:' in line:
                m = re.search(r'Channel:(\d+)', line)
                if m:
                    current.channel = int(m.group(1))

            elif 'Frequency:' in line:
                m = re.search(r'Frequency:([\d.]+)', line)
                if m:
                    current.freq_ghz = float(m.group(1))

            elif 'Signal level=' in line:
                m = re.search(r'Signal level=(-?\d+)', line)
                if m:
                    current.signal_dbm = int(m.group(1))
                    current.quality = max(0, min(100, 2 * (current.signal_dbm + 100)))

            elif 'Encryption key:' in line:
                if 'off' in line.lower():
                    current.security = 'OPEN'

            elif 'IE: WPA' in line or 'WPA2' in line:
                current.security = 'WPA2' if 'WPA2' in line else 'WPA'

            elif 'IE: IEEE 802.11i' in line:
                current.security = 'WPA2'

            elif 'WPS' in line:
                if current.security == 'OPEN':
                    current.security = 'WPS'

        if current:
            networks.append(current)

        return networks

    # -----------------------------------------------------------------------
    # nmcli fallback
    # -----------------------------------------------------------------------

    def _scan_nmcli(self) -> list[WiFiNetwork]:
        try:
            result = subprocess.run(
                ['nmcli', '-t', '-f',
                 'SSID,BSSID,CHAN,FREQ,SIGNAL,SECURITY',
                 'dev', 'wifi', 'list'],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode != 0:
                return []
            return self._parse_nmcli(result.stdout)
        except FileNotFoundError:
            return []

    def _parse_nmcli(self, output: str) -> list[WiFiNetwork]:
        networks = []
        for line in output.splitlines():
            parts = line.split(':')
            if len(parts) < 6:
                continue
            try:
                n = WiFiNetwork(
                    ssid=parts[0],
                    bssid=parts[1],
                    channel=int(parts[2]) if parts[2].isdigit() else 0,
                    signal_dbm=int(parts[4]) - 100 if parts[4].isdigit() else -100,
                    quality=int(parts[4]) if parts[4].isdigit() else 0,
                    security=parts[5] if parts[5] else 'OPEN',
                )
                networks.append(n)
            except (ValueError, IndexError):
                continue
        return networks
