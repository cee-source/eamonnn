"""
Iron-Man-visor-style HUD, drawn with plain pygame primitives (no PIL
compositing, no Three.js) since this has to run in real time on a Pi
Zero's CPU.
"""
from __future__ import annotations

import math
import time

import pygame

CYAN = (45, 227, 255)
AMBER = (255, 154, 31)


class VisorHUD:
    def __init__(self, width: int, height: int) -> None:
        self.w = width
        self.h = height
        self.font = pygame.font.SysFont('monospace', max(12, height // 22), bold=True)
        self._t0 = time.time()

    def draw(self, surface: pygame.Surface, fps: float) -> None:
        t = time.time() - self._t0
        cx, cy = self.w // 2, self.h // 2

        self._corner_brackets(surface)
        self._reticle(surface, cx, cy, t)
        self._reactor_gauge(surface, int(self.w * 0.5), int(self.h * 0.86), t)
        self._text(surface, time.strftime('%H:%M:%S'), (self.w - 8, 8), align='right')
        self._text(surface, f'{fps:4.1f} FPS', (8, 8))
        self._text(surface, 'VISOR ONLINE', (8, self.h - 26), color=AMBER)

    def _corner_brackets(self, surface: pygame.Surface) -> None:
        length = max(14, self.w // 22)
        pad = 6
        corners = [
            ((pad, pad), (pad + length, pad), (pad, pad + length)),
            ((self.w - pad, pad), (self.w - pad - length, pad), (self.w - pad, pad + length)),
            ((pad, self.h - pad), (pad + length, self.h - pad), (pad, self.h - pad - length)),
            ((self.w - pad, self.h - pad), (self.w - pad - length, self.h - pad), (self.w - pad, self.h - pad - length)),
        ]
        for corner, horiz, vert in corners:
            pygame.draw.line(surface, CYAN, corner, horiz, 2)
            pygame.draw.line(surface, CYAN, corner, vert, 2)

    def _reticle(self, surface: pygame.Surface, cx: int, cy: int, t: float) -> None:
        r = min(self.w, self.h) // 14
        pygame.draw.circle(surface, CYAN, (cx, cy), r, 2)
        pygame.draw.circle(surface, CYAN, (cx, cy), 2)
        for i in range(4):
            a = t * 0.6 + i * math.pi / 2
            x1, y1 = cx + math.cos(a) * (r + 4), cy + math.sin(a) * (r + 4)
            x2, y2 = cx + math.cos(a) * (r + 10), cy + math.sin(a) * (r + 10)
            pygame.draw.line(surface, CYAN, (x1, y1), (x2, y2), 2)

    def _reactor_gauge(self, surface: pygame.Surface, cx: int, cy: int, t: float) -> None:
        r = min(self.w, self.h) // 10
        outer = pygame.Rect(cx - r, cy - r, r * 2, r * 2)
        pygame.draw.arc(surface, CYAN, outer, t * 1.4, t * 1.4 + 4.5, 3)
        inner = pygame.Rect(cx - r + 6, cy - r + 6, r * 2 - 12, r * 2 - 12)
        pygame.draw.arc(surface, AMBER, inner, -t * 2.0, -t * 2.0 + 3.0, 3)

    def _text(self, surface: pygame.Surface, text: str, pos: tuple[int, int],
              color: tuple[int, int, int] = CYAN, align: str = 'left') -> None:
        img = self.font.render(text, True, color)
        x, y = pos
        if align == 'right':
            x -= img.get_width()
        surface.blit(img, (x, y))
