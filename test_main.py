import unittest
from unittest.mock import patch

from main import (
    apply_skill_points,
    assess_attack,
    assess_health_needs,
    assess_icicle_use,
    assess_zapper_use,
    bomb_nearby,
    dedupe_moves,
    dist_squared_to,
    filter_threats,
    handle_bomb_threat,
    handle_collisions,
    handle_icicle_threat,
    losing_battle,
    peripheral_danger,
    player_unprepared,
    stock_full,
)


class TestPlayerUnpreparedFunction(unittest.TestCase):
    def test_no_big_potions_and_low_health(self):
        # Case: Player has no big potions and low health, item is not a big potion
        own_player = {
            "items": {"big_potions": []},
            "health": 50,
            "special_equipped": "shield",
        }
        item = {"type": "wolf"}
        self.assertTrue(player_unprepared(own_player, item))

    def test_no_big_potions_but_sufficient_health(self):
        # Case: Player has no big potions but health is sufficient
        own_player = {
            "items": {"big_potions": []},
            "health": 90,
            "special_equipped": "shield",
        }
        item = {"type": "wolf"}
        self.assertFalse(player_unprepared(own_player, item))

    def test_item_is_big_potion(self):
        # Case: Item is a big potion
        own_player = {
            "items": {"big_potions": []},
            "health": 50,
            "special_equipped": "shield",
        }
        item = {"type": "big_potion"}
        self.assertFalse(player_unprepared(own_player, item))

    def test_chest_or_power_up_with_no_bomb(self):
        # Case: Item is chest or power_up and special equipped is not bomb
        own_player = {
            "items": {"big_potions": [1]},
            "health": 100,
            "special_equipped": "shield",
        }
        item = {"type": "chest"}
        self.assertFalse(player_unprepared(own_player, item))

    def test_shockwave_with_special_equipped(self):
        # Case: Item has power "shockwave" and player has a special equipped
        own_player = {
            "items": {"big_potions": [1]},
            "health": 100,
            "special_equipped": "shield",
        }
        item = {"power": "shockwave"}
        self.assertTrue(player_unprepared(own_player, item))

    def test_shockwave_without_special_equipped(self):
        # Case: Item has power "shockwave" but no special is equipped
        own_player = {
            "items": {"big_potions": [1]},
            "health": 100,
            "special_equipped": None,
        }
        item = {"power": "shockwave"}
        self.assertFalse(player_unprepared(own_player, item))

    def test_other_items_with_no_conditions_met(self):
        # Case: None of the conditions are met for other item types
        own_player = {
            "items": {"big_potions": [1]},
            "health": 100,
            "special_equipped": "shield",
        }
        item = {"type": "wolf"}
        self.assertFalse(player_unprepared(own_player, item))


class TestHandleBombThreatFunction(unittest.TestCase):
    def test_bomb_on_the_right(self):
        # Case: Bomb is to the right of the player
        own_player = {"position": {"x": 50, "y": 50}}
        target = {"position": {"x": 0, "y": 0}}
        bomb = {"position": {"x": 100, "y": 50}}
        moves = []

        updated_moves = handle_bomb_threat(own_player, target, bomb, moves)

        self.assertIn("shield", updated_moves)
        self.assertEqual(target["position"], {"x": -50, "y": 50})

    def test_bomb_on_the_left(self):
        # Case: Bomb is to the left of the player
        own_player = {"position": {"x": 50, "y": 50}}
        target = {"position": {"x": 0, "y": 0}}
        bomb = {"position": {"x": 0, "y": 50}}
        moves = []

        updated_moves = handle_bomb_threat(own_player, target, bomb, moves)

        self.assertIn("shield", updated_moves)
        self.assertEqual(target["position"], {"x": 150, "y": 50})

    def test_bomb_above(self):
        # Case: Bomb is above the player
        own_player = {"position": {"x": 50, "y": 50}}
        target = {"position": {"x": 0, "y": 0}}
        bomb = {"position": {"x": 50, "y": 100}}
        moves = []

        updated_moves = handle_bomb_threat(own_player, target, bomb, moves)

        self.assertIn("shield", updated_moves)
        self.assertEqual(target["position"], {"x": 50, "y": -50})

    def test_bomb_below(self):
        # Case: Bomb is below the player
        own_player = {"position": {"x": 50, "y": 50}}
        target = {"position": {"x": 0, "y": 0}}
        bomb = {"position": {"x": 50, "y": 0}}
        moves = []

        updated_moves = handle_bomb_threat(own_player, target, bomb, moves)

        self.assertIn("shield", updated_moves)
        self.assertEqual(target["position"], {"x": 50, "y": 150})

    def test_no_bomb(self):
        # Case: No bomb present
        own_player = {"position": {"x": 50, "y": 50}}
        target = {"position": {"x": 0, "y": 0}}
        bomb = None
        moves = []

        updated_moves = handle_bomb_threat(own_player, target, bomb, moves)

        self.assertEqual(updated_moves, [])
        self.assertEqual(target["position"], {"x": 0, "y": 0})


class TestFilterThreatsFunction(unittest.TestCase):
    def test_all_threats_filtered(self):
        # Case: All threats meet the criteria and should be included
        threats = [
            {"health": 50, "status": "active"},
            {"health": 100},
            {"status": "alert"},
        ]
        filtered = filter_threats(threats)
        self.assertEqual(len(filtered), len(threats))
        self.assertEqual(filtered, threats)

    def test_no_threats_filtered(self):
        # Case: No threats meet the criteria
        threats = [
            {"health": 0, "status": "idle"},
            {"health": None, "status": "idle"},
        ]
        filtered = filter_threats(threats)
        self.assertEqual(filtered, [])

    def test_some_threats_filtered(self):
        # Case: Only some threats meet the criteria
        threats = [
            {"health": 50, "status": "active"},  # Valid
            {"health": 0, "status": "idle"},  # Invalid
            {"status": "alert"},  # Valid
        ]
        filtered = filter_threats(threats)
        self.assertEqual(len(filtered), 2)
        self.assertIn({"health": 50, "status": "active"}, filtered)
        self.assertIn({"status": "alert"}, filtered)

    def test_threats_with_missing_fields(self):
        # Case: Threats missing fields
        threats = [
            {"health": 50},  # Valid
            {},  # Invalid
            {"status": "idle"},  # Invalid
        ]
        filtered = filter_threats(threats)
        self.assertEqual(len(filtered), 1)
        self.assertIn({"health": 50}, filtered)

    def test_empty_list(self):
        # Case: Empty threats list
        threats = []
        filtered = filter_threats(threats)
        self.assertEqual(filtered, [])


class TestPeripheralDanger(unittest.TestCase):
    def setUp(self):
        """Set up common test data."""
        self.own_player = {
            "health": 100,
            "items": {"big_potions": [100, 100]},  # Adds 200 health
        }
        self.item = {"position": {"x": 50, "y": 50}}
        self.enemies = []
        self.players = []
        self.hazards = []

    def test_no_threats(self):
        """Test when there are no enemies, players, or hazards."""
        result = peripheral_danger(
            self.own_player, self.item, self.enemies, self.players, self.hazards
        )
        self.assertFalse(result, "No threats should result in no danger.")

    def test_low_danger_within_radius(self):
        """Test when danger in the radius is less than player health."""
        self.enemies = [{"position": {"x": 60, "y": 60}, "attack_damage": 50}]
        result = peripheral_danger(
            self.own_player, self.item, self.enemies, self.players, self.hazards
        )
        self.assertFalse(result, "Danger less than player health is okay.")

    def test_enemy_outside_danger_radius(self):
        """Test when an enemy is outside the danger radius."""
        self.enemies = [{"position": {"x": 500, "y": 50}, "attack_damage": 50}]
        result = peripheral_danger(
            self.own_player, self.item, self.enemies, self.players, self.hazards
        )
        self.assertFalse(
            result, "An enemy outside the radius should not result in danger."
        )

    def test_danger_on_the_edge(self):
        """Test with multiple enemies, players, and hazards contributing to danger."""
        self.enemies = [{"position": {"x": 60, "y": 60}, "attack_damage": 50}]
        self.players = [{"position": {"x": 55, "y": 55}, "attack_damage": 30}]
        self.hazards = [{"position": {"x": 52, "y": 52}, "attack_damage": 20}]
        result = peripheral_danger(
            self.own_player, self.item, self.enemies, self.players, self.hazards
        )
        self.assertFalse(result, "Multiple threats can be below threshold.")

    def test_danger_exceeds_threshold(self):
        """Test with multiple enemies, players, and hazards contributing to danger."""
        self.enemies = [{"position": {"x": 60, "y": 60}, "attack_damage": 150}]
        self.players = [{"position": {"x": 55, "y": 55}, "attack_damage": 90}]
        self.hazards = [{"position": {"x": 52, "y": 52}, "attack_damage": 80}]
        result = peripheral_danger(
            self.own_player, self.item, self.enemies, self.players, self.hazards
        )
        self.assertTrue(result, "Multiple threats can exceed danger threshold.")

    def test_edge_case_radius(self):
        """Test when a threat is at the exact edge of the danger radius."""
        self.hazards = [
            {"position": {"x": 50 + int(60000**0.5), "y": 50}, "attack_damage": 50}
        ]
        result = peripheral_danger(
            self.own_player, self.item, self.enemies, self.players, self.hazards
        )
        self.assertFalse(
            result, "Threats at the edge of the radius should not count as danger."
        )


class TestDistSquaredTo(unittest.TestCase):
    def test_zero_distance(self):
        """Test when both points are the same."""
        point_a = {"x": 0, "y": 0}
        point_b = {"x": 0, "y": 0}
        self.assertEqual(dist_squared_to(point_a, point_b), 0)

    def test_positive_coordinates(self):
        """Test with points in the first quadrant."""
        point_a = {"x": 3, "y": 4}
        point_b = {"x": 0, "y": 0}
        self.assertEqual(dist_squared_to(point_a, point_b), 25)

    def test_negative_coordinates(self):
        """Test with points in the third quadrant."""
        point_a = {"x": -3, "y": -4}
        point_b = {"x": 0, "y": 0}
        self.assertEqual(dist_squared_to(point_a, point_b), 25)

    def test_mixed_coordinates(self):
        """Test with points in different quadrants."""
        point_a = {"x": -3, "y": 4}
        point_b = {"x": 3, "y": -4}
        self.assertEqual(dist_squared_to(point_a, point_b), 100)

    def test_large_coordinates(self):
        """Test with very large coordinates."""
        point_a = {"x": 100000, "y": 100000}
        point_b = {"x": 0, "y": 0}
        self.assertEqual(dist_squared_to(point_a, point_b), 20000000000)

    def test_decimal_coordinates(self):
        """Test with decimal values."""
        point_a = {"x": 1.5, "y": 2.5}
        point_b = {"x": 0, "y": 0}
        self.assertAlmostEqual(dist_squared_to(point_a, point_b), 8.5)

    def test_invalid_input_missing_keys(self):
        """Test with dictionaries missing keys."""
        point_a = {"x": 1}
        point_b = {"x": 0, "y": 0}
        with self.assertRaises(KeyError):
            dist_squared_to(point_a, point_b)

    def test_invalid_input_non_dict(self):
        """Test with non-dictionary input."""
        point_a = [1, 2]
        point_b = {"x": 0, "y": 0}
        with self.assertRaises(TypeError):
            dist_squared_to(point_a, point_b)


class TestApplySkillPoints(unittest.TestCase):
    def setUp(self):
        """Set up a base player and moves list."""
        self.base_player = {
            "levelling": {
                "available_skill_points": 0,
                "attack": 5,
                "speed": 5,
                "health": 5,
            }
        }
        self.base_moves = []

    def test_no_skill_points(self):
        """Test when there are no available skill points."""
        own_player = self.base_player
        moves = self.base_moves.copy()
        result = apply_skill_points(own_player, moves)
        self.assertEqual(
            result, [], "No moves should be added if no skill points are available."
        )

    def test_attack_higher_than_speed(self):
        """Test when attack is higher than speed."""
        own_player = {
            "levelling": {
                "available_skill_points": 1,
                "attack": 10,
                "speed": 5,
                "health": 5,
            }
        }
        moves = self.base_moves.copy()
        result = apply_skill_points(own_player, moves)
        self.assertIn(
            {"redeem_skill_point": "speed"},
            result,
            "Speed should be prioritized when attack is higher than speed.",
        )

    def test_speed_higher_than_health(self):
        """Test when speed is higher than health."""
        own_player = {
            "levelling": {
                "available_skill_points": 1,
                "attack": 5,
                "speed": 10,
                "health": 5,
            }
        }
        moves = self.base_moves.copy()
        result = apply_skill_points(own_player, moves)
        self.assertIn(
            {"redeem_skill_point": "health"},
            result,
            "Health should be prioritized when speed is higher than health.",
        )

    def test_health_highest(self):
        """Test when health is the highest attribute."""
        own_player = {
            "levelling": {
                "available_skill_points": 1,
                "attack": 5,
                "speed": 5,
                "health": 10,
            }
        }
        moves = self.base_moves.copy()
        result = apply_skill_points(own_player, moves)
        self.assertIn(
            {"redeem_skill_point": "attack"},
            result,
            "Attack should be prioritized when health is the highest attribute.",
        )

    def test_all_below_max(self):
        """Test when all attributes are below the maximum."""
        own_player = {
            "levelling": {
                "available_skill_points": 1,
                "attack": 10,
                "speed": 10,
                "health": 10,
            }
        }
        moves = self.base_moves.copy()
        result = apply_skill_points(own_player, moves)
        self.assertIn({"redeem_skill_point": "speed"}, result)
        self.assertIn({"redeem_skill_point": "health"}, result)
        self.assertIn({"redeem_skill_point": "attack"}, result)

    def test_some_at_max(self):
        """Test when some attributes are already at maximum."""
        own_player = {
            "levelling": {
                "available_skill_points": 1,
                "attack": 20,
                "speed": 15,
                "health": 15,
            }
        }
        moves = self.base_moves.copy()
        result = apply_skill_points(own_player, moves)
        self.assertIn(
            {"redeem_skill_point": "speed"},
            result,
            "Speed should still be redeemable if below max.",
        )
        self.assertIn(
            {"redeem_skill_point": "health"},
            result,
            "Health should still be redeemable if below max.",
        )
        self.assertNotIn(
            {"redeem_skill_point": "attack"},
            result,
            "Attack should not be redeemable if at max.",
        )

    def test_multiple_skill_points(self):
        """Test when there are multiple available skill points."""
        own_player = {
            "levelling": {
                "available_skill_points": 2,
                "attack": 5,
                "speed": 5,
                "health": 5,
            }
        }
        moves = self.base_moves.copy()
        result = apply_skill_points(own_player, moves)
        self.assertGreaterEqual(
            len(result),
            2,
            "Multiple skill points should allow multiple moves to be added.",
        )


class TestLosingBattle(unittest.TestCase):
    def test_losing_battle_true(self):
        """Test when the item's attack damage exceeds the player's health."""
        own_player = {"health": 50}
        item = {"attack_damage": 60}
        result = losing_battle(own_player, item)
        self.assertTrue(
            result,
            "Should return True when item attack damage is greater than player health.",
        )

    def test_losing_battle_false(self):
        """Test when the item's attack damage does not exceed the player's health."""
        own_player = {"health": 100}
        item = {"attack_damage": 60}
        result = losing_battle(own_player, item)
        self.assertFalse(
            result,
            "Should return False when item attack damage is less than or equal to player health.",
        )

    def test_no_attack_damage_key(self):
        """Test when the item does not have an attack_damage key."""
        own_player = {"health": 100}
        item = {"name": "Sword"}
        result = losing_battle(own_player, item)
        self.assertFalse(
            result, "Should return False when attack_damage key is missing in item."
        )

    def test_none_attack_damage(self):
        """Test when the attack_damage value is None."""
        own_player = {"health": 100}
        item = {"attack_damage": None}
        result = losing_battle(own_player, item)
        self.assertFalse(result, "Should return False when attack_damage is None.")

    def test_exactly_equal_damage_and_health(self):
        """Test when the item's attack damage is exactly equal to the player's health."""
        own_player = {"health": 120}
        item = {"attack_damage": 100}
        result = losing_battle(own_player, item)
        self.assertTrue(
            result, "Should return True when item attack damage equals player health."
        )

    def test_missing_health_key(self):
        """Test when the player does not have a health key."""
        own_player = {"mana": 50}
        item = {"attack_damage": 50}
        with self.assertRaises(
            KeyError,
            msg="Should raise KeyError if own_player does not have a health key.",
        ):
            losing_battle(own_player, item)


class TestStockFullFunction(unittest.TestCase):
    def test_ring_stock_full(self):
        # Case where ring stock is full
        own_player = {
            "items": {"rings": [1, 2, 3, 4], "speed_zappers": [], "big_potions": []}
        }
        item = {"type": "ring"}
        self.assertTrue(stock_full(own_player, item))

        # Case where ring stock is not full
        own_player["items"]["rings"] = [1, 2, 3]
        self.assertFalse(stock_full(own_player, item))

    def test_speed_zapper_stock_full(self):
        # Case where speed zapper stock is full
        own_player = {"items": {"rings": [], "speed_zappers": [1], "big_potions": []}}
        item = {"type": "speed_zapper"}
        self.assertTrue(stock_full(own_player, item))

        # Case where speed zapper stock is not full
        own_player["items"]["speed_zappers"] = []
        self.assertFalse(stock_full(own_player, item))

    def test_big_potion_stock_full(self):
        # Case where big potion stock is full
        own_player = {
            "items": {"rings": [], "speed_zappers": [], "big_potions": [1, 2, 3, 4, 5]}
        }
        item = {"type": "big_potion"}
        self.assertTrue(stock_full(own_player, item))

        # Case where big potion stock is not full
        own_player["items"]["big_potions"] = [1, 2, 3, 4]
        self.assertFalse(stock_full(own_player, item))

    def test_other_item_type(self):
        # Case for an unhandled item type
        own_player = {"items": {"rings": [], "speed_zappers": [], "big_potions": []}}
        item = {"type": "unknown_item"}
        self.assertFalse(stock_full(own_player, item))


class TestDedupeMovesFunction(unittest.TestCase):
    def test_no_duplicates(self):
        # Case where there are no duplicates
        moves = ["move1", "move2", "move3"]
        self.assertEqual(dedupe_moves(moves), ["move1", "move2", "move3"])

    def test_with_duplicates(self):
        # Case where there are duplicates
        moves = ["move1", "move2", "move1", "move3", "move2"]
        self.assertEqual(dedupe_moves(moves), ["move1", "move2", "move3"])

    def test_empty_list(self):
        # Case with an empty list
        moves = []
        self.assertEqual(dedupe_moves(moves), [])

    def test_all_duplicates(self):
        # Case where all elements are duplicates
        moves = ["move1", "move1", "move1"]
        self.assertEqual(dedupe_moves(moves), ["move1"])

    def test_single_element_list(self):
        # Case with a single-element list
        moves = ["move1"]
        self.assertEqual(dedupe_moves(moves), ["move1"])

    def test_mixed_data_types(self):
        # Case with mixed data types
        moves = ["move1", 2, "move1", 2, 3.5, "move2", 3.5]
        self.assertEqual(dedupe_moves(moves), ["move1", 2, 3.5, "move2"])


class TestBombNearbyFunction(unittest.TestCase):
    def test_bomb_nearby(self):
        # Case where a bomb is nearby and active
        item = {"position": {"x": 100, "y": 100}}
        hazards = [
            {"type": "bomb", "position": {"x": 110, "y": 110}, "status": "active"},
            {"type": "bomb", "position": {"x": 200, "y": 200}, "status": "idle"},
        ]
        self.assertEqual(
            bomb_nearby(item, hazards),
            {"type": "bomb", "position": {"x": 110, "y": 110}, "status": "active"},
        )

    def test_no_bomb_nearby(self):
        # Case where no bomb is nearby
        item = {"position": {"x": 100, "y": 100}}
        hazards = [
            {"type": "bomb", "position": {"x": 300, "y": 300}, "status": "active"},
            {"type": "bomb", "position": {"x": 400, "y": 400}, "status": "active"},
        ]
        self.assertEqual(bomb_nearby(item, hazards), {})

    def test_no_hazards(self):
        # Case with an empty hazard list
        item = {"position": {"x": 100, "y": 100}}
        hazards = []
        self.assertEqual(bomb_nearby(item, hazards), {})

    def test_other_hazard_type(self):
        # Case where hazards are not bombs
        item = {"position": {"x": 100, "y": 100}}
        hazards = [
            {"type": "icicle", "position": {"x": 110, "y": 110}, "status": "active"},
            {"type": "shockwave", "position": {"x": 120, "y": 120}, "status": "active"},
        ]
        self.assertEqual(bomb_nearby(item, hazards), {})

    def test_multiple_nearby_bombs(self):
        # Case with multiple nearby bombs, should return the first one
        item = {"position": {"x": 100, "y": 100}}
        hazards = [
            {"type": "bomb", "position": {"x": 110, "y": 110}, "status": "active"},
            {"type": "bomb", "position": {"x": 120, "y": 120}, "status": "active"},
        ]
        self.assertEqual(
            bomb_nearby(item, hazards),
            {"type": "bomb", "position": {"x": 110, "y": 110}, "status": "active"},
        )


class TestAssessAttackFunction(unittest.TestCase):
    def test_valid_attack(self):
        # Case where the target is in range, has health, and should be attacked
        own_player = {"position": {"x": 10, "y": 10}}
        target = {"position": {"x": 15, "y": 15}, "health": 50}
        moves = []

        updated_moves = assess_attack(own_player, target, moves)
        self.assertEqual(updated_moves, ["attack"])

    def test_target_out_of_range(self):
        # Case where the target is out of range
        own_player = {"position": {"x": 10, "y": 10}}
        target = {"position": {"x": 200, "y": 200}, "health": 50}
        moves = []

        updated_moves = assess_attack(own_player, target, moves)
        self.assertEqual(updated_moves, [])

    def test_target_no_health_field(self):
        # Case where the target has no health field
        own_player = {"position": {"x": 10, "y": 10}}
        target = {"position": {"x": 15, "y": 15}}
        moves = []

        updated_moves = assess_attack(own_player, target, moves)
        self.assertEqual(updated_moves, [])

    def test_attack_appends_to_existing_moves(self):
        # Case where moves already contain other actions
        own_player = {"position": {"x": 10, "y": 10}}
        target = {"position": {"x": 15, "y": 15}, "health": 50}
        moves = ["special"]

        updated_moves = assess_attack(own_player, target, moves)
        self.assertEqual(updated_moves, ["special", "attack"])


class TestAssessHealthNeedsFunction(unittest.TestCase):
    def test_danger_exceeds_health(self):
        # Case: Danger value exceeds player's health
        own_player = {
            "health": 30,
            "max_health": 100,
            "items": {"big_potions": [1, 2]},
            "is_cloaked": False,
        }
        total_danger_value = 50
        moves = []

        assess_health_needs(own_player, total_danger_value, moves)
        self.assertIn({"use": "big_potion"}, moves)
        self.assertIn({"use": "ring"}, moves)

    def test_health_below_40_percent(self):
        # Case: Player's health is below 40% of max health
        own_player = {
            "health": 35,
            "max_health": 100,
            "items": {"big_potions": [1]},
            "is_cloaked": False,
        }
        total_danger_value = 20
        moves = []

        assess_health_needs(own_player, total_danger_value, moves)
        self.assertIn({"use": "big_potion"}, moves)
        self.assertIn({"use": "ring"}, moves)

    def test_health_below_50_percent_with_two_potions(self):
        # Case: Health is below 50% but there are at least two potions
        own_player = {
            "health": 45,
            "max_health": 100,
            "items": {"big_potions": [1, 2]},
            "is_cloaked": False,
        }
        total_danger_value = 10
        moves = []

        assess_health_needs(own_player, total_danger_value, moves)
        self.assertIn({"use": "big_potion"}, moves)
        self.assertIn({"use": "ring"}, moves)

    def test_health_below_60_percent_with_five_potions(self):
        # Case: Health is below 60% but there are at least five potions
        own_player = {
            "health": 55,
            "max_health": 100,
            "items": {"big_potions": [1, 2, 3, 4, 5]},
            "is_cloaked": False,
        }
        total_danger_value = 10
        moves = []

        assess_health_needs(own_player, total_danger_value, moves)
        self.assertIn({"use": "big_potion"}, moves)
        self.assertNotIn({"use": "ring"}, moves)

    def test_cloaked_player_no_ring(self):
        # Case: Player is cloaked, so no ring is used
        own_player = {
            "health": 30,
            "max_health": 100,
            "items": {"big_potions": [1]},
            "is_cloaked": True,
        }
        total_danger_value = 40
        moves = []

        assess_health_needs(own_player, total_danger_value, moves)
        self.assertIn({"use": "big_potion"}, moves)
        self.assertNotIn({"use": "ring"}, moves)

    def test_no_health_needs(self):
        # Case: Player's health is sufficient, and no danger
        own_player = {
            "health": 70,
            "max_health": 100,
            "items": {"big_potions": []},
            "is_cloaked": False,
        }
        total_danger_value = 10
        moves = []

        assess_health_needs(own_player, total_danger_value, moves)
        self.assertNotIn({"use": "big_potion"}, moves)
        self.assertNotIn({"use": "ring"}, moves)


class TestAssessZapperUseFunction(unittest.TestCase):
    def test_use_zapper_on_player_in_range(self):
        # Case: Target is a player in range and not zapped
        own_player = {"position": {"x": 100, "y": 100}}
        target = {
            "type": "player",
            "position": {"x": 200, "y": 200},
            "is_zapped": False,
        }
        moves = []

        updated_moves = assess_zapper_use(own_player, target, moves)
        self.assertIn({"use": "speed_zapper"}, updated_moves)

    def test_use_zapper_on_tiny_in_range(self):
        # Case: Target is tiny in range and not zapped
        own_player = {"position": {"x": 100, "y": 100}}
        target = {"type": "tiny", "position": {"x": 150, "y": 150}, "is_zapped": False}
        moves = []

        updated_moves = assess_zapper_use(own_player, target, moves)
        self.assertIn({"use": "speed_zapper"}, updated_moves)

    def test_do_not_use_zapper_out_of_range(self):
        # Case: Target is out of zapper range
        own_player = {"position": {"x": 100, "y": 100}}
        target = {
            "type": "player",
            "position": {"x": 600, "y": 600},
            "is_zapped": False,
        }
        moves = []

        updated_moves = assess_zapper_use(own_player, target, moves)
        self.assertNotIn({"use": "speed_zapper"}, updated_moves)

    def test_do_not_use_zapper_on_zapped_target(self):
        # Case: Target is already zapped
        own_player = {"position": {"x": 100, "y": 100}}
        target = {"type": "player", "position": {"x": 200, "y": 200}, "is_zapped": True}
        moves = []

        updated_moves = assess_zapper_use(own_player, target, moves)
        self.assertNotIn({"use": "speed_zapper"}, updated_moves)

    def test_do_not_use_zapper_on_invalid_target_type(self):
        # Case: Target type is not player or tiny
        own_player = {"position": {"x": 100, "y": 100}}
        target = {
            "type": "monster",
            "position": {"x": 150, "y": 150},
            "is_zapped": False,
        }
        moves = []

        updated_moves = assess_zapper_use(own_player, target, moves)
        self.assertNotIn({"use": "speed_zapper"}, updated_moves)

    def test_append_to_existing_moves(self):
        # Case: Moves already have other actions, zapper use should append
        own_player = {"position": {"x": 100, "y": 100}}
        target = {"type": "tiny", "position": {"x": 150, "y": 150}, "is_zapped": False}
        moves = [{"use": "ring"}]

        updated_moves = assess_zapper_use(own_player, target, moves)
        self.assertIn({"use": "speed_zapper"}, updated_moves)
        self.assertIn({"use": "ring"}, updated_moves)


class TestHandleIcicleThreatFunction(unittest.TestCase):
    def test_handle_icicle_threat_in_range(self):
        # Case: Icicle hazard is within range and not owned by the player
        own_player = {"position": {"x": 100, "y": 100}, "id": 1}
        hazards = [{"type": "icicle", "position": {"x": 110, "y": 110}, "owner_id": 2}]
        moves = []

        updated_moves = handle_icicle_threat(own_player, hazards, moves)
        self.assertIn("shield", updated_moves)

    def test_no_icicle_threat_out_of_range(self):
        # Case: Icicle hazard is out of range
        own_player = {"position": {"x": 100, "y": 100}, "id": 1}
        hazards = [{"type": "icicle", "position": {"x": 400, "y": 400}, "owner_id": 2}]
        moves = []

        updated_moves = handle_icicle_threat(own_player, hazards, moves)
        self.assertNotIn("shield", updated_moves)

    def test_no_icicle_threat_same_owner(self):
        # Case: Icicle hazard is owned by the player
        own_player = {"position": {"x": 100, "y": 100}, "id": 1}
        hazards = [{"type": "icicle", "position": {"x": 110, "y": 110}, "owner_id": 1}]
        moves = []

        updated_moves = handle_icicle_threat(own_player, hazards, moves)
        self.assertNotIn("shield", updated_moves)

    def test_no_icicle_threat_wrong_type(self):
        # Case: Hazard is not an icicle
        own_player = {"position": {"x": 100, "y": 100}, "id": 1}
        hazards = [{"type": "bomb", "position": {"x": 110, "y": 110}, "owner_id": 2}]
        moves = []

        updated_moves = handle_icicle_threat(own_player, hazards, moves)
        self.assertNotIn("shield", updated_moves)

    def test_handle_multiple_hazards(self):
        # Case: Multiple hazards, one icicle in range
        own_player = {"position": {"x": 100, "y": 100}, "id": 1}
        hazards = [
            {"type": "bomb", "position": {"x": 150, "y": 150}, "owner_id": 2},
            {"type": "icicle", "position": {"x": 110, "y": 110}, "owner_id": 3},
            {"type": "icicle", "position": {"x": 300, "y": 300}, "owner_id": 2},
        ]
        moves = []

        updated_moves = handle_icicle_threat(own_player, hazards, moves)
        self.assertIn("shield", updated_moves)
        self.assertEqual(
            updated_moves.count("shield"), 1
        )  # Ensure only one shield move is added

    def test_append_to_existing_moves(self):
        # Case: Existing moves already contain actions
        own_player = {"position": {"x": 100, "y": 100}, "id": 1}
        hazards = [{"type": "icicle", "position": {"x": 110, "y": 110}, "owner_id": 2}]
        moves = ["dash"]

        updated_moves = handle_icicle_threat(own_player, hazards, moves)
        self.assertIn("shield", updated_moves)
        self.assertIn("dash", updated_moves)


class TestHandleCollisionsFunction(unittest.TestCase):
    def test_no_collisions(self):
        # Case: No collisions
        own_player = {"position": {"x": 10, "y": 10}, "collisions": []}
        target = {"position": {"x": 20, "y": 20}, "type": "npc"}
        moves = []

        updated_moves = handle_collisions(own_player, target, moves)

        self.assertEqual(updated_moves, [])
        self.assertEqual(target["position"], {"x": 20, "y": 20})

    def test_single_collision_with_attack(self):
        # Case: Single collision requiring an attack
        own_player = {
            "position": {"x": 10, "y": 10},
            "collisions": [{"type": "wolf", "relative_position": {"x": 1, "y": 1}}],
        }
        target = {"position": {"x": 20, "y": 20}, "type": "npc"}
        moves = []

        updated_moves = handle_collisions(own_player, target, moves)

        self.assertIn("attack", updated_moves)
        self.assertIn({"move_to": {"x": 7, "y": 7}}, updated_moves)
        self.assertEqual(target["position"], {"x": 7, "y": 7})

    def test_single_collision_no_attack(self):
        # Case: Single collision but no attack due to target type match
        own_player = {
            "position": {"x": 10, "y": 10},
            "collisions": [{"type": "rock", "relative_position": {"x": 1, "y": 1}}],
        }
        target = {"position": {"x": 20, "y": 20}, "type": "player"}
        moves = []

        updated_moves = handle_collisions(own_player, target, moves)

        self.assertNotIn("attack", updated_moves)
        self.assertIn({"move_to": {"x": 7, "y": 7}}, updated_moves)
        self.assertEqual(target["position"], {"x": 7, "y": 7})

    def test_multiple_collisions(self):
        # Case: Multiple collisions with cumulative position adjustments
        own_player = {
            "position": {"x": 10, "y": 10},
            "collisions": [
                {"type": "wolf", "relative_position": {"x": 1, "y": 1}},
                {"type": "ghoul", "relative_position": {"x": 2, "y": 2}},
            ],
        }
        target = {"position": {"x": 20, "y": 20}, "type": "npc"}
        moves = []

        updated_moves = handle_collisions(own_player, target, moves)

        self.assertIn("attack", updated_moves)
        self.assertIn({"move_to": {"x": 1, "y": 1}}, updated_moves)
        self.assertEqual(
            target["position"], {"x": 1, "y": 1}
        )  # Adjusted for both collisions

    def test_mixed_collision_types(self):
        # Case: Mixed valid and invalid collision types
        own_player = {
            "position": {"x": 10, "y": 10},
            "collisions": [
                {"type": "wolf", "relative_position": {"x": 1, "y": 1}},
                {"type": "rock", "relative_position": {"x": 2, "y": 2}},
            ],
        }
        target = {"position": {"x": 20, "y": 20}, "type": "npc"}
        moves = []

        updated_moves = handle_collisions(own_player, target, moves)

        self.assertIn("attack", updated_moves)  # Only for "wolf"
        self.assertIn({"move_to": {"x": 1, "y": 1}}, updated_moves)
        self.assertEqual(
            target["position"], {"x": 1, "y": 1}
        )  # Adjusted only for "wolf" collision


class TestAssessIcicleUseFunction(unittest.TestCase):
    def test_valid_target_in_range(self):
        # Case: Target is a valid type, not frozen, in range, and shield not raised
        own_player = {"position": {"x": 100, "y": 100}, "shield_raised": False}
        target = {"type": "ghoul", "position": {"x": 150, "y": 150}, "is_frozen": False}
        moves = []

        updated_moves = assess_icicle_use(own_player, target, moves)

        self.assertIn("special", updated_moves)

    def test_target_out_of_range(self):
        # Case: Target is out of range
        own_player = {"position": {"x": 100, "y": 100}, "shield_raised": False}
        target = {"type": "ghoul", "position": {"x": 600, "y": 600}, "is_frozen": False}
        moves = []

        updated_moves = assess_icicle_use(own_player, target, moves)

        self.assertNotIn("special", updated_moves)

    def test_target_already_frozen(self):
        # Case: Target is already frozen
        own_player = {"position": {"x": 100, "y": 100}, "shield_raised": False}
        target = {"type": "tiny", "position": {"x": 150, "y": 150}, "is_frozen": True}
        moves = []

        updated_moves = assess_icicle_use(own_player, target, moves)

        self.assertNotIn("special", updated_moves)

    def test_target_invalid_type(self):
        # Case: Target is not a valid type
        own_player = {"position": {"x": 100, "y": 100}, "shield_raised": False}
        target = {"type": "wolf", "position": {"x": 150, "y": 150}, "is_frozen": False}
        moves = []

        updated_moves = assess_icicle_use(own_player, target, moves)

        self.assertNotIn("special", updated_moves)

    def test_player_shield_raised(self):
        # Case: Player's shield is raised
        own_player = {"position": {"x": 100, "y": 100}, "shield_raised": True}
        target = {
            "type": "minotaur",
            "position": {"x": 150, "y": 150},
            "is_frozen": False,
        }
        moves = []

        updated_moves = assess_icicle_use(own_player, target, moves)

        self.assertNotIn("special", updated_moves)

    def test_valid_target_append_to_moves(self):
        # Case: Valid target and moves already contain other actions
        own_player = {"position": {"x": 100, "y": 100}, "shield_raised": False}
        target = {
            "type": "player",
            "position": {"x": 150, "y": 150},
            "is_frozen": False,
        }
        moves = ["attack"]

        updated_moves = assess_icicle_use(own_player, target, moves)

        self.assertIn("special", updated_moves)
        self.assertIn("attack", updated_moves)
