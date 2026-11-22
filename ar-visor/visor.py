#!/usr/bin/env python3
"""
Pi Zero AR visor -- live camera passthrough with a holographic HUD
overlay, rendered fullscreen to a small HDMI display worn in a lens
headset. Separate device/project from the PiFlip -- this runs standalone
on its own Pi, not wired into main.py's menu.

One-time Pi setup (Raspberry Pi OS Bullseye+):
    sudo raspi-config        # Interface Options -> Camera -> Enable, reboot
    sudo apt install -y python3-picamera2 python3-pygame --no-install-recommends

picamera2 is apt-only (it wraps the system libcamera stack) -- do not
pip install it.

Wiring: camera module into the Zero's CSI port. The Zero's CSI
connector is physically smaller than on other Pi boards, so it needs
the Pi Zero's own camera ribbon cable, not the standard one a Camera
Module ships with. Small display into the Zero's mini-HDMI port.

Run:
    python3 visor.py                 # fullscreen on the attached HDMI display
    python3 visor.py --windowed      # windowed, for testing over VNC/desktop
    python3 visor.py --split         # duplicate the view into left/right
                                      # halves, for a stereo lens headset
    python3 visor.py --res 480x320   # drop resolution if the FPS counter
                                      # drawn in the corner is too choppy

Stop it with Ctrl+C over SSH -- there's no physical button yet since
this board has no GPIO header soldered on.
"""
from __future__ import annotations

import argparse
import os
import signal
import sys
import time

import pygame

from hud_overlay import VisorHUD


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Pi Zero AR visor')
    parser.add_argument('--windowed', action='store_true',
                        help='run in a window instead of fullscreen framebuffer')
    parser.add_argument('--split', action='store_true',
                        help='duplicate the view into left/right halves for lens stereo')
    parser.add_argument('--res', default='640x480',
                        help='camera capture resolution, e.g. 640x480 (default) or 480x320')
    return parser.parse_args()


def start_camera(width: int, height: int):
    from picamera2 import Picamera2

    cam = Picamera2()
    config = cam.create_preview_configuration(main={'size': (width, height), 'format': 'RGB888'})
    cam.configure(config)
    cam.start()
    time.sleep(1)  # let auto-exposure/white-balance settle before the first frame
    return cam


def main() -> int:
    args = parse_args()
    width, height = (int(v) for v in args.res.split('x'))

    if not args.windowed:
        os.environ.setdefault('SDL_FBDEV', '/dev/fb0')
        os.environ.setdefault('SDL_VIDEODRIVER', 'fbcon')
        os.environ.setdefault('SDL_NOMOUSE', '1')

    pygame.init()
    pygame.mouse.set_visible(False)
    screen = pygame.display.set_mode(
        (width, height) if args.windowed else (0, 0),
        0 if args.windowed else pygame.FULLSCREEN,
    )
    screen_w, screen_h = screen.get_size()

    cam = start_camera(width, height)
    hud = VisorHUD(width, height)

    state = {'running': True}
    signal.signal(signal.SIGTERM, lambda *_: state.update(running=False))

    frame_surf = pygame.Surface((width, height))
    clock = pygame.time.Clock()
    fps = 0.0

    try:
        while state['running']:
            frame = cam.capture_array()  # HxWx3, RGB order
            # If colours come out swapped (blue skin tones), the capture
            # config's format is actually giving BGR on this libcamera
            # build -- change 'RGB888' to 'BGR888' in start_camera() above.
            pygame.surfarray.blit_array(frame_surf, frame[:, :, :3].swapaxes(0, 1))
            hud.draw(frame_surf, fps)

            if args.split:
                half = pygame.transform.scale(frame_surf, (screen_w // 2, screen_h))
                screen.blit(half, (0, 0))
                screen.blit(half, (screen_w // 2, 0))
            else:
                scaled = pygame.transform.scale(frame_surf, (screen_w, screen_h))
                screen.blit(scaled, (0, 0))

            pygame.display.flip()
            clock.tick(30)
            fps = clock.get_fps()

            for event in pygame.event.get():
                if event.type == pygame.QUIT or (
                    event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
                ):
                    state['running'] = False
    except KeyboardInterrupt:
        pass
    finally:
        cam.stop()
        pygame.quit()

    return 0


if __name__ == '__main__':
    sys.exit(main())
