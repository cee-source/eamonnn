"""
Chess game for terminal.
Full rules: castling, en passant, promotion, check/checkmate detection.
Play vs AI (minimax with alpha-beta pruning, depth 3) or vs another player.
"""
from __future__ import annotations

import curses
import copy
import time
from typing import Optional

# Piece constants
EMPTY = '.'
WK, WQ, WR, WB, WN, WP = 'K', 'Q', 'R', 'B', 'N', 'P'
BK, BQ, BR, BB, BN, BP = 'k', 'q', 'r', 'b', 'n', 'p'

WHITE_PIECES = set('KQRBNP')
BLACK_PIECES = set('kqrbnp')

PIECE_VALUES = {
    'P': 100, 'N': 320, 'B': 330, 'R': 500, 'Q': 900, 'K': 20000,
    'p': -100,'n': -320,'b': -330,'r': -500,'q': -900,'k': -20000,
}

INITIAL_BOARD = [
    list('rnbqkbnr'),
    list('pppppppp'),
    list('........'),
    list('........'),
    list('........'),
    list('........'),
    list('PPPPPPPP'),
    list('RNBQKBNR'),
]


def is_white(p: str) -> bool: return p in WHITE_PIECES
def is_black(p: str) -> bool: return p in BLACK_PIECES
def is_empty(p: str) -> bool: return p == EMPTY
def enemy(p: str, white_turn: bool) -> bool:
    return is_black(p) if white_turn else is_white(p)
def friendly(p: str, white_turn: bool) -> bool:
    return is_white(p) if white_turn else is_black(p)


class ChessGame:
    def __init__(self) -> None:
        self.board      = copy.deepcopy(INITIAL_BOARD)
        self.white_turn = True
        self.selected   : Optional[tuple[int,int]] = None
        self.en_passant : Optional[tuple[int,int]] = None
        self.castling   = {'K': True, 'Q': True, 'k': True, 'q': True}
        self.status     = ''
        self.move_count = 0

    # -----------------------------------------------------------------------
    # Move generation
    # -----------------------------------------------------------------------

    def legal_moves(self, r: int, c: int) -> list[tuple[int,int]]:
        piece = self.board[r][c]
        if is_empty(piece):
            return []
        white = is_white(piece)
        moves = self._pseudo_moves(r, c, white)
        # Filter moves that leave own king in check
        legal = []
        for tr, tc in moves:
            nb = copy.deepcopy(self.board)
            nb[tr][tc] = nb[r][c]
            nb[r][c] = EMPTY
            if not self._in_check(nb, white):
                legal.append((tr, tc))
        return legal

    def _pseudo_moves(self, r: int, c: int, white: bool) -> list[tuple[int,int]]:
        piece = self.board[r][c].upper()
        moves = []
        dirs = {
            'R': [(0,1),(0,-1),(1,0),(-1,0)],
            'B': [(1,1),(1,-1),(-1,1),(-1,-1)],
            'Q': [(0,1),(0,-1),(1,0),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)],
        }
        if piece in dirs:
            for dr, dc in dirs[piece]:
                nr, nc = r+dr, c+dc
                while 0 <= nr < 8 and 0 <= nc < 8:
                    if is_empty(self.board[nr][nc]):
                        moves.append((nr, nc))
                    elif enemy(self.board[nr][nc], white):
                        moves.append((nr, nc)); break
                    else:
                        break
                    nr += dr; nc += dc
        elif piece == 'N':
            for dr, dc in [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]:
                nr, nc = r+dr, c+dc
                if 0 <= nr < 8 and 0 <= nc < 8:
                    if not friendly(self.board[nr][nc], white):
                        moves.append((nr, nc))
        elif piece == 'K':
            for dr in [-1,0,1]:
                for dc in [-1,0,1]:
                    if dr == 0 and dc == 0: continue
                    nr, nc = r+dr, c+dc
                    if 0 <= nr < 8 and 0 <= nc < 8:
                        if not friendly(self.board[nr][nc], white):
                            moves.append((nr, nc))
            # Castling
            row = 7 if white else 0
            if r == row and c == 4:
                if white and self.castling['K'] or not white and self.castling['k']:
                    if all(is_empty(self.board[row][cc]) for cc in [5,6]):
                        if self.board[row][7].upper() == 'R':
                            moves.append((row, 6))
                if white and self.castling['Q'] or not white and self.castling['q']:
                    if all(is_empty(self.board[row][cc]) for cc in [1,2,3]):
                        if self.board[row][0].upper() == 'R':
                            moves.append((row, 2))
        elif piece == 'P':
            fwd = -1 if white else 1
            start_row = 6 if white else 1
            # Forward
            nr = r + fwd
            if 0 <= nr < 8 and is_empty(self.board[nr][c]):
                moves.append((nr, c))
                if r == start_row and is_empty(self.board[r+2*fwd][c]):
                    moves.append((r+2*fwd, c))
            # Captures
            for dc in [-1, 1]:
                nc = c + dc
                if 0 <= nr < 8 and 0 <= nc < 8:
                    if enemy(self.board[nr][nc], white):
                        moves.append((nr, nc))
                    elif (nr, nc) == self.en_passant:
                        moves.append((nr, nc))
        return moves

    def _in_check(self, board: list, white: bool) -> bool:
        king = WK if white else BK
        kr = kc = -1
        for r in range(8):
            for c in range(8):
                if board[r][c] == king:
                    kr, kc = r, c
        if kr == -1:
            return True
        # Check if any enemy piece attacks king
        for r in range(8):
            for c in range(8):
                p = board[r][c]
                if (white and is_black(p)) or (not white and is_white(p)):
                    for tr, tc in self._pseudo_moves_on(board, r, c, not white):
                        if (tr, tc) == (kr, kc):
                            return True
        return False

    def _pseudo_moves_on(self, board, r, c, white) -> list:
        orig = self.board
        self.board = board
        moves = self._pseudo_moves(r, c, white)
        self.board = orig
        return moves

    # -----------------------------------------------------------------------
    # Apply move
    # -----------------------------------------------------------------------

    def apply_move(self, fr: int, fc: int, tr: int, tc: int) -> None:
        piece = self.board[fr][fc]
        self.en_passant = None

        # Castling
        if piece.upper() == 'K' and abs(fc - tc) == 2:
            row = fr
            if tc == 6:  # kingside
                self.board[row][5] = self.board[row][7]
                self.board[row][7] = EMPTY
            else:        # queenside
                self.board[row][3] = self.board[row][0]
                self.board[row][0] = EMPTY
            if is_white(piece):
                self.castling['K'] = self.castling['Q'] = False
            else:
                self.castling['k'] = self.castling['q'] = False

        # En passant capture
        if piece.upper() == 'P' and (tr, tc) == (self.en_passant or (-1,-1)):
            cap_r = tr + (1 if is_white(piece) else -1)
            self.board[cap_r][tc] = EMPTY

        # Set en passant target
        if piece.upper() == 'P' and abs(tr - fr) == 2:
            self.en_passant = ((fr + tr) // 2, tc)

        # Promotion (auto-queen)
        if piece == WP and tr == 0:
            piece = WQ
        elif piece == BP and tr == 7:
            piece = BQ

        # Update castling rights
        if piece == WK: self.castling['K'] = self.castling['Q'] = False
        if piece == BK: self.castling['k'] = self.castling['q'] = False
        if piece == WR:
            if fc == 0: self.castling['Q'] = False
            if fc == 7: self.castling['K'] = False
        if piece == BR:
            if fc == 0: self.castling['q'] = False
            if fc == 7: self.castling['k'] = False

        self.board[tr][tc] = piece
        self.board[fr][fc] = EMPTY
        self.white_turn = not self.white_turn
        self.move_count += 1

        # Update status
        in_chk = self._in_check(self.board, self.white_turn)
        has_moves = any(
            self.legal_moves(r, c)
            for r in range(8) for c in range(8)
            if friendly(self.board[r][c], self.white_turn)
        )
        if not has_moves:
            self.status = 'CHECKMATE' if in_chk else 'STALEMATE'
        elif in_chk:
            self.status = 'CHECK'
        else:
            self.status = ''

    # -----------------------------------------------------------------------
    # Simple AI (minimax depth 3)
    # -----------------------------------------------------------------------

    def ai_move(self, depth: int = 3) -> Optional[tuple]:
        best_score = float('-inf')
        best_move  = None
        for fr, fc, tr, tc in self._all_moves(True):
            nb = copy.deepcopy(self)
            nb.apply_move(fr, fc, tr, tc)
            score = -nb._minimax(depth - 1, float('-inf'), float('inf'), False)
            if score > best_score:
                best_score = score
                best_move  = (fr, fc, tr, tc)
        return best_move

    def _minimax(self, depth: int, alpha: float, beta: float, maximising: bool) -> float:
        if depth == 0 or self.status in ('CHECKMATE', 'STALEMATE'):
            return self._evaluate()
        moves = list(self._all_moves(maximising))
        if not moves:
            return self._evaluate()
        if maximising:
            val = float('-inf')
            for fr, fc, tr, tc in moves:
                nb = copy.deepcopy(self)
                nb.apply_move(fr, fc, tr, tc)
                val = max(val, nb._minimax(depth-1, alpha, beta, False))
                alpha = max(alpha, val)
                if alpha >= beta: break
            return val
        else:
            val = float('inf')
            for fr, fc, tr, tc in moves:
                nb = copy.deepcopy(self)
                nb.apply_move(fr, fc, tr, tc)
                val = min(val, nb._minimax(depth-1, alpha, beta, True))
                beta = min(beta, val)
                if alpha >= beta: break
            return val

    def _all_moves(self, white: bool):
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if (white and is_white(p)) or (not white and is_black(p)):
                    for tr, tc in self.legal_moves(r, c):
                        yield r, c, tr, tc

    def _evaluate(self) -> float:
        if self.status == 'CHECKMATE':
            return -9999 if self.white_turn else 9999
        if self.status == 'STALEMATE':
            return 0
        return sum(PIECE_VALUES.get(p, 0)
                   for row in self.board for p in row)


# ---------------------------------------------------------------------------
# Terminal UI
# ---------------------------------------------------------------------------

PIECE_DISPLAY = {
    WK:'♔', WQ:'♕', WR:'♖', WB:'♗', WN:'♘', WP:'♙',
    BK:'♚', BQ:'♛', BR:'♜', BB:'♝', BN:'♞', BP:'♟',
    EMPTY:'..',
}


def play_chess(display=None, vs_ai: bool = True) -> None:
    if display and hasattr(display, '_stdscr') and display._stdscr:
        _play_chess_curses(display._stdscr, vs_ai)
    else:
        scr = curses.initscr()
        try:
            curses.noecho(); curses.cbreak(); curses.curs_set(0)
            scr.keypad(True)
            if curses.has_colors():
                curses.start_color()
                curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
                curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)
                curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
                curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_BLACK)
            _play_chess_curses(scr, vs_ai)
        finally:
            curses.nocbreak(); curses.echo(); curses.endwin()


def _play_chess_curses(scr, vs_ai: bool) -> None:
    game = ChessGame()
    cursor = [7, 4]   # row, col
    scr.timeout(100)

    while game.status not in ('CHECKMATE', 'STALEMATE'):
        # AI move
        if vs_ai and not game.white_turn:
            scr.addstr(0, 0, 'AI thinking...')
            scr.refresh()
            move = game.ai_move(depth=3)
            if move:
                game.apply_move(*move)
            continue

        # Draw board
        h, w = scr.getmaxyx()
        scr.clear()

        # Header
        turn = 'WHITE' if game.white_turn else 'BLACK'
        status_str = f'  {game.status}' if game.status else ''
        scr.addstr(0, 0, f'Chess — {turn} to move{status_str}')
        scr.addstr(1, 0, 'Arrows=move  Enter=select  Q=quit')

        # Board
        sel = game.selected
        highlights = game.legal_moves(*sel) if sel else []
        for r in range(8):
            scr.addstr(r + 2, 0, f'{8-r} ')
            for c in range(8):
                piece = game.board[r][c]
                ch = PIECE_DISPLAY.get(piece, '..')
                is_light = (r + c) % 2 == 0
                attr = curses.color_pair(1) if is_light else curses.color_pair(2)
                if (r, c) == tuple(cursor):
                    attr = curses.color_pair(3) | curses.A_BOLD
                elif (r, c) == sel:
                    attr = curses.color_pair(4) | curses.A_BOLD
                elif (r, c) in highlights:
                    attr = curses.color_pair(4)
                try:
                    scr.addstr(r + 2, c * 3 + 2, f'{ch} ', attr)
                except curses.error:
                    pass
        scr.addstr(10, 2, 'a  b  c  d  e  f  g  h')

        scr.refresh()

        ch = scr.getch()
        if ch == curses.KEY_UP    and cursor[0] > 0: cursor[0] -= 1
        elif ch == curses.KEY_DOWN  and cursor[0] < 7: cursor[0] += 1
        elif ch == curses.KEY_LEFT  and cursor[1] > 0: cursor[1] -= 1
        elif ch == curses.KEY_RIGHT and cursor[1] < 7: cursor[1] += 1
        elif ch in (ord('\n'), ord('\r'), ord(' ')):
            r, c = cursor
            if game.selected:
                sr, sc = game.selected
                if (r, c) in game.legal_moves(sr, sc):
                    game.apply_move(sr, sc, r, c)
                    game.selected = None
                elif friendly(game.board[r][c], game.white_turn):
                    game.selected = (r, c)
                else:
                    game.selected = None
            else:
                if friendly(game.board[r][c], game.white_turn):
                    game.selected = (r, c)
        elif ch in (27, ord('q')):
            break

    # Game over screen
    scr.clear()
    h, w = scr.getmaxyx()
    msg = f'GAME OVER — {game.status}'
    scr.addstr(h//2, max(0, w//2 - len(msg)//2), msg)
    scr.addstr(h//2+1, max(0, w//2 - 8), 'Press any key')
    scr.timeout(-1)
    scr.getch()
