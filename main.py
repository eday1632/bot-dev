from fastapi import FastAPI
from pydantic import BaseModel
import random
import datetime
import pandas as pd
import numpy as np

DEAD = False
POTIONS = 0
RINGS = 0
ZAPPERS = 0


# death tax: odds of dying x the cost of losing that time: odds * (xp/s * 5)
# subtract this death tax from the projected exp of entering an area
# how to calculate odds of dying? --> my bot-death logs
# is this essentially avoidance?
# logarithmic dropoff to the directions adjacent to the highest value?


def dist_squared_to(a: dict, b: dict) -> float:
    return (a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2


def slope(a: dict, b: dict) -> float:
    return (int(b["y"]) - a["y"]) / (int(b["x"]) - a["x"])


def calculate_potion_value(own_player):
    potion_values = {
        0: 1548,
        1: 524,
        2: 212,
        3: 126,
        4: 108,
        5: 64,
        6: 32,
    }
    if own_player["special_equipped"] == "bomb":
        for val in potion_values:
            potion_values[val] *= 2
    on_hand = len(own_player["items"]["big_potions"])
    return potion_values[on_hand]


def calculate_ring_value(own_player):
    ring_values = {
        0: 125,
        1: 100,
        2: 70,
        3: 16,
        4: 12,
        5: 12,
    }
    on_hand = len(own_player["items"]["rings"])
    return ring_values[on_hand]


def calculate_zapper_value(own_player):
    zapper_values = {
        0: 90,
        1: 12,
        2: 12,
        3: 12,
        4: 12,
        5: 12,
    }
    on_hand = len(own_player["items"]["speed_zappers"])
    return zapper_values[on_hand]


def peripheral_danger(
    own_player: dict, item: dict, enemies: list, players: list, hazards: list
) -> bool:
    total_health = (
        own_player["health"]
        + len(own_player["items"]["big_potions"]) * own_player["max_health"]
    )
    total_danger = 0

    for enemy in enemies:
        if dist_squared_to(item["position"], enemy["position"]) < 80000:
            total_danger += enemy["attack_damage"]

    for player in players:
        if dist_squared_to(item["position"], player["position"]) < 80000:
            total_danger += player["attack_damage"]

    for hazard in hazards:
        if dist_squared_to(item["position"], hazard["position"]) < 60000:
            total_danger += hazard["attack_damage"]

    return total_danger > total_health


def apply_skill_points(own_player: dict, moves: list) -> list:
    max_points = 20

    if own_player["levelling"]["available_skill_points"] > 0:
        if own_player["levelling"]["attack"] > own_player["levelling"]["speed"]:
            moves.append({"redeem_skill_point": "speed"})
        elif own_player["levelling"]["speed"] > own_player["levelling"]["health"]:
            moves.append({"redeem_skill_point": "health"})
        else:
            moves.append({"redeem_skill_point": "attack"})

        if own_player["levelling"]["speed"] < max_points:
            moves.append({"redeem_skill_point": "speed"})
        if own_player["levelling"]["health"] < max_points:
            moves.append({"redeem_skill_point": "health"})
        if own_player["levelling"]["attack"] < max_points:
            moves.append({"redeem_skill_point": "attack"})

    return moves


def losing_battle(own_player: dict, item: dict) -> bool:
    if (
        item.get("attack_damage") is not None
        and item["attack_damage"] * 1.2 > own_player["health"]
    ):
        return True
    return False


def bomb_nearby(item: dict, hazards: list) -> dict:
    for hazard in hazards:
        if (
            hazard["type"] == "bomb"
            and dist_squared_to(item["position"], hazard["position"]) < 80000
        ):
            return hazard
    return {}


def total_danger(players: list, enemies: list, hazards: list) -> int:
    total_danger = 0

    for player in players:
        if player["distance"] < 30000 and not player["is_frozen"]:
            total_danger += player["attack_damage"]

    for enemy in enemies:
        if enemy["distance"] < 30000 and not enemy["is_frozen"]:
            total_danger += enemy["attack_damage"]

    for hazard in hazards:
        if hazard["distance"] < 60000:
            total_danger += hazard["attack_damage"]

    return total_danger


def get_best_item(
    own_player: dict, items: list, hazards: list, enemies: list, players: list
) -> dict:
    max_xp = float("-inf")
    target = {}

    for item in items:
        if item["type"] == "tiny" and item["distance"] < 17500:
            return item

        # # Skip items based on various conditions
        # if losing_battle(own_player, item):
        #     continue
        # if peripheral_danger(own_player, item, enemies, players, hazards):
        #     continue

        # Additional checks for items with "attack_damage"
        if item.get("attack_damage") is not None:
            for hazard in hazards:
                if (
                    hazard["attack_damage"] > item["health"]
                    and dist_squared_to(hazard["position"], item["position"]) < 50000
                ):
                    continue

        # Calculate experience rate and update the target if this is the best option
        exponent = 0.7
        my_speed = 15000**exponent + own_player["levelling"]["speed"] * 500**exponent
        total_xp = item["xp"]
        total_effort = 0
        if item["type"] == "player":
            item["health"] += 200  # Assume players have an average of 2 potions
        if item.get("health") is not None:
            total_effort += (
                item["health"] / own_player["attack_damage"]
            ) * 0.5  # Assuming attack cooldown
        total_effort += (item["distance"] ** exponent) / my_speed

        for other_item in items:
            distance = dist_squared_to(item["position"], other_item["position"])
            if 0 < distance < 50000:
                total_xp += other_item["xp"]
                # Calculate total effort: kill time + travel time
                if other_item["type"] == "player":
                    other_item[
                        "health"
                    ] += 200  # Assume players have an average of 2 potions
                if (
                    other_item.get("health") is not None
                ):  # Check if the other_item has a health attribute
                    total_effort += (
                        other_item["health"] / own_player["attack_damage"]
                    ) * 0.5  # Assuming attack cooldown
                total_effort += (distance**exponent) / my_speed

        potential_xp = total_xp / total_effort
        if potential_xp > max_xp:
            max_xp = potential_xp
            target = item
            target["xp"] = int(potential_xp)

    return target


def assess_attack(own_player, target, moves):
    if target.get("health") is not None and target["distance"] < 16625:
        moves.append("attack")
    if (
        target.get("attack_damage") is not None
        and target["distance"] < 90000
        and target["distance"] > 50000
        and target["is_frozen"]
    ):
        moves.append("dash")
    elif (
        target.get("attack_damage") is not None
        and target["distance"] < 90000
        and target.get("health") < own_player["attack_damage"]
    ):
        moves.append("dash")
        moves.append("shield")

    if len(own_player["collisions"]) > 0:
        for collision in own_player["collisions"]:
            if collision["type"] in [
                "wolf",
                "ghoul",
                "tiny",
                "minotaur",
                "player",
            ]:
                moves.append("attack")
                moves.append("shield")

    return moves


def assess_health_needs(own_player, total_danger_value, moves):
    # Handle health and potion usage
    if total_danger_value >= own_player["health"] * 1.2:
        moves.append({"use": "big_potion"})
        if not own_player["is_cloaked"]:
            moves.append({"use": "ring"})
    elif own_player["health"] / own_player["max_health"] < 0.4:
        moves.append("shield")
        moves.append({"use": "big_potion"})
        moves.append("dash")
        if not own_player["is_cloaked"]:
            moves.append({"use": "ring"})
    elif (
        own_player["health"] / own_player["max_health"] < 0.6
        and len(own_player["items"]["big_potions"]) > 4
    ):
        moves.append({"use": "big_potion"})
    elif (
        own_player["health"] / own_player["max_health"] < 0.8
        and len(own_player["items"]["big_potions"]) == 6
    ):
        moves.append({"use": "big_potion"})
    return moves


def assess_zapper_use(target, moves):
    if (
        target["type"] in ["player", "tiny"]
        and target["distance"] < 200000
        and not target["is_zapped"]
    ):
        moves.append({"use": "speed_zapper"})
    return moves


def handle_bomb_threat(own_player, target, bomb, moves):
    if bomb:
        space = 100
        moves.append("shield")
        target["position"]["x"] = (
            own_player["position"]["x"] - space
            if bomb["position"]["x"] >= own_player["position"]["x"]
            else own_player["position"]["x"] + space
        )
        target["position"]["y"] = (
            own_player["position"]["y"] - space
            if bomb["position"]["y"] >= own_player["position"]["y"]
            else own_player["position"]["y"] + space
        )
        moves.append("dash")
    return moves, target


def handle_icicle_threat(own_player, hazards, moves):
    for hazard in hazards:
        if (
            hazard["type"] == "icicle"
            and hazard["distance"] < 40000
            and own_player["id"] != hazard["owner_id"]
        ):
            moves.append("shield")
    return moves


def retreat(own_player, target, threats):
    retreat = 200
    for threat in threats:
        threat_slope = slope(own_player["position"], threat["position"])
        threat_inverse = 1 / threat_slope
        if (
            threat["position"]["x"] > own_player["position"]["x"]
            and threat["position"]["y"] > own_player["position"]["y"]
        ):
            target["position"]["x"] = (
                own_player["position"]["x"] - retreat * threat_inverse
            )
            target["position"]["y"] = (
                own_player["position"]["y"] - retreat * threat_slope
            )
        elif (
            threat["position"]["x"] < own_player["position"]["x"]
            and threat["position"]["y"] < own_player["position"]["y"]
        ):
            target["position"]["x"] = (
                own_player["position"]["x"] + retreat * threat_inverse
            )
            target["position"]["y"] = (
                own_player["position"]["y"] + retreat * threat_slope
            )
        elif (
            threat["position"]["x"] > own_player["position"]["x"]
            and threat["position"]["y"] < own_player["position"]["y"]
        ):
            target["position"]["x"] = (
                own_player["position"]["x"] - retreat * threat_inverse
            )
            target["position"]["y"] = (
                own_player["position"]["y"] + retreat * threat_slope
            )
        elif (
            threat["position"]["x"] < own_player["position"]["x"]
            and threat["position"]["y"] > own_player["position"]["y"]
        ):
            target["position"]["x"] = (
                own_player["position"]["x"] + retreat * threat_inverse
            )
            target["position"]["y"] = (
                own_player["position"]["y"] - retreat * threat_slope
            )
    return target


def avoid_collisions(own_player, target, threats):
    nearby_threats = []
    for threat in threats:
        if threat["distance"] < 70000:
            nearby_threats.append(threat)

    for threat in nearby_threats:
        if threat["id"] != target["id"] and threat["type"] != target["type"]:
            buffer = 200
            threat_slope = slope(own_player["position"], threat["position"])
            target_slope = slope(own_player["position"], target["position"])
            threat_inverse = 1 / (threat_slope or 1)
            if (
                target["position"]["x"] > threat["position"]["x"]
                and threat["position"]["x"] > own_player["position"]["x"]
            ):
                if (
                    target["position"]["y"] > threat["position"]["y"]
                    and threat["position"]["y"] > own_player["position"]["y"]
                ):
                    if threat_slope > target_slope:
                        target["position"]["x"] = (
                            own_player["position"]["x"] + buffer * threat_inverse
                        )
                        target["position"]["y"] = (
                            own_player["position"]["y"] - buffer * threat_slope
                        )
                    else:
                        target["position"]["x"] = (
                            own_player["position"]["x"] - buffer * threat_inverse
                        )
                        target["position"]["y"] = (
                            own_player["position"]["y"] + buffer * threat_slope
                        )
                elif (
                    target["position"]["y"] < threat["position"]["y"]
                    and threat["position"]["y"] < own_player["position"]["y"]
                ):
                    if threat_slope > target_slope:
                        target["position"]["x"] = (
                            own_player["position"]["x"] - buffer * threat_inverse
                        )
                        target["position"]["y"] = (
                            own_player["position"]["y"] - buffer * threat_slope
                        )
                    else:
                        target["position"]["x"] = (
                            own_player["position"]["x"] + buffer * threat_inverse
                        )
                        target["position"]["y"] = (
                            own_player["position"]["y"] + buffer * threat_slope
                        )
            elif (
                target["position"]["x"] < threat["position"]["x"]
                and threat["position"]["x"] < own_player["position"]["x"]
            ):
                if (
                    target["position"]["y"] > threat["position"]["y"]
                    and threat["position"]["y"] > own_player["position"]["y"]
                ):
                    if threat_slope > target_slope:
                        target["position"]["x"] = (
                            own_player["position"]["x"] + buffer * threat_inverse
                        )
                        target["position"]["y"] = (
                            own_player["position"]["y"] + buffer * threat_slope
                        )
                    else:
                        target["position"]["x"] = (
                            own_player["position"]["x"] - buffer * threat_inverse
                        )
                        target["position"]["y"] = (
                            own_player["position"]["y"] - buffer * threat_slope
                        )
                elif (
                    target["position"]["y"] < threat["position"]["y"]
                    and threat["position"]["y"] < own_player["position"]["y"]
                ):
                    if threat_slope > target_slope:
                        target["position"]["x"] = (
                            own_player["position"]["x"] - buffer * threat_inverse
                        )
                        target["position"]["y"] = (
                            own_player["position"]["y"] + buffer * threat_slope
                        )
                    else:
                        target["position"]["x"] = (
                            own_player["position"]["x"] + buffer * threat_inverse
                        )
                        target["position"]["y"] = (
                            own_player["position"]["y"] - buffer * threat_slope
                        )

    if len(own_player["collisions"]) > 0:
        for collision in own_player["collisions"]:
            if collision["type"] not in [
                "wolf",
                "ghoul",
                "tiny",
                "minotaur",
                "player",
                "chest",
            ]:
                target["position"]["x"] = own_player["position"]["x"] + random.randint(
                    -400, 400
                )
                target["position"]["y"] = own_player["position"]["y"] + random.randint(
                    -400, 400
                )
                break

    return target


def assess_bomb_use(own_player, target, enemies, moves):
    bomb_distance = 130000
    for enemy in enemies:
        # and enemy["direction"] == own_player["direction"] ???
        if (
            target["position"]["x"] > own_player["position"]["x"]
            and own_player["position"]["x"] > enemy["position"]["x"]
            and target["position"]["y"] > own_player["position"]["y"]
            and own_player["position"]["y"] > enemy["position"]["y"]
            and 50000 < enemy["distance"] < bomb_distance
            and target["id"] != enemy["id"]
        ):
            moves.append("special")
        elif (
            target["position"]["x"] < own_player["position"]["x"]
            and own_player["position"]["x"] < enemy["position"]["x"]
            and target["position"]["y"] < own_player["position"]["y"]
            and own_player["position"]["y"] < enemy["position"]["y"]
            and 50000 < enemy["distance"] < bomb_distance
            and target["id"] != enemy["id"]
        ):
            moves.append("special")
        elif (
            target["position"]["x"] < own_player["position"]["x"]
            and own_player["position"]["x"] < enemy["position"]["x"]
            and target["position"]["y"] > own_player["position"]["y"]
            and own_player["position"]["y"] > enemy["position"]["y"]
            and 50000 < enemy["distance"] < bomb_distance
            and target["id"] != enemy["id"]
        ):
            moves.append("special")
        elif (
            target["position"]["x"] > own_player["position"]["x"]
            and own_player["position"]["x"] > enemy["position"]["x"]
            and target["position"]["y"] < own_player["position"]["y"]
            and own_player["position"]["y"] < enemy["position"]["y"]
            and 50000 < enemy["distance"] < bomb_distance
            and target["id"] != enemy["id"]
        ):
            moves.append("special")
        elif (
            enemy["distance"] < 50000
            and own_player["health"] > own_player["attack_damage"] * 2.5
            and target["id"] == enemy["id"]
            and target["health"] > own_player["attack_damage"]
        ):
            moves.append("special")
    return moves


def assess_icicle_use(own_player, target, moves):
    if (
        target["type"] in ["wolf", "ghoul", "tiny", "minotaur", "player"]
        and not target["is_frozen"]
        and target["distance"] < 220000
    ):
        moves.append("special")

    if len(own_player["collisions"]) > 0:
        for collision in own_player["collisions"]:
            if collision["type"] in [
                "wolf",
                "ghoul",
                "tiny",
                "minotaur",
                "player",
            ]:
                moves.append("special")

    return moves


def filter_threats(own_player, threats):
    existing_threats = []
    for threat in threats:
        if threat.get("health") and threat["health"] > 0:
            existing_threats.append(threat)
        elif threat.get("status") and threat["status"] != "idle":
            if threat["type"] == "icicle" and threat["owner_id"] == own_player["id"]:
                continue
            existing_threats.append(threat)
    return existing_threats


def generate_distance(own_player, items):
    items_of_interest = []
    for item in items:
        distance = dist_squared_to(own_player["position"], item["position"])
        if distance < 6000000:
            item["distance"] = distance
            items_of_interest.append(item)
    return items_of_interest


def apply_metadata(own_player, items):
    potion_value = calculate_potion_value(own_player)
    ring_value = calculate_ring_value(own_player)
    zapper_value = calculate_zapper_value(own_player)

    # Experience values for different item types
    exps = {
        "minotaur": 600,
        "tiny": 400,
        "ghoul": 100,
        "wolf": 80,
        "player": 0,
        "coin": 250,
        "big_potion": potion_value,
        "speed_zapper": zapper_value,
        "ring": ring_value,
        "chest": 0,
        "power_up": 0,
    }
    for item in items:

        # Adjust experience for player level
        level_vals = {
            1: 82,
            2: 95,
            3: 109,
            4: 126,
            5: 144,
            6: 166,
            7: 191,
            8: 220,
            9: 253,
            10: 291,
            11: 335,
            12: 386,
            13: 444,
            14: 511,
            15: 587,
            16: 676,
            17: 777,
            18: 894,
            19: 1029,
            20: 1184,
        }
        if item["type"] == "player":
            exps["player"] = level_vals[item["levelling"]["level"]]
            if item["special_equipped"] == "freeze":
                exps["player"] = exps["player"] * 0.75

        # Special cases for chest and power-up
        if item["type"] in ["chest", "power_up"] and own_player[
            "special_equipped"
        ] not in [
            "bomb",
            "freeze",
        ]:
            exps["chest"] = 1500
            exps["power_up"] = 1500

        # Special case for tinys
        if (
            item["type"] == "tiny"
            and len(own_player["items"]["speed_zappers"]) == 0
            and not item["is_zapped"]
            and not item["is_frozen"]
        ):
            exps["tiny"] = 50

        item["xp"] = exps[item["type"]]


def cb_steering(level_data):

    moves = []
    own_player = level_data.own_player
    threats = []
    enemies = filter_threats(level_data.enemies)
    enemies = generate_distance(own_player, enemies)
    apply_metadata(own_player, enemies)
    threats.extend(enemies)

    hazards = filter_threats(level_data.hazards)
    hazards = generate_distance(own_player, hazards)
    threats.extend(hazards)

    players = filter_threats(level_data.players)
    players = generate_distance(own_player, players)
    apply_metadata(own_player, players)
    threats.extend(players)

    items = level_data.items
    items = generate_distance(own_player, items)
    apply_metadata(own_player, items)

    obstacles = []
    for obstacle in level_data.obstacles:
        obstacles.append({"position": {"x": obstacle["x"], "y": obstacle["y"]}})
    obstacles = generate_distance(own_player, obstacles)

    max_xp = float("-inf")
    target = items[0]

    for item in items:
        # Calculate experience rate and update the target if this is the best option
        exponent = 0.6
        my_speed = 15000**exponent + own_player["levelling"]["speed"] * 500**exponent
        total_xp = item["xp"]
        total_effort = 0
        if item["type"] == "player":
            item["health"] += 200  # Assume players have an average of 2 potions
        if item.get("health") is not None:
            total_effort += (
                item["health"] / own_player["attack_damage"]
            ) * 0.5  # Assuming attack cooldown
        total_effort += (item["distance"] ** exponent) / my_speed

        for other_item in items:
            distance = dist_squared_to(item["position"], other_item["position"])
            if 0 < distance < 70000:
                total_xp += other_item["xp"]
                # Calculate total effort: kill time + travel time
                if other_item["type"] == "player":
                    other_item[
                        "health"
                    ] += 200  # Assume players have an average of 2 potions
                if (
                    other_item.get("health") is not None
                ):  # Check if the other_item has a health attribute
                    total_effort += (
                        other_item["health"] / own_player["attack_damage"]
                    ) * 0.5  # Assuming attack cooldown
                total_effort += (distance**exponent) / my_speed

        potential_xp = total_xp / total_effort
        if potential_xp > max_xp:
            max_xp = potential_xp
            target = item
            target["xp"] = int(potential_xp)

    position = [own_player["position"]["x"], own_player["position"]["y"]]
    velocity = [0, 0]
    max_speed = 100000
    max_force = 200000
    radii = {
        "minotaur": 300,
        "tiny": 100,
        "ghoul": 200,
        "wolf": 100,
        "player": 250,
        "bomb": 400,
        "obstacle": 10,
        "icicle": 200,
    }

    agent = Agent(position, velocity, max_speed, max_force)

    target_pos = [target["position"]["x"], target["position"]["y"]]
    steering_force = agent.seek(target_pos)
    for enemy in threats:
        if enemy["distance"] < 30000 and enemy["id"] != target["id"]:
            enemy_pos = [enemy["position"]["x"], enemy["position"]["y"]]
            steering_force += agent.avoid_obstacle(enemy_pos, radii[enemy["type"]])
    for obstacle in obstacles:
        if obstacle["distance"] < 10000:
            obstacle_pos = [obstacle["position"]["x"], obstacle["position"]["y"]]
            steering_force += agent.avoid_obstacle(obstacle_pos, radii["obstacle"])

        # Apply and update
    agent.apply_force(steering_force)
    agent.update()
    own_player["position"]["x"] = agent.position[0]
    own_player["position"]["y"] = agent.position[1]
    moves.append({"move_to": own_player["position"]})
    return moves


class Agent:
    def __init__(self, position, velocity, max_speed, max_force):
        self.position = np.array(position, dtype=float)
        self.velocity = np.array(velocity, dtype=float)
        self.acceleration = np.zeros(2)
        self.max_speed = max_speed
        self.max_force = max_force

    def apply_force(self, force):
        self.acceleration += force

    def seek(self, target):
        desired = np.array(target) - self.position
        desired = self._set_magnitude(desired, self.max_speed)
        steer = desired - self.velocity
        steer = self._limit(steer, self.max_force)
        return steer

    def avoid_obstacle(self, obstacle, avoid_radius):
        to_obstacle = np.array(obstacle) - self.position
        distance = np.linalg.norm(to_obstacle)
        if distance < avoid_radius:
            # Calculate a repulsive force
            repulsion = -to_obstacle / distance
            repulsion = self._set_magnitude(repulsion, self.max_force)
            return repulsion
        return np.zeros(2)

    def update(self):
        self.velocity += self.acceleration
        self.velocity = self._limit(self.velocity, self.max_speed)
        self.position += self.velocity
        self.acceleration = np.zeros(2)

    def _set_magnitude(self, vector, magnitude):
        return vector / np.linalg.norm(vector) * magnitude

    def _limit(self, vector, max_value):
        magnitude = np.linalg.norm(vector)
        if magnitude > max_value:
            vector = vector / magnitude * max_value
        return vector


class LevelData(BaseModel):
    enemies: list
    players: list
    hazards: list
    items: list
    game_info: dict
    own_player: dict
    obstacles: list


def play(level_data: LevelData):
    moves = []
    own_player = level_data.own_player
    threats = []
    global DEAD
    if own_player["health"] <= 0 and not DEAD:
        timestamp = datetime.datetime.now()
        DEAD = True
        with open("/tmp/enemies.log", "a") as f:
            df = pd.json_normalize(level_data.enemies)
            df["timestamp"] = timestamp
            f.write(df.to_csv(index=False))
        with open("/tmp/items.log", "a") as f:
            df = pd.json_normalize(level_data.items)
            df["timestamp"] = timestamp
            f.write(df.to_csv(index=False))
        with open("/tmp/own_player.log", "a") as f:
            df = pd.json_normalize(level_data.own_player)
            df["timestamp"] = timestamp
            f.write(df.to_csv(index=False))
        with open("/tmp/hazards.log", "a") as f:
            df = pd.json_normalize(level_data.hazards)
            df["timestamp"] = timestamp
            f.write(df.to_csv(index=False))
        with open("/tmp/game_info.log", "a") as f:
            df = pd.json_normalize(level_data.game_info)
            df["timestamp"] = timestamp
            f.write(df.to_csv(index=False))

    elif own_player["health"] > 0:
        DEAD = False

    enemies = filter_threats(own_player, level_data.enemies)
    enemies = generate_distance(own_player, enemies)
    apply_metadata(own_player, enemies)
    threats.extend(enemies)

    hazards = filter_threats(own_player, level_data.hazards)
    hazards = generate_distance(own_player, hazards)
    threats.extend(hazards)

    players = filter_threats(own_player, level_data.players)
    players = generate_distance(own_player, players)
    apply_metadata(own_player, players)
    threats.extend(players)

    items = level_data.items
    items = generate_distance(own_player, items)
    apply_metadata(own_player, items)

    obstacles = []
    for obstacle in level_data.obstacles:
        obstacles.append({"position": {"x": obstacle["x"], "y": obstacle["y"]}})
    obstacles = generate_distance(own_player, obstacles)

    potential_targets = []
    potential_targets.extend(items)
    potential_targets.extend(enemies)
    potential_targets.extend(players)

    moves = apply_skill_points(own_player, moves)

    target = get_best_item(own_player, potential_targets, hazards, enemies, players)
    if not target:
        print("No target found")
        return moves

    message = f'{target["type"]}: {target["xp"]}'
    moves.append({"speak": message})

    total_danger_value = total_danger(players, enemies, hazards)
    moves = assess_health_needs(own_player, total_danger_value, moves)
    moves = assess_attack(own_player, target, moves)
    moves = assess_zapper_use(target, moves)

    bomb = bomb_nearby(own_player, hazards)
    # Handle special equipped logic
    if own_player["special_equipped"] == "bomb":
        # Check for enemies
        moves = assess_bomb_use(own_player, target, enemies, moves)
        # Check for players
        moves = assess_bomb_use(own_player, target, players, moves)
    elif own_player["special_equipped"] == "freeze":
        moves = assess_icicle_use(own_player, target, moves)
    elif own_player["special_equipped"] == "shockwave":
        if bomb:
            moves.append("special")
        elif peripheral_danger(own_player, own_player, enemies, players, hazards):
            moves.append("shield")
            moves.append("special")

    moves = handle_icicle_threat(own_player, hazards, moves)
    moves, target = handle_bomb_threat(own_player, target, bomb, moves)
    target = avoid_collisions(own_player, target, threats)

    # Final move to the target
    if target.get("health"):
        position = [own_player["position"]["x"], own_player["position"]["y"]]
        velocity = [0, 0]
        max_speed = 1000
        max_force = 2000
        radii = {
            "minotaur": 300,
            "tiny": 100,
            "ghoul": 200,
            "wolf": 100,
            "player": 250,
            "bomb": 400,
            "obstacle": 100,
            "icicle": 200,
        }

        agent = Agent(position, velocity, max_speed, max_force)

        target_pos = [target["position"]["x"], target["position"]["y"]]
        steering_force = agent.seek(target_pos)
        min_distance = float("inf")
        min_threat = {}
        for threat in threats:
            if threat["distance"] < min_distance:
                min_threat = threat

        if (
            min_threat
            and min_threat["id"] != target["id"]
            and min_threat["distance"] < 40000
        ):
            threat_pos = [threat["position"]["x"], threat["position"]["y"]]
            steering_force += agent.avoid_obstacle(threat_pos, radii[threat["type"]])

        min_distance = float("inf")
        min_obs = {}
        for obstacle in obstacles:
            if obstacle["distance"] < min_distance:
                min_obs = obstacle

        if min_obs["distance"] < 20000:
            obs_pos = [min_obs["position"]["x"], min_obs["position"]["y"]]
            steering_force += agent.avoid_obstacle(obs_pos, radii["obstacle"])

            # Apply and update
        agent.apply_force(steering_force)
        agent.update()
        own_player["position"]["x"] = agent.position[0]
        own_player["position"]["y"] = agent.position[1]
        moves.append({"move_to": own_player["position"]})
    elif len(own_player["items"]["big_potions"]) == 0 or bomb:
        min_distance = float("inf")
        min_threat = {}
        for threat in threats:
            if threat["distance"] < min_distance:
                min_threat = threat
        if (
            min_threat
            and min_threat["id"] != target["id"]
            and min_threat["distance"] < 40000
        ):
            target = retreat(own_player, target, threats)
        moves.append({"move_to": target["position"]})
    else:
        moves.append({"move_to": target["position"]})

    return moves


app = FastAPI()


@app.post("/")
async def receive_level_data(level_data: LevelData):
    moves = play(level_data)
    return moves


@app.post("/steering")
async def steering(level_data: LevelData):
    moves = cb_steering(level_data)
    return moves


@app.get("/enemies")
async def get():
    with open("/tmp/enemies.log") as fp:
        return fp.readlines()


@app.get("/own-player")
async def get():
    with open("/tmp/own_player.log") as fp:
        return fp.read()


@app.get("/items")
async def get():
    with open("/tmp/items.log") as fp:
        return fp.read()


@app.get("/hazards")
async def get():
    with open("/tmp/hazards.log") as fp:
        return fp.read()


@app.get("/game-info")
async def get():
    with open("/tmp/game_info.log") as fp:
        return fp.read()
