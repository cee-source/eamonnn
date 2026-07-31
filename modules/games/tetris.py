"""Tetris for terminal (curses) or 3.5-inch touchscreen (pygame)."""
from __future__ import annotations

import curses
import random
import time
from typing import Optional, List

COLS = 10
ROWS = 20
SCORE_TABLE = {1: 100, 2: 300, 3: 500, 4: 800}

TETROMINOES = {
    'I': {'shape': [[1, 1, 1, 1]],         'color': (0,   240, 240)},
    'O': {'shape': [[1, 1], [1, 1]],        'color': (240, 240,   0)},
    'T': {'shape': [[0, 1, 0], [1, 1, 1]], 'color': (160,   0, 240)},
    'S': {'shape': [[0, 1, 1], [1, 1, 0]], 'color': (0,   240,   0)},
    'Z': {'shape': [[1, 1, 0], [0, 1, 1]], 'color': (240,   0,   0)},
    'J': {'shape': [[1, 0, 0], [1, 1, 1]], 'color': (0,     0, 240)},
    'L': {'shape': [[0, 0, 1], [1, 1, 1]], 'color': (240, 160,   0)},
}


class TetrisGame:
    def __init__(self) -> None:
        self.board: List[List] = [[None] * COLS for _ in range(ROWS)]
        self.score     = 0
        self.lines     = 0
        self.level     = 1
        self.alive     = True
        self._shape: Optional[List[List[int]]] = None
        self._color: Optional[tuple] = None
        self._px       = 0
        self._py       = 0
        self._last_fall = time.monotonic()
        self._spawn()

    # ------------------------------------------------------------------ helpers

    def _valid(self, shape: List[List[int]], px: int, py: int) -> bool:
        for r, row in enumerate(shape):
            for c, cell in enumerate(row):
                if cell:
                    nr, nc = py + r, px + c
                    if nc < 0 or nc >= COLS or nr >= ROWS:
                        return False
                    if nr >= 0 and self.board[nr][nc] is not None:
                        return False
        return True

    def _spawn(self) -> None:
        key = random.choice(list(TETROMINOES))
        defn = TETROMINOES[key]
        self._shape = [row[:] for row in defn['shape']]
        self._color = defn['color']
        self._px = (COLS - len(self._shape[0])) // 2
        self._py = 0
        if not self._valid(self._shape, self._px, self._py):
            self.alive = False

    def _lock(self) -> None:
        for r, row in enumerate(self._shape):
            for c, cell in enumerate(row):
                if cell:
                    nr = self._py + r
                    nc = self._px + c
                    if 0 <= nr < ROWS and 0 <= nc < COLS:
                        self.board[nr][nc] = self._color
        self._clear_lines()
        self._spawn()

    def _clear_lines(self) -> None:
        new_board = [row for row in self.board if any(cell is None for cell in row)]
        cleared = ROWS - len(new_board)
        if cleared:
            for _ in range(cleared):
                new_board.insert(0, [None] * COLS)
            self.board = new_board
            self.lines += cleared
            self.score += SCORE_TABLE.get(cleared, 0) * self.level
            self.level  = self.lines // 10 + 1

    # ------------------------------------------------------------------ controls

    def move_left(self) -> None:
        if self.alive and self._valid(self._shape, self._px - 1, self._py):
            self._px -= 1

    def move_right(self) -> None:
        if self.alive and self._valid(self._shape, self._px + 1, self._py):
            self._px += 1

    def rotate(self) -> None:
        if not self.alive:
            return
        rotated = [list(row) for row in zip(*reversed(self._shape))]
        if self._valid(rotated, self._px, self._py):
            self._shape = rotated
        elif self._valid(rotated, self._px - 1, self._py):
            self._shape = rotated
            self._px -= 1
        elif self._valid(rotated, self._px + 1, self._py):
            self._shape = rotated
            self._px += 1

    def soft_drop(self) -> None:
        if not self.alive:
            return
        if self._valid(self._shape, self._px, self._py + 1):
            self._py    += 1
            self.score  += 1
        else:
            self._lock()

    def hard_drop(self) -> None:
        if not self.alive:
            return
        gy          = self.ghost_y()
        dist        = gy - self._py
        self._py    = gy
        self.score += dist * 2
        self._lock()

    def ghost_y(self) -> int:
        gy = self._py
        while self._valid(self._shape, self._px, gy + 1):
            gy += 1
        return gy

    def step(self) -> bool:
        """Auto-fall based on fall_interval. Returns alive."""
        if not self.alive:
            return False
        now = time.monotonic()
        if now - self._last_fall >= self.fall_interval:
            self._last_fall = now
            if self._valid(self._shape, self._px, self._py + 1):
                self._py += 1
            else:
                self._lock()
        return self.alive

    @property
    def fall_interval(self) -> float:
        return max(0.05, 0.5 - (self.level - 1) * 0.05)


# ---------------------------------------------------------------------------
# Curses renderer
# ---------------------------------------------------------------------------

def _draw_curses(game: TetrisGame, scr) -> None:
    h, w = scr.getmaxyx()
    scr.clear()

    header = f'Score:{game.score:6d}  Level:{game.level:2d}  Lines:{game.lines:3d}'
    try:
        scr.addstr(0, 0, header[:w - 1])
    except curses.error:
        pass

    # Build display buffer: 0=empty, 1=ghost, 2=piece, 3=board
    buf = [[0] * COLS for _ in range(ROWS)]

    for r in range(ROWS):
        for c in range(COLS):
            if game.board[r][c] is not None:
                buf[r][c] = 3

    if game._shape:
        gy = game.ghost_y()
        for r, row in enumerate(game._shape):
            for c, cell in enumerate(row):
                if cell:
                    nr, nc = gy + r, game._px + c
                    if 0 <= nr < ROWS and 0 <= nc < COLS and buf[nr][nc] == 0:
                        buf[nr][nc] = 1

        for r, row in enumerate(game._shape):
            for c, cell in enumerate(row):
                if cell:
                    nr, nc = game._py + r, game._px + c
                    if 0 <= nr < ROWS and 0 <= nc < COLS:
                        buf[nr][nc] = 2

    try:
        scr.addstr(1, 0, '+' + '--' * COLS + '+')
    except curses.error:
        pass

    for r in range(ROWS):
        row_str = '|'
        for c in range(COLS):
            v = buf[r][c]
            if v == 0:
                row_str += '  '
            elif v == 1:
                row_str += '..'
            elif v == 2:
                row_str += '[]'
            else:
                row_str += '##'
        row_str += '|'
        try:
            scr.addstr(2 + r, 0, row_str[:w - 1])
        except curses.error:
            pass

    try:
        scr.addstr(2 + ROWS, 0, '+' + '--' * COLS + '+')
    except curses.error:
        pass

    if not game.alive:
        msg = ' GAME OVER '
        try:
            scr.addstr(h // 2, max(0, w // 2 - len(msg) // 2), msg)
        except curses.error:
            pass

    scr.refresh()


def _play_tetris_curses(game: TetrisGame, scr) -> int:
    scr.timeout(50)

    while True:
        ch = scr.getch()
        if ch in (ord('q'), 27):
            break
        elif ch in (curses.KEY_LEFT, ord('a')):
            game.move_left()
        elif ch in (curses.KEY_RIGHT, ord('d')):
            game.move_right()
        elif ch in (curses.KEY_UP, ord('w')):
            game.rotate()
        elif ch in (curses.KEY_DOWN, ord('s')):
            game.soft_drop()
        elif ch == ord(' '):
            game.hard_drop()

        game.step()
        _draw_curses(game, scr)

        if not game.alive:
            time.sleep(1)
            break

    return game.score


# ---------------------------------------------------------------------------
# Pygame renderer
# ---------------------------------------------------------------------------

BOARD_X  = 60
BOARD_Y  = 50
CELL     = 20
HEADER_H = 50
CTRL_H   = 30
CTRL_Y   = 480 - CTRL_H   # 450

C_BG    = ( 10,  12,  20)
C_GRID  = ( 30,  35,  50)
C_PANEL = ( 22,  26,  42)
C_BTN   = ( 25,  35,  60)
C_WHITE = (255, 255, 255)
C_GHOST = ( 60,  65,  80)
C_DIM   = (130, 135, 150)


def _draw_pygame(game: TetrisGame, screen, pg, font_sm, font_md) -> None:
    screen.fill(C_BG)

    # Header bar
    pg.draw.rect(screen, C_PANEL, (0, 0, 320, HEADER_H))
    hdr = font_md.render(
        f'Score:{game.score:6d}  Lv:{game.level}  Ln:{game.lines}',
        True, C_WHITE)
    screen.blit(hdr, (4, (HEADER_H - hdr.get_height()) // 2))

    # Board background
    pg.draw.rect(screen, C_PANEL, (BOARD_X, BOARD_Y, COLS * CELL, ROWS * CELL))

    # Grid lines
    for col in range(COLS + 1):
        x = BOARD_X + col * CELL
        pg.draw.line(screen, C_GRID, (x, BOARD_Y), (x, BOARD_Y + ROWS * CELL))
    for row in range(ROWS + 1):
        y = BOARD_Y + row * CELL
        pg.draw.line(screen, C_GRID, (BOARD_X, y), (BOARD_X + COLS * CELL, y))

    # Locked board cells
    for r in range(ROWS):
        for c in range(COLS):
            color = game.board[r][c]
            if color is not None:
                pg.draw.rect(screen, color,
                             (BOARD_X + c * CELL + 1, BOARD_Y + r * CELL + 1,
                              CELL - 2, CELL - 2))

    if game._shape:
        # Ghost piece (outline only)
        gy = game.ghost_y()
        for r, row in enumerate(game._shape):
            for c, cell in enumerate(row):
                if cell:
                    nr, nc = gy + r, game._px + c
                    if 0 <= nr < ROWS and 0 <= nc < COLS:
                        pg.draw.rect(screen, C_GHOST,
                                     (BOARD_X + nc * CELL + 1, BOARD_Y + nr * CELL + 1,
                                      CELL - 2, CELL - 2), 1)

        # Active piece
        for r, row in enumerate(game._shape):
            for c, cell in enumerate(row):
                if cell:
                    nr, nc = game._py + r, game._px + c
                    if 0 <= nr < ROWS and 0 <= nc < COLS:
                        pg.draw.rect(screen, game._color,
                                     (BOARD_X + nc * CELL + 1, BOARD_Y + nr * CELL + 1,
                                      CELL - 2, CELL - 2))

    # Side panel
    pg.draw.rect(screen, C_PANEL, (265, BOARD_Y, 55, ROWS * CELL))
    lbl = font_sm.render('NEXT', True, C_DIM)
    screen.blit(lbl, (268, BOARD_Y + 8))

    # Controls bar
    pg.draw.rect(screen, C_BTN, (0, CTRL_Y, 320, CTRL_H))
    for text, x0, x1 in [('LEFT', 0, 80), ('ROT', 80, 160), ('DROP', 160, 240), ('RIGHT', 240, 320)]:
        pg.draw.line(screen, C_GRID, (x0, CTRL_Y), (x0, 480), 1)
        s = font_sm.render(text, True, C_WHITE)
        mid = (x0 + x1) // 2
        screen.blit(s, (mid - s.get_width() // 2, CTRL_Y + (CTRL_H - s.get_height()) // 2))


def _play_tetris_pygame(game: TetrisGame, display) -> int:
    pg     = display._pg
    screen = display._screen
    clock  = pg.time.Clock()

    font_sm = pg.font.SysFont('freemono', 16)
    font_md = pg.font.SysFont('freemono', 18, bold=True)
    font_lg = pg.font.SysFont('freemono', 28, bold=True)

    while game.alive:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return game.score
            elif event.type == pg.MOUSEBUTTONDOWN:
                x, y = event.pos
                if y >= CTRL_Y:
                    if x < 80:
                        game.move_left()
                    elif x < 160:
                        game.rotate()
                    elif x < 240:
                        game.hard_drop()
                    else:
                        game.move_right()

        game.step()
        _draw_pygame(game, screen, pg, font_sm, font_md)
        pg.display.flip()
        clock.tick(60)

    # Game over screen
    screen.fill(C_BG)
    surfs = [
        font_lg.render('GAME OVER', True, C_WHITE),
        font_md.render(f'Score: {game.score}', True, C_WHITE),
        font_sm.render('Tap to exit', True, C_DIM),
    ]
    total_h = sum(s.get_height() + 12 for s in surfs)
    y = (480 - total_h) // 2
    for surf in surfs:
        screen.blit(surf, ((320 - surf.get_width()) // 2, y))
        y += surf.get_height() + 12
    pg.display.flip()

    waiting = True
    while waiting:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                waiting = False
            elif event.type == pg.MOUSEBUTTONDOWN:
                waiting = False
        clock.tick(30)

    return game.score


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def play_tetris(display=None) -> int:
    """Run Tetris. Returns final score."""
    from core.display import TouchDisplay
    game = TetrisGame()
    if isinstance(display, TouchDisplay):
        return _play_tetris_pygame(game, display)
    elif display and hasattr(display, '_stdscr') and display._stdscr:
        return _play_tetris_curses(game, display._stdscr)
    else:
        scr = curses.initscr()
        try:
            curses.noecho()
            curses.cbreak()
            curses.curs_set(0)
            scr.keypad(True)
            return _play_tetris_curses(game, scr)
        finally:
            curses.nocbreak()
            curses.echo()
            curses.endwin()
