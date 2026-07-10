"""BlueNet mesh network menu for PiFlip."""

import time
import threading
from core.menu import MenuEntry

# One shared node per process — started lazily on first use
_node = None
_node_lock = threading.Lock()


def _get_node(config) -> 'BlueNetNode':
    global _node
    with _node_lock:
        if _node is None:
            from modules.bluenet.bluenet_node import BlueNetNode
            name = 'PiFlip'
            if config:
                try:
                    name = config.parser['bluenet']['device_name']
                except (KeyError, AttributeError):
                    pass
            _node = BlueNetNode(name=name)
            _node.start()
    return _node


def build_bluenet_menu(config, display) -> list:

    def _status():
        node = _get_node(config)
        peers = node.peers()
        lines = [
            f'BlueNet: {"ON" if node.running else "OFF"}',
            f'Name : {node.name}',
            f'IP   : {node.local_ip}',
            f'Peers: {len(peers)}',
        ]
        if display:
            display.draw_message(lines)
            time.sleep(4)
        else:
            print('\n'.join(lines))

    def _peer_list():
        node  = _get_node(config)
        peers = node.peers()
        if not peers:
            _show(display, 'No peers found', 'Are they on same WiFi?')
            return
        lines = [f'Peers ({len(peers)}):'] + [p.summary() for p in peers]
        if display:
            display.draw_message(lines)
            time.sleep(5)
        else:
            print('\n'.join(lines))

    def _chat():
        node = _get_node(config)
        if not node.peers():
            _show(display, 'No peers online', 'Nothing to send to')
            return
        text = input('Message to all PiFlips: ').strip()
        if not text:
            return
        count = node.chat(text)
        _show(display, f'Sent to {count} peer(s)', text[:30])

    def _inbox():
        node  = _get_node(config)
        lines = node.inbox_lines(max_lines=8)
        if not lines:
            lines = ['Inbox empty', 'Waiting for messages...']
        if display:
            display.draw_message(lines)
            time.sleep(5)
        else:
            print('\n'.join(lines))

    def _ping_all():
        node = _get_node(config)
        if not node.peers():
            _show(display, 'No peers', 'Nothing to ping')
            return
        _show(display, 'Pinging...', '')
        results = node.ping_all()
        lines = ['Ping results:']
        for name, ms in results.items():
            lines.append(f'{name}: {"timeout" if ms is None else f"{ms:.0f}ms"}')
        if display:
            display.draw_message(lines)
            time.sleep(4)
        else:
            print('\n'.join(lines))

    def _share_last():
        node = _get_node(config)
        if not node.peers():
            _show(display, 'No peers', 'Nothing to share to')
            return
        # Try to grab the last saved capture from config manager
        signal = {'description': 'Manual test signal', 'source': node.name}
        try:
            captures = config.load_captures() if config else []
            if captures:
                last = captures[-1]
                signal = {
                    'description': last.get('label', 'Captured signal'),
                    'data':        last,
                    'source':      node.name,
                }
        except Exception:
            pass
        count = node.share_signal(signal)
        _show(display, f'Shared to {count}', signal['description'][:30])

    def _live_chat():
        """Real-time chat: type messages, see replies scroll on screen."""
        node = _get_node(config)
        import curses

        def _inner(stdscr):
            curses.curs_set(1)
            stdscr.nodelay(False)
            h, w = stdscr.getmaxyx()
            input_row = h - 2
            msg_rows  = h - 4

            buf = ''
            while True:
                # Draw inbox
                stdscr.clear()
                stdscr.addstr(0, 0, f' BlueNet Chat — {node.name} ({node.local_ip}) ')
                stdscr.addstr(1, 0, '─' * w)
                lines = node.inbox_lines(max_lines=msg_rows)
                for i, line in enumerate(lines):
                    try:
                        stdscr.addstr(2 + i, 0, line[:w - 1])
                    except curses.error:
                        pass
                stdscr.addstr(h - 3, 0, '─' * w)
                stdscr.addstr(h - 2, 0, f'> {buf}')
                stdscr.addstr(h - 1, 0, ' ESC=quit  ENTER=send ')
                stdscr.refresh()

                key = stdscr.getch()
                if key == 27:       # ESC
                    break
                elif key in (10, 13):  # ENTER
                    if buf.strip():
                        node.chat(buf.strip())
                        node._push_inbox(node.name, buf.strip())
                    buf = ''
                elif key == curses.KEY_BACKSPACE or key == 127:
                    buf = buf[:-1]
                elif 32 <= key < 127:
                    buf += chr(key)

        curses.wrapper(_inner)

    return [
        MenuEntry(label='Status',        action=_status),
        MenuEntry(label='Peer List',     action=_peer_list),
        MenuEntry(label='Live Chat',     action=_live_chat),
        MenuEntry(label='Inbox',         action=_inbox),
        MenuEntry(label='Ping All',      action=_ping_all),
        MenuEntry(label='Share Signal',  action=_share_last),
    ]


def _show(display, title: str, body: str, secs: int = 2):
    if display:
        display.draw_message([title, body])
        time.sleep(secs)
    else:
        print(f'{title}  {body}')
