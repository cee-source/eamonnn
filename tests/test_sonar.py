"""Tests for the Sonar module."""
import math
import time
import unittest

from modules.sonar.radar_display import OLEDRadar, TerminalRadar
from modules.sonar.hcsr04 import HCSR04, SPEED_OF_SOUND_CM_S


class TestDistanceCalc(unittest.TestCase):

    def test_speed_of_sound_constant(self):
        # 34300 cm/s is standard value at ~20°C
        self.assertAlmostEqual(SPEED_OF_SOUND_CM_S, 34300, delta=500)

    def test_pulse_to_distance(self):
        # 1000µs echo → 17.15cm (round trip / 2)
        pulse_us = 1000
        dist = (pulse_us * 1e-6 * SPEED_OF_SOUND_CM_S) / 2.0
        self.assertAlmostEqual(dist, 17.15, places=1)

    def test_100cm_pulse_width(self):
        # 100cm → pulse = 2 * 100 / 34300 seconds = 5831µs
        expected_us = (2 * 100 / SPEED_OF_SOUND_CM_S) * 1e6
        self.assertAlmostEqual(expected_us, 5831, delta=10)


class TestOLEDRadarPolarConvert(unittest.TestCase):

    def setUp(self):
        self.radar = OLEDRadar(device=None, max_range_cm=300.0)

    def test_90deg_points_up(self):
        # 90° straight up from centre-bottom should be at top centre
        x, y = self.radar._polar_to_xy(90, 300)
        # x should be near CX=64, y should be near top (CY - RADIUS)
        self.assertAlmostEqual(x, OLEDRadar.CX, delta=2)
        self.assertAlmostEqual(y, OLEDRadar.CY - OLEDRadar.RADIUS, delta=2)

    def test_0deg_points_left(self):
        x, y = self.radar._polar_to_xy(0, 300)
        self.assertLess(x, OLEDRadar.CX)
        self.assertAlmostEqual(y, OLEDRadar.CY, delta=2)

    def test_180deg_points_right(self):
        x, y = self.radar._polar_to_xy(180, 300)
        self.assertGreater(x, OLEDRadar.CX)
        self.assertAlmostEqual(y, OLEDRadar.CY, delta=2)

    def test_zero_distance_is_centre(self):
        x, y = self.radar._polar_to_xy(90, 0)
        self.assertEqual(x, OLEDRadar.CX)
        self.assertEqual(y, OLEDRadar.CY)

    def test_hit_update(self):
        self.radar.update(45, 150.0)
        self.assertEqual(len(self.radar._hits), 1)
        angle, dist, ts = self.radar._hits[0]
        self.assertEqual(angle, 45)
        self.assertEqual(dist, 150.0)

    def test_none_distance_not_stored(self):
        self.radar.update(45, None)
        self.assertEqual(len(self.radar._hits), 0)


class TestTerminalRadarPolarConvert(unittest.TestCase):

    def setUp(self):
        self.radar = TerminalRadar(max_range_cm=300.0)

    def test_90deg_top_row(self):
        row, col = self.radar._polar_to_rc(90, 300)
        self.assertAlmostEqual(col, TerminalRadar.CX, delta=1)
        self.assertLess(row, TerminalRadar.CY)

    def test_hit_stored(self):
        self.radar.update(90, 100.0)
        self.assertEqual(len(self.radar._hits), 1)


class TestSonarMenu(unittest.TestCase):

    def test_menu_builds(self):
        from modules.sonar.sonar_menu import build_sonar_menu
        entries = build_sonar_menu(config=None, display=None)
        self.assertEqual(len(entries), 3)
        labels = [e.label for e in entries]
        self.assertIn("Radar Sweep",  labels)
        self.assertIn("Single Ping",  labels)
        self.assertIn("Servo Test",   labels)

    def test_entries_have_actions(self):
        from modules.sonar.sonar_menu import build_sonar_menu
        entries = build_sonar_menu(config=None, display=None)
        for e in entries:
            self.assertIsNotNone(e.action)


if __name__ == '__main__':
    unittest.main()
