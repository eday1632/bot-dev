from fastapi import FastAPI
from pydantic import BaseModel
import random


def dist_squared_to(a, b):
    return (a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2


def slope(a, b):
    return (b["y"] - a["y"]) / (b["x"] - a["x"])


def exp_rate(own_player, item):
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
        "big_potion": 72,
        "speed_zapper": 36,
        "ring": 36,
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
        exps["chest"] = 10000
        exps["power_up"] = 10000

    # Special case for tiny type
    if (
        item["type"] == "tiny"
        and len(own_player["items"]["speed_zappers"]) == 0
        and not item["is_zapped"]
    ):
        exps["tiny"] = 60

    # Calculate distance, travel time, and kill time
    distance = dist_squared_to(item["position"], own_player["position"])
    travel_time = distance / my_speed
    kill_time = 0

    if item.get("health"):  # Check if the item has a health attribute
        kill_time = (
            item["health"] / own_player["attack_damage"]
        ) * 0.5  # Assuming attack cooldown

    # Return experience rate
    return exps[item["type"]] / (travel_time + kill_time)


def peripheral_danger(own_player, item, enemies, players, hazards):
    total_health = own_player["health"] + len(own_player["items"]["big_potions"]) * 100
    total_danger = 0

    for enemy in enemies:
        if dist_squared_to(item["position"], enemy["position"]) < 120000:
            total_danger += enemy["attack_damage"]

    for player in players:
        if dist_squared_to(item["position"], player["position"]) < 120000:
            total_danger += player["attack_damage"]

    for hazard in hazards:
        if dist_squared_to(item["position"], hazard["position"]) < 80000:
            total_danger += hazard["attack_damage"]

    return total_danger > total_health


def apply_skill_points(own_player, moves):
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


def losing_battle(own_player, item):
    if item.get("attack_damage") and item["attack_damage"] > own_player["health"]:
        return True
    return False


def stock_full(own_player, item):
    if item["type"] == "ring" and len(own_player["items"]["rings"]) >= 2:
        return True
    if (
        item["type"] == "speed_zapper"
        and len(own_player["items"]["speed_zappers"]) >= 2
    ):
        return True
    if item["type"] == "big_potion" and len(own_player["items"]["big_potions"]) >= 5:
        return True
    return False


def player_unprepared(own_player, item, game_info):
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


def bomb_nearby(item, hazards):
    for hazard in hazards:
        if (
            hazard["type"] == "bomb"
            and dist_squared_to(item["position"], hazard["position"]) < 50000
            and hazard["status"] != "idle"
        ):
            return hazard
    return None


def total_danger(own_player, players, enemies, hazards):
    total_danger = 0

    for player in players:
        if (
            dist_squared_to(own_player["position"], player["position"]) < 100000
            and player["health"] > 0
            and not player["is_frozen"]
        ):
            total_danger += player["attack_damage"]

    for enemy in enemies:
        if (
            dist_squared_to(own_player["position"], enemy["position"]) < 100000
            and enemy["health"] > 0
            and not enemy["is_frozen"]
        ):
            total_danger += enemy["attack_damage"]

    for hazard in hazards:
        if (
            dist_squared_to(own_player["position"], hazard["position"]) < 80000
            and hazard["status"] != "idle"
        ):
            total_danger += hazard["attack_damage"]

    return total_danger


def get_best_item(own_player, items, hazards, enemies, players, game_info):
    max_exp = float("-inf")
    target = None

    for item in items:
        # Skip items with zero or negative health
        if item.get("health") and item["health"] <= 0:
            continue

        # Skip items based on various conditions
        if player_unprepared(own_player, item, game_info):
            continue
        if losing_battle(own_player, item):
            continue
        if stock_full(own_player, item):
            continue
        if peripheral_danger(own_player, item, enemies, players, hazards):
            continue

        # Additional checks for items with "attack_damage"
        if item.get("attack_damage"):
            for hazard in hazards:
                if (
                    hazard["attack_damage"] > item["health"]
                    and dist_squared_to(hazard["position"], item["position"]) < 60000
                ):
                    continue

            if (
                item["type"] in ["minotaur", "player"]
                and game_info["time_remaining_s"] > 1680
                and item["health"] > own_player["attack_damage"] * 3
            ):
                continue

            if (
                item["type"] != "minotaur"
                and game_info["time_remaining_s"] < 1020
                and dist_squared_to(item["position"], own_player["position"]) > 240000
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


def dedupe_moves(moves: list):
    # Remove duplicate moves
    deduped_moves = []
    for move in moves:
        if move not in deduped_moves:
            deduped_moves.append(move)
    return deduped_moves


class LevelData(BaseModel):
    enemies: list
    players: list
    hazards: list
    items: list
    game_info: dict
    own_player: dict


CURRENT_EXP_RATE = 0
CURRENT_MOVE_LIST = ()


def play(level_data):
    moves = []
    own_player = level_data.own_player
    enemies = level_data.enemies
    players = level_data.players
    hazards = level_data.hazards
    game_info = level_data.game_info
    items = level_data.items
    zap_distance = 225000

    potential_targets = []
    potential_targets.extend(items)
    potential_targets.extend(enemies)
    potential_targets.extend(players)

    # Apply skill points
    moves = apply_skill_points(own_player, moves)

    # Log exp rate periodically
    if game_info["time_remaining_s"] % 5 == 0:
        exp_rate = own_player["score"] / (1800 - game_info["time_remaining_s"])
        print(f"Score rate: {exp_rate}")

    target = get_best_item(
        own_player, potential_targets, hazards, enemies, players, game_info
    )
    bomb = bomb_nearby(own_player, hazards)
    total_danger_value = total_danger(own_player, players, enemies, hazards)

    # Add moves based on the target and conditions
    if target:
        moves.append({"speak": target["type"]})
    moves.append("dash")

    if (
        target.get("health")
        and dist_squared_to(own_player["position"], target["position"]) < 15625
        and target["health"] > 0
    ):
        moves.append("attack")

    # Handle health and potion usage
    if (
        total_danger_value > own_player["health"]
        or (own_player["health"] / own_player["max_health"] < 0.4)
        or (
            own_player["health"] / own_player["max_health"] < 0.5
            and len(own_player["items"]["big_potions"]) > 1
        )
        or (
            own_player["health"] / own_player["max_health"] < 0.6
            and len(own_player["items"]["big_potions"]) > 4
        )
    ):
        moves.append({"use": "big_potion"})
        if not own_player["is_cloaked"]:
            moves.append({"use": "ring"})

    # Handle speed zapper usage
    if (
        target["type"] in ["player", "tiny"]
        and dist_squared_to(own_player["position"], target["position"]) < zap_distance
        and not getattr(target, "is_zapped", False)
    ):
        moves.append({"use": "speed_zapper"})

    # Handle collisions
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
                moves.append("shield")
                if own_player["special_equipped"] != "bomb":
                    moves.append("special")
                elif (
                    own_player["special_equipped"] == "bomb"
                    and own_player["is_shield_ready"]
                    and not bomb
                    and own_player["health"] > own_player["attack_damage"] * 2.5
                ):
                    moves.append("shield")
                    moves.append("special")
                break
        target["position"]["x"] += random.randint(-400, 400)
        target["position"]["y"] += random.randint(-400, 400)

    # Handle bomb-related logic
    bomb_distance = 160000
    if (
        own_player["special_equipped"] == "bomb"
        and len(own_player["items"]["big_potions"]) > 0
    ):
        for enemy in enemies:
            if (
                dist_squared_to(enemy["position"], own_player["position"])
                < bomb_distance
                and dist_squared_to(enemy["position"], own_player["position"]) > 50000
                and enemy["health"] > 0
            ):
                moves.append("special")
                break
        for player in players:
            if (
                dist_squared_to(player["position"], own_player["position"])
                < bomb_distance
                and dist_squared_to(player["position"], own_player["position"]) > 50000
                and player["health"] > 0
            ):
                moves.append("special")
                break

    elif own_player["special_equipped"] == "freeze":
        if (
            target["type"] in ["ghoul", "tiny", "minotaur", "player"]
            and not getattr(target, "is_frozen", False)
            and dist_squared_to(target["position"], own_player["position"])
            < zap_distance
            and not own_player["shield_raised"]
        ):
            moves.append("special")

    elif own_player["special_equipped"] == "shockwave":
        if bomb:
            moves.append("special")
        elif peripheral_danger(own_player, own_player, enemies, players, hazards):
            moves.append("special")

    # Handle icicle hazard
    for hazard in hazards:
        if (
            hazard["type"] == "icicle"
            and dist_squared_to(hazard["position"], own_player["position"]) < 17625
            and own_player["id"] != hazard["owner_id"]
        ):
            moves.append("shield")

    # Handle bomb response
    if bomb and bomb["status"] != "idle":
        space = 35
        moves.append("shield")
        if bomb["attack_damage"] > own_player["health"]:
            moves.append({"use": "big_potion"})
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

    # Final move to the target
    if target:
        moves.append({"move_to": target["position"]})
    else:
        print("No target found")

    return dedupe_moves(moves)


app = FastAPI()


@app.post("/")
async def receive_level_data(level_data: LevelData):
    moves = play(level_data)
    print(moves)
    return moves
