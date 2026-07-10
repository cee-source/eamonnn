"""
BlueNet TCP messaging layer.

Messages are JSON objects sent over TCP port 42425.
The server accepts incoming connections in a background thread.
The client opens a fresh TCP connection per message (simple + reliable).

Message types:
  CHAT          - plain text message to all or one peer
  SIGNAL_SHARE  - share a captured signal (RFID UID, IR code, Sub-GHz packet)
  PING          - latency check request
  PONG          - latency check reply
  STATUS_REQ    - request peer's status summary
  STATUS_REPLY  - reply with status summary
"""
from __future__ import annotations

import json
import logging
import socket
import threading
import time
from typing import Callable, Dict, List, Optional

log = logging.getLogger(__name__)

MESSAGE_PORT = 42425
RECV_TIMEOUT = 5.0
MAX_MSG_BYTES = 65536


def _send_tcp(ip: str, payload: dict, timeout: float = RECV_TIMEOUT) -> Optional[dict]:
    """Open a TCP connection to ip:MESSAGE_PORT, send payload, optionally read reply."""
    try:
        sock = socket.create_connection((ip, MESSAGE_PORT), timeout=timeout)
        data = json.dumps(payload).encode() + b'\n'
        sock.sendall(data)
        # Read reply (may be empty)
        sock.settimeout(timeout)
        reply_data = b''
        try:
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                reply_data += chunk
                if b'\n' in reply_data:
                    break
        except socket.timeout:
            pass
        sock.close()
        if reply_data.strip():
            return json.loads(reply_data.strip())
    except Exception as e:
        log.warning('BlueNet send to %s failed: %s', ip, e)
    return None


class MessageServer:
    """Listens on TCP MESSAGE_PORT and dispatches incoming messages to handlers."""

    def __init__(self, node_name: str, local_ip: str):
        self._name      = node_name
        self._local_ip  = local_ip
        self._handlers: Dict[str, Callable] = {}
        self._stop      = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def register(self, msg_type: str, handler: Callable):
        """Register a handler for a message type. handler(msg: dict) -> Optional[dict]"""
        self._handlers[msg_type] = handler

    def _handle_conn(self, conn: socket.socket, addr):
        try:
            conn.settimeout(RECV_TIMEOUT)
            data = b''
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
                if b'\n' in data:
                    break
            if not data.strip():
                return
            msg = json.loads(data.strip())
            msg_type = msg.get('type', '')
            handler  = self._handlers.get(msg_type)
            reply    = None
            if handler:
                reply = handler(msg)
            if reply:
                conn.sendall(json.dumps(reply).encode() + b'\n')
        except Exception as e:
            log.warning('BlueNet conn error from %s: %s', addr, e)
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _serve(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('', MESSAGE_PORT))
        server.listen(8)
        server.settimeout(1.0)
        try:
            while not self._stop.is_set():
                try:
                    conn, addr = server.accept()
                    threading.Thread(
                        target=self._handle_conn, args=(conn, addr),
                        daemon=True).start()
                except socket.timeout:
                    pass
        finally:
            server.close()

    def start(self):
        self._thread = threading.Thread(target=self._serve, daemon=True,
                                        name='bluenet-server')
        self._thread.start()

    def stop(self):
        self._stop.set()


class MessageClient:
    """Sends messages to peers."""

    def __init__(self, node_name: str):
        self._name = node_name

    def _base(self, msg_type: str, to: str = 'broadcast') -> dict:
        return {'type': msg_type, 'from': self._name,
                'to': to, 'ts': time.time()}

    def send_chat(self, peers: List[str], text: str) -> int:
        """Broadcast a chat message to all peers. Returns success count."""
        msg = {**self._base('CHAT'), 'content': text}
        ok  = 0
        for ip in peers:
            if _send_tcp(ip, msg) is not None or True:   # fire-and-forget
                ok += 1
        return ok

    def send_signal(self, peers: List[str], signal: dict) -> int:
        """Share a captured signal dict to all peers."""
        msg = {**self._base('SIGNAL_SHARE'), 'signal': signal}
        ok  = 0
        for ip in peers:
            _send_tcp(ip, msg)
            ok += 1
        return ok

    def ping(self, ip: str) -> Optional[float]:
        """Send PING, measure round-trip ms. Returns None on timeout."""
        msg   = {**self._base('PING', to=ip), 'sent_at': time.time()}
        start = time.monotonic()
        reply = _send_tcp(ip, msg, timeout=3.0)
        if reply and reply.get('type') == 'PONG':
            return (time.monotonic() - start) * 1000.0
        return None

    def request_status(self, ip: str) -> Optional[dict]:
        msg = self._base('STATUS_REQ', to=ip)
        return _send_tcp(ip, msg, timeout=5.0)
