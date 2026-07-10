"""
BlueNet peer discovery via UDP broadcast.

Every 5 seconds each PiFlip broadcasts a HELLO packet to the LAN.
All other PiFlips on the same WiFi network hear it and add/update
the sender in their PeerRegistry.

Broadcast port: 42424 (UDP)
Packet format : JSON, max 1024 bytes
"""
from __future__ import annotations

import json
import logging
import socket
import threading
import time
from typing import Callable, Optional

from modules.bluenet.peer import PeerRegistry

log = logging.getLogger(__name__)

DISCOVERY_PORT    = 42424
BROADCAST_ADDR    = '255.255.255.255'
HELLO_INTERVAL    = 5.0    # seconds between beacons
EVICT_INTERVAL    = 10.0   # seconds between stale-peer sweeps
MAX_PACKET        = 1024


def _local_ip() -> str:
    """Best-effort: get the LAN IP of this device."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'


class DiscoveryService:
    """
    Runs two background threads:
      - _broadcaster : sends HELLO every HELLO_INTERVAL seconds
      - _listener    : receives HELLO packets from peers
    """

    def __init__(self, node_name: str, version: str,
                 capabilities: list, registry: PeerRegistry,
                 on_new_peer: Optional[Callable] = None):
        self._name         = node_name
        self._version      = version
        self._capabilities = capabilities
        self._registry     = registry
        self._on_new_peer  = on_new_peer
        self._stop         = threading.Event()
        self._ip           = _local_ip()
        self._threads: list[threading.Thread] = []

    @property
    def local_ip(self) -> str:
        return self._ip

    def _hello_packet(self) -> bytes:
        return json.dumps({
            'type':         'HELLO',
            'name':         self._name,
            'version':      self._version,
            'ip':           self._ip,
            'capabilities': self._capabilities,
        }).encode()

    def _broadcaster(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            while not self._stop.is_set():
                try:
                    sock.sendto(self._hello_packet(),
                                (BROADCAST_ADDR, DISCOVERY_PORT))
                except Exception as e:
                    log.warning('BlueNet broadcast error: %s', e)
                self._stop.wait(HELLO_INTERVAL)
        finally:
            sock.close()

    def _listener(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind(('', DISCOVERY_PORT))
        sock.settimeout(1.0)

        last_evict = time.time()
        try:
            while not self._stop.is_set():
                try:
                    data, (sender_ip, _) = sock.recvfrom(MAX_PACKET)
                except socket.timeout:
                    pass
                except Exception as e:
                    log.warning('BlueNet listen error: %s', e)
                    continue
                else:
                    self._handle_packet(data, sender_ip)

                if time.time() - last_evict > EVICT_INTERVAL:
                    self._registry.evict_stale()
                    last_evict = time.time()
        finally:
            sock.close()

    def _handle_packet(self, data: bytes, sender_ip: str):
        if sender_ip == self._ip:
            return   # ignore our own broadcasts
        try:
            msg = json.loads(data.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            return

        if msg.get('type') != 'HELLO':
            return

        name  = msg.get('name', sender_ip)
        ver   = msg.get('version', 'unknown')
        caps  = msg.get('capabilities', [])
        is_new = self._registry.get(sender_ip) is None

        self._registry.upsert(sender_ip, name, ver, caps)

        if is_new:
            log.info('BlueNet: new peer %s @ %s', name, sender_ip)
            if self._on_new_peer:
                try:
                    self._on_new_peer(name, sender_ip)
                except Exception:
                    pass

    def start(self):
        self._ip = _local_ip()
        for target in (self._broadcaster, self._listener):
            t = threading.Thread(target=target, daemon=True, name=f'bluenet-{target.__name__}')
            t.start()
            self._threads.append(t)
        log.info('BlueNet discovery started as "%s" @ %s', self._name, self._ip)

    def stop(self):
        self._stop.set()
