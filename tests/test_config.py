"""Tests for ConfigManager — no hardware required."""
import sys
import os
import json
import tempfile
import unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.config_manager import ConfigManager


def make_config(tmp_dir: str) -> ConfigManager:
    cfg_file = os.path.join(tmp_dir, 'config.ini')
    with open(cfg_file, 'w') as f:
        f.write(
            '[hardware]\n'
            'ir_rx_pin = 24\n'
            'ir_tx_pin = 18\n'
            '[storage]\n'
            f'data_dir = {tmp_dir}\n'
            '[subghz]\n'
            'default_frequency = 433.92\n'
            'default_baud = 4800\n'
            'default_modulation = ASK_OOK\n'
        )
    return ConfigManager(cfg_file)


class TestConfigManager(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cfg = make_config(self.tmp)

    def test_get_string(self):
        self.assertEqual(self.cfg.get('subghz', 'default_modulation'), 'ASK_OOK')

    def test_getint(self):
        self.assertEqual(self.cfg.getint('hardware', 'ir_rx_pin'), 24)

    def test_getfloat(self):
        self.assertAlmostEqual(self.cfg.getfloat('subghz', 'default_frequency'), 433.92, places=2)

    def test_get_fallback(self):
        self.assertEqual(self.cfg.get('no_section', 'no_key', fallback='default'), 'default')

    def test_save_and_load_capture(self):
        data = {'uid': '0xAABBCCDD', 'type': 'MIFARE_CLASSIC'}
        path = self.cfg.save_capture('rfid', data, prefix='test')
        self.assertTrue(os.path.exists(path))
        captures = self.cfg.load_captures('rfid')
        self.assertEqual(len(captures), 1)
        self.assertEqual(captures[0]['data']['uid'], '0xAABBCCDD')

    def test_load_captures_empty(self):
        self.assertEqual(self.cfg.load_captures('nonexistent'), [])

    def test_save_multiple_captures(self):
        import time
        for i in range(3):
            self.cfg.save_capture('ir', {'index': i, 'protocol': 'NEC'}, prefix=f'sig{i}')
            time.sleep(0.01)  # ensure unique filenames
        captures = self.cfg.load_captures('ir')
        self.assertEqual(len(captures), 3)

    def test_data_dir_is_absolute(self):
        self.assertTrue(os.path.isabs(self.cfg.data_dir))


if __name__ == '__main__':
    unittest.main()
