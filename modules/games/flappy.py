"""Flappy Bird for 3.5-inch touchscreen (pygame only)."""
from __future__ import annotations

import random

W          = 320
H          = 480
BIRD_X     = 80
GRAVITY    = 0.4
FLAP_VEL   = -7.5
PIPE_W     = 55
PIPE_GAP   = 155
PIPE_SPEED = 3


class FlappyGame:
    def __init__(self) -> None:
        self.bird_y:  float = H / 2
        self.bird_vy: float = 0.0
        self.pipes:   list  = []
        self.score    = 0
        self.alive    = True
        self.frame    = 0

    def flap(self) -> None:
        self.bird_vy = FLAP_VEL

    def spawn_pipe(self) -> None:
        gap_y = random.randint(80, H - 80 - PIPE_GAP)
        self.pipes.append([float(W), gap_y, False])

    def step(self) -> None:
        if not self.alive:
            return

        # Gravity
        self.bird_vy += GRAVITY
        self.bird_y  += self.bird_vy

        # Ceiling / floor
        if self.bird_y - 10 <= 0 or self.bird_y + 10 >= H:
            self.alive = False
            return

        # Move pipes left
        for pipe in self.pipes:
            pipe[0] -= PIPE_SPEED

        # Remove pipes that have left the screen
        self.pipes = [p for p in self.pipes if p[0] + PIPE_W > 0]

        # Score: pipe right-edge has passed bird
        for pipe in self.pipes:
            if not pipe[2] and pipe[0] + PIPE_W <= BIRD_X:
                pipe[2]     = True
                self.score += 1

        # Pipe collision
        for pipe in self.pipes:
            px, gap_y = pipe[0], pipe[1]
            if px < BIRD_X + 10 and px + PIPE_W > BIRD_X - 10:
                if self.bird_y - 10 < gap_y or self.bird_y + 10 > gap_y + PIPE_GAP:
                    self.alive = False
                    return

        # Spawn new pipe every 100 frames
        self.frame += 1
        if self.frame % 100 == 0:
            self.spawn_pipe()


# ---------------------------------------------------------------------------
# Pygame renderer
# ---------------------------------------------------------------------------

def play_flappy(display=None) -> int:
    """Run Flappy Bird. Returns final score. Requires TouchDisplay."""
    from core.display import TouchDisplay
    if not isinstance(display, TouchDisplay):
        print('Flappy Bird needs the 3.5" touchscreen')
        return 0

    pg     = display._pg
    screen = display._screen
    clock  = pg.time.Clock()

    font_lg = pg.font.SysFont('freemono', 36, bold=True)
    font_md = pg.font.SysFont('freemono', 24, bold=True)
    font_sm = pg.font.SysFont('freemono', 18)

    C_SKY  = (113, 197, 255)
    C_PIPE = ( 74, 164,  74)
    C_BIRD = (255, 220,   0)
    C_WHITE= (255, 255, 255)
    C_DARK = ( 20,  20,  40)
    C_HINT = (180, 185, 200)

    def draw_game(game: FlappyGame) -> None:
        screen.fill(C_SKY)
        for pipe in game.pipes:
            px, gap_y = int(pipe[0]), pipe[1]
            pg.draw.rect(screen, C_PIPE, (px, 0, PIPE_W, gap_y))
            pg.draw.rect(screen, C_PIPE,
                         (px, gap_y + PIPE_GAP, PIPE_W, H - gap_y - PIPE_GAP))
        pg.draw.circle(screen, C_BIRD, (BIRD_X, int(game.bird_y)), 10)
        score_surf = font_md.render(str(game.score), True, C_WHITE)
        screen.blit(score_surf, ((W - score_surf.get_width()) // 2, 20))
        pg.display.flip()

    def wait_for_tap() -> bool:
        """Block until tap or QUIT. Returns True on tap, False on QUIT."""
        while True:
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    return False
                elif event.type == pg.MOUSEBUTTONDOWN:
                    return True
            clock.tick(30)

    # Start screen
    screen.fill(C_SKY)
    start_s = font_md.render('TAP TO START', True, C_WHITE)
    screen.blit(start_s, ((W - start_s.get_width()) // 2, H // 2 - 20))
    pg.display.flip()
    if not wait_for_tap():
        return 0

    while True:
        game = FlappyGame()

        # Game loop
        while game.alive:
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    return game.score
                elif event.type == pg.MOUSEBUTTONDOWN:
                    game.flap()

            game.step()
            if game.alive:
                draw_game(game)
            clock.tick(60)

        # Game over screen
        screen.fill(C_DARK)
        lines = [
            font_lg.render('GAME OVER', True, C_WHITE),
            font_md.render(f'Score: {game.score}', True, C_WHITE),
            font_sm.render('Tap to play again', True, C_HINT),
        ]
        total_h = sum(s.get_height() + 12 for s in lines)
        y = (H - total_h) // 2
        for surf in lines:
            screen.blit(surf, ((W - surf.get_width()) // 2, y))
            y += surf.get_height() + 12
        pg.display.flip()

        if not wait_for_tap():
            return game.score
        # tap received → loop back and start a new game
