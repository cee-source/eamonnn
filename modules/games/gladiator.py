"""
Gladiator Arena — turn-based combat RPG for PiFlip.

Fight a roster of opponents, earn gold, buy armor from Magnus the
Armorer, get patched up by Vita the Healer, and hear the next match-up
from Dominus the Arena Master. Progress (gold, armor, win/loss record)
is saved to disk between sessions.

Renders through the shared DisplayDriver abstraction (draw_menu /
draw_message / draw_progress) only, so it runs on the OLED, the 3.5"
touchscreen, and the terminal alike. Input is polled directly from the
TerminalDisplay's curses window or the TouchDisplay's pygame surface —
NOT via core.menu.InputHandler, because the running MenuEngine already
owns one InputHandler bound to the GPIO buttons; standing up a second
one here would re-register edge detection on the same pins and fight
the outer menu for keys.
"""
from __future__ import annotations

import curses
import json
import logging
import os
import random
import time
from dataclasses import dataclass
from typing import Optional

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Armor catalog
# ---------------------------------------------------------------------------

SLOTS = ('Helmet', 'Chest', 'Shield')


@dataclass(frozen=True)
class ArmorPiece:
    name: str
    slot: str
    defense: int
    price: int


ARMOR_CATALOG: list[ArmorPiece] = [
    ArmorPiece('Leather Cap',    'Helmet', 2,  20),
    ArmorPiece('Bronze Helm',    'Helmet', 5,  60),
    ArmorPiece('Iron Helm',      'Helmet', 9,  140),
    ArmorPiece('Spartan Helm',   'Helmet', 14, 260),
    ArmorPiece('Padded Tunic',   'Chest',  3,  30),
    ArmorPiece('Bronze Cuirass', 'Chest',  8,  90),
    ArmorPiece('Iron Plate',     'Chest',  14, 200),
    ArmorPiece('Myrmillo Plate', 'Chest',  22, 380),
    ArmorPiece('Wooden Buckler', 'Shield', 3,  25),
    ArmorPiece('Bronze Scutum',  'Shield', 7,  80),
    ArmorPiece('Iron Scutum',    'Shield', 13, 180),
    ArmorPiece('Tower Shield',   'Shield', 20, 340),
]


def armor_for_slot(slot: str) -> list[ArmorPiece]:
    return [a for a in ARMOR_CATALOG if a.slot == slot]


def find_armor(name: str) -> Optional[ArmorPiece]:
    for a in ARMOR_CATALOG:
        if a.name == name:
            return a
    return None


# ---------------------------------------------------------------------------
# Opponent roster
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Opponent:
    name: str
    max_hp: int
    attack: int
    defense: int
    gold: int
    taunt: str


OPPONENTS: list[Opponent] = [
    Opponent('Straw Dummy',             20,  3, 0,   10, 'It does not move.'),
    Opponent('Rusty Marcus',            28,  6, 1,   22, 'Fresh meat for the sand!'),
    Opponent('Titus the Bull',          40,  9, 3,   38, "I'll crush you like a grape!"),
    Opponent('Flavia Ironfist',         50, 12, 5,   58, 'Show me your worst, weakling.'),
    Opponent('Brutus Maximus',          65, 15, 6,   85, 'None have survived me.'),
    Opponent('The Retiarius',           78, 18, 8,  120, 'Net or trident — pick your death.'),
    Opponent('Crixus the Undefeated',   95, 22, 10, 170, 'I am undefeated. You are next.'),
    Opponent("The Emperor's Champion", 125, 27, 13, 260, 'For glory and the Emperor!'),
]


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------

STARTING_GOLD    = 30
STARTING_MAX_HP  = 50
STARTING_ATTACK  = 8
STARTING_DEFENSE = 1


class Gladiator:
    """The player's persistent gladiator: stats, gold, armor and record."""

    def __init__(self) -> None:
        self.max_hp          = STARTING_MAX_HP
        self.hp               = STARTING_MAX_HP
        self.base_attack      = STARTING_ATTACK
        self.base_defense     = STARTING_DEFENSE
        self.gold             = STARTING_GOLD
        self.armor: dict[str, Optional[str]] = {slot: None for slot in SLOTS}
        self.wins             = 0
        self.losses           = 0
        self.opponent_index   = 0

    @property
    def attack(self) -> int:
        """Gladiators hit harder as they rack up wins."""
        return self.base_attack + self.wins

    @property
    def defense(self) -> int:
        bonus = 0
        for name in self.armor.values():
            piece = find_armor(name) if name else None
            if piece:
                bonus += piece.defense
        return self.base_defense + bonus

    @property
    def next_opponent(self) -> Opponent:
        idx = max(0, min(self.opponent_index, len(OPPONENTS) - 1))
        return OPPONENTS[idx]

    @property
    def champion_of_arena(self) -> bool:
        return self.opponent_index >= len(OPPONENTS) - 1 and self.wins >= len(OPPONENTS)

    def equip(self, piece: ArmorPiece) -> None:
        self.armor[piece.slot] = piece.name

    def can_afford(self, price: int) -> bool:
        return self.gold >= price

    def heal(self, amount: int) -> int:
        """Heal up to `amount`, capped at max_hp. Returns HP actually restored."""
        before = self.hp
        self.hp = min(self.max_hp, self.hp + amount)
        return self.hp - before

    def record_win(self, opponent: Opponent) -> None:
        self.gold += opponent.gold
        self.wins += 1
        if self.opponent_index < len(OPPONENTS) - 1:
            self.opponent_index += 1

    def record_loss(self) -> None:
        self.losses += 1
        self.hp = max(1, self.max_hp // 2)   # carried out alive, but battered

    def to_dict(self) -> dict:
        return {
            'max_hp': self.max_hp,
            'hp': self.hp,
            'base_attack': self.base_attack,
            'base_defense': self.base_defense,
            'gold': self.gold,
            'armor': dict(self.armor),
            'wins': self.wins,
            'losses': self.losses,
            'opponent_index': self.opponent_index,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Gladiator':
        g = cls()
        g.max_hp          = int(data.get('max_hp', STARTING_MAX_HP))
        g.hp               = int(data.get('hp', g.max_hp))
        g.base_attack      = int(data.get('base_attack', STARTING_ATTACK))
        g.base_defense     = int(data.get('base_defense', STARTING_DEFENSE))
        g.gold             = int(data.get('gold', STARTING_GOLD))
        saved_armor        = data.get('armor') or {}
        g.armor            = {slot: saved_armor.get(slot) for slot in SLOTS}
        g.wins             = int(data.get('wins', 0))
        g.losses           = int(data.get('losses', 0))
        g.opponent_index   = max(0, min(int(data.get('opponent_index', 0)), len(OPPONENTS) - 1))
        return g


# ---------------------------------------------------------------------------
# Save / load
# ---------------------------------------------------------------------------

SAVE_CATEGORY = 'gladiator'
SAVE_FILENAME = 'save.json'


def _save_path(config) -> Optional[str]:
    if config is None:
        return None
    return os.path.join(config.data_dir, SAVE_CATEGORY, SAVE_FILENAME)


def load_game(config=None) -> Gladiator:
    """Load saved progress, or return a fresh Gladiator if none exists."""
    path = _save_path(config)
    if path and os.path.exists(path):
        try:
            with open(path) as f:
                return Gladiator.from_dict(json.load(f))
        except Exception as e:
            log.warning('Could not load gladiator save (%s), starting fresh', e)
    return Gladiator()


def save_game(config, player: Gladiator) -> None:
    """Persist progress. Silently does nothing if config is None."""
    path = _save_path(config)
    if not path:
        return
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            json.dump(player.to_dict(), f, indent=2)
    except OSError as e:
        log.warning('Could not save gladiator progress (%s)', e)


# ---------------------------------------------------------------------------
# Combat — display-agnostic, safe to unit test without any UI
# ---------------------------------------------------------------------------

MISS_CHANCE           = 0.08
CRIT_CHANCE           = 0.12
CRIT_MULT             = 1.5
POWER_MULT            = 1.5
ENEMY_POWER_MULT      = 1.4
ENEMY_HESITATE_CHANCE = 0.12
ENEMY_POWER_CHANCE    = 0.15


def roll_damage(atk: int, dfn: int, rng: random.Random) -> tuple[int, bool]:
    """Return (damage, is_crit) for one hit. Damage is always >= 1."""
    dmg = max(1, atk - dfn + rng.randint(-2, 2))
    crit = rng.random() < CRIT_CHANCE
    if crit:
        dmg = int(dmg * CRIT_MULT) + 1
    return dmg, crit


class Combat:
    """One battle between the player and a live copy of an opponent's HP."""

    def __init__(self, player: Gladiator, opponent: Opponent,
                 rng: Optional[random.Random] = None) -> None:
        self.player   = player
        self.opponent = opponent
        self.enemy_hp = opponent.max_hp
        self.rng      = rng or random.Random()
        self.log: list[str] = [f'"{opponent.taunt}"']
        self.defending = False
        self.result: Optional[str] = None   # None | 'win' | 'loss' | 'fled'

    @property
    def over(self) -> bool:
        return self.result is not None

    def player_attack(self, power: bool = False) -> None:
        if self.over:
            return
        self.defending = False
        if self.rng.random() < MISS_CHANCE:
            self.log.append('You swing and miss!')
        else:
            atk = int(self.player.attack * POWER_MULT) if power else self.player.attack
            dmg, crit = roll_damage(atk, self.opponent.defense, self.rng)
            self.enemy_hp = max(0, self.enemy_hp - dmg)
            verb = 'smash' if power else 'strike'
            self.log.append(f'You {verb} for {dmg}!' + (' CRITICAL!' if crit else ''))
        self._check_end()
        if not self.over:
            self._enemy_turn()

    def player_defend(self) -> None:
        if self.over:
            return
        self.defending = True
        healed = self.player.heal(2)
        msg = 'You brace behind your shield.'
        if healed:
            msg += f' (+{healed} HP)'
        self.log.append(msg)
        self._enemy_turn()

    def flee(self) -> None:
        if self.over:
            return
        self.result = 'fled'
        self.log.append('You flee the arena!')

    def _enemy_turn(self) -> None:
        if self.over:
            return
        roll = self.rng.random()
        if roll < ENEMY_HESITATE_CHANCE:
            self.log.append(f'{self.opponent.name} hesitates, catching their breath.')
        else:
            power = roll > (1 - ENEMY_POWER_CHANCE)
            atk = int(self.opponent.attack * ENEMY_POWER_MULT) if power else self.opponent.attack
            dmg, crit = roll_damage(atk, self.player.defense, self.rng)
            if self.defending:
                dmg = max(1, dmg // 2)
            self.player.hp = max(0, self.player.hp - dmg)
            verb = 'crushes' if power else 'hits'
            self.log.append(f'{self.opponent.name} {verb} you for {dmg}!' + (' CRITICAL!' if crit else ''))
        self.defending = False
        self._check_end()

    def _check_end(self) -> None:
        if self.enemy_hp <= 0:
            self.result = 'win'
            self.log.append(f'{self.opponent.name} falls! Victory!')
        elif self.player.hp <= 0:
            self.result = 'loss'
            self.log.append('You collapse in the sand...')


# ---------------------------------------------------------------------------
# Input — polled directly from the display, no second InputHandler
# ---------------------------------------------------------------------------

_CURSES_KEYMAP = {
    curses.KEY_UP: 'UP', curses.KEY_DOWN: 'DOWN',
    ord('w'): 'UP', ord('s'): 'DOWN',
    ord('\n'): 'SELECT', ord('\r'): 'SELECT', ord(' '): 'SELECT',
    27: 'BACK', ord('q'): 'BACK',
}


def _supports_input(display) -> bool:
    return hasattr(display, 'get_tap') or hasattr(display, '_stdscr')


def _read_key(display) -> Optional[str]:
    """Poll one input event. Returns 'UP'/'DOWN'/'SELECT'/'BACK'/'JUMP:<n>'/None."""
    if hasattr(display, 'get_tap'):                       # TouchDisplay
        tap = display.get_tap()
        return display.tap_to_zone(*tap) if tap else None
    if hasattr(display, '_stdscr') and display._stdscr:   # TerminalDisplay
        display._stdscr.timeout(100)
        return _CURSES_KEYMAP.get(display.getch())
    return None


def _select(display, title: str, options: list[str]) -> int:
    """Blocking menu select. Returns the chosen index, or -1 on BACK."""
    selected = 0
    while True:
        display.draw_menu(title, options, selected)
        key = _read_key(display)
        if key is None:
            time.sleep(0.02)
            continue
        if key == 'UP':
            selected = max(0, selected - 1)
        elif key == 'DOWN':
            selected = min(len(options) - 1, selected + 1)
        elif key.startswith('JUMP:'):
            return int(key.split(':', 1)[1])
        elif key == 'SELECT':
            return selected
        elif key == 'BACK':
            return -1


def _show(display, lines: list[str]) -> None:
    """Show a message screen and block until SELECT/BACK/tap dismisses it."""
    display.draw_message(lines)
    while True:
        key = _read_key(display)
        if key in ('SELECT', 'BACK') or (key and key.startswith('JUMP:')):
            return
        time.sleep(0.02)


# ---------------------------------------------------------------------------
# Combat screen rendering
# ---------------------------------------------------------------------------

def _bar(value: int, max_value: int, width: int = 10) -> str:
    value = max(0, min(value, max_value))
    filled = int(width * value / max(1, max_value))
    return '[' + '#' * filled + '-' * (width - filled) + ']'


def _combat_screen_lines(combat: Combat) -> list[str]:
    p, o = combat.player, combat.opponent
    lines = [
        o.name,
        f'You {_bar(p.hp, p.max_hp)} {p.hp}/{p.max_hp}',
        f'Foe {_bar(combat.enemy_hp, o.max_hp)} {combat.enemy_hp}/{o.max_hp}',
        '',
    ]
    lines.extend(combat.log[-4:])
    return lines


# ---------------------------------------------------------------------------
# Talking NPCs
# ---------------------------------------------------------------------------

ARMORER_LINES = [
    'Steel keeps you breathing, friend.',
    'Bronze is cheap. Cheap gets you killed.',
    'Iron for those who mean business.',
    'A good shield outlives a good sword arm.',
]


def _owned_label(player: Gladiator, slot: str) -> str:
    name = player.armor.get(slot)
    if not name:
        return 'none'
    piece = find_armor(name)
    return f'{name} +{piece.defense}' if piece else name


def _talk_armorer(display, player: Gladiator, config) -> None:
    _show(display, ['Magnus the Armorer', '', random.choice(ARMORER_LINES)])
    while True:
        options = [f'{slot}: {_owned_label(player, slot)}' for slot in SLOTS] + ['Leave']
        choice = _select(display, 'Magnus the Armorer', options)
        if choice == -1 or choice == len(SLOTS):
            return
        _buy_armor_menu(display, player, SLOTS[choice], config)


def _buy_armor_menu(display, player: Gladiator, slot: str, config) -> None:
    items = armor_for_slot(slot)
    while True:
        labels = []
        for a in items:
            mark = ' [equipped]' if player.armor.get(slot) == a.name else ''
            labels.append(f'{a.name} +{a.defense}DEF {a.price}g{mark}')
        labels.append('Back')
        choice = _select(display, f'Buy {slot}', labels)
        if choice == -1 or choice == len(items):
            return
        piece = items[choice]
        if player.armor.get(slot) == piece.name:
            _show(display, ['Already equipped.'])
            continue
        if not player.can_afford(piece.price):
            _show(display, ['Not enough gold.', f'Need {piece.price}g, have {player.gold}g'])
            continue
        player.gold -= piece.price
        player.equip(piece)
        save_game(config, player)
        _show(display, [f'Equipped {piece.name}!', f'Defense is now {player.defense}'])


HEAL_SMALL_AMOUNT   = 20
HEAL_SMALL_COST     = 10
GOLD_PER_HP_FULL    = 1


def _talk_healer(display, player: Gladiator, config) -> None:
    _show(display, ['Vita the Healer', '', 'Let me mend your wounds.'])
    while True:
        missing = player.max_hp - player.hp
        full_cost = missing * GOLD_PER_HP_FULL
        options = [
            f'Patch up {HEAL_SMALL_AMOUNT}HP ({HEAL_SMALL_COST}g)',
            f'Full heal ({full_cost}g)',
            'Leave',
        ]
        choice = _select(display, 'Vita the Healer', options)
        if choice == -1 or choice == 2:
            return
        if choice == 0:
            _do_heal(display, player, config, HEAL_SMALL_AMOUNT, HEAL_SMALL_COST)
        elif choice == 1:
            if missing <= 0:
                _show(display, ['Already at full HP!'])
            else:
                _do_heal(display, player, config, missing, full_cost)


def _do_heal(display, player: Gladiator, config, amount: int, cost: int) -> None:
    if player.hp >= player.max_hp:
        _show(display, ['Already at full HP!'])
        return
    if not player.can_afford(cost):
        _show(display, ['Not enough gold.', f'Need {cost}g, have {player.gold}g'])
        return
    player.gold -= cost
    healed = player.heal(amount)
    save_game(config, player)
    _show(display, [f'Healed {healed} HP!', f'HP: {player.hp}/{player.max_hp}'])


def _talk_arena_master(display, player: Gladiator, config) -> None:
    opp = player.next_opponent
    _show(display, ['Dominus, Arena Master', '', f'Next: {opp.name}', f'"{opp.taunt}"'])
    while True:
        choice = _select(display, 'Dominus', ['Enter the Arena', 'Opponent stats', 'Leave'])
        if choice == -1 or choice == 2:
            return
        if choice == 1:
            _show(display, [
                opp.name,
                f'HP {opp.max_hp}  ATK {opp.attack}',
                f'DEF {opp.defense}  Reward {opp.gold}g',
            ])
        elif choice == 0:
            if player.hp <= max(1, player.max_hp * 0.15):
                _show(display, ['Too wounded to fight!', 'See Vita the Healer first.'])
                continue
            _run_combat(display, player, config)
            opp = player.next_opponent


def _run_combat(display, player: Gladiator, config) -> None:
    opp = player.next_opponent
    for pct in (25, 50, 75, 100):
        display.draw_progress('Entering the Arena...', pct, 100)
        time.sleep(0.1)

    combat = Combat(player, opp)
    _show(display, _combat_screen_lines(combat))
    while not combat.over:
        action = _select(display, 'Your move', ['Attack', 'Power Attack', 'Defend', 'Flee'])
        if action == -1:
            continue   # BACK does nothing mid-fight — Flee is the only way out
        if action == 0:
            combat.player_attack(power=False)
        elif action == 1:
            combat.player_attack(power=True)
        elif action == 2:
            combat.player_defend()
        elif action == 3:
            combat.flee()
        _show(display, _combat_screen_lines(combat))

    if combat.result == 'win':
        was_champion = player.champion_of_arena
        player.record_win(opp)
        lines = ['VICTORY!', f'+{opp.gold} gold  ({player.gold}g total)']
        if not was_champion and player.champion_of_arena:
            lines = ['CHAMPION OF THE ARENA!'] + lines
    elif combat.result == 'loss':
        player.record_loss()
        lines = ['DEFEATED...', 'Carried from the sand.', f'HP restored to {player.hp}']
    else:
        lines = ['You flee the arena.', 'No shame in living to fight on.']
    save_game(config, player)
    _show(display, lines)


def _view_stats(display, player: Gladiator) -> None:
    _show(display, [
        'Your Stats',
        f'Gold: {player.gold}',
        f'HP: {player.hp}/{player.max_hp}',
        f'ATK {player.attack}  DEF {player.defense}',
        f'Wins {player.wins}  Losses {player.losses}',
        f'Helmet: {_owned_label(player, "Helmet")}',
        f'Chest: {_owned_label(player, "Chest")}',
        f'Shield: {_owned_label(player, "Shield")}',
    ])


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def play_gladiator(display=None, config=None) -> dict:
    """Run the Gladiator Arena hub until the player leaves.
    Returns the player's final stats as a dict."""
    from core.display import TerminalDisplay

    owns_display = display is None
    if owns_display:
        display = TerminalDisplay()
    if config is None:
        from core.config_manager import ConfigManager
        config = ConfigManager()

    try:
        if not _supports_input(display):
            display.draw_message(['Gladiator Arena', 'needs the touch', 'screen or terminal', 'to play.'])
            time.sleep(3)
            return {}

        player = load_game(config)
        _show(display, ['GLADIATOR ARENA', '', 'Fight. Earn gold.', 'Gear up. Survive.'])
        while True:
            choice = _select(display, 'Gladiator Arena', [
                'Talk to Magnus (Armor)',
                'Talk to Vita (Healer)',
                'Talk to Dominus (Fight)',
                'View My Stats',
                'Leave Arena',
            ])
            if choice == -1 or choice == 4:
                break
            elif choice == 0:
                _talk_armorer(display, player, config)
            elif choice == 1:
                _talk_healer(display, player, config)
            elif choice == 2:
                _talk_arena_master(display, player, config)
            elif choice == 3:
                _view_stats(display, player)
        save_game(config, player)
        return player.to_dict()
    finally:
        if owns_display:
            display.cleanup()
