"""Unit tests for TetrisGame and FlappyGame logic (no display required)."""
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from modules.games.tetris import TetrisGame, ROWS, COLS
from modules.games.flappy import FlappyGame, H, W, BIRD_X, PIPE_W, PIPE_GAP, PIPE_SPEED


# ---------------------------------------------------------------------------
# Tetris tests
# ---------------------------------------------------------------------------

class TestTetrisGame(unittest.TestCase):

    def setUp(self):
        self.game = TetrisGame()

    def test_initial_board_empty(self):
        for r in range(ROWS):
            for c in range(COLS):
                self.assertIsNone(self.game.board[r][c])

    def test_piece_spawns_on_init(self):
        self.assertIsNotNone(self.game._shape)
        self.assertTrue(self.game.alive)

    def test_move_left_decrements_px(self):
        old_px = self.game._px
        self.game.move_left()
        self.assertLess(self.game._px, old_px)

    def test_move_right_increments_px(self):
        old_px = self.game._px
        self.game.move_right()
        self.assertGreater(self.game._px, old_px)

    def test_rotate_changes_shape(self):
        # Force a T piece, which has a non-symmetric rotation
        self.game._shape = [[0, 1, 0], [1, 1, 1]]
        self.game._px = 3
        self.game._py = 0
        original = [row[:] for row in self.game._shape]
        self.game.rotate()
        self.assertNotEqual(self.game._shape, original)

    def test_hard_drop_locks_piece(self):
        self.game.hard_drop()
        has_cell = any(
            self.game.board[r][c] is not None
            for r in range(ROWS)
            for c in range(COLS)
        )
        self.assertTrue(has_cell)

    def test_score_increases_on_line_clear(self):
        color = (255, 0, 0)
        self.game.board[19] = [color] * COLS
        old_score = self.game.score
        self.game._clear_lines()
        self.assertGreater(self.game.score, old_score)

    def test_level_increases_every_10_lines(self):
        self.game.lines = 9
        color = (255, 0, 0)
        self.game.board[19] = [color] * COLS
        self.game._clear_lines()   # 1 line cleared → total 10 → level 2
        self.assertEqual(self.game.level, 2)

    def test_fall_interval_decreases_with_level(self):
        g1 = TetrisGame()
        g1.level = 1
        g5 = TetrisGame()
        g5.level = 5
        self.assertGreater(g1.fall_interval, g5.fall_interval)

    def test_ghost_y_below_or_equal_piece_y(self):
        self.assertGreaterEqual(self.game.ghost_y(), self.game._py)

    def test_alive_false_after_overflow(self):
        color = (255, 0, 0)
        for r in range(4):
            self.game.board[r] = [color] * COLS
        self.game.alive = True
        self.game._spawn()
        self.assertFalse(self.game.alive)


# ---------------------------------------------------------------------------
# Flappy Bird tests
# ---------------------------------------------------------------------------

class TestFlappyGame(unittest.TestCase):

    def setUp(self):
        self.game = FlappyGame()

    def test_initial_state(self):
        self.assertTrue(self.game.alive)
        self.assertEqual(self.game.score, 0)
        self.assertAlmostEqual(self.game.bird_y, H / 2)

    def test_flap_sets_negative_velocity(self):
        self.game.flap()
        self.assertLess(self.game.bird_vy, 0)

    def test_gravity_pulls_bird_down(self):
        initial_y = self.game.bird_y
        self.game.step()
        self.assertGreater(self.game.bird_y, initial_y)

    def test_pipe_spawns_on_step(self):
        # Advance frame counter to just before trigger, then step once
        self.game.frame = 99
        self.game.step()
        self.assertGreater(len(self.game.pipes), 0)

    def test_score_increases_when_pipe_passed(self):
        # Pipe right-edge is just right of BIRD_X; after one step it will pass
        gap_y  = H // 2 - PIPE_GAP // 2   # centre gap on bird
        pipe_x = float(BIRD_X - PIPE_W + 2)   # right edge = BIRD_X+2
        self.game.pipes = [[pipe_x, gap_y, False]]
        self.game.step()
        self.assertEqual(self.game.score, 1)

    def test_ceiling_kills_bird(self):
        self.game.bird_y = -20.0
        self.game.step()
        self.assertFalse(self.game.alive)

    def test_floor_kills_bird(self):
        self.game.bird_y = float(H + 20)
        self.game.step()
        self.assertFalse(self.game.alive)

    def test_pipe_collision_kills_bird(self):
        # Pipe overlaps bird horizontally; gap is far above bird_y
        self.game.pipes = [[float(BIRD_X), 10, False]]
        # bird_y = H/2 = 240; gap ends at 10+155=165 → bird below gap
        self.game.step()
        self.assertFalse(self.game.alive)


if __name__ == '__main__':
    unittest.main()
