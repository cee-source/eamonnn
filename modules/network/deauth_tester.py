"""
WiFi deauth tester — tests YOUR OWN network's resilience to deauth attacks.
Sends 802.11 deauthentication frames using aireplay-ng or scapy.

IMPORTANT: Only use on networks you own or have explicit permission to test.
Deauthing someone else's network is illegal under the CFAA and similar laws.

Requires:
  sudo apt install aircrack-ng
  WiFi adapter that supports monitor mode (many USB adapters do)

What it tests:
  A real attacker can disconnect clients from any WiFi network by sending
  forged deauth frames. This tests if your router/clients handle it.
  Modern WPA3 networks with Management Frame Protection (MFP/802.11w)
  are immune. This tool helps you verify that.
"""
from __future__ import annotations

import logging
import subprocess
import time
from typing import Optional

log = logging.getLogger(__name__)


class DeauthTester:
    def __init__(self, interface: str = 'wlan0') -> None:
        self._iface      = interface
        self._mon_iface  = f'{interface}mon'
        self._in_monitor = False

    # -----------------------------------------------------------------------
    # Availability
    # -----------------------------------------------------------------------

    def aircrack_available(self) -> bool:
        try:
            r = subprocess.run(['which', 'aireplay-ng'],
                               capture_output=True, timeout=2)
            return r.returncode == 0
        except Exception:
            return False

    def monitor_mode_supported(self) -> bool:
        try:
            r = subprocess.run(
                ['iw', self._iface, 'info'],
                capture_output=True, text=True, timeout=3
            )
            return 'monitor' in r.stdout.lower()
        except Exception:
            return False

    # -----------------------------------------------------------------------
    # Monitor mode
    # -----------------------------------------------------------------------

    def enable_monitor(self) -> bool:
        try:
            subprocess.run(['sudo', 'airmon-ng', 'start', self._iface],
                           capture_output=True, timeout=10)
            self._in_monitor = True
            log.info('Monitor mode enabled on %s', self._mon_iface)
            return True
        except Exception as e:
            log.error('Monitor mode failed: %s', e)
            return False

    def disable_monitor(self) -> None:
        try:
            subprocess.run(['sudo', 'airmon-ng', 'stop', self._mon_iface],
                           capture_output=True, timeout=10)
            self._in_monitor = False
            log.info('Monitor mode disabled')
        except Exception:
            pass

    # -----------------------------------------------------------------------
    # Scan for nearby APs (while in monitor mode)
    # -----------------------------------------------------------------------

    def scan_aps(self, duration_s: float = 10.0) -> list[dict]:
        """
        Scan for nearby access points using airodump-ng.
        Returns list of APs with BSSID, ESSID, channel, encryption.
        """
        import tempfile, os, csv

        if not self._in_monitor:
            if not self.enable_monitor():
                return []

        tmp = tempfile.mkdtemp()
        prefix = os.path.join(tmp, 'scan')

        proc = subprocess.Popen(
            ['sudo', 'airodump-ng',
             '--output-format', 'csv',
             '--write', prefix,
             self._mon_iface],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        time.sleep(duration_s)
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            pass

        aps = []
        csv_file = prefix + '-01.csv'
        if os.path.exists(csv_file):
            with open(csv_file, errors='ignore') as f:
                lines = f.readlines()
            # Parse AP section (before blank line)
            in_aps = False
            for line in lines:
                if 'BSSID' in line and 'ESSID' in line:
                    in_aps = True
                    continue
                if in_aps and line.strip() == '':
                    break
                if in_aps:
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 14:
                        aps.append({
                            'bssid':      parts[0],
                            'channel':    parts[3],
                            'encryption': parts[5],
                            'essid':      parts[13],
                            'power':      parts[8],
                        })

        return [ap for ap in aps if ap['bssid'] and ':' in ap['bssid']]

    # -----------------------------------------------------------------------
    # Deauth test
    # -----------------------------------------------------------------------

    def test_deauth(self,
                    target_bssid: str,
                    client_mac:   str = 'FF:FF:FF:FF:FF:FF',
                    packets:      int = 10,
                    channel:      int = 6) -> dict:
        """
        Send deauth frames to your own AP/client to test resilience.

        target_bssid : MAC of YOUR access point
        client_mac   : MAC of client to deauth (FF:FF:FF:FF:FF:FF = broadcast)
        packets      : number of deauth frames to send
        channel      : WiFi channel your AP is on

        Returns result dict with success status and observations.
        """
        if not self._in_monitor:
            if not self.enable_monitor():
                return {'success': False, 'error': 'Monitor mode failed'}

        # Set channel
        subprocess.run(
            ['sudo', 'iwconfig', self._mon_iface, 'channel', str(channel)],
            capture_output=True, timeout=3
        )

        log.info('Deauth test: AP=%s client=%s pkts=%d ch=%d',
                 target_bssid, client_mac, packets, channel)

        start = time.time()
        result = subprocess.run(
            ['sudo', 'aireplay-ng',
             '--deauth', str(packets),
             '-a', target_bssid,
             '-c', client_mac,
             self._mon_iface],
            capture_output=True, text=True, timeout=30
        )
        elapsed = time.time() - start

        success = result.returncode == 0
        output  = result.stdout + result.stderr

        # Detect if MFP protected (immune)
        mfp_protected = 'protected' in output.lower() or 'MFP' in output

        return {
            'success':       success,
            'target':        target_bssid,
            'client':        client_mac,
            'packets_sent':  packets,
            'elapsed_s':     round(elapsed, 2),
            'mfp_protected': mfp_protected,
            'output':        output[:200],
            'verdict': (
                'PROTECTED (WPA3/MFP immune)' if mfp_protected
                else 'VULNERABLE — clients can be disconnected'
                if success else 'TEST FAILED'
            ),
        }

    def cleanup(self) -> None:
        if self._in_monitor:
            self.disable_monitor()
