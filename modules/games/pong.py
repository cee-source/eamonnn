"""
Pong game for terminal (curses).
Player 1: W/S keys.  Player 2: UP/DOWN arrows (or AI).
First to 7 points wins.
"""
from __future__ import annotations

import curses
import random
import time


WINNING_SCORE = 7


class PongGame:
    def __init__(self, h: int, w: int, vs_ai: bool = True) -> None:
        self.h = h
        self.w = w
        self.vs_ai = vs_ai
        self.reset()

    def reset(self) -> None:
        h, w = self.h, self.w
        self.ball   = [w // 2, h // 2]
        self.bvel   = [random.choice([-1, 1]), random.choice([-1, 1])]
        self.p1y    = h // 2
        self.p2y    = h // 2
        self.pad_h  = 4
        self.score  = [0, 0]

    def step(self, p1_dir: int, p2_dir: int) -> tuple[bool, int]:
        """
        Advance one frame.
        p1_dir/p2_dir: -1 up, 0 still, +1 down
        Returns (still_playing, scorer)  scorer=0 means no score this frame
        """
        h, w = self.h, self.w

        # Move paddles
        self.p1y = max(self.pad_h, min(h - self.pad_h - 1, self.p1y + p1_dir))

        if self.vs_ai:
            # Simple AI: track ball
            if self.ball[1] < self.p2y:
                self.p2y = max(self.pad_h, self.p2y - 1)
            elif self.ball[1] > self.p2y:
                self.p2y = min(h - self.pad_h - 1, self.p2y + 1)
        else:
            self.p2y = max(self.pad_h, min(h - self.pad_h - 1, self.p2y + p2_dir))

        # Move ball
        self.ball[0] += self.bvel[0]
        self.ball[1] += self.bvel[1]

        # Top/bottom bounce
        if self.ball[1] <= 1 or self.ball[1] >= h - 2:
            self.bvel[1] *= -1

        scorer = 0

        # Left paddle (x=1)
        if self.ball[0] <= 2:
            if abs(self.ball[1] - self.p1y) <= self.pad_h:
                self.bvel[0] = abs(self.bvel[0])   # bounce right
                # Add slight vertical deflection based on hit position
                offset = self.ball[1] - self.p1y
                self.bvel[1] = 1 if offset > 0 else -1
            else:
                self.score[1] += 1
                scorer = 2
                self._reset_ball()

        # Right paddle
        elif self.ball[0] >= w - 3:
            if abs(self.ball[1] - self.p2y) <= self.pad_h:
                self.bvel[0] = -abs(self.bvel[0])  # bounce left
                offset = self.ball[1] - self.p2y
                self.bvel[1] = 1 if offset > 0 else -1
            else:
                self.score[0] += 1
                scorer = 1
                self._reset_ball()

        winner = self._check_winner()
        return (winner == 0), scorer

    def _reset_ball(self) -> None:
        self.ball = [self.w // 2, self.h // 2]
        self.bvel = [random.choice([-1, 1]), random.choice([-1, 1])]

    def _check_winner(self) -> int:
        if self.score[0] >= WINNING_SCORE:
            return 1
        if self.score[1] >= WINNING_SCORE:
            return 2
        return 0


def play_pong(display=None, vs_ai: bool = True) -> None:
    if display and hasattr(display, '_stdscr') and display._stdscr:
        _play_pong_curses(display._stdscr, vs_ai)
    else:
        scr = curses.initscr()
        try:
            curses.noecho(); curses.cbreak(); curses.curs_set(0)
            scr.keypad(True)
            _play_pong_curses(scr, vs_ai)
        finally:
            curses.nocbreak(); curses.echo(); curses.endwin()


def _play_pong_curses(scr, vs_ai: bool) -> None:
    h, w = scr.getmaxyx()
    game = PongGame(h - 2, w - 2, vs_ai=vs_ai)
    scr.timeout(60)   # ~16fps

    p1_dir = p2_dir = 0

    while True:
        ch = scr.getch()
        p1_dir = p2_dir = 0

        if ch == ord('w'):   p1_dir = -1
        elif ch == ord('s'): p1_dir =  1
        elif not vs_ai:
            if ch == curses.KEY_UP:   p2_dir = -1
            elif ch == curses.KEY_DOWN: p2_dir = 1
        if ch in (27, ord('q')):
            break

        playing, _ = game.step(p1_dir, p2_dir)

        scr.clear()
        # Scores
        scr.addstr(0, w//2 - 6, f'P1: {game.score[0]}   P2: {game.score[1]}')
        # Border
        scr.addstr(1, 0, '-' * (w - 1))
        scr.addstr(h - 2, 0, '-' * (w - 1))
        # Paddles
        ph = game.pad_h
        for dy in range(-ph, ph + 1):
            y = game.p1y + dy + 2
            if 2 <= y < h - 2:
                try: scr.addstr(y, 1, '|')
                except curses.error: pass
            y = game.p2y + dy + 2
            if 2 <= y < h - 2:
                try: scr.addstr(y, w - 2, '|')
                except curses.error: pass
        # Ball
        by, bx = game.ball[1] + 2, game.ball[0]
        if 2 <= by < h - 2 and 0 <= bx < w - 1:
            try: scr.addstr(by, bx, 'O')
            except curses.error: pass

        if not playing:
            winner = 'P1' if game.score[0] >= WINNING_SCORE else 'P2'
            scr.addstr(h // 2, w // 2 - 5, f'{winner} WINS!')
            scr.addstr(h // 2 + 1, w // 2 - 8, 'Press R to restart')
            scr.refresh()
            while True:
                c = scr.getch()
                if c == ord('r'):
                    game.reset()
                    break
                elif c in (27, ord('q')):
                    return

        scr.refresh()
