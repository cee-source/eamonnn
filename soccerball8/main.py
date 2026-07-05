"""Main loop: wait for the button, listen, think, animate the answer, repeat."""

import traceback

from .animation import iter_full_sequence, iter_typewriter_frames
from .answer_engine import answer_question
from .audio import listen_for_question
from .config import SETTINGS, Settings
from .display import Display, build_display, play_frames
from .ollama_client import OllamaClient


def _wait_for_trigger(settings: Settings) -> None:
    """Blocks until the physical button is pressed (or Enter, off the Pi)."""
    try:
        from gpiozero import Button

        button = Button(settings.button_gpio_pin, bounce_time=0.05)
        button.wait_for_press()
    except Exception:
        input("Press Enter to ask the soccer 8-ball a question... ")


def run_once(settings: Settings, ollama: OllamaClient, display: Display) -> None:
    _wait_for_trigger(settings)
    print("Listening...")

    question = listen_for_question(settings.mic_device)
    if not question:
        play_frames(display, iter_typewriter_frames(
            display.width, display.height, "Sorry, I didn't catch that."))
        return

    print(f"Question: {question}")
    answer = answer_question(question, ollama, settings)
    print(f"Answer ({answer.verdict}, confidence={answer.confidence:.0%}): {answer.text}")

    play_frames(display, iter_full_sequence(display.width, display.height, answer.text))


def main() -> None:
    settings = SETTINGS
    ollama = OllamaClient(settings.ollama_host, settings.ollama_model)
    display = build_display(settings)
    try:
        while True:
            try:
                run_once(settings, ollama, display)
            except KeyboardInterrupt:
                raise
            except Exception:
                traceback.print_exc()
    except KeyboardInterrupt:
        pass
    finally:
        display.close()


if __name__ == "__main__":
    main()
