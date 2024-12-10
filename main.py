from fastapi import FastAPI
from pydantic import BaseModel
import json
import random

CURRENT_EXP_RATE = 0


def dist_squared_to(a: dict, b: dict) -> float:
    return (a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2


def slope(a: dict, b: dict) -> float:
    return (b["y"] - a["y"]) / (b["x"] - a["x"])


def exp_rate(own_player: dict, item: dict) -> float:
    # Calculate the player's speed
    my_speed = 15000 + own_player["levelling"]["speed"] * 500  # TODO: add dash?

    # Experience values for different item types
    exps = {
        "minotaur": 600,
        "tiny": 300,
        "ghoul": 100,
        "wolf": 80,
        "player": 60,
        "coin": 200,
        "big_potion": 100,
        "speed_zapper": 50,
        "ring": 50,
        "chest": 0,
        "power_up": 0,
    }

    # Adjust experience for player type
    if item["type"] == "player":
        exps["player"] += item["levelling"]["level"] * 10

    # Special cases for chest and power-up
    if item["type"] in ["chest", "power_up"] and own_player["special_equipped"] not in [
        "bomb",
        "freeze",
    ]:
        exps["chest"] = 5000
        exps["power_up"] = 5000

    # Special case for tinys
    if (
        item["type"] == "tiny"
        and len(own_player["items"]["speed_zappers"]) == 0
        and not item["is_zapped"]
        and not item["is_frozen"]
    ):
        exps["tiny"] = 50

    # Calculate distance, travel time, and kill time
    distance = dist_squared_to(item["position"], own_player["position"])
    if distance > 100000:
        distance -= 50000  # Dash proxy
    if distance > 200000:
        distance -= 50000  # Dash proxy
    travel_time = distance / my_speed
    kill_time = 0

    if item.get("health") is not None:  # Check if the item has a health attribute
        if item["type"] == "player":
            item["health"] += 150  # Assume players have an average of 1.5 potions
        kill_time = (
            item["health"] / own_player["attack_damage"]
        ) * 0.5  # Assuming attack cooldown

    # Return experience rate
    return exps[item["type"]] / (travel_time + kill_time)


def peripheral_danger(
    own_player: dict, item: dict, enemies: list, players: list, hazards: list
) -> bool:
    total_health = own_player["health"] + len(own_player["items"]["big_potions"]) * 100
    total_danger = 0

    for enemy in enemies:
        if dist_squared_to(item["position"], enemy["position"]) < 100000:
            total_danger += enemy["attack_damage"]

    for player in players:
        if dist_squared_to(item["position"], player["position"]) < 100000:
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
        and item["attack_damage"] >= own_player["health"] * 1.2
    ):
        return True
    return False


def stock_full(own_player: dict, item: dict) -> bool:
    if item["type"] == "ring" and len(own_player["items"]["rings"]) >= 4:
        return True
    if (
        item["type"] == "speed_zapper"
        and len(own_player["items"]["speed_zappers"]) >= 1
    ):
        return True
    if item["type"] == "big_potion" and len(own_player["items"]["big_potions"]) >= 5:
        return True
    return False


def player_unprepared(own_player: dict, item: dict) -> bool:
    if len(own_player["items"]["big_potions"]) == 0 and own_player["health"] < 85:
        if item["type"] != "big_potion":
            return True
    elif (
        item["type"] in ["chest", "power_up"]
        and own_player["special_equipped"] != "bomb"
    ):
        return False
    elif item.get("power") == "shockwave" and own_player["special_equipped"]:
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


def total_danger(own_player: dict, players: list, enemies: list, hazards: list) -> int:
    total_danger = 0

    for player in players:
        if (
            dist_squared_to(own_player["position"], player["position"]) < 100000
            and not player["is_frozen"]
        ):
            total_danger += player["attack_damage"]

    for enemy in enemies:
        if (
            dist_squared_to(own_player["position"], enemy["position"]) < 100000
            and not enemy["is_frozen"]
        ):
            total_danger += enemy["attack_damage"]

    for hazard in hazards:
        if dist_squared_to(own_player["position"], hazard["position"]) < 60000:
            total_danger += hazard["attack_damage"]

    return total_danger


def get_best_item(
    own_player: dict, items: list, hazards: list, enemies: list, players: list
) -> dict:
    max_exp = float("-inf")
    target = None

    for item in items:
        if (
            item["type"] == "tiny"
            and dist_squared_to(own_player["position"], item["position"]) < 16500
        ):
            return item

        # Skip items based on various conditions
        if player_unprepared(own_player, item):
            continue
        if losing_battle(own_player, item):
            continue
        if stock_full(own_player, item):
            continue
        if peripheral_danger(own_player, item, enemies, players, hazards):
            continue

        # Additional checks for items with "attack_damage"
        if item.get("attack_damage") is not None:
            for hazard in hazards:
                if (
                    hazard["attack_damage"] > item["health"]
                    and dist_squared_to(hazard["position"], item["position"]) < 45000
                ):
                    continue

            if (
                item.get("special_equipped") == "freeze"
                and item["health"] > own_player["attack_damage"] * 3
                and len(own_player["items"]["big_potions"]) == 0
            ):
                continue

        # Calculate experience rate and update the target if this is the best option
        exp = exp_rate(own_player, item)
        if exp > max_exp:
            max_exp = exp
            target = item

    return target


def dedupe_moves(moves: list) -> list:
    # Remove duplicate moves
    deduped_moves = []
    for move in moves:
        if move not in deduped_moves:
            deduped_moves.append(move)
    return deduped_moves


def print_exp_rate(game_info: dict, own_player: dict) -> None:
    # Log exp rate periodically
    global CURRENT_EXP_RATE
    if game_info["time_remaining_s"] % 5 == 0:
        exp_rate = round(
            own_player["score"] / (1801 - game_info["time_remaining_s"]), 2
        )
        if CURRENT_EXP_RATE != exp_rate:
            CURRENT_EXP_RATE = exp_rate
            print(f"Score rate: {CURRENT_EXP_RATE}")


def assess_attack(own_player, target, moves):
    if (
        target.get("health") is not None
        and dist_squared_to(own_player["position"], target["position"]) < 15625
    ):
        moves.append("attack")
    return moves


def assess_health_needs(own_player, total_danger_value, moves):
    # Handle health and potion usage
    if total_danger_value > own_player["health"] * 1.25:
        moves.append({"use": "big_potion"})
        if not own_player["is_cloaked"]:
            moves.append({"use": "ring"})
    elif own_player["health"] / own_player["max_health"] < 0.4:
        moves.append({"use": "big_potion"})
        if not own_player["is_cloaked"]:
            moves.append({"use": "ring"})
    elif (
        own_player["health"] / own_player["max_health"] < 0.5
        and len(own_player["items"]["big_potions"]) > 1
    ):
        moves.append({"use": "big_potion"})
        if not own_player["is_cloaked"]:
            moves.append({"use": "ring"})
    elif (
        own_player["health"] / own_player["max_health"] < 0.6
        and len(own_player["items"]["big_potions"]) > 4
    ):
        moves.append({"use": "big_potion"})
    return moves


def assess_zapper_use(own_player, target, moves):
    if (
        target["type"] in ["player", "tiny"]
        and dist_squared_to(own_player["position"], target["position"]) < 225000
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
            if bomb["position"]["x"] > own_player["position"]["x"]
            else own_player["position"]["x"] + space
        )
        target["position"]["y"] = (
            own_player["position"]["y"] - space
            if bomb["position"]["y"] > own_player["position"]["y"]
            else own_player["position"]["y"] + space
        )
    return moves


def handle_icicle_threat(own_player, hazards, moves):
    for hazard in hazards:
        if (
            hazard["type"] == "icicle"
            and dist_squared_to(hazard["position"], own_player["position"]) < 20625
            and own_player["id"] != hazard["owner_id"]
        ):
            moves.append("shield")
            break
    return moves


def handle_collisions(own_player, target, moves):
    if len(own_player["collisions"]) > 0:
        target["position"]["x"] = own_player["position"]["x"]
        target["position"]["y"] = own_player["position"]["y"]
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
            if collision["type"] != target["type"]:
                target["position"]["x"] -= collision["relative_position"]["x"] * 3
                target["position"]["y"] -= collision["relative_position"]["y"] * 3

        moves.append({"move_to": target["position"]})
    return moves


def assess_bomb_use(own_player, target):
    pass


def assess_icicle_use(own_player, target):
    pass


def assess_shockwave_use(own_player, target):
    pass


def filter_threats(threats):
    existing_threats = []
    for threat in threats:
        if threat.get("health") and threat["health"] > 0:
            existing_threats.append(threat)
        elif threat.get("status") and threat["status"] != "idle":
            existing_threats.append(threat)
    return existing_threats


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
    if own_player["health"] <= 0:
        with open("/Users/dastardly/Desktop/bot-deaths.txt", "a") as f:
            f.write(str(level_data))

    enemies = filter_threats(level_data.enemies)
    threats.extend(enemies)

    hazards = filter_threats(level_data.hazards)
    threats.extend(hazards)

    players = filter_threats(level_data.players)
    threats.extend(players)

    game_info = level_data.game_info
    items = level_data.items

    potential_targets = []
    potential_targets.extend(items)
    potential_targets.extend(enemies)
    potential_targets.extend(players)

    print_exp_rate(game_info, own_player)

    moves = apply_skill_points(own_player, moves)

    target = get_best_item(own_player, potential_targets, hazards, enemies, players)
    if not target:
        print("No target found")
        return moves

    moves.append({"speak": target["type"]})
    moves.append("dash")

    bomb = bomb_nearby(own_player, hazards)
    total_danger_value = total_danger(own_player, players, enemies, hazards)

    moves = assess_health_needs(own_player, total_danger_value, moves)
    moves = assess_attack(own_player, target, moves)
    moves = assess_zapper_use(own_player, target, moves)

    moves = handle_collisions(own_player, target, moves)

    # Handle bomb-related logic
    bomb_distance = 160000
    if own_player["special_equipped"] == "bomb":
        # Check for enemies
        for enemy in enemies:
            if (
                target["position"]["x"] > own_player["position"]["x"]
                and own_player["position"]["x"] > enemy["position"]["x"]
                and target["position"]["y"] > own_player["position"]["y"]
                and own_player["position"]["y"] > enemy["position"]["y"]
                and 50000
                < dist_squared_to(enemy["position"], own_player["position"])
                < bomb_distance
                and target["id"] != enemy["id"]
                and len(own_player["collisions"]) == 0
            ):
                moves.append("special")
                break

            if (
                target["position"]["x"] < own_player["position"]["x"]
                and own_player["position"]["x"] < enemy["position"]["x"]
                and target["position"]["y"] < own_player["position"]["y"]
                and own_player["position"]["y"] < enemy["position"]["y"]
                and 50000
                < dist_squared_to(enemy["position"], own_player["position"])
                < bomb_distance
                and target["id"] != enemy["id"]
                and len(own_player["collisions"]) == 0
            ):
                moves.append("special")
                break

            if (
                target["position"]["x"] < own_player["position"]["x"]
                and own_player["position"]["x"] < enemy["position"]["x"]
                and target["position"]["y"] > own_player["position"]["y"]
                and own_player["position"]["y"] > enemy["position"]["y"]
                and 50000
                < dist_squared_to(enemy["position"], own_player["position"])
                < bomb_distance
                and target["id"] != enemy["id"]
                and len(own_player["collisions"]) == 0
            ):
                moves.append("special")
                break

            if (
                target["position"]["x"] < own_player["position"]["x"]
                and own_player["position"]["x"] < enemy["position"]["x"]
                and target["position"]["y"] > own_player["position"]["y"]
                and own_player["position"]["y"] > enemy["position"]["y"]
                and 50000
                < dist_squared_to(enemy["position"], own_player["position"])
                < bomb_distance
                and target["id"] != enemy["id"]
                and len(own_player["collisions"]) == 0
            ):
                moves.append("special")
                break

            if (
                dist_squared_to(enemy["position"], own_player["position"]) < 50000
                and own_player["is_shield_ready"]
                and not bomb
                and own_player["health"] > own_player["attack_damage"] * 2.5
                and target["id"] == enemy["id"]
            ):
                moves.append("special")
                break

        # Check for players
        for player in players:
            if (
                target["position"]["x"] > own_player["position"]["x"]
                and own_player["position"]["x"] > player["position"]["x"]
                and target["position"]["y"] > own_player["position"]["y"]
                and own_player["position"]["y"] > player["position"]["y"]
                and 50000
                < dist_squared_to(player["position"], own_player["position"])
                < bomb_distance
                and len(own_player["collisions"]) == 0
                and target["id"] != player["id"]
            ):
                moves.append("special")
                break

            if (
                target["position"]["x"] < own_player["position"]["x"]
                and own_player["position"]["x"] < player["position"]["x"]
                and target["position"]["y"] < own_player["position"]["y"]
                and own_player["position"]["y"] < player["position"]["y"]
                and 50000
                < dist_squared_to(player["position"], own_player["position"])
                < bomb_distance
                and len(own_player["collisions"]) == 0
                and target["id"] != player["id"]
            ):
                moves.append("special")
                break

            if (
                target["position"]["x"] < own_player["position"]["x"]
                and own_player["position"]["x"] < player["position"]["x"]
                and target["position"]["y"] > own_player["position"]["y"]
                and own_player["position"]["y"] > player["position"]["y"]
                and 50000
                < dist_squared_to(player["position"], own_player["position"])
                < bomb_distance
                and len(own_player["collisions"]) == 0
                and target["id"] != player["id"]
            ):
                moves.append("special")
                break

            if (
                target["position"]["x"] < own_player["position"]["x"]
                and own_player["position"]["x"] < player["position"]["x"]
                and target["position"]["y"] > own_player["position"]["y"]
                and own_player["position"]["y"] > player["position"]["y"]
                and 50000
                < dist_squared_to(player["position"], own_player["position"])
                < bomb_distance
                and len(own_player["collisions"]) == 0
                and target["id"] != player["id"]
            ):
                moves.append("special")
                break

            if (
                dist_squared_to(player["position"], own_player["position"]) < 50000
                and own_player["is_shield_ready"]
                and not bomb
                and own_player["health"] > own_player["attack_damage"] * 2.5
                and target["id"] == player["id"]
            ):
                moves.append("special")
                break

    elif own_player["special_equipped"] == "freeze":
        if (
            target["type"] in ["ghoul", "tiny", "minotaur", "player"]
            and not target["is_frozen"]
            and dist_squared_to(target["position"], own_player["position"]) < 225000
            and not own_player["shield_raised"]
        ):
            moves.append("special")

    elif own_player["special_equipped"] == "shockwave":
        if bomb:
            moves.append("special")
        elif peripheral_danger(own_player, own_player, enemies, players, hazards):
            moves.append("special")

    moves = handle_icicle_threat(own_player, hazards, moves)
    moves = handle_bomb_threat(own_player, target, bomb, moves)

    # Final move to the target
    moves.append({"move_to": target["position"]})
    return dedupe_moves(moves)


app = FastAPI()


@app.post("/")
async def receive_level_data(level_data: LevelData):
    moves = play(level_data)
    return moves
