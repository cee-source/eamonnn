from core.menu import MenuEntry
from core.config_manager import ConfigManager


def build_games_menu(config: ConfigManager, display=None) -> list[MenuEntry]:
    return [
        MenuEntry(label='Snake',              action=lambda: _snake(display)),
        MenuEntry(label='Pong vs AI',         action=lambda: _pong(display, vs_ai=True)),
        MenuEntry(label='Pong 2 Player',      action=lambda: _pong(display, vs_ai=False)),
        MenuEntry(label='Chess vs AI',        action=lambda: _chess(display, vs_ai=True)),
        MenuEntry(label='Chess 2 Player',     action=lambda: _chess(display, vs_ai=False)),
    ]


def _snake(display) -> None:
    from modules.games.snake import play_snake
    score = play_snake(display)
    import time
    if display:
        display.draw_message([f'Game Over!', f'Score: {score}'])
        time.sleep(2)


def _pong(display, vs_ai: bool) -> None:
    from modules.games.pong import play_pong
    play_pong(display, vs_ai=vs_ai)


def _chess(display, vs_ai: bool) -> None:
    from modules.games.chess import play_chess
    play_chess(display, vs_ai=vs_ai)
