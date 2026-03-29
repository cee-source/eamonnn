"""
Snake game for OLED (128x64) or terminal.
Button controls: UP/DOWN/LEFT/RIGHT to steer, SELECT to pause.
"""
from __future__ import annotations

import curses
import random
import time
from typing import Optional


GRID_W = 21   # cells wide  (128px / 6px per cell)
GRID_H = 9    # cells tall  (64px  / 7px per cell)
CELL_W = 6
CELL_H = 7

UP    = (0, -1)
DOWN  = (0,  1)
LEFT  = (-1, 0)
RIGHT = (1,  0)


class SnakeGame:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        cx, cy = GRID_W // 2, GRID_H // 2
        self.snake  = [(cx, cy), (cx-1, cy), (cx-2, cy)]
        self.direction = RIGHT
        self.next_dir  = RIGHT
        self.food   = self._new_food()
        self.score  = 0
        self.alive  = True
        self.paused = False

    def _new_food(self) -> tuple[int, int]:
        while True:
            pos = (random.randint(0, GRID_W-1), random.randint(0, GRID_H-1))
            if pos not in self.snake:
                return pos

    def steer(self, direction: tuple[int, int]) -> None:
        # Prevent reversing
        if (direction[0] * -1, direction[1] * -1) != self.direction:
            self.next_dir = direction

    def step(self) -> bool:
        if not self.alive or self.paused:
            return self.alive
        self.direction = self.next_dir
        head = (self.snake[0][0] + self.direction[0],
                self.snake[0][1] + self.direction[1])
        # Wall collision
        if not (0 <= head[0] < GRID_W and 0 <= head[1] < GRID_H):
            self.alive = False
            return False
        # Self collision
        if head in self.snake:
            self.alive = False
            return False
        self.snake.insert(0, head)
        if head == self.food:
            self.score += 10
            self.food = self._new_food()
        else:
            self.snake.pop()
        return True


def play_snake(display=None) -> int:
    """Run the snake game. Returns final score."""
    game = SnakeGame()

    if display and hasattr(display, '_stdscr') and display._stdscr:
        return _play_snake_curses(game, display._stdscr)
    elif display:
        return _play_snake_oled(game, display)
    else:
        scr = curses.initscr()
        try:
            curses.noecho(); curses.cbreak(); curses.curs_set(0)
            scr.keypad(True)
            return _play_snake_curses(game, scr)
        finally:
            curses.nocbreak(); curses.echo(); curses.endwin()


def _play_snake_curses(game: SnakeGame, scr) -> int:
    scr.timeout(150)
    key_map = {
        curses.KEY_UP: UP, curses.KEY_DOWN: DOWN,
        curses.KEY_LEFT: LEFT, curses.KEY_RIGHT: RIGHT,
        ord('w'): UP, ord('s'): DOWN,
        ord('a'): LEFT, ord('d'): RIGHT,
    }
    while game.alive:
        ch = scr.getch()
        if ch in key_map:
            game.steer(key_map[ch])
        elif ch == ord(' '):
            game.paused = not game.paused
        elif ch in (27, ord('q')):
            break

        game.step()
        h, w = scr.getmaxyx()
        scr.clear()
        scr.addstr(0, 0, f'Snake  Score: {game.score}')
        for x, y in game.snake:
            if 0 <= y+2 < h and 0 <= x < w-1:
                scr.addstr(y+2, x*2, '##')
        fx, fy = game.food
        if 0 <= fy+2 < h and 0 <= fx*2 < w-1:
            scr.addstr(fy+2, fx*2, '()')
        if not game.alive:
            scr.addstr(h//2, max(0, w//2-6), 'GAME OVER')
        scr.refresh()

    time.sleep(1)
    return game.score


def _play_snake_oled(game: SnakeGame, display) -> int:
    """Render on SSD1306 OLED using luma.oled canvas."""
    try:
        from luma.core.render import canvas
        from PIL import ImageDraw
    except ImportError:
        return 0

    key_map = {}
    if hasattr(display, 'getch'):
        key_map = {
            curses.KEY_UP: UP, curses.KEY_DOWN: DOWN,
            curses.KEY_LEFT: LEFT, curses.KEY_RIGHT: RIGHT,
        }

    while game.alive:
        if hasattr(display, 'getch'):
            display._stdscr.timeout(150)
            ch = display.getch()
            if ch in key_map:
                game.steer(key_map[ch])
            elif ch in (27, ord('q')):
                break

        game.step()

        with canvas(display._device) as draw:
            draw.text((0, 0), f'Score:{game.score}', fill='white')
            for sx, sy in game.snake:
                x0, y0 = sx * CELL_W, sy * CELL_H + 10
                draw.rectangle([x0, y0, x0+CELL_W-1, y0+CELL_H-1], fill='white')
            fx, fy = game.food
            x0, y0 = fx * CELL_W, fy * CELL_H + 10
            draw.ellipse([x0, y0, x0+CELL_W-1, y0+CELL_H-1], fill='white')

        time.sleep(0.15)

    return game.score
