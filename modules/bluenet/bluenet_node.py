"""
BlueNet node — the top-level coordinator for one PiFlip on the mesh.

Usage:
    node = BlueNetNode(name='PiFlip-Alpha')
    node.start()          # begins advertising + listening
    node.peers()          # list of Peer objects
    node.chat('hello!')   # broadcast to all peers
    node.share_signal({}) # share a captured signal
    node.ping_all()       # ping every peer, update latencies
    node.stop()

Incoming messages are queued in node.inbox for the menu to display.
"""
from __future__ import annotations

import logging
import socket
import time
from collections import deque
from typing import Deque, List, Optional, Tuple

from modules.bluenet.peer       import Peer, PeerRegistry
from modules.bluenet.discovery  import DiscoveryService
from modules.bluenet.messenger  import MessageServer, MessageClient

log = logging.getLogger(__name__)

VERSION      = '0.1.0'
CAPABILITIES = ['rfid', 'ir', 'subghz', 'bluetooth', 'radio',
                'aircraft', 'network', 'sonar']

# (timestamp, from_name, message_text)
InboxEntry = Tuple[float, str, str]


class BlueNetNode:

    def __init__(self, name: str = 'PiFlip'):
        self.name     = name
        self._registry = PeerRegistry()
        self.inbox: Deque[InboxEntry] = deque(maxlen=50)

        self._discovery = DiscoveryService(
            node_name    = name,
            version      = VERSION,
            capabilities = CAPABILITIES,
            registry     = self._registry,
            on_new_peer  = self._on_new_peer,
        )
        self._server = MessageServer(name, '0.0.0.0')
        self._client = MessageClient(name)

        self._server.register('CHAT',         self._handle_chat)
        self._server.register('SIGNAL_SHARE', self._handle_signal)
        self._server.register('PING',         self._handle_ping)
        self._server.register('STATUS_REQ',   self._handle_status_req)

        self._running = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self):
        if self._running:
            return
        self._discovery.start()
        self._server.start()
        self._running = True
        log.info('BlueNet node "%s" started', self.name)

    def stop(self):
        self._discovery.stop()
        self._server.stop()
        self._running = False
        log.info('BlueNet node stopped')

    @property
    def running(self) -> bool:
        return self._running

    @property
    def local_ip(self) -> str:
        return self._discovery.local_ip

    # ------------------------------------------------------------------
    # Peer access
    # ------------------------------------------------------------------

    def peers(self) -> List[Peer]:
        return self._registry.all()

    def peer_count(self) -> int:
        return len(self._registry)

    def _peer_ips(self) -> List[str]:
        return [p.ip for p in self._registry.all()]

    # ------------------------------------------------------------------
    # Outgoing
    # ------------------------------------------------------------------

    def chat(self, text: str) -> int:
        ips = self._peer_ips()
        if not ips:
            return 0
        return self._client.send_chat(ips, text)

    def share_signal(self, signal: dict) -> int:
        ips = self._peer_ips()
        if not ips:
            return 0
        return self._client.send_signal(ips, signal)

    def ping_all(self) -> dict:
        results = {}
        for peer in self._registry.all():
            ms = self._client.ping(peer.ip)
            peer.latency_ms = ms
            results[peer.name] = ms
        return results

    def ping_peer(self, ip: str) -> Optional[float]:
        peer = self._registry.get(ip)
        ms   = self._client.ping(ip)
        if peer:
            peer.latency_ms = ms
        return ms

    def get_peer_status(self, ip: str) -> Optional[dict]:
        return self._client.request_status(ip)

    # ------------------------------------------------------------------
    # Incoming handlers
    # ------------------------------------------------------------------

    def _on_new_peer(self, name: str, ip: str):
        self._push_inbox('BlueNet', f'[+] {name} joined ({ip})')

    def _push_inbox(self, sender: str, text: str):
        self.inbox.append((time.time(), sender, text))

    def _handle_chat(self, msg: dict) -> None:
        sender  = msg.get('from', '?')
        content = msg.get('content', '')
        self._push_inbox(sender, content)
        log.info('BlueNet chat from %s: %s', sender, content)
        return None   # no reply needed

    def _handle_signal(self, msg: dict) -> None:
        sender = msg.get('from', '?')
        signal = msg.get('signal', {})
        desc   = signal.get('description', str(signal)[:40])
        self._push_inbox(sender, f'[signal] {desc}')
        log.info('BlueNet signal from %s: %s', sender, desc)
        return None

    def _handle_ping(self, msg: dict) -> dict:
        return {'type': 'PONG', 'from': self.name,
                'to': msg.get('from'), 'ts': time.time()}

    def _handle_status_req(self, msg: dict) -> dict:
        return {
            'type':        'STATUS_REPLY',
            'from':        self.name,
            'ip':          self.local_ip,
            'version':     VERSION,
            'peers':       self.peer_count(),
            'capabilities': CAPABILITIES,
            'uptime':      time.time(),
        }

    # ------------------------------------------------------------------
    # Inbox helpers
    # ------------------------------------------------------------------

    def inbox_lines(self, max_lines: int = 10) -> List[str]:
        entries = list(self.inbox)[-max_lines:]
        lines   = []
        for ts, sender, text in entries:
            t = time.strftime('%H:%M', time.localtime(ts))
            lines.append(f'[{t}] {sender}: {text}')
        return lines

    def clear_inbox(self):
        self.inbox.clear()
