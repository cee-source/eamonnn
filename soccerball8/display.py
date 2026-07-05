"""Display driver abstraction: real SPI hardware, or a windowed simulator
for developing off the Pi."""

import time
from typing import Iterable, Protocol

from PIL import Image


class Display(Protocol):
    width: int
    height: int

    def show(self, frame: Image.Image) -> None: ...
    def close(self) -> None: ...


class DummyDisplay:
    """Fallback for development off the Pi: opens a live preview window with
    pygame if it's installed, otherwise just no-ops."""

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self._pygame = None
        self._screen = None
        try:
            import pygame

            pygame.init()
            self._pygame = pygame
            self._screen = pygame.display.set_mode((width, height))
            pygame.display.set_caption("Soccer 8-Ball (simulator)")
        except Exception:
            self._pygame = None

    def show(self, frame: Image.Image) -> None:
        if not self._pygame or not self._screen:
            return
        surface = self._pygame.image.fromstring(frame.tobytes(), frame.size, frame.mode)
        self._screen.blit(surface, (0, 0))
        self._pygame.display.flip()
        for event in self._pygame.event.get():
            if event.type == self._pygame.QUIT:
                raise KeyboardInterrupt

    def close(self) -> None:
        if self._pygame:
            self._pygame.quit()


class _LumaSPIDisplay:
    """Shared setup for luma.lcd SPI devices (ST7789 / ILI9341 etc.)."""

    def __init__(
        self, device_factory, width: int, height: int,
        spi_port: int, spi_device: int, gpio_dc: int, gpio_rst: int,
    ):
        from luma.core.interface.serial import spi

        self.width = width
        self.height = height
        serial = spi(
            port=spi_port, device=spi_device,
            gpio_DC=gpio_dc, gpio_RST=gpio_rst, bus_speed_hz=32_000_000,
        )
        self._device = device_factory(serial, width=width, height=height, rotate=0)

    def show(self, frame: Image.Image) -> None:
        self._device.display(frame)

    def close(self) -> None:
        self._device.cleanup()


class ST7789Display(_LumaSPIDisplay):
    def __init__(self, width: int, height: int, spi_port: int, spi_device: int, gpio_dc: int, gpio_rst: int):
        from luma.lcd.device import st7789

        super().__init__(st7789, width, height, spi_port, spi_device, gpio_dc, gpio_rst)


class ILI9341Display(_LumaSPIDisplay):
    def __init__(self, width: int, height: int, spi_port: int, spi_device: int, gpio_dc: int, gpio_rst: int):
        from luma.lcd.device import ili9341

        super().__init__(ili9341, width, height, spi_port, spi_device, gpio_dc, gpio_rst)


def build_display(settings) -> Display:
    driver = settings.display_driver.lower()
    if driver == "st7789":
        return ST7789Display(
            settings.screen_width, settings.screen_height,
            settings.display_spi_port, settings.display_spi_device,
            settings.display_gpio_dc, settings.display_gpio_rst,
        )
    if driver == "ili9341":
        return ILI9341Display(
            settings.screen_width, settings.screen_height,
            settings.display_spi_port, settings.display_spi_device,
            settings.display_gpio_dc, settings.display_gpio_rst,
        )
    return DummyDisplay(settings.screen_width, settings.screen_height)


def play_frames(display: Display, frames: Iterable[Image.Image], fps: int = 20) -> None:
    delay = 1.0 / fps
    for frame in frames:
        if frame.size != (display.width, display.height):
            frame = frame.resize((display.width, display.height))
        display.show(frame)
        time.sleep(delay)
