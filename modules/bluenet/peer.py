"""
BlueNet peer dataclass and peer registry.

Each PiFlip on the network is a Peer. The PeerRegistry keeps track of
all discovered peers, evicting ones that haven't been heard from in a while.
"""
from __future__ import annotations

import time
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional

PEER_EXPIRY_SECS = 30.0   # remove peer if no HELLO heard for this long


@dataclass
class Peer:
    name:         str
    ip:           str
    version:      str        = "unknown"
    capabilities: List[str]  = field(default_factory=list)
    last_seen:    float      = field(default_factory=time.time)
    latency_ms:   Optional[float] = None

    def update(self, version: str, capabilities: List[str]):
        self.version      = version
        self.capabilities = capabilities
        self.last_seen    = time.time()

    @property
    def age_secs(self) -> float:
        return time.time() - self.last_seen

    @property
    def online(self) -> bool:
        return self.age_secs < PEER_EXPIRY_SECS

    def summary(self) -> str:
        ping = f" {self.latency_ms:.0f}ms" if self.latency_ms else ""
        return f"{self.name} [{self.ip}]{ping}"


class PeerRegistry:
    """Thread-safe registry of known BlueNet peers."""

    def __init__(self):
        self._peers: Dict[str, Peer] = {}   # keyed by IP
        self._lock  = threading.Lock()

    def upsert(self, ip: str, name: str, version: str,
               capabilities: List[str]) -> Peer:
        with self._lock:
            if ip in self._peers:
                self._peers[ip].name = name
                self._peers[ip].update(version, capabilities)
            else:
                self._peers[ip] = Peer(name, ip, version, capabilities)
            return self._peers[ip]

    def remove(self, ip: str):
        with self._lock:
            self._peers.pop(ip, None)

    def evict_stale(self):
        with self._lock:
            stale = [ip for ip, p in self._peers.items()
                     if not p.online]
            for ip in stale:
                del self._peers[ip]

    def all(self) -> List[Peer]:
        with self._lock:
            return sorted(self._peers.values(), key=lambda p: p.name)

    def get(self, ip: str) -> Optional[Peer]:
        with self._lock:
            return self._peers.get(ip)

    def __len__(self) -> int:
        with self._lock:
            return len(self._peers)
