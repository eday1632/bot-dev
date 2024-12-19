from fastapi import FastAPI
from pydantic import BaseModel
import random
import datetime
import pandas as pd

DEAD = False
POTIONS = 0
RINGS = 0
ZAPPERS = 0


def dist_squared_to(a: dict, b: dict) -> float:
    return (a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2


def slope(a: dict, b: dict) -> float:
    return (int(b["y"]) - a["y"]) / (int(b["x"]) - a["x"])


def calculate_potion_value(own_player):
    potion_values = {
        0: 1024,
        1: 350,
        2: 150,
        3: 100,
        4: 50,
        5: 25,
        6: 12,
    }
    on_hand = len(own_player["items"]["big_potions"])
    return potion_values[on_hand]


def calculate_ring_value(own_player):
    ring_values = {
        0: 85,
        1: 50,
        2: 35,
        3: 16,
        4: 12,
        5: 12,
    }
    on_hand = len(own_player["items"]["rings"])
    return ring_values[on_hand]


def calculate_zapper_value(own_player):
    zapper_values = {
        0: 85,
        1: 50,
        2: 35,
        3: 12,
        4: 12,
        5: 12,
    }
    on_hand = len(own_player["items"]["speed_zappers"])
    return zapper_values[on_hand]


def peripheral_danger(
    own_player: dict, item: dict, enemies: list, players: list, hazards: list
) -> bool:
    total_health = own_player["health"] + len(own_player["items"]["big_potions"]) * 100
    total_danger = 0

    for enemy in enemies:
        if dist_squared_to(item["position"], enemy["position"]) < 100000:  # 316
            total_danger += enemy["attack_damage"]

    for player in players:
        if dist_squared_to(item["position"], player["position"]) < 100000:  # 316
            total_danger += player["attack_damage"]

    for hazard in hazards:
        if dist_squared_to(item["position"], hazard["position"]) < 60000:  # 245
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
        and item["attack_damage"] * 1.2 >= own_player["health"]
    ):
        return True
    return False


def bomb_nearby(item: dict, hazards: list) -> dict:
    for hazard in hazards:
        if (
            hazard["type"] == "bomb"
            and dist_squared_to(item["position"], hazard["position"]) < 50000
        ):
            return hazard
    return {}


def total_danger(players: list, enemies: list, hazards: list) -> int:
    total_danger = 0

    for player in players:
        if player["distance"] < 100000 and not player["is_frozen"]:
            total_danger += player["attack_damage"]

    for enemy in enemies:
        if enemy["distance"] < 100000 and not enemy["is_frozen"]:
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

        # Skip items based on various conditions
        if losing_battle(own_player, item):
            continue
        if peripheral_danger(own_player, item, enemies, players, hazards):
            continue

        # Additional checks for items with "attack_damage"
        if item.get("attack_damage") is not None:
            for hazard in hazards:
                if (
                    hazard["attack_damage"] > item["health"]
                    and dist_squared_to(hazard["position"], item["position"]) < 50000
                ):
                    continue

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

    if len(own_player["collisions"]) > 0:
        for collision in own_player["collisions"]:
            if collision["type"] in [
                "wolf",
                "ghoul",
                "tiny",
                "minotaur",
                "player",
                "chest",
            ]:
                moves.append("attack")

    return moves


def assess_health_needs(own_player, total_danger_value, moves):
    # Handle health and potion usage
    if total_danger_value > own_player["health"] * 1.4:
        moves.append({"use": "big_potion"})
        moves.append("dash")
        if not own_player["is_cloaked"]:
            moves.append({"use": "ring"})
        if own_player["health"] + 100 >= own_player["max_health"]:
            return moves

    if own_player["health"] / own_player["max_health"] < 0.4:
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
        own_player["health"] / own_player["max_health"] < 0.9
        and len(own_player["items"]["big_potions"]) == 6
    ):
        moves.append({"use": "big_potion"})
    return moves


def assess_zapper_use(target, moves):
    if (
        target["type"] in ["player", "tiny"]
        and target["distance"] < 225000
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
            and hazard["distance"] < 20000
            and own_player["id"] != hazard["owner_id"]
        ):
            moves.append("shield")
    return moves


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
            threat_inverse = (1 / threat_slope) * buffer
            if (
                target["position"]["x"] > threat["position"]["x"]
                and threat["position"]["x"] > own_player["position"]["x"]
            ):
                if (
                    target["position"]["y"] > threat["position"]["y"]
                    and threat["position"]["y"] > own_player["position"]["y"]
                ):
                    if threat_slope > target_slope:
                        target["position"]["x"] = own_player["position"]["x"] + buffer
                        target["position"]["y"] = (
                            own_player["position"]["y"] - threat_inverse
                        )
                    else:
                        target["position"]["x"] = (
                            own_player["position"]["x"] - threat_inverse
                        )
                        target["position"]["y"] = own_player["position"]["y"] + buffer
                elif (
                    target["position"]["y"] < threat["position"]["y"]
                    and threat["position"]["y"] < own_player["position"]["y"]
                ):
                    if threat_slope > target_slope:
                        target["position"]["x"] = (
                            own_player["position"]["x"] - threat_inverse
                        )
                        target["position"]["y"] = own_player["position"]["y"] - buffer
                    else:
                        target["position"]["x"] = own_player["position"]["x"] + buffer
                        target["position"]["y"] = (
                            own_player["position"]["y"] + threat_inverse
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
                            own_player["position"]["x"] + threat_inverse
                        )
                        target["position"]["y"] = own_player["position"]["y"] + buffer
                    else:
                        target["position"]["x"] = own_player["position"]["x"] - buffer
                        target["position"]["y"] = (
                            own_player["position"]["y"] - threat_inverse
                        )
                elif (
                    target["position"]["y"] < threat["position"]["y"]
                    and threat["position"]["y"] < own_player["position"]["y"]
                ):
                    if threat_slope > target_slope:
                        target["position"]["x"] = own_player["position"]["x"] - buffer
                        target["position"]["y"] = (
                            own_player["position"]["y"] + threat_inverse
                        )
                    else:
                        target["position"]["x"] = (
                            own_player["position"]["x"] + threat_inverse
                        )
                        target["position"]["y"] = own_player["position"]["y"] - buffer

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

    return target


def assess_bomb_use(own_player, target, enemies, moves):
    bomb_distance = 160000
    for enemy in enemies:
        if (
            target["position"]["x"] > own_player["position"]["x"]
            and own_player["position"]["x"] > enemy["position"]["x"]
            and target["position"]["y"] > own_player["position"]["y"]
            and own_player["position"]["y"] > enemy["position"]["y"]
            and 50000 < enemy["distance"] < bomb_distance
            and target["id"] != enemy["id"]
        ):
            moves.append("special")
            break

        if (
            target["position"]["x"] < own_player["position"]["x"]
            and own_player["position"]["x"] < enemy["position"]["x"]
            and target["position"]["y"] < own_player["position"]["y"]
            and own_player["position"]["y"] < enemy["position"]["y"]
            and 50000 < enemy["distance"] < bomb_distance
            and target["id"] != enemy["id"]
        ):
            moves.append("special")
            break

        if (
            target["position"]["x"] < own_player["position"]["x"]
            and own_player["position"]["x"] < enemy["position"]["x"]
            and target["position"]["y"] > own_player["position"]["y"]
            and own_player["position"]["y"] > enemy["position"]["y"]
            and 50000 < enemy["distance"] < bomb_distance
            and target["id"] != enemy["id"]
        ):
            moves.append("special")
            break

        if (
            target["position"]["x"] > own_player["position"]["x"]
            and own_player["position"]["x"] > enemy["position"]["x"]
            and target["position"]["y"] < own_player["position"]["y"]
            and own_player["position"]["y"] < enemy["position"]["y"]
            and 50000 < enemy["distance"] < bomb_distance
            and target["id"] != enemy["id"]
        ):
            moves.append("special")
            break

        if (
            enemy["distance"] < 50000
            and own_player["is_shield_ready"]
            and own_player["health"] > own_player["attack_damage"] * 2.5
            and target["id"] == enemy["id"]
            and own_player["is_shield_ready"]
            and target["health"] > own_player["attack_damage"]
        ):
            moves.append("special")
            break
    return moves


def assess_icicle_use(own_player, target, moves):
    if (
        target["type"] in ["wolf", "ghoul", "tiny", "minotaur", "player"]
        and not target["is_frozen"]
        and target["distance"] < 225000
        and not own_player["shield_raised"]
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
                "chest",
            ]:
                moves.append("special")

    return moves


def filter_threats(threats):
    existing_threats = []
    for threat in threats:
        if threat.get("health") and threat["health"] > 0:
            existing_threats.append(threat)
        elif threat.get("status") and threat["status"] != "idle":
            existing_threats.append(threat)
    return existing_threats


def generate_distance(own_player, items):
    items_of_interest = []
    for item in items:
        distance = dist_squared_to(own_player["position"], item["position"])
        if distance < 2250000:  # 2000 px
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
        "tiny": 300,
        "ghoul": 100,
        "wolf": 80,
        "player": 80,
        "coin": 200,
        "big_potion": potion_value,
        "speed_zapper": zapper_value,
        "ring": ring_value,
        "chest": 0,
        "power_up": 0,
    }
    for item in items:

        # Adjust experience for player level
        if item["type"] == "player":
            exps["player"] += item["levelling"]["level"] * 25

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
    pass


class LevelData(BaseModel):
    enemies: list
    players: list
    hazards: list
    items: list
    game_info: dict
    own_player: dict


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

    potential_targets = []
    potential_targets.extend(items)
    potential_targets.extend(enemies)
    potential_targets.extend(players)

    moves = apply_skill_points(own_player, moves)

    target = get_best_item(own_player, potential_targets, hazards, enemies, players)
    if not target:
        print("No target found")
        return moves

    message = f'{target["type"]}: {target.get("xp")}'
    moves.append({"speak": message})

    bomb = bomb_nearby(own_player, hazards)
    total_danger_value = total_danger(players, enemies, hazards)

    moves = assess_health_needs(own_player, total_danger_value, moves)
    moves = assess_attack(own_player, target, moves)
    moves = assess_zapper_use(target, moves)

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
            moves.append("special")

    moves = handle_icicle_threat(own_player, hazards, moves)
    target = avoid_collisions(own_player, target, threats)
    moves, target = handle_bomb_threat(own_player, target, bomb, moves)

    # Final move to the target
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
