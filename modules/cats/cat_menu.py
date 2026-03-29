"""Cat Videos menu for PiFlip."""

from core.menu import MenuEntry
from modules.cats.cat_player import CatPlayer, ANIMATIONS, CAT_VIDEO_URLS


def build_cats_menu(config, display) -> list:
    player = CatPlayer(display)

    def _play(idx):
        label = ANIMATIONS[idx][0]
        display.draw_message(label, "Any btn = stop")
        import time; time.sleep(0.8)
        player.play_animation(idx)

    def _hdmi(idx):
        display.draw_message("Launching mpv...", "HDMI output")
        ok, msg = player.play_on_hdmi(idx)
        if ok:
            display.draw_message("Playing!", msg[:20])
        else:
            display.draw_message("Error", msg[:20])
        import time; time.sleep(3)

    return [
        MenuEntry(label="Nyan Cat",        action=lambda: _play(0)),
        MenuEntry(label="Walking Cat",      action=lambda: _play(1)),
        MenuEntry(label="Loaf Cat",         action=lambda: _play(2)),
        MenuEntry(label="HDMI: Cat Clips",  action=lambda: _hdmi(0)),
        MenuEntry(label="HDMI: Nyan Cat",   action=lambda: _hdmi(1)),
    ]
