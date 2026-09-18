"""Unit tests for Gladiator Arena logic (no display required)."""
import sys
import os
import random
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.config_manager import ConfigManager
from modules.games.gladiator import (
    ARMOR_CATALOG, OPPONENTS, SLOTS,
    ArmorPiece, Opponent, Gladiator, Combat,
    armor_for_slot, find_armor, roll_damage,
    load_game, save_game,
    STARTING_GOLD, STARTING_MAX_HP, STARTING_ATTACK, STARTING_DEFENSE,
)
from modules.games.games_menu import build_games_menu


def make_config(tmp_dir: str) -> ConfigManager:
    cfg_file = os.path.join(tmp_dir, 'config.ini')
    with open(cfg_file, 'w') as f:
        f.write(f'[storage]\ndata_dir = {tmp_dir}\n')
    return ConfigManager(cfg_file)


class _FixedRNG:
    """Deterministic stand-in for random.Random: pops queued .random()
    values in order, and always returns a fixed .randint()."""

    def __init__(self, randoms, randint_value=0):
        self._randoms = list(randoms)
        self._randint_value = randint_value

    def random(self):
        return self._randoms.pop(0) if self._randoms else 0.99

    def randint(self, a, b):
        return self._randint_value


# ---------------------------------------------------------------------------
# Catalog helpers
# ---------------------------------------------------------------------------

class TestCatalog(unittest.TestCase):

    def test_armor_for_slot_only_returns_that_slot(self):
        for slot in SLOTS:
            pieces = armor_for_slot(slot)
            self.assertTrue(pieces)
            self.assertTrue(all(p.slot == slot for p in pieces))

    def test_find_armor_by_name(self):
        piece = ARMOR_CATALOG[0]
        self.assertEqual(find_armor(piece.name), piece)

    def test_find_armor_missing_returns_none(self):
        self.assertIsNone(find_armor('Nonexistent Item'))

    def test_opponents_increase_in_difficulty(self):
        for a, b in zip(OPPONENTS, OPPONENTS[1:]):
            self.assertLessEqual(a.max_hp, b.max_hp)
            self.assertLessEqual(a.attack, b.attack)
            self.assertLessEqual(a.gold, b.gold)


# ---------------------------------------------------------------------------
# Gladiator (player) state
# ---------------------------------------------------------------------------

class TestGladiator(unittest.TestCase):

    def setUp(self):
        self.player = Gladiator()

    def test_starting_stats(self):
        self.assertEqual(self.player.hp, STARTING_MAX_HP)
        self.assertEqual(self.player.gold, STARTING_GOLD)
        self.assertEqual(self.player.attack, STARTING_ATTACK)
        self.assertEqual(self.player.defense, STARTING_DEFENSE)
        self.assertEqual(self.player.wins, 0)

    def test_attack_grows_with_wins(self):
        before = self.player.attack
        self.player.record_win(OPPONENTS[0])
        self.assertEqual(self.player.attack, before + 1)

    def test_defense_includes_equipped_armor(self):
        helmet = armor_for_slot('Helmet')[0]
        shield = armor_for_slot('Shield')[0]
        self.player.equip(helmet)
        self.player.equip(shield)
        self.assertEqual(self.player.defense, STARTING_DEFENSE + helmet.defense + shield.defense)

    def test_equip_replaces_previous_piece_in_same_slot(self):
        cheap = armor_for_slot('Chest')[0]
        pricey = armor_for_slot('Chest')[1]
        self.player.equip(cheap)
        self.player.equip(pricey)
        self.assertEqual(self.player.armor['Chest'], pricey.name)

    def test_can_afford(self):
        self.assertTrue(self.player.can_afford(self.player.gold))
        self.assertFalse(self.player.can_afford(self.player.gold + 1))

    def test_heal_caps_at_max_hp(self):
        self.player.hp = self.player.max_hp - 5
        healed = self.player.heal(999)
        self.assertEqual(healed, 5)
        self.assertEqual(self.player.hp, self.player.max_hp)

    def test_heal_returns_zero_when_already_full(self):
        self.assertEqual(self.player.heal(10), 0)

    def test_record_win_adds_gold_and_advances_opponent(self):
        opp = OPPONENTS[0]
        gold_before = self.player.gold
        self.player.record_win(opp)
        self.assertEqual(self.player.gold, gold_before + opp.gold)
        self.assertEqual(self.player.opponent_index, 1)
        self.assertEqual(self.player.wins, 1)

    def test_record_win_does_not_advance_past_last_opponent(self):
        self.player.opponent_index = len(OPPONENTS) - 1
        self.player.record_win(OPPONENTS[-1])
        self.assertEqual(self.player.opponent_index, len(OPPONENTS) - 1)

    def test_record_loss_halves_hp_and_keeps_progress(self):
        self.player.gold = 123
        self.player.opponent_index = 3
        self.player.hp = self.player.max_hp
        self.player.record_loss()
        self.assertEqual(self.player.hp, self.player.max_hp // 2)
        self.assertEqual(self.player.gold, 123)
        self.assertEqual(self.player.opponent_index, 3)
        self.assertEqual(self.player.losses, 1)

    def test_record_loss_never_drops_hp_to_zero(self):
        self.player.max_hp = 1
        self.player.hp = 1
        self.player.record_loss()
        self.assertGreaterEqual(self.player.hp, 1)

    def test_champion_of_arena_false_initially(self):
        self.assertFalse(self.player.champion_of_arena)

    def test_champion_of_arena_true_after_beating_whole_roster(self):
        for opp in OPPONENTS:
            self.player.record_win(opp)
        self.assertTrue(self.player.champion_of_arena)

    def test_next_opponent_matches_index(self):
        self.assertEqual(self.player.next_opponent, OPPONENTS[0])
        self.player.record_win(OPPONENTS[0])
        self.assertEqual(self.player.next_opponent, OPPONENTS[1])


# ---------------------------------------------------------------------------
# roll_damage (pure damage formula)
# ---------------------------------------------------------------------------

class TestRollDamage(unittest.TestCase):

    def test_damage_never_below_one_even_when_outmatched(self):
        rng = random.Random(1)
        for _ in range(200):
            dmg, _ = roll_damage(atk=1, dfn=999, rng=rng)
            self.assertGreaterEqual(dmg, 1)

    def test_crit_multiplies_damage(self):
        normal, crit = 0, 0
        # First .random() call is miss-independent here since roll_damage
        # only consumes randint() then random() for the crit check.
        normal, _ = roll_damage(20, 5, _FixedRNG([0.99], randint_value=0))
        crit, is_crit = roll_damage(20, 5, _FixedRNG([0.0], randint_value=0))
        self.assertTrue(is_crit)
        self.assertGreater(crit, normal)


# ---------------------------------------------------------------------------
# Combat — outcomes tested via lopsided stats so the result is
# deterministic regardless of exact RNG draws (miss/crit/hesitate).
# ---------------------------------------------------------------------------

class TestCombat(unittest.TestCase):

    def _overwhelming_player(self):
        player = Gladiator()
        player.base_attack = 999
        player.base_defense = 999
        player.hp = player.max_hp = 999
        return player

    def _overwhelming_opponent(self):
        return Opponent('Colossus', max_hp=999, attack=999, defense=0, gold=0, taunt='...')

    def test_overwhelming_player_wins(self):
        player = self._overwhelming_player()
        opponent = OPPONENTS[0]
        combat = Combat(player, opponent, rng=random.Random(42))
        for _ in range(50):
            if combat.over:
                break
            combat.player_attack()
        self.assertEqual(combat.result, 'win')
        self.assertEqual(combat.enemy_hp, 0)
        self.assertGreater(player.hp, 0)

    def test_overwhelming_opponent_wins(self):
        player = Gladiator()
        player.hp = player.max_hp = 5
        player.base_defense = 0
        opponent = self._overwhelming_opponent()
        combat = Combat(player, opponent, rng=random.Random(7))
        for _ in range(50):
            if combat.over:
                break
            combat.player_attack()
        self.assertEqual(combat.result, 'loss')
        self.assertEqual(player.hp, 0)

    def test_flee_ends_combat_without_changing_hp(self):
        player = Gladiator()
        opponent = OPPONENTS[0]
        combat = Combat(player, opponent, rng=random.Random(3))
        combat.flee()
        self.assertEqual(combat.result, 'fled')
        self.assertEqual(combat.enemy_hp, opponent.max_hp)
        self.assertEqual(player.hp, player.max_hp)

    def test_actions_after_combat_over_are_no_ops(self):
        player = Gladiator()
        opponent = OPPONENTS[0]
        combat = Combat(player, opponent, rng=random.Random(5))
        combat.flee()
        log_len = len(combat.log)
        combat.player_attack()
        combat.player_defend()
        self.assertEqual(len(combat.log), log_len)

    def test_defend_does_not_raise_and_keeps_hp_in_bounds(self):
        player = Gladiator()
        opponent = OPPONENTS[0]
        combat = Combat(player, opponent, rng=random.Random(9))
        combat.player_defend()
        self.assertTrue(0 <= player.hp <= player.max_hp)
        self.assertTrue(any('brace' in line for line in combat.log))


# ---------------------------------------------------------------------------
# Save / load
# ---------------------------------------------------------------------------

class TestPersistence(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.config = make_config(self.tmp)

    def test_load_without_save_returns_fresh_player(self):
        player = load_game(self.config)
        self.assertEqual(player.gold, STARTING_GOLD)

    def test_save_and_load_round_trip(self):
        player = Gladiator()
        player.gold = 321
        player.wins = 4
        player.losses = 2
        player.hp = 17
        piece = ARMOR_CATALOG[0]
        player.equip(piece)
        save_game(self.config, player)

        loaded = load_game(self.config)
        self.assertEqual(loaded.gold, 321)
        self.assertEqual(loaded.wins, 4)
        self.assertEqual(loaded.losses, 2)
        self.assertEqual(loaded.hp, 17)
        self.assertEqual(loaded.armor[piece.slot], piece.name)

    def test_load_ignores_corrupt_save_file(self):
        path = os.path.join(self.tmp, 'gladiator', 'save.json')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            f.write('not valid json{{{')
        player = load_game(self.config)
        self.assertEqual(player.gold, STARTING_GOLD)

    def test_save_game_with_none_config_does_not_raise(self):
        save_game(None, Gladiator())

    def test_load_game_with_none_config_returns_fresh_player(self):
        player = load_game(None)
        self.assertEqual(player.gold, STARTING_GOLD)


# ---------------------------------------------------------------------------
# Menu wiring
# ---------------------------------------------------------------------------

class TestGamesMenuWiring(unittest.TestCase):

    def test_gladiator_arena_registered_in_games_menu(self):
        tmp = tempfile.mkdtemp()
        config = make_config(tmp)
        entries = build_games_menu(config, display=None)
        labels = [e.label for e in entries]
        self.assertIn('Gladiator Arena', labels)


if __name__ == '__main__':
    unittest.main()
