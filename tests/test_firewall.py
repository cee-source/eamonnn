"""Tests for firewall manager — no root/iptables required."""
import sys
import os
import unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from modules.firewall.firewall_manager import FirewallManager, _run


class TestFirewallManagerNoHardware(unittest.TestCase):
    """Tests that don't require iptables or root."""

    def setUp(self):
        self.fw = FirewallManager()

    def test_profiles_dict_has_expected_keys(self):
        expected = {'open', 'ssh_only', 'web', 'lockdown'}
        self.assertEqual(set(self.fw.PROFILES.keys()), expected)

    def test_profiles_have_descriptions(self):
        for name, desc in self.fw.PROFILES.items():
            self.assertIsInstance(desc, str)
            self.assertGreater(len(desc), 0)

    def test_is_available_returns_bool(self):
        result = self.fw.is_available()
        self.assertIsInstance(result, bool)

    def test_run_valid_command(self):
        code, out, err = _run(['echo', 'hello'])
        self.assertEqual(code, 0)
        self.assertEqual(out, 'hello')

    def test_run_missing_command(self):
        code, out, err = _run(['nonexistent_command_xyz'])
        self.assertNotEqual(code, 0)
        self.assertIn('not found', err)

    def test_run_timeout(self):
        # This just checks the timeout param is accepted
        code, out, err = _run(['echo', 'ok'])
        self.assertEqual(code, 0)


class TestFirewallMenuBuilds(unittest.TestCase):
    def test_menu_builds_without_hardware(self):
        from modules.firewall.firewall_menu import build_firewall_menu
        from core.config_manager import ConfigManager
        import tempfile

        tmp = tempfile.mkdtemp()
        cfg_file = os.path.join(tmp, 'config.ini')
        with open(cfg_file, 'w') as f:
            f.write(f'[storage]\ndata_dir = {tmp}\n')

        config = ConfigManager(cfg_file)
        entries = build_firewall_menu(config, display=None)
        self.assertGreater(len(entries), 0)
        labels = [e.label for e in entries]
        self.assertIn('View Rules', labels)
        self.assertIn('Profile: Lockdown', labels)
        self.assertIn('Block IP', labels)
        self.assertIn('Save Rules', labels)


if __name__ == '__main__':
    unittest.main()
