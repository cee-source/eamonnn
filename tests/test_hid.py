"""Tests for HID device module — no hardware required."""
import sys
import os
import time
import unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from modules.badusb.hid_device import KEYCODES, CHAR_MAP, MOD_NONE, MOD_LSHIFT


class MockHID:
    def __init__(self):
        self.actions = []

    def type_string(self, s):
        self.actions.append(('string', s))

    def press_key(self, k):
        self.actions.append(('key', k))

    def combo(self, *args):
        self.actions.append(('combo',) + args)


class TestKeycodes(unittest.TestCase):
    def test_all_letters_present(self):
        for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            self.assertIn(c, KEYCODES)

    def test_all_digits_present(self):
        for d in '0123456789':
            self.assertIn(d, KEYCODES)

    def test_special_keys_present(self):
        for key in ('ENTER', 'ESC', 'BACKSPACE', 'TAB', 'SPACE',
                    'DELETE', 'UP', 'DOWN', 'LEFT', 'RIGHT', 'F1', 'F12', 'GUI'):
            self.assertIn(key, KEYCODES)

    def test_keycodes_are_valid_hid_range(self):
        for name, code in KEYCODES.items():
            self.assertGreaterEqual(code, 0x00)
            self.assertLessEqual(code, 0xFF)


class TestCharMap(unittest.TestCase):
    def test_lowercase_no_shift(self):
        for c in 'abcdefghijklmnopqrstuvwxyz':
            self.assertIn(c, CHAR_MAP)
            mod, _ = CHAR_MAP[c]
            self.assertEqual(mod, MOD_NONE)

    def test_uppercase_requires_shift(self):
        for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            self.assertIn(c, CHAR_MAP)
            mod, _ = CHAR_MAP[c]
            self.assertEqual(mod, MOD_LSHIFT)

    def test_shift_special_chars(self):
        for c in '!@#$%^&*()_+{}|:"<>?~':
            self.assertIn(c, CHAR_MAP)
            mod, _ = CHAR_MAP[c]
            self.assertEqual(mod, MOD_LSHIFT)

    def test_space(self):
        self.assertIn(' ', CHAR_MAP)
        mod, code = CHAR_MAP[' ']
        self.assertEqual(mod, MOD_NONE)
        self.assertEqual(code, KEYCODES['SPACE'])

    def test_newline_maps_to_enter(self):
        self.assertIn('\n', CHAR_MAP)
        _, code = CHAR_MAP['\n']
        self.assertEqual(code, KEYCODES['ENTER'])


class TestScriptRunner(unittest.TestCase):
    def _runner(self):
        from modules.badusb.script_runner import ScriptRunner
        hid = MockHID()
        return ScriptRunner(hid), hid

    def test_string_command(self):
        runner, hid = self._runner()
        runner.run_script('STRING hello world')
        self.assertIn(('string', 'hello world'), hid.actions)

    def test_enter_command(self):
        runner, hid = self._runner()
        runner.run_script('ENTER')
        self.assertIn(('key', 'ENTER'), hid.actions)

    def test_delay_command(self):
        runner, hid = self._runner()
        start = time.time()
        runner.run_script('DELAY 100')
        self.assertGreaterEqual(time.time() - start, 0.09)

    def test_gui_combo(self):
        runner, hid = self._runner()
        runner.run_script('GUI r')
        self.assertIn(('combo', 'GUI', 'r'), hid.actions)

    def test_ctrl_combo(self):
        runner, hid = self._runner()
        runner.run_script('CTRL c')
        self.assertIn(('combo', 'CTRL', 'c'), hid.actions)

    def test_comments_ignored(self):
        runner, hid = self._runner()
        runner.run_script('REM this is a comment\n# also ignored')
        self.assertEqual(len(hid.actions), 0)

    def test_repeat_command(self):
        runner, hid = self._runner()
        runner.run_script('STRING hello\nREPEAT 2')
        string_actions = [a for a in hid.actions if a[0] == 'string']
        self.assertEqual(len(string_actions), 3)  # 1 original + 2 repeats


if __name__ == '__main__':
    unittest.main()
