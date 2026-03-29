"""Tests for IR decoder module — no hardware required."""
import sys
import os
import unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from modules.infrared.ir_decoder import decode


def make_nec_pulses(address: int, command: int) -> list:
    pulses = [(1, 9000), (0, 4500)]
    for val in [address, address ^ 0xFF, command, command ^ 0xFF]:
        for i in range(8):
            pulses.append((1, 562))
            pulses.append((0, 1687 if (val >> i) & 1 else 562))
    pulses.append((1, 562))
    return pulses


def make_sony_pulses(address: int, command: int) -> list:
    pulses = [(1, 2400)]
    bits = [(command >> i) & 1 for i in range(7)] + [(address >> i) & 1 for i in range(5)]
    for bit in bits:
        pulses.append((0, 1200 if bit else 600))
        pulses.append((1, 600))
    return pulses


class TestNECDecoder(unittest.TestCase):
    def test_decode_valid_nec(self):
        result = decode(make_nec_pulses(0x04, 0x09))
        self.assertIsNotNone(result)
        self.assertEqual(result.protocol, 'NEC')
        self.assertEqual(result.address, 0x04)
        self.assertEqual(result.command, 0x09)

    def test_decode_zero_values(self):
        result = decode(make_nec_pulses(0x00, 0x00))
        self.assertIsNotNone(result)
        self.assertEqual(result.address, 0x00)
        self.assertEqual(result.command, 0x00)

    def test_decode_max_values(self):
        result = decode(make_nec_pulses(0xFF, 0xFF))
        self.assertIsNotNone(result)
        self.assertEqual(result.address, 0xFF)
        self.assertEqual(result.command, 0xFF)

    def test_decode_returns_raw(self):
        pulses = make_nec_pulses(0x10, 0x20)
        result = decode(pulses)
        self.assertIsNotNone(result)
        self.assertEqual(len(result.raw), len(pulses))

    def test_too_short_returns_none(self):
        self.assertIsNone(decode([(1, 9000), (0, 4500)]))

    def test_empty_returns_none(self):
        self.assertIsNone(decode([]))

    def test_bad_header_returns_none(self):
        pulses = make_nec_pulses(0x01, 0x01)
        pulses[0] = (1, 5000)
        self.assertIsNone(decode(pulses))


class TestSonyDecoder(unittest.TestCase):
    def test_decode_valid_sony(self):
        result = decode(make_sony_pulses(0x01, 0x15))
        self.assertIsNotNone(result)
        self.assertEqual(result.protocol, 'SONY_SIRC12')
        self.assertEqual(result.address, 0x01)
        self.assertEqual(result.command, 0x15)

    def test_decode_zero_values(self):
        result = decode(make_sony_pulses(0x00, 0x00))
        self.assertIsNotNone(result)
        self.assertEqual(result.address, 0x00)
        self.assertEqual(result.command, 0x00)


class TestDecodeUnknown(unittest.TestCase):
    def test_random_pulses_return_none(self):
        self.assertIsNone(decode([(1, 1000), (0, 500)] * 5))


if __name__ == '__main__':
    unittest.main()
