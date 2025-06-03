import pygame
from common_b_s import (
    Character,
    roll_dice_expression,
    add_message,
    can_equip_item,
    TILE_SIZE,
    RED,
    GREEN,
    Item,
)

# Player class definition moved from blade_sigil_v5_5.py
class Player(Character):
    def __init__(self, name, race, char_class, start_position, sprite, abilities=None):
        super().__init__(name, race, char_class, abilities)
        self.position = start_position
        self.sprite = sprite
        self.inventory = []
        self.equipment = {
            "weapon": None, "armor": None, "shield": None, "jewelry": []
        }
        self.gold = roll_dice_expression("4d6+200") # roll_dice_expression is in common_b_s

    def pickup_item(self, item):
        self.inventory.append(item)
        add_message(f"{self.name} picked up {item.name}!") # add_message is in common_b_s

    def equip_item(self, item):
        can_equip, reason = can_equip_item(self, item) # can_equip_item is in common_b_s
        if not can_equip:
            add_message(f"Cannot equip {item.name}: {reason}", RED) # RED is in common_b_s
            return False
        if item in self.inventory: self.inventory.remove(item)

        item_type_str = getattr(item, "item_type", "") # Safe access to item_type

        if item_type_str.startswith("weapon"):
            if self.equipment["weapon"]: self.equipment["weapon"].remove_effect(self)
            item.apply_effect(self)
        elif item_type_str.startswith("armor"):
            if self.equipment["armor"]: self.equipment["armor"].remove_effect(self)
            item.apply_effect(self)
        elif item_type_str.startswith("shield"):
            if self.equipment.get("shield"): self.equipment["shield"].remove_effect(self)
            item.apply_effect(self)
        elif item_type_str.startswith("jewelry"):
            if hasattr(item, 'can_equip') and not item.can_equip(self):
                add_message(f"Cannot equip {item.name}: Maximum number already equipped", RED)
                return False
            item.apply_effect(self)
        add_message(f"{self.name} equipped {item.name}!", GREEN) # GREEN is in common_b_s
        return True

    def move(self, dx, dy, dungeon):
        new_x = self.position[0] + dx
        new_y = self.position[1] + dy
        tile_x = new_x // TILE_SIZE # TILE_SIZE is global in common_b_s
        tile_y = new_y // TILE_SIZE

        if not (0 <= tile_x < dungeon.width and 0 <= tile_y < dungeon.height):
            return False, "", "You can't move through walls."
        target_tile = dungeon.tiles[tile_x][tile_y]

        if target_tile.type == 'locked_door':
            door_coords = (tile_x, tile_y)
            if door_coords in dungeon.doors and dungeon.doors[door_coords].locked:
                return False, "", "The door is locked. Try another approach."

        if target_tile.type in ('floor', 'corridor', 'door'):
            door_coords = (tile_x, tile_y)
            if target_tile.type == 'door' and door_coords in dungeon.doors:
                door = dungeon.doors[door_coords]
                self.position = [new_x, new_y]
                if door.door_type == "level_transition":
                    new_dungeon_level = dungeon.level + 1
                    if self.level < new_dungeon_level:
                        self.level = new_dungeon_level
                        hp_per_level = {'Warrior': 10, 'Priest': 6, 'Wizard': 4}.get(self.char_class, 8)
                        self.max_hit_points += hp_per_level
                        self.hit_points += hp_per_level
                        pygame.event.post(pygame.event.Event(pygame.USEREVENT + 1)) # pygame is imported
                        return True, "level_transition", f"Found stairs! Completed level {dungeon.level}. Leveled up to {self.level}!"
                    return True, "level_transition", f"Found stairs! Completed level {dungeon.level}."
                elif door.door_type == "map_transition":
                    return True, "map_transition", door.destination_map, f"Passage to map {door.destination_map}."
                else: return True, "", "You pass through the door."
            else:
                self.position = [new_x, new_y]
                return True, "", ""
        else: return False, "", "You can't move there."

    def attack(self, target):
        effective_str_mod = self.calculate_modifier(self.get_effective_ability("strength"))
        attack_roll = roll_dice_expression("1d20") + effective_str_mod
        if attack_roll >= target.get_effective_ac(): # Assumes target has get_effective_ac
            damage = self.get_effective_damage()
            target.hit_points -= damage # Assumes target has hit_points
            return f"{self.name} hits {target.name} for {damage} damage!"
        else: return f"{self.name} misses {target.name}!"

    def get_effective_ability(self, stat):
        base = self.abilities.get(stat, 0)
        bonus = 0
        for item in self.equipment.get('jewelry', []):
            item_stat = getattr(item, 'bonus_stat', getattr(item, 'stat_bonus', None))
            if item_stat == stat and hasattr(item, 'bonus_value'):
                bonus += item.bonus_value
        return base + bonus

    def get_effective_ac(self):
        base_ac = self.ac
        if self.equipment.get("armor"): base_ac += self.equipment["armor"].ac_bonus
        if self.equipment.get("shield"):
            shield_item = self.equipment["shield"]
            # Check if shield_ac_bonus is defined on player and is relevant for the current shield
            # This logic might need refinement based on how shield_ac_bonus is set/managed
            if hasattr(self, 'shield_ac_bonus') and shield_item == self.equipment.get("shield"):
                 base_ac += self.shield_ac_bonus
            elif hasattr(shield_item, 'ac_bonus'): # Fallback to item's own ac_bonus
                 base_ac += shield_item.ac_bonus
        return base_ac

    def get_effective_damage(self):
        if self.equipment.get("weapon"):
            return self.equipment["weapon"].roll_damage(self) # Assumes weapon has roll_damage method
        else: return roll_dice_expression("1d2") + self.calculate_modifier(self.get_effective_ability("strength"))

    def add_experience(self, xp_amount):
        if not hasattr(self, 'experience'): self.experience = 0
        if not hasattr(self, 'level_thresholds'):
            base_xp = 1000
            self.level_thresholds = [0] + [base_xp * lvl * lvl for lvl in range(1, 21)]
        self.experience += xp_amount
        has_enough_xp = (self.level < 20 and self.experience >= self.level_thresholds[self.level + 1])
        return has_enough_xp
