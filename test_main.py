import unittest
from unittest.mock import patch

from main import (
    peripheral_danger,
    dist_squared_to,
    apply_skill_points,
    losing_battle,
    stock_full,
    dedupe_moves,
    bomb_nearby,
    print_exp_rate,
    assess_attack
)

# Mock global variable
CURRENT_EXP_RATE = None


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
        own_player = {"health": 100}
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

    def test_bomb_is_idle(self):
        # Case where bomb is nearby but idle
        item = {"position": {"x": 100, "y": 100}}
        hazards = [{"type": "bomb", "position": {"x": 110, "y": 110}, "status": "idle"}]
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


def set_current_exp_rate(value):
    global CURRENT_EXP_RATE
    CURRENT_EXP_RATE = value


class TestPrintExpRateFunction(unittest.TestCase):
    def setUp(self):
        # Reset the global variable before each test
        set_current_exp_rate(None)

    def test_print_on_change(self):
        # Test that the function prints when the exp rate changes
        game_info = {"time_remaining_s": 5}
        own_player = {"score": 100}

        with patch("builtins.print") as mock_print:
            print_exp_rate(game_info, own_player)
            mock_print.assert_called_once_with("Score rate: 0.06")

    def test_no_print_no_change(self):
        # Test that the function does not print if exp rate hasn't changed
        game_info = {"time_remaining_s": 10}
        own_player = {"score": 100}
        set_current_exp_rate(0.06)

        with patch("builtins.print") as mock_print:
            print_exp_rate(game_info, own_player)
            mock_print.assert_not_called()

    def test_no_print_not_multiple_of_5(self):
        # Test that the function does not print when time is not a multiple of 5
        game_info = {"time_remaining_s": 6}
        own_player = {"score": 100}

        with patch("builtins.print") as mock_print:
            print_exp_rate(game_info, own_player)
            mock_print.assert_not_called()

    def test_zero_division_handling(self):
        # Test division by zero is handled (edge case)
        game_info = {"time_remaining_s": 1800}
        own_player = {"score": 100}

        with patch("builtins.print") as mock_print:
            with self.assertRaises(ZeroDivisionError):
                print_exp_rate(game_info, own_player)

    def tearDown(self):
        # Reset the global variable after each test
        set_current_exp_rate(None)


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

    def test_target_no_health(self):
        # Case where the target has no health
        own_player = {"position": {"x": 10, "y": 10}}
        target = {"position": {"x": 15, "y": 15}, "health": 0}
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

    def test_target_health_negative(self):
        # Case where the target has negative health
        own_player = {"position": {"x": 10, "y": 10}}
        target = {"position": {"x": 15, "y": 15}, "health": -10}
        moves = []

        updated_moves = assess_attack(own_player, target, moves)
        self.assertEqual(updated_moves, [])


if __name__ == "__main__":
    unittest.main()
