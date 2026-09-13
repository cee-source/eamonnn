"""
Thermal camera driver for the MLX90640 (32x24 pixel IR array, I2C).

This images infrared radiated off surfaces — skin, engines, pipes, warm
breath — so it works in total darkness and reads temperature differences
through smoke or thin fabric, same as any commercial thermal scope.

It cannot see through solid walls. Walls are opaque to long-wave IR, so a
wall's own surface temperature is all a thermal camera will ever show of
it — there is no "through-wall" mode here, because there isn't one in
physics. Detecting a person on the other side of a wall needs a different
sensing method entirely (UWB/RF radar), not a thermal camera.
"""
from __future__ import annotations

import logging
from typing import Optional

log = logging.getLogger(__name__)

FRAME_W = 32
FRAME_H = 24
GRADIENT = ' .:-=+*#%@'


class ThermalCam:
    """MLX90640 32x24 thermal array over I2C."""

    def __init__(self, config) -> None:
        self._i2c_port = config.getint('hardware', 'thermal_i2c_port', fallback=1)
        self._refresh_hz = config.getfloat('hardware', 'thermal_refresh_hz', fallback=4.0)
        self._sensor = None

    def _connect(self):
        if self._sensor is not None:
            return self._sensor

        import adafruit_mlx90640
        import board
        import busio

        i2c = busio.I2C(board.SCL, board.SDA, frequency=400000)
        sensor = adafruit_mlx90640.MLX90640(i2c)
        rate_map = {
            0.5: adafruit_mlx90640.RefreshRate.REFRESH_0_5_HZ,
            1: adafruit_mlx90640.RefreshRate.REFRESH_1_HZ,
            2: adafruit_mlx90640.RefreshRate.REFRESH_2_HZ,
            4: adafruit_mlx90640.RefreshRate.REFRESH_4_HZ,
            8: adafruit_mlx90640.RefreshRate.REFRESH_8_HZ,
        }
        sensor.refresh_rate = rate_map.get(
            self._refresh_hz, adafruit_mlx90640.RefreshRate.REFRESH_4_HZ)

        self._sensor = sensor
        log.info('MLX90640 thermal camera connected on I2C port %d', self._i2c_port)
        return sensor

    def read_frame(self) -> Optional[list[float]]:
        """768 (32x24) surface temperatures in Celsius, row-major, or None on failure."""
        sensor = self._connect()
        frame = [0.0] * (FRAME_W * FRAME_H)
        try:
            sensor.getFrame(frame)
            return frame
        except (ValueError, RuntimeError) as e:
            log.warning('Thermal frame read failed: %s', e)
            return None

    def render_ascii(self, frame: list[float], cols: int, rows: int) -> tuple[list[str], float, float]:
        """Downsample the 32x24 frame to a cols x rows ASCII heat-gradient grid."""
        lo, hi = min(frame), max(frame)
        span = max(hi - lo, 0.1)
        lines = []
        for r in range(rows):
            src_y = min(r * FRAME_H // rows, FRAME_H - 1)
            row_chars = []
            for c in range(cols):
                src_x = min(c * FRAME_W // cols, FRAME_W - 1)
                temp = frame[src_y * FRAME_W + src_x]
                level = int((temp - lo) / span * (len(GRADIENT) - 1))
                row_chars.append(GRADIENT[max(0, min(level, len(GRADIENT) - 1))])
            lines.append(''.join(row_chars))
        return lines, lo, hi
