"""
Network port scanner.
Scans hosts on your own network for open ports.
Uses raw sockets — no nmap required, though nmap is used if available
for richer service detection.
"""
from __future__ import annotations

import ipaddress
import logging
import socket
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

log = logging.getLogger(__name__)

# Common ports with service names
COMMON_PORTS = {
    21:   'FTP',      22:   'SSH',      23:   'Telnet',
    25:   'SMTP',     53:   'DNS',      80:   'HTTP',
    110:  'POP3',     143:  'IMAP',     443:  'HTTPS',
    445:  'SMB',      3306: 'MySQL',    3389: 'RDP',
    5900: 'VNC',      8080: 'HTTP-Alt', 8443: 'HTTPS-Alt',
    1883: 'MQTT',     6379: 'Redis',    27017:'MongoDB',
}

TOP_20_PORTS = [21, 22, 23, 25, 53, 80, 110, 139, 143,
                443, 445, 3306, 3389, 5900, 8080, 8443,
                1883, 6379, 27017, 9200]


def get_local_network() -> Optional[str]:
    """Detect the local /24 subnet (e.g. 192.168.1.0/24)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        parts = ip.split('.')
        return f'{parts[0]}.{parts[1]}.{parts[2]}.0/24'
    except Exception:
        return None


def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'


class PortScanner:
    def __init__(self, timeout_s: float = 0.5, max_threads: int = 50) -> None:
        self._timeout = timeout_s
        self._threads = max_threads

    # -----------------------------------------------------------------------
    # Single host port scan
    # -----------------------------------------------------------------------

    def scan_host(self,
                  host: str,
                  ports: list[int] = None,
                  progress_cb=None) -> dict:
        """
        Scan a single host for open ports.
        Returns dict with host info and open ports list.
        """
        if ports is None:
            ports = TOP_20_PORTS

        open_ports = []
        total = len(ports)

        with ThreadPoolExecutor(max_workers=self._threads) as ex:
            futures = {ex.submit(self._check_port, host, p): p for p in ports}
            done = 0
            for future in as_completed(futures):
                port = futures[future]
                done += 1
                if progress_cb:
                    progress_cb(done, total)
                result = future.result()
                if result:
                    open_ports.append(result)

        open_ports.sort(key=lambda p: p['port'])

        hostname = self._resolve(host)
        return {
            'host':       host,
            'hostname':   hostname,
            'open_ports': open_ports,
            'scan_time':  time.strftime('%H:%M:%S'),
        }

    def _check_port(self, host: str, port: int) -> Optional[dict]:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(self._timeout)
                result = s.connect_ex((host, port))
                if result == 0:
                    service = COMMON_PORTS.get(port, '?')
                    banner = self._grab_banner(host, port)
                    return {
                        'port':    port,
                        'service': service,
                        'banner':  banner,
                    }
        except Exception:
            pass
        return None

    def _grab_banner(self, host: str, port: int) -> str:
        """Try to grab a service banner."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)
                s.connect((host, port))
                if port in (80, 8080, 8443):
                    s.send(b'HEAD / HTTP/1.0\r\n\r\n')
                banner = s.recv(256).decode('ascii', errors='ignore').strip()
                return banner.split('\n')[0][:50]
        except Exception:
            return ''

    def _resolve(self, host: str) -> str:
        try:
            return socket.gethostbyaddr(host)[0]
        except Exception:
            return host

    # -----------------------------------------------------------------------
    # Network host discovery (ping sweep)
    # -----------------------------------------------------------------------

    def discover_hosts(self,
                       network: str = None,
                       progress_cb=None) -> list[str]:
        """
        Ping sweep a /24 network to find live hosts.
        Returns list of responding IP addresses.
        """
        if network is None:
            network = get_local_network()
        if not network:
            return []

        try:
            net = ipaddress.ip_network(network, strict=False)
        except ValueError:
            return []

        hosts = [str(ip) for ip in net.hosts()]
        live  = []
        lock  = threading.Lock()
        total = len(hosts)
        done  = [0]

        def ping(ip):
            try:
                result = subprocess.run(
                    ['ping', '-c', '1', '-W', '1', ip],
                    capture_output=True, timeout=2
                )
                with lock:
                    done[0] += 1
                    if progress_cb:
                        progress_cb(done[0], total)
                    if result.returncode == 0:
                        live.append(ip)
            except Exception:
                with lock:
                    done[0] += 1

        with ThreadPoolExecutor(max_workers=50) as ex:
            list(ex.map(ping, hosts))

        live.sort(key=lambda ip: [int(x) for x in ip.split('.')])
        log.info('Host discovery: %d live hosts on %s', len(live), network)
        return live

    # -----------------------------------------------------------------------
    # Full network scan
    # -----------------------------------------------------------------------

    def scan_network(self,
                     network: str = None,
                     ports: list[int] = None,
                     progress_cb=None) -> list[dict]:
        """Discover hosts then scan each one."""
        live = self.discover_hosts(network, progress_cb)
        results = []
        for i, host in enumerate(live):
            if progress_cb:
                progress_cb(i, len(live))
            result = self.scan_host(host, ports)
            if result['open_ports']:
                results.append(result)
        return results
