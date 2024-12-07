import unittest
from main import peripheral_danger, dist_squared_to, apply_skill_points


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


if __name__ == "__main__":
    unittest.main()
