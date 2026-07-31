"""Tests for BlueNet mesh networking module."""
import time
import unittest
from modules.bluenet.peer import Peer, PeerRegistry, PEER_EXPIRY_SECS
from modules.bluenet.bluenet_node import BlueNetNode, VERSION, CAPABILITIES


class TestPeer(unittest.TestCase):

    def test_peer_online_by_default(self):
        p = Peer('PiFlip-A', '192.168.1.2')
        self.assertTrue(p.online)

    def test_peer_summary_format(self):
        p = Peer('PiFlip-A', '192.168.1.2')
        s = p.summary()
        self.assertIn('PiFlip-A', s)
        self.assertIn('192.168.1.2', s)

    def test_peer_summary_with_latency(self):
        p = Peer('PiFlip-A', '192.168.1.2', latency_ms=42.5)
        self.assertIn('42ms', p.summary())

    def test_peer_update_refreshes_last_seen(self):
        p = Peer('PiFlip-A', '192.168.1.2')
        p.last_seen = time.time() - 10
        old_age = p.age_secs
        p.update('0.1.0', ['rfid'])
        self.assertLess(p.age_secs, old_age)

    def test_stale_peer_not_online(self):
        p = Peer('PiFlip-A', '192.168.1.2')
        p.last_seen = time.time() - PEER_EXPIRY_SECS - 1
        self.assertFalse(p.online)


class TestPeerRegistry(unittest.TestCase):

    def setUp(self):
        self.reg = PeerRegistry()

    def test_empty_on_init(self):
        self.assertEqual(len(self.reg), 0)
        self.assertEqual(self.reg.all(), [])

    def test_upsert_new_peer(self):
        self.reg.upsert('1.2.3.4', 'Alpha', '0.1.0', ['rfid'])
        self.assertEqual(len(self.reg), 1)

    def test_upsert_same_ip_updates(self):
        self.reg.upsert('1.2.3.4', 'Alpha', '0.1.0', ['rfid'])
        self.reg.upsert('1.2.3.4', 'Alpha-v2', '0.2.0', ['rfid', 'ir'])
        self.assertEqual(len(self.reg), 1)
        peer = self.reg.get('1.2.3.4')
        self.assertEqual(peer.name, 'Alpha-v2')
        self.assertEqual(peer.version, '0.2.0')

    def test_multiple_peers(self):
        self.reg.upsert('1.1.1.1', 'Alpha', '0.1.0', [])
        self.reg.upsert('2.2.2.2', 'Beta',  '0.1.0', [])
        self.reg.upsert('3.3.3.3', 'Gamma', '0.1.0', [])
        self.assertEqual(len(self.reg), 3)

    def test_sorted_by_name(self):
        self.reg.upsert('3.3.3.3', 'Zebra', '0.1.0', [])
        self.reg.upsert('1.1.1.1', 'Alpha', '0.1.0', [])
        self.reg.upsert('2.2.2.2', 'Mango', '0.1.0', [])
        names = [p.name for p in self.reg.all()]
        self.assertEqual(names, sorted(names))

    def test_remove_peer(self):
        self.reg.upsert('1.1.1.1', 'Alpha', '0.1.0', [])
        self.reg.remove('1.1.1.1')
        self.assertEqual(len(self.reg), 0)

    def test_evict_stale(self):
        self.reg.upsert('1.1.1.1', 'Fresh', '0.1.0', [])
        stale_peer = self.reg.upsert('2.2.2.2', 'Stale', '0.1.0', [])
        stale_peer.last_seen = time.time() - PEER_EXPIRY_SECS - 5
        self.reg.evict_stale()
        self.assertEqual(len(self.reg), 1)
        self.assertIsNone(self.reg.get('2.2.2.2'))

    def test_get_unknown_ip_returns_none(self):
        self.assertIsNone(self.reg.get('9.9.9.9'))


class TestBlueNetNode(unittest.TestCase):

    def setUp(self):
        self.node = BlueNetNode(name='TestPiFlip')

    def test_name(self):
        self.assertEqual(self.node.name, 'TestPiFlip')

    def test_not_running_before_start(self):
        self.assertFalse(self.node.running)

    def test_no_peers_initially(self):
        self.assertEqual(self.node.peer_count(), 0)
        self.assertEqual(self.node.peers(), [])

    def test_inbox_empty_initially(self):
        self.assertEqual(len(self.node.inbox), 0)
        self.assertEqual(self.node.inbox_lines(), [])

    def test_chat_no_peers_returns_zero(self):
        count = self.node.chat('hello')
        self.assertEqual(count, 0)

    def test_share_signal_no_peers_returns_zero(self):
        count = self.node.share_signal({'description': 'test'})
        self.assertEqual(count, 0)

    def test_ping_all_no_peers_returns_empty(self):
        results = self.node.ping_all()
        self.assertEqual(results, {})

    def test_push_inbox(self):
        self.node._push_inbox('Alpha', 'Hello!')
        self.assertEqual(len(self.node.inbox), 1)
        lines = self.node.inbox_lines()
        self.assertEqual(len(lines), 1)
        self.assertIn('Alpha', lines[0])
        self.assertIn('Hello!', lines[0])

    def test_clear_inbox(self):
        self.node._push_inbox('A', 'msg1')
        self.node._push_inbox('B', 'msg2')
        self.node.clear_inbox()
        self.assertEqual(len(self.node.inbox), 0)

    def test_handle_ping_returns_pong(self):
        msg   = {'type': 'PING', 'from': 'OtherFlip', 'ts': time.time()}
        reply = self.node._handle_ping(msg)
        self.assertEqual(reply['type'], 'PONG')
        self.assertEqual(reply['from'], 'TestPiFlip')

    def test_handle_chat_adds_to_inbox(self):
        msg = {'type': 'CHAT', 'from': 'Alpha', 'content': 'yo!'}
        self.node._handle_chat(msg)
        lines = self.node.inbox_lines()
        self.assertTrue(any('yo!' in l for l in lines))

    def test_handle_status_req_returns_correct_fields(self):
        msg   = {'type': 'STATUS_REQ', 'from': 'Alpha'}
        reply = self.node._handle_status_req(msg)
        self.assertEqual(reply['type'], 'STATUS_REPLY')
        self.assertEqual(reply['from'], 'TestPiFlip')
        self.assertIn('version',      reply)
        self.assertIn('capabilities', reply)
        self.assertIn('peers',        reply)

    def test_version_constant(self):
        self.assertRegex(VERSION, r'^\d+\.\d+\.\d+$')

    def test_capabilities_list(self):
        self.assertIsInstance(CAPABILITIES, list)
        self.assertGreater(len(CAPABILITIES), 0)


class TestBlueNetMenu(unittest.TestCase):

    def test_menu_builds(self):
        from modules.bluenet.bluenet_menu import build_bluenet_menu
        entries = build_bluenet_menu(config=None, display=None)
        labels = [e.label for e in entries]
        self.assertIn('Status',       labels)
        self.assertIn('Peer List',    labels)
        self.assertIn('Live Chat',    labels)
        self.assertIn('Inbox',        labels)
        self.assertIn('Ping All',     labels)
        self.assertIn('Share Signal', labels)

    def test_all_entries_have_actions_or_children(self):
        from modules.bluenet.bluenet_menu import build_bluenet_menu
        for entry in build_bluenet_menu(config=None, display=None):
            has_action   = entry.action   is not None
            has_children = entry.children is not None
            self.assertTrue(has_action or has_children, f'{entry.label!r} has neither')


if __name__ == '__main__':
    unittest.main()
