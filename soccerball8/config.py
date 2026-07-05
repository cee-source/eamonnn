"""Central configuration, populated from environment variables (see .env.example)."""

import os
from dataclasses import dataclass


def _int_env(name: str, default: str) -> int:
    return int(os.environ.get(name, default))


def _float_env(name: str, default: str) -> float:
    return float(os.environ.get(name, default))


@dataclass
class Settings:
    # Ollama runs on a separate, more powerful machine on the same network -
    # a Pi Zero does not have anywhere near enough RAM/CPU to host an LLM.
    ollama_host: str = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    ollama_model: str = os.environ.get("OLLAMA_MODEL", "llama3.2")

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
    button_gpio_pin: int = _int_env("BUTTON_GPIO_PIN", "17")

    @property
    def mic_device(self):
        return None if self.mic_device_index < 0 else self.mic_device_index


SETTINGS = Settings()
