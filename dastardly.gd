\
#can use a ring if the item is a potion and it's too dangerous 
#still not using potion when health is low
# target jucier areas of the map, peripheral points
# write down questions for json
# behavior trees
#incorporate weighting into potion based on health
#adjust use of shield and bomb. killing self too much

func dist_squared_to(a, b):
	return pow(a.x - b.x, 2) + pow(a.y - b.y, 2)

func slope(a, b):
	return (b.y - a.y) / (b.x - a.x) 
	
func exp_rate(own_player, item):
	var my_speed = 15000 + own_player.levelling.speed * 500  # TODO: add dash?
	var exps = {
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
		"power_up": 0
	}
	if item.type == "player":
		exps["player"] += item.level * 10
	
	if (item.type in ["chest", "power_up"] and 
		own_player.special_equipped not in ["bomb", "freeze"]):
		exps["chest"] = 10000
		exps["power_up"] = 10000
		
	if (item.type == "tiny" and 
		len(own_player.items.speed_zappers) == 0 and
		not item.is_zapped):
		exps["tiny"] = 60
		
	var distance = dist_squared_to(item.position, own_player.position)
	var travel_time = distance / my_speed
	var kill_time = 0

	if item.has("health"):
		kill_time = (item.health / own_player.attack_damage) * .5  # guessing at attack cooldown

	return exps[item.type] / (travel_time + kill_time)
	
func peripheral_danger(own_player, item, enemies, players, hazards):
	var total_health = own_player.health + len(own_player.items.big_potions) * 100
	var total_danger = 0
	for enemy in enemies:
		if dist_squared_to(item.position, enemy.position) < 120000:
			total_danger += enemy.attack_damage
	for player in players:
		if dist_squared_to(item.position, player.position) < 120000:
			total_danger += player.attack_damage
	for hazard in hazards:
		if dist_squared_to(item.position, hazard.position) < 80000:
			total_danger += hazard.attack_damage
	return total_danger > total_health

func apply_skill_points(own_player, moves):
	var max = 20
	if own_player.levelling.available_skill_points > 0:
		if own_player.levelling.attack > own_player.levelling.speed:
			moves.append({ "redeem_skill_point": "speed" })
		elif own_player.levelling.speed > own_player.levelling.health:
			moves.append({ "redeem_skill_point": "health" })
		else:
			moves.append({ "redeem_skill_point": "attack" })

		if own_player.levelling.speed < max:
			moves.append({ "redeem_skill_point": "speed" })
		if own_player.levelling.health < max:
			moves.append({ "redeem_skill_point": "health" })
		if own_player.levelling.attack < max:
			moves.append({ "redeem_skill_point": "attack" })
	return moves

func losing_battle(own_player, item):
	if (item.has("attack_damage") and 
		item.attack_damage > own_player.health):
		return true
	return false

func stock_full(own_player, item):
	if item.type == "ring" and len(own_player.items.rings) >= 2:
		return true
	if item.type == "speed_zapper" and len(own_player.items.speed_zappers) >= 2:
		return true
	if item.type == "big_potion" and len(own_player.items.big_potions) >= 5:
		return true
	return false

#
#
#
#

func get_best_item(own_player, items, hazards, enemies, players, game_info):
	var max_exp = -INF
	var target = null

	for item in items:
		if item.has("health") and item.health <= 0:
			continue
		if player_unprepared(own_player, item, game_info):
			continue
		if losing_battle(own_player, item):
			continue
		if stock_full(own_player, item):
			continue
		if peripheral_danger(own_player, item, enemies, players, hazards):
			continue
		if item.has("attack_damage"):
			for hazard in hazards:
				if (hazard.attack_damage > item.health and 
				dist_squared_to(hazard.position, item.position) < 60000):
					continue
			if (item.type in ["minotaur", "player"] and 
				game_info.time_remaining_s > 1680 and 
				item.health > own_player.attack_damage * 3):
				continue
			if (item.type != "minotaur" and 
				game_info.time_remaining_s < 1020 and 
				dist_squared_to(item.position, own_player.position) > 240000):
				continue
			if (item.special_equipped == "freeze" and 
				item.health > own_player.attack_damage * 3 and
				len(own_player.items.big_potions) == 0):
				continue
							
		var exp = exp_rate(own_player, item)
		if exp > max_exp:
			max_exp = exp
			target = item

	return target

func player_unprepared(own_player, item, game_info):
	if len(own_player.items.big_potions) == 0 and own_player.health < 85:
		if item.type != "big_potion":
			return true
	elif (item.type in ["chest", "power_up"] and 
		own_player.special_equipped != "bomb"):
		return false
	elif item.power == "shockwave" and own_player.special_equipped:
		return true
	return false

func bomb_nearby(item, hazards):
	for hazard in hazards:
		if (hazard.type == "bomb" and 
			dist_squared_to(item.position, hazard.position) < 50000 and 
			hazard.status != "idle"):
			return hazard
	return null

func total_danger(own_player, players, enemies, hazards):
	var total_danger = 0
	for player in players:
		if (dist_squared_to(own_player.position, player.position) < 100000 and
			player.health > 0 and 
			not player.is_frozen):
			total_danger += player.attack_damage
	for enemy in enemies:
		if (dist_squared_to(own_player.position, enemy.position) < 100000 and
			enemy.health > 0 and 
			not enemy.is_frozen):
			total_danger += enemy.attack_damage
	for hazard in hazards:
		if (dist_squared_to(own_player.position, hazard.position) < 80000 and 
			hazard.status != "idle"):
			total_danger += hazard.attack_damage
	return total_danger

#
#
#
#

func play(level_data):
	var moves = []
	var own_player = level_data.own_player
	var enemies = level_data.enemies
	var players = level_data.players
	var hazards = level_data.hazards
	var game_info = level_data.game_info
	var items = level_data.items
	var zap_distance = 225000
		
	var potential_targets = []
	potential_targets.append_array(items)
	potential_targets.append_array(enemies)
	potential_targets.append_array(players)
	moves = apply_skill_points(own_player, moves)

	if game_info.time_remaining_s % 15 == 0:
		print_message(own_player.score / (1800 - game_info.time_remaining_s))
	
	var target = get_best_item(own_player, potential_targets, hazards, enemies, players, game_info)
	var bomb = bomb_nearby(own_player, hazards)
	var total_danger = total_danger(own_player, players, enemies, hazards)
	moves.append({"speak": target.type})
	moves.append("dash")

	if (target.has("health") and 
		dist_squared_to(own_player.position, target.position) < 15625 and
		target.health > 0):
		moves.append("attack")

	if ((total_danger > own_player.health) or 
		(own_player.health / own_player.max_health < .4) or
		(own_player.health / own_player.max_health < .5 and len(own_player.items.big_potions) > 1) or
		(own_player.health / own_player.max_health < .6 and len(own_player.items.big_potions) > 4)):
		moves.append({"use":"big_potion"})
		if not own_player.is_cloaked:
			moves.append({"use":"ring"})

	if (dist_squared_to(own_player.position, target.position) < zap_distance and 
		target.type in ["player", "tiny"] and
		not target.is_zapped):
		moves.append({"use":"speed_zapper"})
			
	if len(own_player.collisions) > 0:
		for collision in own_player.collisions:
			if collision.type in ["wolf", "ghoul", "tiny", "minotaur", "player", "chest"]:
				moves.append("attack")
				moves.append("shield")
				if own_player.special_equipped != "bomb":
					moves.append("special")
				elif (own_player.special_equipped == "bomb" and 
					own_player.is_shield_ready and 
					not bomb and
					own_player.health > own_player.attack_damage * 2.5):
					moves.append("shield")
					moves.append("special")
				break
		target.position.x += randi_range(-400, 400)
		target.position.y += randi_range(-400, 400)

	var bomb_distance = 160000
	if own_player.special_equipped == "bomb" and len(own_player.items.big_potions) > 0:
		for enemy in enemies:
			if (target.position.x > own_player.position.x and 
				own_player.position.x > enemy.position.x and 
				target.position.y > own_player.position.y and
				own_player.position.y > enemy.position.y and
				dist_squared_to(enemy.position, own_player.position) < bomb_distance and 
				dist_squared_to(enemy.position, own_player.position) > 50000 and
				enemy.health > 0):
				moves.append("special")
				break
				
			if (target.position.x < own_player.position.x and 
				own_player.position.x < enemy.position.x and 
				target.position.y < own_player.position.y and
				own_player.position.y < enemy.position.y and
				dist_squared_to(enemy.position, own_player.position) < bomb_distance and 
				dist_squared_to(enemy.position, own_player.position) > 50000 and
				enemy.health > 0):
				moves.append("special")
				break
				
			if (target.position.x < own_player.position.x and 
				own_player.position.x < enemy.position.x and 
				target.position.y > own_player.position.y and
				own_player.position.y > enemy.position.y and
				dist_squared_to(enemy.position, own_player.position) < bomb_distance and 
				dist_squared_to(enemy.position, own_player.position) > 50000 and
				enemy.health > 0):
				moves.append("special")
				break
				
			if (target.position.x < own_player.position.x and 
				own_player.position.x < enemy.position.x and 
				target.position.y > own_player.position.y and
				own_player.position.y > enemy.position.y and
				dist_squared_to(enemy.position, own_player.position) < bomb_distance and 
				dist_squared_to(enemy.position, own_player.position) > 50000 and
				enemy.health > 0):
				moves.append("special")
				break

			if (dist_squared_to(enemy.position, own_player.position) < 30000 and 
				own_player.is_shield_ready and 
				not bomb and
				enemy.health > 0 and
				own_player.health > own_player.attack_damage * 2.5):
				moves.append("special")
				break
				
		for player in players:
			if (target.position.x > own_player.position.x and 
				own_player.position.x > player.position.x and 
				target.position.y > own_player.position.y and
				own_player.position.y > player.position.y and
				dist_squared_to(player.position, own_player.position) < bomb_distance and 
				dist_squared_to(player.position, own_player.position) > 50000 and
				player.health > 0):
				moves.append("special")
				break
				
			if (target.position.x < own_player.position.x and 
				own_player.position.x < player.position.x and 
				target.position.y < own_player.position.y and
				own_player.position.y < player.position.y and
				dist_squared_to(player.position, own_player.position) < bomb_distance and 
				dist_squared_to(player.position, own_player.position) > 50000 and
				player.health > 0):
				moves.append("special")
				break

			if (target.position.x < own_player.position.x and 
				own_player.position.x < player.position.x and 
				target.position.y > own_player.position.y and
				own_player.position.y > player.position.y and
				dist_squared_to(player.position, own_player.position) < bomb_distance and 
				dist_squared_to(player.position, own_player.position) > 50000 and
				player.health > 0):
				moves.append("special")
				break
				
			if (target.position.x < own_player.position.x and 
				own_player.position.x < player.position.x and 
				target.position.y > own_player.position.y and
				own_player.position.y > player.position.y and
				dist_squared_to(player.position, own_player.position) < bomb_distance and 
				dist_squared_to(player.position, own_player.position) > 50000 and
				player.health > 0):
				moves.append("special")
				break

			if (dist_squared_to(player.position, own_player.position) < 50000 and 
				own_player.is_shield_ready and 
				not bomb and
				player.health > 0 and
				own_player.health > own_player.attack_damage * 2.5):
				moves.append("special")
				break
	elif own_player.special_equipped == "freeze":
		if (target.type in ["ghoul", "tiny", "minotaur", "player"] and 
			not target.is_frozen and 
			dist_squared_to(target.position, own_player.position) < zap_distance and
			not own_player.shield_raised):
			moves.append("special")
	elif own_player.special_equipped == "shockwave": 
		if bomb:
			moves.append("special")
		elif peripheral_danger(own_player, own_player, enemies, players, hazards):
			moves.append("special")
		
	for hazard in hazards:
		if (hazard.type == "icicle" and 
			dist_squared_to(hazard.position, own_player.position) < 17625 and
			own_player.id != hazard.owner_id):
				moves.append("shield")
				
	if bomb and bomb.status != "idle":
		var space = 35
		moves.append("shield")
		if bomb.attack_damage > own_player.health:
			moves.append({"use":"big_potion"})
		if bomb.position.x > own_player.position.x:
			target.position.x = own_player.position.x - space
		else:
			target.position.x = own_player.position.x + space
		if bomb.position.y > own_player.position.y:
			target.position.y = own_player.position.y - space
		else:
			target.position.y = own_player.position.y + space

	if target:
		moves.append({"move_to": target.position})
	else:
		print_message("no target found")

	var deduped_moves = []
	for move in moves:
		if move not in deduped_moves:
			deduped_moves.append(move)
	return deduped_moves