"""Tests for BlueNet HotspotManager."""
import unittest
from unittest.mock import MagicMock, patch


class TestHotspotManager(unittest.TestCase):

    def _make(self, ssid='TestNet', password='testpass'):
        from modules.bluenet.hotspot import HotspotManager
        return HotspotManager(ssid=ssid, password=password)

    def test_not_running_on_init(self):
        hs = self._make()
        self.assertFalse(hs.running)

    def test_ssid_and_password_stored(self):
        hs = self._make(ssid='MyNet', password='secret99')
        self.assertEqual(hs.ssid, 'MyNet')
        self.assertEqual(hs.password, 'secret99')

    def test_default_ssid(self):
        from modules.bluenet.hotspot import HotspotManager
        hs = HotspotManager()
        self.assertEqual(hs.ssid, 'PiFlip-Mesh')

    def test_default_password(self):
        from modules.bluenet.hotspot import HotspotManager
        hs = HotspotManager()
        self.assertEqual(hs.password, 'piflip123')

    @patch('modules.bluenet.hotspot.subprocess.Popen')
    @patch('modules.bluenet.hotspot._run')
    @patch('modules.bluenet.hotspot.tempfile.mkdtemp', return_value='/tmp/fake_ap')
    @patch('modules.bluenet.hotspot.os.path.join', side_effect=lambda *a: '/'.join(a))
    @patch('builtins.open', unittest.mock.mock_open())
    def test_start_sets_running(self, _join, _mkdtemp, _run, _popen):
        _popen.return_value = MagicMock(poll=lambda: None)
        hs = self._make()
        result = hs.start()
        self.assertTrue(result)
        self.assertTrue(hs.running)

    @patch('modules.bluenet.hotspot.subprocess.Popen')
    @patch('modules.bluenet.hotspot._run')
    @patch('modules.bluenet.hotspot.tempfile.mkdtemp', return_value='/tmp/fake_ap')
    @patch('modules.bluenet.hotspot.os.path.join', side_effect=lambda *a: '/'.join(a))
    @patch('builtins.open', unittest.mock.mock_open())
    def test_start_twice_is_idempotent(self, _join, _mkdtemp, _run, _popen):
        _popen.return_value = MagicMock(poll=lambda: None)
        hs = self._make()
        hs.start()
        result = hs.start()
        self.assertTrue(result)
        self.assertEqual(_popen.call_count, 2)  # only launched once

    @patch('modules.bluenet.hotspot.subprocess.Popen')
    @patch('modules.bluenet.hotspot._run')
    @patch('modules.bluenet.hotspot.tempfile.mkdtemp', return_value='/tmp/fake_ap')
    @patch('modules.bluenet.hotspot.os.path.join', side_effect=lambda *a: '/'.join(a))
    @patch('modules.bluenet.hotspot.shutil.rmtree')
    @patch('builtins.open', unittest.mock.mock_open())
    def test_stop_clears_running(self, _rmtree, _join, _mkdtemp, _run, _popen):
        proc = MagicMock()
        proc.poll.return_value = None
        _popen.return_value = proc
        hs = self._make()
        hs.start()
        hs.stop()
        self.assertFalse(hs.running)

    def test_stop_when_not_started_is_safe(self):
        hs = self._make()
        hs.stop()  # should not raise
        self.assertFalse(hs.running)

    @patch('modules.bluenet.hotspot._run', side_effect=Exception('no ip command'))
    @patch('modules.bluenet.hotspot.tempfile.mkdtemp', return_value='/tmp/fake_ap')
    @patch('modules.bluenet.hotspot.os.path.join', side_effect=lambda *a: '/'.join(a))
    @patch('modules.bluenet.hotspot.shutil.rmtree')
    @patch('builtins.open', unittest.mock.mock_open())
    def test_start_returns_false_on_failure(self, _rmtree, _join, _mkdtemp, _run):
        hs = self._make()
        result = hs.start()
        self.assertFalse(result)
        self.assertFalse(hs.running)

    def test_ap_ip_constant(self):
        from modules.bluenet.hotspot import AP_IP
        parts = AP_IP.split('.')
        self.assertEqual(len(parts), 4)

    def test_dhcp_range_valid(self):
        from modules.bluenet.hotspot import DHCP_START, DHCP_END
        start_last = int(DHCP_START.split('.')[-1])
        end_last   = int(DHCP_END.split('.')[-1])
        self.assertLess(start_last, end_last)


class TestHotspotMenu(unittest.TestCase):

    def test_menu_has_hotspot_entry(self):
        from modules.bluenet.bluenet_menu import build_bluenet_menu
        entries = build_bluenet_menu(config=None, display=None)
        labels = [e.label for e in entries]
        self.assertIn('Hotspot', labels)

    def test_hotspot_submenu_entries(self):
        from modules.bluenet.bluenet_menu import build_bluenet_menu
        entries = build_bluenet_menu(config=None, display=None)
        hotspot = next(e for e in entries if e.label == 'Hotspot')
        self.assertIsNotNone(hotspot.children)
        sub_labels = [e.label for e in hotspot.children]
        self.assertIn('Start/Stop Hotspot', sub_labels)
        self.assertIn('Hotspot Info',       sub_labels)

    def test_all_top_level_entries_present(self):
        from modules.bluenet.bluenet_menu import build_bluenet_menu
        entries = build_bluenet_menu(config=None, display=None)
        labels  = [e.label for e in entries]
        for expected in ('Status', 'Peer List', 'Live Chat',
                         'Inbox', 'Ping All', 'Share Signal', 'Hotspot'):
            self.assertIn(expected, labels)


if __name__ == '__main__':
    unittest.main()
