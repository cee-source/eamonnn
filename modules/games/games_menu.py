from core.menu import MenuEntry
from core.config_manager import ConfigManager


def build_games_menu(config: ConfigManager, display=None) -> list[MenuEntry]:
    return [
        MenuEntry(label='Snake',          action=lambda: _snake(display)),
        MenuEntry(label='Pong vs AI',     action=lambda: _pong(display, vs_ai=True)),
        MenuEntry(label='Pong 2 Player',  action=lambda: _pong(display, vs_ai=False)),
        MenuEntry(label='Chess vs AI',    action=lambda: _chess(display, vs_ai=True)),
        MenuEntry(label='Chess 2 Player', action=lambda: _chess(display, vs_ai=False)),
        MenuEntry(label='Tetris',         action=lambda: _tetris(display)),
        MenuEntry(label='Flappy Bird',    action=lambda: _flappy(display)),
    ]


def _snake(display) -> None:
    from modules.games.snake import play_snake
    import time
    score = play_snake(display)
    if display:
        display.draw_message([f'Game Over!', f'Score: {score}'])
        time.sleep(2)


def _pong(display, vs_ai: bool) -> None:
    from modules.games.pong import play_pong
    play_pong(display, vs_ai=vs_ai)


def _chess(display, vs_ai: bool) -> None:
    from modules.games.chess import play_chess
    play_chess(display, vs_ai=vs_ai)


def _tetris(display) -> None:
    from modules.games.tetris import play_tetris
    import time
    score = play_tetris(display)
    if display:
        display.draw_message([f'Game Over!', f'Score: {score}'])
        time.sleep(2)


def _flappy(display) -> None:
    from modules.games.flappy import play_flappy
    import time
    score = play_flappy(display)
    if display:
        display.draw_message([f'Game Over!', f'Score: {score}'])
        time.sleep(2)
