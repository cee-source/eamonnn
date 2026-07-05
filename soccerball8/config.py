"""Central configuration, populated from environment variables (see .env.example)."""

import os
from dataclasses import dataclass


def _int_env(name: str, default: str) -> int:
    return int(os.environ.get(name, default))


def _float_env(name: str, default: str) -> float:
    return float(os.environ.get(name, default))


def _int_env_auto_base(name: str, default: str) -> int:
    """Like _int_env, but accepts hex like "0x68" (for I2C addresses)."""
    return int(os.environ.get(name, default), 0)


@dataclass
class Settings:
    # Google Custom Search JSON API (https://programmablesearchengine.google.com/).
    google_api_key: str = os.environ.get("GOOGLE_API_KEY", "")
    google_cse_id: str = os.environ.get("GOOGLE_CSE_ID", "")

    search_results: int = _int_env("SEARCH_RESULTS", "8")
    min_relevant_results: int = _int_env("MIN_RELEVANT_RESULTS", "3")
    confidence_threshold: float = _float_env("CONFIDENCE_THRESHOLD", "0.7")

    # 2.4"-2.5" SPI displays are commonly 240x320 (ST7789 / ILI9341).
    screen_width: int = _int_env("SCREEN_WIDTH", "240")
    screen_height: int = _int_env("SCREEN_HEIGHT", "320")
    display_driver: str = os.environ.get("DISPLAY_DRIVER", "dummy")  # dummy | st7789 | ili9341
    display_spi_port: int = _int_env("DISPLAY_SPI_PORT", "0")
    display_spi_device: int = _int_env("DISPLAY_SPI_DEVICE", "0")
    display_gpio_dc: int = _int_env("DISPLAY_GPIO_DC", "24")
    display_gpio_rst: int = _int_env("DISPLAY_GPIO_RST", "25")

    mic_device_index: int = _int_env("MIC_DEVICE_INDEX", "-1")

    # Shake-to-ask trigger (MPU6050 accelerometer over I2C).
    accelerometer_bus: int = _int_env("ACCELEROMETER_BUS", "1")
    accelerometer_address: int = _int_env_auto_base("ACCELEROMETER_ADDRESS", "0x68")
    shake_threshold_g: float = _float_env("SHAKE_THRESHOLD_G", "0.8")
    shake_required_spikes: int = _int_env("SHAKE_REQUIRED_SPIKES", "3")
    shake_window_seconds: float = _float_env("SHAKE_WINDOW_SECONDS", "1.0")
    shake_cooldown_seconds: float = _float_env("SHAKE_COOLDOWN_SECONDS", "1.5")

    @property
    def mic_device(self):
        return None if self.mic_device_index < 0 else self.mic_device_index


SETTINGS = Settings()
