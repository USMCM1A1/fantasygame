#!/usr/bin/env python
# coding: utf-8

# In[2]:


"""
Fantasy CRPG Dungeon Crawl
Inspired by classic dungeon crawl games like Wizardry.

This code is divided into modular sections:
  • Initialization & Constants Module
  • Asset Loading Module
  • Item Module
  • UI Drawing Module
  • Game Classes Module (including Character Leveling Mechanics)
  • Spell Data & Spell Casting Module
  • Combat Module
  • Character Creation & Selection Functions
  • Main Game Loop
"""

import pygame
import sys
import json
import random
import os
import re
import import_ipynb
from novamagus_hub import run_hub

# =============================================================================
# === Initialization & Constants Module ===
# =============================================================================
pygame.init()

#sound mixer
pygame.mixer.init()

# Import from common_b_s
import common_b_s
from common_b_s import (
    # Dungeon-specific configurations
    DUNGEON_SCREEN_WIDTH, DUNGEON_SCREEN_HEIGHT, DUNGEON_FPS, DUNGEON_TILE_SIZE,
    DUNGEON_RIGHT_PANEL_WIDTH, DUNGEON_BOTTOM_PANEL_HEIGHT, DUNGEON_PLAYABLE_AREA_WIDTH, DUNGEON_PLAYABLE_AREA_HEIGHT,
    RIGHT_PANEL_OFFSET, BOTTOM_PANEL_OFFSET,
    
    # Door and Chest configuration
    DOOR_CHANCE, LOCKED_DOOR_CHANCE, DOOR_DIFFICULTY, 
    CHEST_DIFFICULTY, CHEST_ITEMS_COUNT, CHEST_GOLD_DICE,
    
    # Colors and Font
    WHITE, BLACK, LIGHT_GRAY, RED, GREEN, BLUE, font,
    
    # Asset loading and JSON utilities
    load_sprite, load_json, assets_data, characters_data, spells_data, items_data, monsters_data, dice_sprite,
    spell_sound, melee_sound, arrow_sound, levelup_sound,
    
    # UI Drawing functions (if used in dungeon mode)
    draw_text, draw_panel, draw_text_lines, draw_playable_area, draw_right_panel, draw_bottom_panel,
    handle_scroll_events, draw_attack_prompt, draw_equipment_panel, draw_debug_info, roll_ability_helper, roll_dice_expression,
    
    # Helper and utility functions
    add_message, update_message_queue, roll_dice_expression, roll_ability_helper,
    can_equip_item, handle_targeting, compute_fov, get_valid_equipment_slots,
    swap_equipment, unequip_item, get_clicked_equipment_slot, print_character_stats, 
    manage_inventory, display_help_screen, loot_drop_sprite,
    
    # Base and derived item classes
    Item, Weapon, WeaponBlade, WeaponBlunt, Armor, Shield, Jewelry, Consumable,
    
    # Spell Casting
    bresenham, has_line_of_sight, spells_dialogue, cast_spell, 
 
    #Combat
    draw_attack_prompt, handle_monster_turn, process_monster_death,
    handle_scroll_events,
    
    # Game Classes
    Character, Player, Tile, Door, Chest,
) 

print("DEBUG: blade_sigil_v5_4.py is running")
print(f"DEBUG: in_dungeon imported from common_b_s is: {common_b_s.in_dungeon}")

import novamagus_hub  # Ensure the hub module is imported
SCREEN_HEIGHT = DUNGEON_SCREEN_HEIGHT
SCREEN_WIDTH = DUNGEON_SCREEN_WIDTH
TILE_SIZE = DUNGEON_TILE_SIZE
# Make sure to use the imported in_dungeon variable
in_dungeon = common_b_s.in_dungeon

screen = pygame.display.set_mode((DUNGEON_SCREEN_WIDTH, DUNGEON_SCREEN_HEIGHT))
pygame.display.set_caption("Blade & Sigil v5")
clock = pygame.time.Clock()
FPS = 60

# Debug logging
import logging
DEBUG_MODE = True  # Set this to False to disable the in-game debug overlay
logging.basicConfig(
    level=logging.DEBUG,
    filename="game_debug.log",
    format="%(asctime)s - %(levelname)s - %(message)s"
)


# In[3]:


# =============================================================================
# === Game Classes Module (including Character Leveling Mechanics) ===
# =============================================================================
class Character:
    def __init__(self, name, race, char_class, abilities=None):
        self.name = name
        self.race = race
        self.char_class = char_class
        # Use the passed abilities if provided, otherwise roll new ones.
        if abilities is None:
            self.abilities = {
                'strength': roll_ability_helper(),
                'intelligence': roll_ability_helper(),
                'wisdom': roll_ability_helper(),
                'dexterity': roll_ability_helper(),
                'constitution': roll_ability_helper()
            }
        else:
            self.abilities = abilities
        self.apply_race_bonus()
        self.level = 1
        self.spell_points = self.calculate_spell_points()
        self.max_hit_points = self.roll_hit_points()  # Roll HP with Constitution applied
        self.hit_points = self.max_hit_points  # Ensure current HP starts at max
        self.ac = self.calculate_ac()  # Base Armor Class (for level 1)
        self.attack_bonus = 0  # Initialize extra attack bonus (for leveling)

    def roll_ability(self):
        roll = sum(random.randint(1, 6) for _ in range(3))
        while roll == 3:  # re-roll if all dice are 1's
            roll = sum(random.randint(1, 6) for _ in range(3))
        return roll

    def apply_race_bonus(self):
        if self.race == 'High Elf':
            self.abilities['intelligence'] += 1
        elif self.race in ['Wood Elf', 'Halfling']:
            self.abilities['dexterity'] += 1
        elif self.race == 'Dwarf':
            self.abilities['constitution'] += 1
        elif self.race == 'Human':
            if self.char_class in ['Warrior', 'Dwarf']:
                self.abilities['strength'] += 1
            elif self.char_class == 'Priest':
                self.abilities['wisdom'] += 1

    def calculate_spell_points(self):
        # Calculate the INT or WIS modifier based on the character class
        if self.char_class in ['Wizard', 'Spellblade']:
            int_bonus = self.calculate_modifier(self.abilities.get('intelligence', 10))
            # For Wizards and Spellblades, use INT modifier
            return 4 + self.level - 1 + int_bonus  # 4 at level 1, +1 per level, plus INT modifier
        elif self.char_class == 'Priest':
            wis_bonus = self.calculate_modifier(self.abilities.get('wisdom', 10))
            # For Priests, use WIS modifier
            return 4 + self.level - 1 + wis_bonus  # 4 at level 1, +1 per level, plus WIS modifier
        elif self.char_class == 'Spellblade':
            int_bonus = self.calculate_modifier(self.abilities.get('intelligence', 10))
            return 2 + int_bonus  # starting value for Spellblades, plus INT modifier
        return 0

    def roll_hit_points(self):
        hit_dice = {
            'Warrior': 10,
            'Priest': 8,
            'Archer': 6,
            'Thief': 6,
            'Wizard': 4,
            'Spellblade': 4
        }
        # Calculate the Constitution modifier
        con_bonus = self.calculate_modifier(self.abilities.get('constitution', 10))
        
        if self.level == 1:
            # At level 1, add the con bonus to the base hit die
            return hit_dice[self.char_class] + con_bonus
        else:
            roll = random.randint(1, hit_dice[self.char_class])
            while roll == 1:
                roll = random.randint(1, hit_dice[self.char_class])
            return roll + con_bonus


    def calculate_ac(self):
        # Set a base AC based on the character class.
        if self.char_class == 'Warrior':
            base_ac = 1
        elif self.char_class == 'Thief':
            base_ac = 1
        elif self.char_class in ['Wizard', 'Priest', 'Spellblade', 'Archer']:
            base_ac = 0
        else:
            base_ac = 0
    
        # Calculate the Dexterity modifier.
        dex_mod = self.calculate_modifier(self.abilities.get('dexterity', 10))
        
        # Add the Dex modifier to the base AC.
        return base_ac + dex_mod
    
    def get_effective_ac(self):
        """
        Returns the effective Armor Class (AC) by combining the base AC,
        the bonus from equipped armor, and the shield bonus.
        """
        base_ac = self.ac  # start with the character's base AC
        if self.equipment.get("armor"):
            base_ac += self.equipment["armor"].ac_bonus
        if self.equipment.get("shield"):
            base_ac += self.shield_ac_bonus  # shield_ac_bonus should be initialized
        return base_ac

    # ---- Added Method: calculate_modifier ----
    def calculate_modifier(self, ability):
        modifiers = {
            3: -2, 4: -2, 5: -2,
            6: -1, 7: -1, 8: -1,
            9: 0, 10: 0, 11: 0, 12: 0,
            13: 1, 14: 1, 15: 1,
            16: 2, 17: 2,
            18: 3, 19: 4, 20: 5
        }
        return modifiers.get(ability, 0)

    # === Character Leveling Mechanics Module ===
    def level_up(self):
        """Increase character level and update stats per design document."""
        self.level += 1

        hit_die = {'Warrior': 10, 'Priest': 8, 'Spellblade': 8, 'Archer': 6, 'Thief': 6, 'Wizard': 4}
        roll = random.randint(1, hit_die[self.char_class])
        while roll == 1:
            roll = random.randint(1, hit_die[self.char_class])
        
        # Calculate the Constitution bonus
        con_bonus = self.calculate_modifier(self.abilities.get('constitution', 10))
        
        # Add both the roll and the constitution bonus
        self.hit_points += roll + con_bonus
        self.max_hit_points += roll + con_bonus

        if self.char_class in ['Wizard', 'Priest']:
            self.spell_points += 1
        elif self.char_class == 'Spellblade':
            if self.level in [3, 6, 9, 12, 15, 18, 19, 20]:
                self.spell_points += 1

        if self.char_class == 'Warrior':
            self.ac = 1 + ((self.level - 1) // 2)
        elif self.char_class == 'Wizard':
            if self.level <= 4:
                self.ac = 0
            elif self.level <= 8:
                self.ac = 2
            elif self.level <= 12:
                self.ac = 3
            elif self.level <= 16:
                self.ac = 4
            else:
                self.ac = 5
        elif self.char_class == 'Archer':
            if self.level <= 3:
                self.ac = 0
            elif self.level <= 6:
                self.ac = 1
            elif self.level <= 9:
                self.ac = 2
            elif self.level <= 12:
                self.ac = 3
            elif self.level <= 15:
                self.ac = 4
            elif self.level <= 18:
                self.ac = 5
            else:
                self.ac = 5
        elif self.char_class == 'Priest':
            if self.level <= 3:
                self.ac = 0
            elif self.level <= 6:
                self.ac = 1
            elif self.level <= 9:
                self.ac = 2
            elif self.level <= 12:
                self.ac = 3
            elif self.level <= 15:
                self.ac = 4
            elif self.level <= 18:
                self.ac = 5
            else:
                self.ac = 6
        elif self.char_class == 'Spellblade':
            if self.level <= 4:
                self.ac = 0
            elif self.level <= 8:
                self.ac = 2
            elif self.level <= 12:
                self.ac = 3
            elif self.level <= 16:
                self.ac = 4
            else:
                self.ac = 5
        elif self.char_class == 'Thief':
            if self.level <= 3:
                self.ac = 1
            elif self.level <= 6:
                self.ac = 2
            elif self.level <= 9:
                self.ac = 3
            elif self.level <= 12:
                self.ac = 4
            elif self.level <= 15:
                self.ac = 5
            elif self.level <= 18:
                self.ac = 6
            else:
                self.ac = 7

        if self.char_class in ['Warrior', 'Wizard', 'Archer']:
            if self.level in [3, 6, 9, 12, 15, 18, 19, 20]:
                self.attack_bonus += 1
        elif self.char_class in ['Priest', 'Spellblade', 'Thief']:
            if self.level in [4, 8, 12, 16, 20]:
                self.attack_bonus += 1

        print(f"[Level Up] {self.name} reached level {self.level}! +HP: {roll}, Spell Points: {self.spell_points}, AC: {self.ac}, Attack Bonus: {self.attack_bonus}")

class Player(Character):
    def __init__(self, name, race, char_class, start_position, sprite, abilities=None):
        # Pass the abilities into the parent constructor.
        super().__init__(name, race, char_class, abilities)
        self.position = start_position
        self.sprite = sprite  # Dynamic sprite
        self.inventory = []
        self.equipment = {
            "weapon": None,
            "armor": None,
            "shield": None,
            "jewelry": []  # allow multiple rings/necklaces
        }
        self.gold = roll_dice_expression("4d6+200")

    def pickup_item(self, item):
        self.inventory.append(item)
        # Add message to the game's message log
        add_message(f"{self.name} picked up {item.name}!")

    def equip_item(self, item):
        # Remove from inventory if present
        if item in self.inventory:
            self.inventory.remove(item)
        # Depending on item type, equip into the proper slot
        if item.item_type.startswith("weapon"):
            # Unequip any existing weapon first.
            if self.equipment["weapon"]:
                self.equipment["weapon"].remove_effect(self)
            item.apply_effect(self)
        elif item.item_type.startswith("armor"):
            if self.equipment["armor"]:
                self.equipment["armor"].remove_effect(self)
            item.apply_effect(self)
        elif item.item_type == "shield":  # Added shield condition
            if self.equipment.get("shield"):
                self.equipment["shield"].remove_effect(self)
            item.apply_effect(self)
        elif item.item_type.startswith("jewelry"):
            item.apply_effect(self)
        # Update the UI or recalc effective stats if needed.
        print(f"{self.name} equipped {item.name}!")  
        
    def move(self, dx, dy, dungeon):
        new_x = self.position[0] + dx
        new_y = self.position[1] + dy
        tile_x = new_x // TILE_SIZE
        tile_y = new_y // TILE_SIZE
        
        # Check if the coordinates are in bounds
        if not (0 <= tile_x < dungeon.width and 0 <= tile_y < dungeon.height):
            return False, "You can't move through walls."
        
        target_tile = dungeon.tiles[tile_x][tile_y]
        
        # Check if it's a locked door
        if target_tile.type == 'locked_door':
            door_coords = (tile_x, tile_y)
            if door_coords in dungeon.doors:
                door = dungeon.doors[door_coords]
                if door.locked:
                    return False, "The door is locked. Try another approach."
            
        # Allow movement if the tile is a floor, corridor, or an open door
        if target_tile.type in ('floor', 'corridor', 'door'):
            self.position = [new_x, new_y]
            # Don't return a message for normal movement to reduce message spam
            return True, ""
        else:
            return False, "You can't move there."

    def attack(self, target):
        # Use effective values for the attack roll and damage
        effective_str_mod = self.calculate_modifier(self.get_effective_ability("strength"))
        attack_roll = roll_dice_expression("1d20") + effective_str_mod
        if attack_roll >= target.get_effective_ac():
            damage = self.get_effective_damage()
            target.hit_points -= damage
            return f"{self.name} hits {target.name} for {damage} damage!"
        else:
            return f"{self.name} misses {target.name}!"
    
    def get_effective_ability(self, stat):
        """
        Returns the effective value of an ability after summing equipment bonuses.
        This does NOT change the base ability stored in self.abilities.
        """
        base = self.abilities.get(stat, 0)
        bonus = 0
        # Iterate through jewelry items that affect this stat.
        for item in self.equipment.get('jewelry', []):
            if item.stat_bonus == stat:
                bonus += item.bonus_value
        return base + bonus

    def get_effective_ac(self):
        base_ac = self.ac
        # If armor is equipped, add its bonus.
        if self.equipment.get("armor"):
            base_ac += self.equipment["armor"].ac_bonus
        # If a shield is equipped, add its bonus.
        if self.equipment.get("shield"):
            base_ac += self.equipment["shield"].ac_bonus
        return base_ac

    def get_effective_damage(self):
        """
        Returns the damage value for an attack.
        If a weapon is equipped, use its damage formula (by calling its roll_damage method).
        Otherwise, return a default damage value.
        """
        if self.equipment.get("weapon"):
            # Let the weapon decide damage. The weapon's roll_damage method
            # can use the effective strength (or even other factors) via the caster parameter.
            return self.equipment["weapon"].roll_damage(self)
        else:
            # Default damage: a simple 1d2 plus effective strength modifier.
            return roll_dice_expression("1d2") + self.calculate_modifier(self.get_effective_ability("strength"))

class Monster:
    def __init__(self, name, hit_points, to_hit, ac, move, dam, sprites):
        self.name = name
        self.hit_points = hit_points
        self.to_hit = to_hit
        self.ac = ac
        self.move = move
        self.dam = dam
        self.sprites = sprites

        # Load and scale the live sprite for the monster
        self.sprite = pygame.image.load(self.sprites['live']).convert_alpha()
        self.sprite = pygame.transform.smoothscale(self.sprite, (TILE_SIZE, TILE_SIZE))

        # Set the position to None initially (will be set when placed in the dungeon)
        self.position = None

    def move_towards(self, target, dungeon, is_player=False):
        if self.position is None or target.position is None:
            print(f"{self.name} or target position is None. Cannot move.")
            return
    
        old_position = self.position.copy()
        monster_x, monster_y = self.position[0] // TILE_SIZE, self.position[1] // TILE_SIZE
        target_x, target_y = target.position[0] // TILE_SIZE, target.position[1] // TILE_SIZE
    
        # Calculate the differences in the x and y positions
        dx = target_x - monster_x
        dy = target_y - monster_y
    
        # Log the monster's movement direction (dx, dy)
        print(f"Monster '{self.name}' moving towards: dx={dx}, dy={dy}")
    
        # Try moving horizontally first, if it's not blocked
        if abs(dx) > abs(dy):
            step_x = 1 if dx > 0 else -1
            new_x = monster_x + step_x
            new_y = monster_y
    
            # Check if the tile is walkable (not blocked by walls)
            if 0 <= new_x < dungeon.width and 0 <= new_y < dungeon.height:
                target_tile = dungeon.tiles[new_x][new_y]
                if target_tile.type not in ('floor', 'corridor', 'door'):
                    print(f"Horizontal move blocked by {target_tile.type}. Trying vertical move.")
                    # Try vertical move instead
                    step_y = 1 if dy > 0 else -1
                    new_x = monster_x
                    new_y = monster_y + step_y
                else:
                    self.position = [new_x * TILE_SIZE + TILE_SIZE // 2, new_y * TILE_SIZE + TILE_SIZE // 2]
                    print(f"{self.name} moved from {old_position} to {self.position}")
            else:
                print(f"{self.name} cannot move horizontally: tile out of bounds.")
        
        # If horizontal move was blocked or diagonal is better, try vertical move
        else:
            step_y = 1 if dy > 0 else -1
            new_x = monster_x
            new_y = monster_y + step_y
    
            if 0 <= new_x < dungeon.width and 0 <= new_y < dungeon.height:
                target_tile = dungeon.tiles[new_x][new_y]
                if target_tile.type not in ('floor', 'corridor', 'door'):
                    print(f"Vertical move blocked by {target_tile.type}.")
                else:
                    self.position = [new_x * TILE_SIZE + TILE_SIZE // 2, new_y * TILE_SIZE + TILE_SIZE // 2]
                    print(f"{self.name} moved from {old_position} to {self.position}")
            else:
                print(f"{self.name} cannot move vertically: tile out of bounds.")

    def get_effective_ac(self):
        return self.ac

    def get_effective_damage(self):
        """Roll damage based on the dice expression from the JSON data (e.g., '1d3', '2d4+1', etc.)."""
        return roll_dice_expression(self.dam)

    def set_dead_sprite(self):
        """Load and scale the dead sprite when the monster dies."""
        self.sprite = pygame.image.load(self.sprites['dead']).convert_alpha()
        self.sprite = pygame.transform.smoothscale(self.sprite, (TILE_SIZE, TILE_SIZE))


class Dungeon:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.tiles = [[Tile(x, y, 'wall') for y in range(height)] for x in range(width)]
        self.monsters = []  # List to store spawned monsters
        self.dropped_items = []  # List for item drops
        self.doors = {}  # Dictionary to store door objects keyed by (x,y) coords
        self.chests = {}  # Dictionary to store chest objects keyed by (x,y) coords
        self.start_position = self.create_rooms_and_corridors()  # Now returns just the start position    

    def place_chest(self, room):
        """Place a treasure chest in a random position within the given room."""
        x, y, w, h = room
        
        # Handle small rooms - ensure there's a valid position
        if w <= 2:  # Room too narrow
            chest_x = x + w // 2  # Place in center of width
        else:
            chest_x = random.randint(x + 1, x + w - 2)  # Avoid edges
            
        if h <= 2:  # Room too short
            chest_y = y + h // 2  # Place in center of height
        else:
            chest_y = random.randint(y + 1, y + h - 2)  # Avoid edges
        
        # Create a new chest
        chest = Chest(chest_x, chest_y)
        
        # Store the chest in our dictionary
        self.chests[(chest_x, chest_y)] = chest
        
        print(f"Placed a treasure chest at ({chest_x}, {chest_y}) with {len(chest.contents)} items and {chest.gold} gold")
        
        return chest
        
    def create_rooms_and_corridors(self):
        # --- Grid Settings ---
        rows = random.randint(4, 6)  # Random number of rows between 4 and 6
        cols = random.randint(4, 6)  # Random number of columns between 4 and 6
        cell_width = self.width // cols
        cell_height = self.height // rows
        rooms = []
        
        margin = 1  # Number of tiles to leave as margin on each side
        for i in range(rows):
            for j in range(cols):
                # Top-left of the cell
                cell_x = j * cell_width
                cell_y = i * cell_height
                
                # Calculate the maximum room width and height available if we leave a margin on both sides
                max_room_w = cell_width - 2 * margin
                max_room_h = cell_height - 2 * margin
                
                # Ensure room width and height are at least 3x2, but no larger than the available space
                room_w = max(3, random.randint(min(max_room_w // 2, max_room_w), max_room_w))  # Random width
                room_h = max(2, random.randint(min(max_room_h // 2, max_room_h), max_room_h))  # Random height

                
                # Random position within the cell
                room_x = cell_x + random.randint(margin, max(margin, cell_width - room_w - margin))
                room_y = cell_y + random.randint(margin, max(margin, cell_height - room_h - margin))

                room = (room_x, room_y, room_w, room_h)
                rooms.append(room)
                
                # Carve the room out as 'floor'
                for rx in range(room_x, room_x + room_w):
                    for ry in range(room_y, room_y + room_h):
                        self.tiles[rx][ry].type = 'floor'
                        self.tiles[rx][ry].sprite = load_sprite(assets_data["sprites"]["tiles"]["floor"])
        
        # --- Connect Rooms with Corridors (carve complete paths) ---
        rooms.sort(key=lambda r: r[0] + r[2] // 2)  # Sort rooms by x-coordinate of the center
        for i in range(len(rooms) - 1):
            (x1, y1, w1, h1) = rooms[i]
            (x2, y2, w2, h2) = rooms[i + 1]
            center1 = (x1 + w1 // 2, y1 + h1 // 2)
            center2 = (x2 + w2 // 2, y2 + h2 // 2)
            
            if random.choice([True, False]):
                # Horizontal then vertical
                for x in range(min(center1[0], center2[0]), max(center1[0], center2[0]) + 1):
                    if self.tiles[x][center1[1]].type != 'floor':
                        self.tiles[x][center1[1]].type = 'corridor'
                        self.tiles[x][center1[1]].sprite = load_sprite(assets_data["sprites"]["tiles"]["floor"])
                for y in range(min(center1[1], center2[1]), max(center1[1], center2[1]) + 1):
                    if self.tiles[center2[0]][y].type != 'floor':
                        self.tiles[center2[0]][y].type = 'corridor'
                        self.tiles[center2[0]][y].sprite = load_sprite(assets_data["sprites"]["tiles"]["floor"])
            else:
                # Vertical then horizontal
                for y in range(min(center1[1], center2[1]), max(center1[1], center2[1]) + 1):
                    if self.tiles[center1[0]][y].type != 'floor':
                        self.tiles[center1[0]][y].type = 'corridor'
                        self.tiles[center1[0]][y].sprite = load_sprite(assets_data["sprites"]["tiles"]["floor"])
                for x in range(min(center1[0], center2[0]), max(center1[0], center2[0]) + 1):
                    if self.tiles[x][center2[1]].type != 'floor':
                        self.tiles[x][center2[1]].type = 'corridor'
                        self.tiles[x][center2[1]].sprite = load_sprite(assets_data["sprites"]["tiles"]["floor"])
        
        # After carving corridors, post-process to place doors
        self.carve_doors()
    
        # --- Set Start and Monster Positions ---
        start_room = rooms[0]
        start_tile_x = start_room[0] + (start_room[2] // 2)
        start_tile_y = start_room[1] + (start_room[3] // 2)
        start_position = [start_tile_x * TILE_SIZE + (TILE_SIZE // 2),
                          start_tile_y * TILE_SIZE + (TILE_SIZE // 2)]
    
        # --- Spawn a Monster ---
        if monsters_data and monsters_data.get('monsters'):
            monster_choice = random.choice(monsters_data['monsters'])
            monster = Monster(
                name=monster_choice['name'],
                hit_points=monster_choice['hit_points'],
                to_hit=monster_choice['to_hit'],
                ac=monster_choice['ac'],
                move=monster_choice['move'],
                dam=monster_choice['dam'],
                sprites=monster_choice['sprites']
            )
            
            # Place the monster in a random room
            monster_room = random.choice(rooms)
            monster_tile_x = monster_room[0] + (monster_room[2] // 2)
            monster_tile_y = monster_room[1] + (monster_room[3] // 2)
            monster.position = [monster_tile_x * TILE_SIZE + (TILE_SIZE // 2),
                                monster_tile_y * TILE_SIZE + (TILE_SIZE // 2)]
            
            # Add the monster to the dungeon's monster list
            self.monsters.append(monster)
            print(f"A wild {monster.name} appears in the dungeon!")
        else:
            print("No monster data available to spawn a monster.")
        
        # --- Place a Treasure Chest ---
        # Choose a random room, but not the starting room
        non_starting_rooms = [room for room in rooms if room != start_room]
        if non_starting_rooms:
            chest_room = random.choice(non_starting_rooms)
            self.place_chest(chest_room)
        else:
            # If there's only one room, place chest in a different part of it
            self.place_chest(start_room)
        
        return start_position


    def remove_monster(self, monster):
        """
        Remove the specified monster from the dungeon.
        Assumes that the monster is in the self.monsters list.
        """
        if monster in self.monsters:
            self.monsters.remove(monster)
            print(f"Monster {monster.name} has been removed from the dungeon.")
        else:
            print(f"Warning: Monster {monster.name} not found in the dungeon.")

    def draw_corridor(self, x1, y1, x2, y2):
        # (This method is not used in the grid-based method but kept for reference.)
        if x1 != x2 and y1 != y2:
            if random.choice([True, False]):
                for x in range(min(x1, x2), max(x1, x2) + 1):
                    self.tiles[x][y1].type = 'floor'
                for y in range(min(y1, y2), max(y1, y2) + 1):
                    self.tiles[x2][y].type = 'floor'
            else:
                for y in range(min(y1, y2), max(y1, y2) + 1):
                    self.tiles[x1][y].type = 'floor'
                for x in range(min(x1, x2), max(x1, x2) + 1):
                    self.tiles[x][y2].type = 'floor'
        elif x1 == x2:
            for y in range(min(y1, y2), max(y1, y2) + 1):
                self.tiles[x1][y].type = 'floor'
        else:
            for x in range(min(x1, x2), max(x1, x2) + 1):
                self.tiles[x][y1].type = 'floor'

    def find_start_position_in_room(self, room):
        x, y, w, h = room
        start_x = random.randint(x, x + w - 1)
        start_y = random.randint(y, y + h - 1)
        return [start_x * TILE_SIZE + TILE_SIZE // 2, start_y * TILE_SIZE + TILE_SIZE // 2]

    def find_random_position_in_room(self, room):
        x, y, w, h = room
        return (random.randint(x, x + w - 1), random.randint(y, y + h - 1))

    def draw(self, surface):
        # Draw the background
        pygame.draw.rect(surface, LIGHT_GRAY, (0, 0, self.width * TILE_SIZE, self.height * TILE_SIZE))
        
        # Draw grid lines (optional)
        for x in range(self.width + 1):
            pygame.draw.line(surface, BLACK, (x * TILE_SIZE, 0), (x * TILE_SIZE, self.height * TILE_SIZE), 1)
        for y in range(self.height + 1):
            pygame.draw.line(surface, BLACK, (0, y * TILE_SIZE), (self.width * TILE_SIZE, y * TILE_SIZE), 1)
        
        # Draw the tiles (blit floor tiles where applicable)
        for x in range(self.width):
            for y in range(self.height):
                # Handle regular tiles
                if self.tiles[x][y].type in ('floor', 'corridor') and self.tiles[x][y].sprite:
                    surface.blit(self.tiles[x][y].sprite, (x * TILE_SIZE, y * TILE_SIZE))
                elif self.tiles[x][y].type == 'wall':
                    pygame.draw.rect(surface, BLACK, (x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE))
                
                # Special handling for doors
                elif self.tiles[x][y].type in ('door', 'locked_door'):
                    # If it's a door object, use its sprite
                    door_coords = (x, y)
                    if door_coords in self.doors:
                        door_sprite = self.doors[door_coords].sprite
                        surface.blit(door_sprite, (x * TILE_SIZE, y * TILE_SIZE))
                        
                        # Draw a red highlight around locked doors
                        pygame.draw.rect(surface, (255, 0, 0), 
                                         (x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE), 4)
                    # Otherwise, use the tile's sprite
                    elif self.tiles[x][y].sprite:
                        surface.blit(self.tiles[x][y].sprite, (x * TILE_SIZE, y * TILE_SIZE))
        
        # Draw treasure chests
        for (x, y), chest in self.chests.items():
            if chest.sprite:
                surface.blit(chest.sprite, (x * TILE_SIZE, y * TILE_SIZE))
                
                # If chest is locked, add a visual indicator
                if chest.locked and not chest.open:
                    # Draw a gold border around locked chests
                    pygame.draw.rect(surface, (255, 215, 0), 
                                    (x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE), 2)
        
        # Now draw dropped items
        for drop in self.dropped_items:
            item_sprite = getattr(drop['item'], 'sprite', loot_drop_sprite)  
            x, y = drop['position']
        
            if item_sprite:
                # Draw the item sprite centered on its tile
                surface.blit(item_sprite, (x - TILE_SIZE // 2, y - TILE_SIZE // 2))
            else:
                # If no sprite, draw a fallback marker
                pygame.draw.circle(surface, RED, (x, y), 5)

                    
    def carve_doors(self):
        """
        Create doors where corridors meet rooms.
        About 30% of eligible corridor tiles become doors.
        About 70% of doors are locked.
        """
        door_coordinates = []
        
        # First, identify all corridor tiles that are adjacent to a room
        for x in range(self.width):
            for y in range(self.height):
                if self.tiles[x][y].type == 'corridor':
                    # Check the four neighbors: left, right, up, down.
                    neighbors = [(x-1, y), (x+1, y), (x, y-1), (x, y+1)]
                    for nx, ny in neighbors:
                        if 0 <= nx < self.width and 0 <= ny < self.height:
                            # If any neighbor is part of a room (i.e. type 'floor'), this is a potential door location
                            if self.tiles[nx][ny].type == 'floor':
                                door_coordinates.append((x, y))
                                break
        
        # Now convert some percentage of these coordinates to doors (all locked)
        for x, y in door_coordinates:
            if random.random() < DOOR_CHANCE:
                # Create the door object (always locked)
                new_door = Door(x, y, locked=True)
                
                # Add it to our doors dictionary
                self.doors[(x, y)] = new_door
                
                # Update the tile to be a locked door
                self.tiles[x][y].type = 'locked_door'
                
                # Use the door's sprite for rendering
                self.tiles[x][y].sprite = new_door.sprite
            else:
                # Make a normal passageway (use corridor type)
                self.tiles[x][y].type = 'corridor'
                self.tiles[x][y].sprite = load_sprite(assets_data["sprites"]["tiles"]["floor"])



# =============================================================================
# === Combat Module ===
# =============================================================================
# Handles both player and monster melee combat
def combat(player, monster, dungeon_instance):
    combat_messages = []
    
    # For the player:
    player_str_mod = player.calculate_modifier(player.get_effective_ability("strength"))
    # For the monster, use its to_hit stat.
    monster_str_mod = monster.to_hit

    # Initiative:
    player_initiative = roll_dice_expression("1d10") + player.calculate_modifier(player.get_effective_ability("dexterity"))
    monster_initiative = roll_dice_expression("1d10") + monster.to_hit

    if player_initiative > monster_initiative:
        attacker, defender = player, monster
        combat_messages.append(f"{player.name} goes first!")
    else:
        attacker, defender = monster, player
        combat_messages.append(f"{monster.name} goes first!")

    while player.hit_points > 0 and monster.hit_points > 0:
        if attacker == player:
            attack_roll = roll_dice_expression("1d20") + player.calculate_modifier(player.get_effective_ability("strength"))
        else:
            attack_roll = roll_dice_expression("1d20") + monster.to_hit

        if attack_roll >= defender.get_effective_ac():
            if attacker == player:
                damage = attacker.get_effective_damage()
            else:
                damage = monster.get_effective_damage()
            defender.hit_points -= damage
            combat_messages.append(f"{attacker.name} hits {defender.name} for {damage} damage!")
            # Play melee sound
            melee_sound.play()
        else:
            combat_messages.append(f"{attacker.name} misses {defender.name}!")
        attacker, defender = defender, attacker

    if player.hit_points <= 0:
        combat_messages.append("YOU have Died.")
        player.sprite = load_sprite(assets_data['sprites']['heroes']['warrior']['dead'])
    elif monster.hit_points <= 0:
        death_messages = process_monster_death(monster, player, dungeon_instance) or []  # ✅ Always a list
        for msg in death_messages:
            combat_messages.append(msg)

    return combat_messages


# =============================================================================
# === Character Creation & Selection Functions ===
# =============================================================================
def create_button(surface, text, color, x, y, width, height):
    button = pygame.Rect(x, y, width, height)
    pygame.draw.rect(surface, color, button)
    draw_text(surface, text, BLACK, x + 10, y + 10)
    return button

def roll_ability():
    roll = sum(random.randint(1, 6) for _ in range(3))
    while roll == 3:
        roll = sum(random.randint(1, 6) for _ in range(3))
    return roll

def select_race():
    races = ['High Elf', 'Wood Elf', 'Halfling', 'Dwarf', 'Human']
    selected_race = None
    race_selected = False
    race_label = font.render("Select Race:", True, WHITE)
    racial_bonuses = {
        'High Elf': '+1 Intelligence',
        'Wood Elf': '+1 Dexterity',
        'Halfling': '+1 Dexterity',
        'Dwarf': '+1 Constitution',
        'Human': '+1 Strength or +1 Wisdom by class'
    }
    while not race_selected:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                for i, race in enumerate(races):
                    button_rect = pygame.Rect(100, SCREEN_HEIGHT // 2 - 50 + i * 40, 200, 32)
                    if button_rect.collidepoint(event.pos):
                        selected_race = race
                        race_selected = True
        screen.fill(BLACK)
        screen.blit(race_label, (100, SCREEN_HEIGHT // 2 - 70))
        for i, race in enumerate(races):
            button_rect = pygame.Rect(100, SCREEN_HEIGHT // 2 - 50 + i * 40, 200, 32)
            pygame.draw.rect(screen, GREEN if not race_selected else LIGHT_GRAY, button_rect)
            draw_text(screen, race, BLACK, 100 + 10, SCREEN_HEIGHT // 2 - 50 + i * 40 + 10)
            bonus_text = font.render(racial_bonuses[race], True, WHITE)
            screen.blit(bonus_text, (320, SCREEN_HEIGHT // 2 - 50 + i * 40 + 10))
        pygame.display.flip()
        clock.tick(FPS)
    return selected_race

def select_class():
    classes = ['Warrior', 'Spellblade', 'Wizard', 'Priest', 'Thief', 'Archer']
    selected_class = None
    class_selected = False
    class_label = font.render("Select Class:", True, WHITE)
    while not class_selected:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                for i, char_class in enumerate(classes):
                    button_rect = pygame.Rect(100, SCREEN_HEIGHT // 2 - 50 + i * 40, 200, 32)
                    if button_rect.collidepoint(event.pos):
                        selected_class = char_class
                        class_selected = True
        screen.fill(BLACK)
        screen.blit(class_label, (100, SCREEN_HEIGHT // 2 - 70))
        for i, char_class in enumerate(classes):
            button_rect = pygame.Rect(100, SCREEN_HEIGHT // 2 - 50 + i * 40, 200, 32)
            pygame.draw.rect(screen, GREEN if not class_selected else LIGHT_GRAY, button_rect)
            draw_text(screen, char_class, BLACK, 100 + 10, SCREEN_HEIGHT // 2 - 50 + i * 40 + 10)
        pygame.display.flip()
        clock.tick(FPS)
    return selected_class

def character_creation(assets_data):
    name = ""
    name_active = False
    stats_accepted = False
    abilities = {}
    input_box = pygame.Rect(100, SCREEN_HEIGHT // 2 - 100, 200, 32)
    color_inactive = LIGHT_GRAY
    color_active = WHITE
    color = color_inactive
    name_label = font.render("Enter Character Name:", True, WHITE)
    stats_label = font.render("Generated Stats:", True, WHITE)
    generate_button = create_button(screen, "Generate Stats", GREEN, 100, SCREEN_HEIGHT // 2 - 50, 200, 32)
    accept_button = create_button(screen, "Accept Stats", BLUE, 100, SCREEN_HEIGHT // 2 + 20, 200, 32)
    while not stats_accepted:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if input_box.collidepoint(event.pos):
                    name_active = not name_active
                else:
                    name_active = False
                color = color_active if name_active else color_inactive
                if generate_button.collidepoint(event.pos):
                    abilities = {
                        'strength': roll_ability_helper(),
                        'intelligence': roll_ability_helper(),
                        'wisdom': roll_ability_helper(),
                        'dexterity': roll_ability_helper(),
                        'constitution': roll_ability_helper()
                    }
                    print("Generated Stats:", abilities)
                if accept_button.collidepoint(event.pos) and abilities:
                    stats_accepted = True
            elif event.type == pygame.KEYDOWN:
                if name_active:
                    if event.key == pygame.K_RETURN:
                        print("Name entered:", name)
                    elif event.key == pygame.K_BACKSPACE:
                        name = name[:-1]
                    else:
                        name += event.unicode
        screen.fill(BLACK)
        pygame.draw.rect(screen, color, input_box, 2)
        txt_surface = font.render(name, True, color)
        screen.blit(txt_surface, (input_box.x + 5, input_box.y + 5))
        input_box.w = max(200, txt_surface.get_width() + 10)
        screen.blit(name_label, (100, SCREEN_HEIGHT // 2 - 130))
        generate_button = create_button(screen, "Generate Stats", GREEN, 100, SCREEN_HEIGHT // 2 - 50, 200, 32)
        accept_button = create_button(screen, "Accept Stats", BLUE, 100, SCREEN_HEIGHT // 2 + 20, 200, 32)
        if abilities:
            screen.blit(stats_label, (100, SCREEN_HEIGHT // 2 + 70))
            draw_text(screen, f"Strength: {abilities['strength']}", WHITE, 100, SCREEN_HEIGHT // 2 + 90)
            draw_text(screen, f"Intelligence: {abilities['intelligence']}", WHITE, 100, SCREEN_HEIGHT // 2 + 110)
            draw_text(screen, f"Wisdom: {abilities['wisdom']}", WHITE, 100, SCREEN_HEIGHT // 2 + 130)
            draw_text(screen, f"Dexterity: {abilities['dexterity']}", WHITE, 100, SCREEN_HEIGHT // 2 + 150)
            draw_text(screen, f"Constitution: {abilities['constitution']}", WHITE, 100, SCREEN_HEIGHT // 2 + 170)
            screen.blit(dice_sprite, (20, SCREEN_HEIGHT // 2 - 50))
        pygame.display.flip()
        clock.tick(FPS)
    selected_class = select_class()
    selected_race = select_race()
    game_dungeon = Dungeon(20, 15)
    player = Player(name=name, race=selected_race, char_class=selected_class, 
                    start_position=game_dungeon.start_position, 
                    sprite=load_sprite(assets_data['sprites']['heroes'][selected_class.lower()]['live']))
    player.abilities = abilities
    player.apply_race_bonus()
    player.level = 1
    player.spell_points = player.calculate_spell_points()
    # player.hit_points = player.roll_hit_points()
    player.ac = player.calculate_ac()
    # print stat debug
    print_character_stats(player)
    screen.fill(BLACK)
    screen.blit(stats_label, (100, SCREEN_HEIGHT // 2 + 70))
    draw_text(screen, f"Strength: {player.abilities['strength']}", WHITE, 100, SCREEN_HEIGHT // 2 + 90)
    draw_text(screen, f"Intelligence: {player.abilities['intelligence']}", WHITE, 100, SCREEN_HEIGHT // 2 + 110)
    draw_text(screen, f"Wisdom: {player.abilities['wisdom']}", WHITE, 100, SCREEN_HEIGHT // 2 + 130)
    draw_text(screen, f"Dexterity: {player.abilities['dexterity']}", WHITE, 100, SCREEN_HEIGHT // 2 + 150)
    draw_text(screen, f"Constitution: {player.abilities['constitution']}", WHITE, 100, SCREEN_HEIGHT // 2 + 170)
    pygame.display.flip()
    pygame.time.wait(3000)
    return player, game_dungeon, name, selected_race, selected_class


# In[ ]:


# =============================================================================
# === Main Game Loop with Proper Monster Reaction ===
# =============================================================================
# Create character only once at the beginning
player, game_dungeon, name, selected_race, selected_class = character_creation(assets_data)

combat_occurred = False
# Set the common_b_s.in_dungeon to True since we're starting in dungeon mode
common_b_s.in_dungeon = True

# Initialize the message queue with simplified welcome and help hint
add_message("Welcome to Blade & Sigil! Use arrow keys to navigate.")
add_message("Press 'h' for Help to see all available commands.")

# Define the initial game state (e.g., starting in the hub)
game_state = "hub"

# Set a flag to track if player data has been initialized
player_initialized = True

running = True
while running:
    if game_state == "hub":
        # Temporarily set in_dungeon to False while in hub
        common_b_s.in_dungeon = False  # This makes sure the inventory and other functions know we're in the hub
        
        # Run the hub module via the novamagus_hub module.
        novamagus_hub.run_hub(screen, clock, player)
    
        # After the hub loop returns, check if the player has stepped on the dungeon entrance.
        if novamagus_hub.transition_to_dungeon:  
            # Transition: generate a new dungeon but preserve the player
            game_dungeon = Dungeon(20, 15)
            # Update player position to the dungeon start position
            player.position = game_dungeon.start_position
            # Update game state
            game_state = "dungeon"
            # Set in_dungeon to True when entering dungeon
            common_b_s.in_dungeon = True
            # --- Reset the transition flag ---
            novamagus_hub.transition_to_dungeon = False  
            print("DEBUG: Transition flag reset to False after entering dungeon.")
        else:
            # If not transitioning, simply continue the loop.
            continue
    
    # We're now in the dungeon - ensure in_dungeon is True
    if game_state == "dungeon":
        common_b_s.in_dungeon = True
    
    # Update and process the message queue
    update_message_queue()
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.USEREVENT + 1:
            levelup_sound.play()
            pygame.time.set_timer(pygame.USEREVENT + 1, 0)  # Disable timer after sound

        elif event.type == pygame.KEYDOWN:
            handle_scroll_events(event)

            moved = False  # Tracks if player took an action

            # === PLAYER MOVEMENT ===
            if event.key in [pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN]:
                dx, dy = 0, 0
                if event.key == pygame.K_LEFT:
                    dx = -TILE_SIZE
                elif event.key == pygame.K_RIGHT:
                    dx = TILE_SIZE
                elif event.key == pygame.K_UP:
                    dy = -TILE_SIZE
                elif event.key == pygame.K_DOWN:
                    dy = TILE_SIZE
                success, message = player.move(dx, dy, game_dungeon)
                if message and message.strip():  # Only add non-empty messages
                    add_message(message)
                moved = success

            # === INVENTORY ===
            elif event.key == pygame.K_i:
                # --- Debug: Print game state and in_dungeon before opening inventory ---
                print(f"DEBUG: game_state before opening inventory: {game_state}")
                print(f"DEBUG: in_dungeon before opening inventory: {common_b_s.in_dungeon}")
                
                # Force in_dungeon to be True when in dungeon game_state before opening inventory
                if game_state == "dungeon":
                    common_b_s.in_dungeon = True
                
                # Open inventory using the imported manage_inventory 
                manage_inventory(player, screen, clock)
                
                # --- Debug: Print game state and in_dungeon after closing inventory ---
                print(f"DEBUG: game_state after closing inventory: {game_state}")
                print(f"DEBUG: in_dungeon after closing inventory: {common_b_s.in_dungeon}")
                
                # Make sure in_dungeon is still True after inventory is closed
                if game_state == "dungeon":
                    common_b_s.in_dungeon = True
                
            # === PLAYER ATTACKS A MONSTER ===
            elif event.key == pygame.K_y and combat_occurred:
                combat_messages = combat(player, game_dungeon.monsters[0], game_dungeon)
                for msg in combat_messages:
                    add_message(msg)
                combat_occurred = False
                moved = True  # Mark that a turn action happened

            elif event.key == pygame.K_n and combat_occurred:
                combat_occurred = False
            
            # === HELP SYSTEM ===
            elif event.key == pygame.K_h:
                # Display popup help screen
                display_help_screen(screen, clock)
                
            # === DOOR INTERACTION KEYS ===
            elif event.key == pygame.K_o:  # 'o' to open/force a door
                # Check for adjacent doors
                player_tile_x = player.position[0] // TILE_SIZE
                player_tile_y = player.position[1] // TILE_SIZE
                
                # Check all adjacent tiles for doors
                adjacent_coords = [
                    (player_tile_x - 1, player_tile_y),
                    (player_tile_x + 1, player_tile_y),
                    (player_tile_x, player_tile_y - 1),
                    (player_tile_x, player_tile_y + 1)
                ]
                
                door_found = False
                for door_x, door_y in adjacent_coords:
                    if (0 <= door_x < game_dungeon.width and 0 <= door_y < game_dungeon.height and
                        game_dungeon.tiles[door_x][door_y].type in ('door', 'locked_door')):
                        door_coords = (door_x, door_y)
                        if door_coords in game_dungeon.doors:
                            door = game_dungeon.doors[door_coords]
                            success, message = door.try_force_open(player)
                            add_message(message)
                            if success:
                                # Update the tile if the door is now open
                                game_dungeon.tiles[door_x][door_y].type = 'door'
                                game_dungeon.tiles[door_x][door_y].sprite = door.sprite
                            door_found = True
                            moved = True
                            break
                
                if not door_found:
                    add_message("There is no door nearby to open.")
            
            elif event.key == pygame.K_p:  # 'p' to pick a lock (door or chest)
                # Check for adjacent locked doors or chests
                player_tile_x = player.position[0] // TILE_SIZE
                player_tile_y = player.position[1] // TILE_SIZE
                
                adjacent_coords = [
                    (player_tile_x - 1, player_tile_y),
                    (player_tile_x + 1, player_tile_y),
                    (player_tile_x, player_tile_y - 1),
                    (player_tile_x, player_tile_y + 1)
                ]
                
                # Check for locked doors first
                locked_door_found = False
                for door_x, door_y in adjacent_coords:
                    if (0 <= door_x < game_dungeon.width and 0 <= door_y < game_dungeon.height and
                        game_dungeon.tiles[door_x][door_y].type == 'locked_door'):
                        door_coords = (door_x, door_y)
                        if door_coords in game_dungeon.doors:
                            door = game_dungeon.doors[door_coords]
                            success, message = door.try_pick_lock(player)
                            add_message(message)
                            if success:
                                # Update the tile if the door is now open
                                game_dungeon.tiles[door_x][door_y].type = 'door'
                                game_dungeon.tiles[door_x][door_y].sprite = door.sprite
                            locked_door_found = True
                            moved = True
                            break
                
                # If no locked door, check for locked chests
                if not locked_door_found:
                    chest_found = False
                    for chest_x, chest_y in adjacent_coords:
                        if (chest_x, chest_y) in game_dungeon.chests:
                            chest = game_dungeon.chests[(chest_x, chest_y)]
                            if chest.locked and not chest.open:
                                success, message = chest.try_pick_lock(player)
                                add_message(message)
                                if success:
                                    add_message(f"The chest contains {len(chest.contents)} items and {chest.gold} gold!")
                                chest_found = True
                                moved = True
                                break
                    
                    if not chest_found and not locked_door_found:
                        add_message("There is nothing nearby to pick.")
                    
            elif event.key == pygame.K_u:  # 'u' to cast magic unlock (door or chest)
                # Check for adjacent locked doors or chests
                player_tile_x = player.position[0] // TILE_SIZE
                player_tile_y = player.position[1] // TILE_SIZE
                
                adjacent_coords = [
                    (player_tile_x - 1, player_tile_y),
                    (player_tile_x + 1, player_tile_y),
                    (player_tile_x, player_tile_y - 1),
                    (player_tile_x, player_tile_y + 1)
                ]
                
                # Check for locked doors first
                locked_door_found = False
                for door_x, door_y in adjacent_coords:
                    if (0 <= door_x < game_dungeon.width and 0 <= door_y < game_dungeon.height and
                        game_dungeon.tiles[door_x][door_y].type == 'locked_door'):
                        door_coords = (door_x, door_y)
                        if door_coords in game_dungeon.doors:
                            door = game_dungeon.doors[door_coords]
                            success, message = door.try_magic_unlock(player)
                            add_message(message)
                            if success:
                                # Update the tile if the door is now open
                                game_dungeon.tiles[door_x][door_y].type = 'door'
                                game_dungeon.tiles[door_x][door_y].sprite = door.sprite
                            locked_door_found = True
                            moved = True
                            break
                
                # If no locked door, check for locked chests
                if not locked_door_found:
                    chest_found = False
                    for chest_x, chest_y in adjacent_coords:
                        if (chest_x, chest_y) in game_dungeon.chests:
                            chest = game_dungeon.chests[(chest_x, chest_y)]
                            if chest.locked and not chest.open:
                                success, message = chest.try_magic_unlock(player)
                                add_message(message)
                                if success:
                                    add_message(f"The chest contains {len(chest.contents)} items and {chest.gold} gold!")
                                chest_found = True
                                moved = True
                                break
                    
                    if not chest_found and not locked_door_found:
                        add_message("There is nothing nearby to unlock with magic.")

            # === PLAYER CASTS A SPELL (NOW MONSTERS REACT!) ===
            elif event.key == pygame.K_x:
                selected_spell = spells_dialogue(screen, player, clock)
                if selected_spell is None:
                    continue
                elif selected_spell["name"] in ["Cure Light Wounds", "Light", "Mage Armor", "Wicked Weapon"]:
                    target = player
                else:
                    target = game_dungeon.monsters[0] if game_dungeon.monsters else None
                            
                if target and target.hit_points > 0:
                    spell_messages = cast_spell(player, target, selected_spell["name"], game_dungeon)
                    for msg in spell_messages:
                        add_message(msg)
                    moved = True  
            
                if moved:
                    for monster in game_dungeon.monsters:
                        if monster.hit_points > 0:
                            print(f"Processing {monster.name}'s turn.")
                            handle_monster_turn(monster, player, game_dungeon)

            # === PLAYER SHOOTS AN ARROW (ARCHER) ===
            elif event.key == pygame.K_a and player.char_class == "Archer":
                if game_dungeon.monsters and game_dungeon.monsters[0].hit_points > 0:
                    add_message(cast_spell(player, game_dungeon.monsters[0], "Arrow Shot", game_dungeon))
                    moved = True

            if moved:
                for monster in game_dungeon.monsters:
                    if monster.hit_points > 0:
                        logging.debug(f"Processing {monster.name}'s turn.")
                        handle_monster_turn(monster, player, game_dungeon)

    # === DRAW GAME STATE ===
    screen.fill(BLACK)
    draw_playable_area(screen, game_dungeon, player)

    # === HANDLE ITEM PICKUPS (Fixed) ===
    player_tile_x = player.position[0] // TILE_SIZE
    player_tile_y = player.position[1] // TILE_SIZE
    
    # Check for normal dropped items
    for drop in game_dungeon.dropped_items[:]:
        drop_tile_x = drop['position'][0] // TILE_SIZE
        drop_tile_y = drop['position'][1] // TILE_SIZE
        if player_tile_x == drop_tile_x and player_tile_y == drop_tile_y:
            # Use the pickup_item method which already adds the message
            player.pickup_item(drop['item'])
            game_dungeon.dropped_items.remove(drop)
    
    # Check for opened chests with loot
    chest_coords = (player_tile_x, player_tile_y)
    if chest_coords in game_dungeon.chests:
        chest = game_dungeon.chests[chest_coords]
        if chest.open and (len(chest.contents) > 0 or chest.gold > 0):
            # Add all chest contents to player's inventory
            if len(chest.contents) > 0:
                for item in chest.contents[:]:  # Create a copy of the list to safely iterate
                    player.pickup_item(item)
                    add_message(f"You picked up {item.name} from the chest!")
            
            # Add gold to player
            if chest.gold > 0:
                player.gold += chest.gold
                add_message(f"You found {chest.gold} gold in the chest!")
            
            # Clear chest contents
            chest.contents = []
            chest.gold = 0

    # === HANDLE MONSTER ATTACK PROMPT ===
    if game_dungeon.monsters and game_dungeon.monsters[0].hit_points > 0:
        monster_tile_x = game_dungeon.monsters[0].position[0] // TILE_SIZE
        monster_tile_y = game_dungeon.monsters[0].position[1] // TILE_SIZE
        if abs(player_tile_x - monster_tile_x) + abs(player_tile_y - monster_tile_y) == 1:
            draw_attack_prompt(screen, game_dungeon.monsters[0].name)
            combat_occurred = True

    # === DRAW UI PANELS ===
    draw_right_panel(
        screen,
        player,
        DUNGEON_PLAYABLE_AREA_WIDTH,
        DUNGEON_PLAYABLE_AREA_HEIGHT,
        DUNGEON_RIGHT_PANEL_WIDTH,
        offset_x=0
    )
    draw_bottom_panel(
        screen,
        DUNGEON_PLAYABLE_AREA_HEIGHT,
        DUNGEON_SCREEN_WIDTH,
        DUNGEON_BOTTOM_PANEL_HEIGHT,
        offset_y=0
    )
        
    if DEBUG_MODE:
        draw_debug_info(screen, player, game_dungeon)
    
    pygame.display.flip()

pygame.quit()
sys.exit()


# In[ ]:




