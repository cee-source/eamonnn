"""Tests for the Cat Videos module."""
import unittest
from modules.cats.cat_player import ANIMATIONS, NYAN_FRAMES, WALKING_CAT_FRAMES, LOAF_CAT_FRAMES, CAT_VIDEO_URLS


class TestCatFrames(unittest.TestCase):

    def test_animation_count(self):
        self.assertEqual(len(ANIMATIONS), 3)

    def test_animation_labels(self):
        labels = [a[0] for a in ANIMATIONS]
        self.assertIn("Nyan Cat", labels)
        self.assertIn("Walking Cat", labels)
        self.assertIn("Loaf Cat", labels)

    def test_nyan_frames_not_empty(self):
        self.assertGreater(len(NYAN_FRAMES), 0)
        for frame in NYAN_FRAMES:
            self.assertEqual(len(frame), 9)

    def test_walking_frames_not_empty(self):
        self.assertGreater(len(WALKING_CAT_FRAMES), 0)
        for frame in WALKING_CAT_FRAMES:
            self.assertEqual(len(frame), 9)

    def test_loaf_frames_not_empty(self):
        self.assertGreater(len(LOAF_CAT_FRAMES), 0)
        for frame in LOAF_CAT_FRAMES:
            self.assertEqual(len(frame), 9)

    def test_fps_positive(self):
        for _, _, fps in ANIMATIONS:
            self.assertGreater(fps, 0)

    def test_video_urls_exist(self):
        self.assertGreater(len(CAT_VIDEO_URLS), 0)
        for url in CAT_VIDEO_URLS:
            self.assertTrue(url.startswith("https://"))


class TestCatMenu(unittest.TestCase):

    def test_menu_builds(self):
        from modules.cats.cat_menu import build_cats_menu
        entries = build_cats_menu(config=None, display=None)
        self.assertEqual(len(entries), 5)
        labels = [e.label for e in entries]
        self.assertIn("Nyan Cat", labels)
        self.assertIn("Walking Cat", labels)
        self.assertIn("Loaf Cat", labels)
        self.assertIn("HDMI: Cat Clips", labels)
        self.assertIn("HDMI: Nyan Cat", labels)

    def test_menu_entries_have_actions(self):
        from modules.cats.cat_menu import build_cats_menu
        entries = build_cats_menu(config=None, display=None)
        for entry in entries:
            self.assertIsNotNone(entry.action)


if __name__ == '__main__':
    unittest.main()
