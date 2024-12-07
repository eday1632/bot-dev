import unittest
from main import peripheral_danger

class TestPeripheralDanger(unittest.TestCase):
    def setUp(self):
        """Set up common test data."""
        self.own_player = {
            "health": 100,
            "items": {"big_potions": [100, 100]}  # Adds 200 health
        }
        self.item = {"position": {"x": 50, "y": 50}}
        self.enemies = []
        self.players = []
        self.hazards = []

    def test_no_threats(self):
        """Test when there are no enemies, players, or hazards."""
        result = peripheral_danger(self.own_player, self.item, self.enemies, self.players, self.hazards)
        self.assertFalse(result, "No threats should result in no danger.")

    def test_low_danger_within_radius(self):
        """Test when danger in the radius is less than player health."""
        self.enemies = [{"position": {"x": 60, "y":60}, "attack_damage": 50}]
        result = peripheral_danger(self.own_player, self.item, self.enemies, self.players, self.hazards)
        self.assertFalse(result, "Danger less than player health is okay.")

    def test_enemy_outside_danger_radius(self):
        """Test when an enemy is outside the danger radius."""
        self.enemies = [{"position": {"x": 500, "y":50}, "attack_damage": 50}]
        result = peripheral_danger(self.own_player, self.item, self.enemies, self.players, self.hazards)
        self.assertFalse(result, "An enemy outside the radius should not result in danger.")

    def test_danger_on_the_edge(self):
        """Test with multiple enemies, players, and hazards contributing to danger."""
        self.enemies = [{"position": {"x": 60, "y":60}, "attack_damage": 50}]
        self.players = [{"position": {"x": 55, "y":55}, "attack_damage": 30}]
        self.hazards = [{"position": {"x": 52, "y":52}, "attack_damage": 20}]
        result = peripheral_danger(self.own_player, self.item, self.enemies, self.players, self.hazards)
        self.assertFalse(result, "Multiple threats can be below threshold.")

    def test_danger_exceeds_threshold(self):
        """Test with multiple enemies, players, and hazards contributing to danger."""
        self.enemies = [{"position": {"x": 60, "y":60}, "attack_damage": 150}]
        self.players = [{"position": {"x": 55, "y":55}, "attack_damage": 90}]
        self.hazards = [{"position": {"x": 52, "y":52}, "attack_damage": 80}]
        result = peripheral_danger(self.own_player, self.item, self.enemies, self.players, self.hazards)
        self.assertTrue(result, "Multiple threats can exceed danger threshold.")

    def test_edge_case_radius(self):
        """Test when a threat is at the exact edge of the danger radius."""
        self.hazards = [{"position": {"x": 50 + int(60000 ** 0.5), "y": 50}, "attack_damage": 50}]
        result = peripheral_danger(self.own_player, self.item, self.enemies, self.players, self.hazards)
        self.assertFalse(result, "Threats at the edge of the radius should not count as danger.")

if __name__ == "__main__":
    unittest.main()
