"""Tests for Bluetooth HID keyboard module."""
import unittest
from modules.badusb.bt_hid_device import BTHIDDevice, HID_CTRL_PSM, HID_INTR_PSM, BT_HID_INPUT


class TestBTHIDConstants(unittest.TestCase):

    def test_psm_values(self):
        self.assertEqual(HID_CTRL_PSM, 0x0011)
        self.assertEqual(HID_INTR_PSM, 0x0013)

    def test_input_report_header(self):
        self.assertEqual(BT_HID_INPUT, 0xA1)


class TestBTHIDDevice(unittest.TestCase):

    def setUp(self):
        self.dev = BTHIDDevice(adapter='hci0', device_name='TestKeyboard')

    def test_not_connected_by_default(self):
        self.assertFalse(self.dev.connected)

    def test_send_report_raises_when_not_connected(self):
        with self.assertRaises(ConnectionError):
            self.dev._send_report(0, 0x04)

    def test_type_string_raises_when_not_connected(self):
        with self.assertRaises(ConnectionError):
            self.dev.type_string('hello')

    def test_press_key_raises_when_not_connected(self):
        with self.assertRaises(ConnectionError):
            self.dev.press_key('A')

    def test_combo_raises_when_not_connected(self):
        with self.assertRaises(ConnectionError):
            self.dev.combo('CTRL', 'C')

    def test_close_when_not_connected_is_safe(self):
        # Should not raise even if never connected
        try:
            self.dev.close()
        except Exception as e:
            self.fail(f'close() raised unexpectedly: {e}')


class TestBTHIDReportFormat(unittest.TestCase):
    """Verify report format without real hardware using a mock socket."""

    def _make_connected_dev(self):
        """Return a BTHIDDevice with a mock interrupt connection."""
        from unittest.mock import MagicMock
        dev = BTHIDDevice()
        dev.connected = True
        dev._intr_conn = MagicMock()
        dev._intr_conn.sent_data = []
        dev._intr_conn.send.side_effect = lambda d: dev._intr_conn.sent_data.append(bytes(d))
        return dev

    def test_report_starts_with_input_header(self):
        dev = self._make_connected_dev()
        dev._send_report(0x00, 0x04)
        data = dev._intr_conn.sent_data[0]
        self.assertEqual(data[0], BT_HID_INPUT)

    def test_report_is_9_bytes(self):
        dev = self._make_connected_dev()
        dev._send_report(0x00, 0x04)
        data = dev._intr_conn.sent_data[0]
        self.assertEqual(len(data), 9)

    def test_modifier_byte_position(self):
        dev = self._make_connected_dev()
        dev._send_report(0x02, 0x04)   # LSHIFT + A
        data = dev._intr_conn.sent_data[0]
        self.assertEqual(data[1], 0x02)

    def test_keycode_byte_position(self):
        dev = self._make_connected_dev()
        dev._send_report(0x00, 0x28)   # ENTER
        data = dev._intr_conn.sent_data[0]
        self.assertEqual(data[3], 0x28)


class TestBTMenuBuilds(unittest.TestCase):

    def test_top_level_menu(self):
        from modules.badusb.badusb_menu import build_badusb_menu
        entries = build_badusb_menu(config=None, display=None)
        labels = [e.label for e in entries]
        self.assertIn('USB (Wired)',    labels)
        self.assertIn('Bluetooth (BT)', labels)
        self.assertIn('Saved Payloads', labels)

    def test_usb_submenu(self):
        from modules.badusb.badusb_menu import _build_usb_menu
        entries = _build_usb_menu('/dev/hidg0', None)
        labels = [e.label for e in entries]
        self.assertIn('Run Payload', labels)
        self.assertIn('Type Text',   labels)
        self.assertIn('HID Status',  labels)

    def test_bt_submenu(self):
        from modules.badusb.badusb_menu import _build_bt_menu
        entries = _build_bt_menu(None)
        labels = [e.label for e in entries]
        self.assertIn('Pair & Run Payload', labels)
        self.assertIn('Pair & Type Text',   labels)
        self.assertIn('BT Status',          labels)


if __name__ == '__main__':
    unittest.main()
