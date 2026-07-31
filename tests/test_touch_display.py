"""Tests for TouchDisplay and touch-aware MenuEngine."""
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


def _make_pygame_stub():
    """Build a minimal pygame stub so TouchDisplay can be imported."""
    pg = types.ModuleType('pygame')
    pg.FULLSCREEN     = 1
    pg.MOUSEBUTTONDOWN = 1025

    pg.init          = MagicMock()
    pg.quit          = MagicMock()
    pg.display       = MagicMock()
    pg.display.set_mode = MagicMock(return_value=MagicMock())
    pg.display.flip  = MagicMock()
    pg.mouse         = MagicMock()
    pg.event         = MagicMock()
    pg.event.get     = MagicMock(return_value=[])
    pg.draw          = MagicMock()
    pg.draw.rect     = MagicMock()
    pg.draw.line     = MagicMock()

    font_mod = types.ModuleType('pygame.font')
    font_mock = MagicMock()
    surf_mock = MagicMock()
    surf_mock.get_height.return_value = 24
    surf_mock.get_width.return_value  = 80
    font_mock.render.return_value = surf_mock
    font_mod.SysFont = MagicMock(return_value=font_mock)
    pg.font = font_mod

    screen_mock = MagicMock()
    screen_mock.fill = MagicMock()
    screen_mock.blit = MagicMock()
    pg.display.set_mode.return_value = screen_mock

    sys.modules['pygame']      = pg
    sys.modules['pygame.font'] = font_mod
    return pg


_PG_STUB = _make_pygame_stub()


class TestTouchDisplayInit(unittest.TestCase):

    def _make(self):
        with patch.dict('os.environ', {}, clear=False):
            from core.display import TouchDisplay
            return TouchDisplay()

    def test_dimensions(self):
        from core.display import TouchDisplay
        self.assertEqual(TouchDisplay.W, 320)
        self.assertEqual(TouchDisplay.H, 480)

    def test_item_height_positive(self):
        from core.display import TouchDisplay
        self.assertGreater(TouchDisplay.ITEM_H, 0)

    def test_back_height_positive(self):
        from core.display import TouchDisplay
        self.assertGreater(TouchDisplay.BACK_H, 0)

    def test_items_fit_screen(self):
        from core.display import TouchDisplay
        avail   = TouchDisplay.H - TouchDisplay.TITLE_H - TouchDisplay.BACK_H
        max_vis = avail // TouchDisplay.ITEM_H
        self.assertGreater(max_vis, 0)

    def test_all_colors_are_rgb_tuples(self):
        from core.display import TouchDisplay
        for attr in ('C_BG', 'C_SEL', 'C_ACCENT', 'C_TEXT', 'C_BRIGHT', 'C_DIV'):
            color = getattr(TouchDisplay, attr)
            self.assertEqual(len(color), 3, f'{attr} must be RGB')
            for ch in color:
                self.assertGreaterEqual(ch, 0)
                self.assertLessEqual(ch, 255)


class TestTouchZones(unittest.TestCase):

    def _make(self):
        with patch.dict('os.environ', {}, clear=False):
            from core.display import TouchDisplay
            td = TouchDisplay.__new__(TouchDisplay)
            td._pg     = _PG_STUB
            td._screen = _PG_STUB.display.set_mode.return_value
            td._ft     = _PG_STUB.font.SysFont()
            td._fi     = _PG_STUB.font.SysFont()
            td._fs     = _PG_STUB.font.SysFont()
            td._zones  = []
            return td

    def test_draw_menu_populates_zones(self):
        td = self._make()
        td.draw_menu('Test', ['A', 'B', 'C'], 0)
        self.assertGreater(len(td._zones), 0)

    def test_draw_menu_back_zone_at_bottom(self):
        td = self._make()
        td.draw_menu('Test', ['A', 'B'], 0)
        last_zone = td._zones[-1]
        self.assertEqual(last_zone[2], 'back')

    def test_tap_to_zone_back_button(self):
        td = self._make()
        td.draw_menu('Test', ['A', 'B'], 0)
        back_y0 = td._zones[-1][0]
        result  = td.tap_to_zone(10, back_y0 + 5)
        self.assertEqual(result, 'BACK')

    def test_tap_to_zone_item(self):
        td = self._make()
        td.draw_menu('Test', ['Alpha', 'Beta', 'Gamma'], 0)
        item_zones = [(y0, y1, t) for y0, y1, t in td._zones if t != 'back']
        self.assertGreater(len(item_zones), 0)
        y0, y1, idx = item_zones[0]
        result = td.tap_to_zone(10, (y0 + y1) // 2)
        self.assertEqual(result, f'JUMP:{idx}')

    def test_tap_outside_zones_returns_none(self):
        td = self._make()
        td._zones = [(100, 150, 0), (150, 200, 1)]
        self.assertIsNone(td.tap_to_zone(10, 50))

    def test_draw_message_sets_fullscreen_back_zone(self):
        td = self._make()
        td.draw_message(['Hello', 'World'])
        self.assertEqual(len(td._zones), 1)
        y0, y1, target = td._zones[0]
        self.assertEqual(target, 'back')
        self.assertEqual(y0, 0)
        self.assertEqual(y1, td.H)

    def test_get_tap_returns_none_when_no_events(self):
        td = self._make()
        _PG_STUB.event.get.return_value = []
        self.assertIsNone(td.get_tap())

    def test_get_tap_returns_coords_on_click(self):
        td = self._make()
        evt = MagicMock()
        evt.type = _PG_STUB.MOUSEBUTTONDOWN
        evt.pos  = (50, 200)
        _PG_STUB.event.get.return_value = [evt]
        pos = td.get_tap()
        self.assertEqual(pos, (50, 200))


class TestMenuEngineJump(unittest.TestCase):
    """MenuEngine should handle JUMP:N from touch input."""

    def _make_engine(self, entries):
        from core.display import TerminalDisplay
        from core.menu    import MenuEngine
        display = MagicMock(spec=TerminalDisplay)
        display.draw_menu = MagicMock()
        display.draw_message = MagicMock()
        display.clear = MagicMock()
        display.cleanup = MagicMock()
        engine = MenuEngine.__new__(MenuEngine)
        engine._display = display
        engine._input   = MagicMock()
        engine._stack   = []
        engine._running = False
        engine.push(entries)
        return engine

    def test_jump_selects_correct_entry(self):
        from core.menu import MenuEntry
        hit = []
        entries = [
            MenuEntry(label='A', action=lambda: hit.append('A')),
            MenuEntry(label='B', action=lambda: hit.append('B')),
            MenuEntry(label='C', action=lambda: hit.append('C')),
        ]
        engine = self._make_engine(entries)
        keys   = iter(['JUMP:2', None])
        engine._input.get_key.side_effect = lambda: next(keys, None)
        engine._running = True

        import threading
        def _run():
            try:
                engine.run()
            except StopIteration:
                pass

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        t.join(timeout=1)
        self.assertIn('C', hit)

    def test_back_token_pops_stack(self):
        from core.menu import MenuEntry
        sub   = [MenuEntry(label='X', action=lambda: None)]
        root  = [MenuEntry(label='Sub', children=sub)]
        engine = self._make_engine(root)
        keys   = iter(['JUMP:0', 'BACK', None])
        engine._input.get_key.side_effect = lambda: next(keys, None)
        engine._running = True

        import threading
        done = threading.Event()
        def _run():
            try:
                engine.run()
            except StopIteration:
                pass
            done.set()

        threading.Thread(target=_run, daemon=True).start()
        done.wait(timeout=1)
        self.assertEqual(len(engine._stack), 1)


if __name__ == '__main__':
    unittest.main()
