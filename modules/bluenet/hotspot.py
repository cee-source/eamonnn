"""
Hotspot manager: turns the Pi's wlan0 into a WiFi access point so other
PiFlips can connect directly — no router or phone hotspot required.

Requires on the Pi (install once):
    sudo apt install hostapd dnsmasq
    sudo systemctl unmask hostapd

BlueNet discovery still works in AP mode because connected devices are on
the same virtual LAN (10.42.0.x) as the Pi.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
import threading
from typing import Optional

log = logging.getLogger(__name__)

AP_INTERFACE  = 'wlan0'
AP_IP         = '10.42.0.1'
DHCP_START    = '10.42.0.10'
DHCP_END      = '10.42.0.100'
AP_CHANNEL    = 6

_HOSTAPD_CONF = """\
interface={iface}
driver=nl80211
ssid={ssid}
hw_mode=g
channel={channel}
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase={password}
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
"""

_DNSMASQ_CONF = """\
interface={iface}
dhcp-range={start},{end},255.255.255.0,24h
dhcp-option=3,{gw}
dhcp-option=6,{gw}
"""


class HotspotManager:

    def __init__(self, ssid: str = 'PiFlip-Mesh', password: str = 'piflip123'):
        self.ssid     = ssid
        self.password = password
        self._lock    = threading.Lock()
        self._running = False
        self._tmpdir: Optional[str]        = None
        self._hostapd: Optional[subprocess.Popen] = None
        self._dnsmasq: Optional[subprocess.Popen] = None

    @property
    def running(self) -> bool:
        return self._running

    def start(self) -> bool:
        with self._lock:
            if self._running:
                return True
            try:
                self._tmpdir = tempfile.mkdtemp(prefix='piflip_ap_')
                self._write_configs()
                self._setup_interface()
                self._hostapd = self._launch('hostapd', self._hostapd_path)
                self._dnsmasq = self._launch(
                    'dnsmasq', '--conf-file', self._dnsmasq_path, '--no-daemon'
                )
                self._running = True
                log.info('Hotspot "%s" started on %s', self.ssid, AP_IP)
                return True
            except Exception as exc:
                log.error('Hotspot start failed: %s', exc)
                self._teardown()
                return False

    def stop(self):
        with self._lock:
            self._teardown()
            self._running = False
            log.info('Hotspot stopped')

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _write_configs(self):
        self._hostapd_path = os.path.join(self._tmpdir, 'hostapd.conf')
        self._dnsmasq_path = os.path.join(self._tmpdir, 'dnsmasq.conf')

        with open(self._hostapd_path, 'w') as f:
            f.write(_HOSTAPD_CONF.format(
                iface=AP_INTERFACE, ssid=self.ssid,
                channel=AP_CHANNEL, password=self.password,
            ))
        with open(self._dnsmasq_path, 'w') as f:
            f.write(_DNSMASQ_CONF.format(
                iface=AP_INTERFACE, start=DHCP_START,
                end=DHCP_END, gw=AP_IP,
            ))

    def _setup_interface(self):
        _run('ip', 'link', 'set', AP_INTERFACE, 'up')
        _run('ip', 'addr', 'flush', 'dev', AP_INTERFACE)
        _run('ip', 'addr', 'add', f'{AP_IP}/24', 'dev', AP_INTERFACE)

    @staticmethod
    def _launch(*cmd) -> subprocess.Popen:
        return subprocess.Popen(
            list(cmd),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def _teardown(self):
        for proc in (self._hostapd, self._dnsmasq):
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                    proc.wait(timeout=3)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
        self._hostapd = None
        self._dnsmasq = None
        if self._tmpdir:
            shutil.rmtree(self._tmpdir, ignore_errors=True)
            self._tmpdir = None


def _run(*cmd):
    subprocess.run(list(cmd), check=True, capture_output=True)
