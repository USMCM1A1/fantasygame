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
from character_creation_ui import character_creation_screen # Import new character creation

# =============================================================================
# === Initialization & Constants Module ===
# =============================================================================
pygame.init()

# Define fonts to be used
# 'font' is imported from common_b_s.
# For small_font, needed by debug_system.draw_key_diagnostics:
small_font = pygame.font.SysFont('monospace', 16)

#sound mixer
pygame.mixer.init()

# Import from common_b_s
import common_b_s
import debug_system # Import the module itself
from test_arena import create_test_arena, create_emergency_arena, handle_test_arena_activation, handle_teleport_button_click # Import functions from test_arena.py
# Import condition system
from Data.condition_system import condition_manager, ConditionType

# Reset condition manager's turn counter at the start of the game
condition_manager.current_turn = 0

# Turn counter will increment whenever the player takes an action via the process_game_turn function

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
    handle_scroll_events, draw_attack_prompt, draw_equipment_panel, roll_ability_helper, roll_dice_expression,
    
    # Helper and utility functions
    add_message, update_message_queue, roll_dice_expression, roll_ability_helper,
    can_equip_item, handle_targeting, compute_fov, get_valid_equipment_slots,
    swap_equipment, unequip_item, get_clicked_equipment_slot, print_character_stats, 
    manage_inventory, display_help_screen, loot_drop_sprite,
    
    # Save/Load Game system
    save_game, load_game,
    
    # Base and derived item classes
    Item, Weapon, WeaponBlade, WeaponBlunt, Armor, Shield, Jewelry, Consumable,
    
    # Spell Casting
    bresenham, has_line_of_sight, spells_dialogue, cast_spell, 
 
    #Combat
    draw_attack_prompt, handle_monster_turn, process_monster_death,
    handle_scroll_events,
    
    # Game Classes
    Character, Tile, Door, Chest, Monster, Dungeon, # Added Monster, Dungeon
    
    # Debug console
    debug_console, MessageCategory, get_memory_usage,
) 

# Startup message
print("Blade & Sigil v5.5 starting up...")

# Add initial debug messages
add_message("Debug system initialized", (200, 200, 255), MessageCategory.DEBUG)
add_message("Press D to toggle debug console", (255, 255, 0), MessageCategory.DEBUG)

# Create spell effect images
import math
from common_b_s import create_fireball_image, create_frost_nova_image
fireball_path = create_fireball_image()
frost_nova_path = create_frost_nova_image()

import novamagus_hub  # Ensure the hub module is imported
SCREEN_HEIGHT = DUNGEON_SCREEN_HEIGHT
SCREEN_WIDTH = DUNGEON_SCREEN_WIDTH
TILE_SIZE = DUNGEON_TILE_SIZE
# Make sure to use the imported in_dungeon variable
in_dungeon = common_b_s.in_dungeon

screen = pygame.display.set_mode((DUNGEON_SCREEN_WIDTH, DUNGEON_SCREEN_HEIGHT))
pygame.display.set_caption("Blade & Sigil v5.5")
clock = pygame.time.Clock()
FPS = 60

# Debug logging setup is now in debug_system.py

# Key diagnostics globals DEBUG_MODE, KEY_DIAGNOSTIC_ENABLED, keys_pressed, key_state
# are now defined in debug_system.py

# Function to create a fireball explosion image
def create_fireball_image():
    """
    Creates a simple fireball explosion image and saves it to the disk
    """
    # Create a new surface with transparency
    size = 256
    img = pygame.Surface((size, size), pygame.SRCALPHA)
    
    # Define colors for the fireball
    colors = [
        (255, 255, 0, 255),   # Bright yellow
        (255, 200, 0, 225),   # Orange-yellow
        (255, 150, 0, 200),   # Orange
        (255, 100, 0, 150),   # Dark orange
        (255, 50, 0, 100),    # Red-orange
        (200, 0, 0, 50)       # Red edge (semi-transparent)
    ]
    
    # Draw concentric circles from outside in
    for i, color in enumerate(reversed(colors)):
        radius = size // 2 - (i * size // 12)
        pygame.draw.circle(img, color, (size // 2, size // 2), radius)
    
    # Add some small flames/sparks around the edge
    for _ in range(16):
        angle = random.random() * 2 * 3.14159  # Random angle
        distance = size // 2 - random.randint(0, size // 8)  # Random distance from center
        x = int(size // 2 + math.cos(angle) * distance)
        y = int(size // 2 + math.sin(angle) * distance)
        radius = random.randint(5, 15)  # Random spark size
        color = random.choice(colors[:3])  # Choose from bright colors
        pygame.draw.circle(img, color, (x, y), radius)
    
    # Save the image
    output_path = "/Users/williammarcellino/Documents/Fantasy_Game/Fantasy_Game_Art_Assets/Misc/spell_assets/fireball_explosion.png"
    pygame.image.save(img, output_path)
    print(f"Created fireball image at {output_path}")
    return output_path

# Function to create the emergency test arena has been moved to test_arena.py

# Function draw_debug_info is now in debug_system.py

# Function draw_key_diagnostics is now in debug_system.py

# In[3]:


# =============================================================================
# === Game Classes Module (including Character Leveling Mechanics) ===
# =============================================================================
# The Character, Monster, and Dungeon classes are now fully defined in common_b_s.py and imported from there

class Player(common_b_s.Character): # Player class remains here as it's specific to game loop logic
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
        # First check if the player can equip this item
        can_equip, reason = can_equip_item(self, item)
        if not can_equip:
            print(f"Cannot equip {item.name}: {reason}")
            add_message(f"Cannot equip {item.name}: {reason}", RED)
            return False
            
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
        elif item.item_type.startswith("shield"):  # Updated to use startswith to match standardized naming
            if self.equipment.get("shield"):
                self.equipment["shield"].remove_effect(self)
            item.apply_effect(self)
        elif item.item_type.startswith("jewelry"):
            # For jewelry items that have a can_equip method (like rings/amulets)
            if hasattr(item, 'can_equip') and not item.can_equip(self):
                print(f"Cannot equip {item.name}: Maximum number already equipped")
                add_message(f"Cannot equip {item.name}: Maximum number already equipped", RED)
                return False
            item.apply_effect(self)
            
        # Update the UI or recalc effective stats if needed.
        print(f"{self.name} equipped {item.name}!")
        add_message(f"{self.name} equipped {item.name}!", GREEN)
        return True
        
    def move(self, dx, dy, dungeon):
        new_x = self.position[0] + dx
        new_y = self.position[1] + dy
        tile_x = new_x // TILE_SIZE
        tile_y = new_y // TILE_SIZE
        
        # Check if the coordinates are in bounds
        if not (0 <= tile_x < dungeon.width and 0 <= tile_y < dungeon.height):
            return False, "", "You can't move through walls."
        
        target_tile = dungeon.tiles[tile_x][tile_y]
        
        # Check if it's a locked door
        if target_tile.type == 'locked_door':
            door_coords = (tile_x, tile_y)
            if door_coords in dungeon.doors:
                door = dungeon.doors[door_coords]
                if door.locked:
                    return False, "", "The door is locked. Try another approach."
            
        # Allow movement if the tile is a floor, corridor, or an open door
        if target_tile.type in ('floor', 'corridor', 'door'):
            # Check if this is a door
            door_coords = (tile_x, tile_y)
            
            # Check if this is a door and if it's a transition door
            if target_tile.type == 'door' and door_coords in dungeon.doors:
                door = dungeon.doors[door_coords]
                
                # Update player position to enter the door tile
                self.position = [new_x, new_y]
                
                # Handle special door types
                if door.door_type == "level_transition":
                    # When transitioning to a new dungeon level, level up the player
                    # Set player level equal to new dungeon level
                    new_dungeon_level = dungeon.level + 1
                    if self.level < new_dungeon_level:
                        self.level = new_dungeon_level
                        # Increase hit points - give more per level depending on class
                        hp_per_level = 8  # Default
                        if hasattr(self, 'char_class'):
                            if self.char_class == 'Warrior':
                                hp_per_level = 10
                            elif self.char_class == 'Priest':
                                hp_per_level = 6
                            elif self.char_class == 'Wizard':
                                hp_per_level = 4
                        
                        # Increase max hit points and current hit points
                        self.max_hit_points += hp_per_level
                        self.hit_points += hp_per_level
                        
                        # Play level up sound on next frame
                        pygame.event.post(pygame.event.Event(pygame.USEREVENT + 1))
                        
                        return True, "level_transition", f"You found stairs leading deeper into the dungeon! You've completed level {dungeon.level}. You leveled up to level {self.level}!"
                    
                    return True, "level_transition", "You found stairs leading deeper into the dungeon! Congratulations, you've completed this level."
                    
                elif door.door_type == "map_transition":
                    # Return a tuple with transition info for the main game loop to handle
                    return True, "map_transition", door.destination_map, f"You found a passage to another area! (Map {door.destination_map})"
                else:
                    # For regular doors, just move through them
                    return True, "", "You pass through the door."
            else:
                # Normal movement to non-door tiles
                self.position = [new_x, new_y]
                return True, "", ""
        else:
            return False, "", "You can't move there."

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
        # Iterate through jewelry items that affect this stat
        for item in self.equipment.get('jewelry', []):
            # Handle both bonus_stat and stat_bonus attributes for backward compatibility
            item_stat = None
            
            if hasattr(item, 'bonus_stat'):
                item_stat = item.bonus_stat
            elif hasattr(item, 'stat_bonus'):
                item_stat = item.stat_bonus
                
            # If we found a matching stat and the item has a bonus value
            if item_stat == stat and hasattr(item, 'bonus_value'):
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
            
    def add_experience(self, xp_amount):
        """
        Add experience points to the player but do NOT trigger level ups automatically.
        In v5.5, level ups only happen when reaching new dungeon depths.
        
        Args:
            xp_amount: The amount of XP to add
            
        Returns:
            bool: True if player has enough XP for next level, False otherwise
        """
        # Initialize experience attribute if it doesn't exist
        if not hasattr(self, 'experience'):
            self.experience = 0
            
        # Initialize level thresholds if they don't exist
        if not hasattr(self, 'level_thresholds'):
            # Simple XP thresholds - each level requires base_xp * level^2
            base_xp = 1000
            self.level_thresholds = [0]  # Level 0 (not used)
            for level in range(1, 21):  # Levels 1-20
                self.level_thresholds.append(base_xp * level * level)
        
        # Add XP
        self.experience += xp_amount
        
        # Check if player has enough XP for next level, but don't level up automatically
        # This is just for information purposes
        has_enough_xp = False
        if self.level < 20 and self.experience >= self.level_thresholds[self.level + 1]:
            has_enough_xp = True
            
        return has_enough_xp

class Monster:
    def __init__(self, name, hit_points, to_hit, ac, move, dam, sprites, **kwargs):
        self.name = name
        self.hit_points = hit_points
        self.max_hit_points = hit_points  # Store max HP for reference
        self.to_hit = to_hit
        self.ac = ac
        self.move = move
        self.dam = dam
        self.sprites = sprites
        
        # Optional parameters with defaults
        self.monster_type = kwargs.get('monster_type', 'beast')
        self.level = kwargs.get('level', 1)
        self.cr = kwargs.get('cr', 1)
        self.vulnerabilities = kwargs.get('vulnerabilities', [])
        self.resistances = kwargs.get('resistances', [])
        self.immunities = kwargs.get('immunities', [])
        self.special_abilities = kwargs.get('special_abilities', [])
        self.is_dead = False
        self.active_effects = []  # For status effects
        self.can_move = True
        self.can_act = True
        
        # Load and scale the live sprite for the monster
        try:
            if self.sprites and self.sprites.get('live') and os.path.exists(self.sprites['live']):
                self.sprite = pygame.image.load(self.sprites['live']).convert_alpha()
                self.sprite = pygame.transform.smoothscale(self.sprite, (TILE_SIZE, TILE_SIZE))
            else:
                # Use a predefined fallback sprite based on monster type
                fallback_sprites = {
                    'beast': '/Users/williammarcellino/Documents/Fantasy_Game/Fantasy_Game_Art_Assets/Enemies/beast/giant_rat.jpg',
                    'humanoid': '/Users/williammarcellino/Documents/Fantasy_Game/Fantasy_Game_Art_Assets/Enemies/humanoids/goblin.png',
                    'undead': '/Users/williammarcellino/Documents/Fantasy_Game/Fantasy_Game_Art_Assets/Enemies/undead/skel_01.png',
                    'elemental': '/Users/williammarcellino/Documents/Fantasy_Game/Fantasy_Game_Art_Assets/Enemies/elemental/fire_elemental.jpg',
                    'extraplanar': '/Users/williammarcellino/Documents/Fantasy_Game/Fantasy_Game_Art_Assets/Enemies/extraplanar/imp.jpg',
                    'monstrosity': '/Users/williammarcellino/Documents/Fantasy_Game/Fantasy_Game_Art_Assets/Enemies/monstrosity/green_slime.jpg'
                }
                
                fallback_path = fallback_sprites.get(self.monster_type, fallback_sprites['beast'])
                self.sprite = pygame.image.load(fallback_path).convert_alpha()
                self.sprite = pygame.transform.smoothscale(self.sprite, (TILE_SIZE, TILE_SIZE))
        except (pygame.error, FileNotFoundError) as e:
            print(f"Error loading sprite for {self.name}: {e}")
            # Create a placeholder sprite if image loading fails
            self.sprite = pygame.Surface((TILE_SIZE, TILE_SIZE))
            self.sprite.fill((255, 0, 0))  # Red for monsters

        # Set the position to None initially (will be set when placed in the dungeon)
        self.position = None

    def move_towards(self, target, dungeon, is_player=False):
        if self.position is None or target.position is None:
            print(f"{self.name} or target position is None. Cannot move.")
            return

        if not self.can_move:
            print(f"Monster {self.name} cannot move because self.can_move is False.")
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
        # Check if a dead sprite exists
        if 'dead' in self.sprites and self.sprites['dead']:
            try:
                self.sprite = pygame.image.load(self.sprites['dead']).convert_alpha()
                self.sprite = pygame.transform.smoothscale(self.sprite, (TILE_SIZE, TILE_SIZE))
            except (pygame.error, FileNotFoundError):
                # If loading fails, just tint the current sprite to indicate death
                self._tint_sprite_gray()
        else:
            # If no dead sprite, just tint the current sprite
            self._tint_sprite_gray()
            
    def _tint_sprite_gray(self):
        """Create a more visually appealing grayscale effect for dead monsters"""
        if self.sprite:
            # More efficient grayscale method using pygame's surface manipulation
            temp_sprite = self.sprite.copy()
            
            # Apply a dark gray overlay with transparency
            gray_overlay = pygame.Surface(temp_sprite.get_size(), pygame.SRCALPHA)
            gray_overlay.fill((30, 30, 30, 180))  # Dark gray with transparency
            temp_sprite.blit(gray_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            
            # Add a slight red tint to indicate "fallen" status
            red_tint = pygame.Surface(temp_sprite.get_size(), pygame.SRCALPHA)
            red_tint.fill((100, 0, 0, 50))  # Red tint with transparency
            temp_sprite.blit(red_tint, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            
            # Reduce the overall brightness
            dark_overlay = pygame.Surface(temp_sprite.get_size(), pygame.SRCALPHA)
            dark_overlay.fill((0, 0, 0, 50))  # Black with transparency
            temp_sprite.blit(dark_overlay, (0, 0))
            
            self.sprite = temp_sprite
    
    def apply_damage(self, damage_amount, damage_type="physical"):
        """
        Apply damage to the monster with vulnerability/resistance/immunity calculation
        Returns the actual damage dealt after modifiers
        """
        # Check for immunities
        if damage_type in self.immunities:
            return 0  # No damage taken
            
        # Check for vulnerabilities (double damage)
        if damage_type in self.vulnerabilities:
            damage_amount *= 2
            
        # Check for resistances (half damage)
        if damage_type in self.resistances:
            damage_amount = max(1, damage_amount // 2)  # At least 1 damage
            
        # Apply the damage
        self.hit_points -= damage_amount
        
        # Ensure hit points don't go below 0
        self.hit_points = max(0, self.hit_points)
        
        # Check if monster died
        if self.hit_points == 0:
            self.is_dead = True
            
        return damage_amount

# Dungeon and Monster class definitions are removed from here. They are now in common_b_s.py

# =============================================================================
# === Combat Module ===
# =============================================================================
# Helper function for turn processing
def process_game_turn(player, dungeon):
    """
    Process one game turn after any player action (movement, combat, spells).
    Advances the condition manager turn counter and processes all active conditions.
    
    Args:
        player: The player character
        dungeon: The current dungeon instance
        
    Returns:
        None (messages are added directly to the message queue)
    """
    debug_system.logger.info(f"blade_sigil_v5_5.process_game_turn: Using condition_manager (id: {id(condition_manager)}) with current_turn: {condition_manager.current_turn}")
    # Process all active conditions on player and monsters
    condition_messages = condition_manager.process_turn([player] + dungeon.monsters)
    
    # Add messages to the game message queue
    for msg in condition_messages:
        add_message(msg)

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


# Removed Character Creation & Selection Functions as they are now in character_creation_ui.py

# In[ ]:


# =============================================================================
# === Title Screen with Load Game / New Character Options ===
# =============================================================================

# The create_test_arena function has been moved to test_arena.py

def show_title_screen():
    """Display the title screen with options to start a new game or load a saved game."""
    # Initialize screen for title
    title_screen = pygame.display.set_mode((DUNGEON_SCREEN_WIDTH, DUNGEON_SCREEN_HEIGHT))
    pygame.display.set_caption("Blade & Sigil")
    
    # Load the title screen image
    try:
        title_image = pygame.image.load("/Users/williammarcellino/Documents/Fantasy_Game/Fantasy_Game_Art_Assets/Misc/b&s_loading_screen.jpg")
        title_image = pygame.transform.scale(title_image, (DUNGEON_SCREEN_WIDTH, DUNGEON_SCREEN_HEIGHT))
    except pygame.error:
        # Fallback if image can't be loaded
        title_image = pygame.Surface((DUNGEON_SCREEN_WIDTH, DUNGEON_SCREEN_HEIGHT))
        title_image.fill((0, 0, 0))  # Black background
        title_text = font.render("BLADE & SIGIL", True, WHITE)
        title_rect = title_text.get_rect(center=(DUNGEON_SCREEN_WIDTH//2, DUNGEON_SCREEN_HEIGHT//3))
        title_image.blit(title_text, title_rect)
    
    # Create buttons
    button_width = 200
    button_height = 50
    button_margin = 20
    
    # Button positions
    new_game_rect = pygame.Rect(
        (DUNGEON_SCREEN_WIDTH - button_width) // 2,
        DUNGEON_SCREEN_HEIGHT * 2 // 3,
        button_width,
        button_height
    )
    
    load_game_rect = pygame.Rect(
        (DUNGEON_SCREEN_WIDTH - button_width) // 2,
        DUNGEON_SCREEN_HEIGHT * 2 // 3 + button_height + button_margin,
        button_width,
        button_height
    )
    
    # Colors
    button_color = (100, 100, 100)
    hover_color = (150, 150, 150)
    text_color = WHITE
    
    # Check if a save game exists
    has_save = os.path.exists(os.path.join("B&S_savegame", "savefile.json"))
    
    running = True
    while running:
        # Reset screen and draw title image
        title_screen.blit(title_image, (0, 0))
        
        # Get mouse position
        mouse_pos = pygame.mouse.get_pos()
        
        # Draw new game button
        new_game_color = hover_color if new_game_rect.collidepoint(mouse_pos) else button_color
        pygame.draw.rect(title_screen, new_game_color, new_game_rect)
        new_game_text = font.render("New Game", True, text_color)
        new_game_text_rect = new_game_text.get_rect(center=new_game_rect.center)
        title_screen.blit(new_game_text, new_game_text_rect)
        
        # Draw load game button (grayed out if no save exists)
        load_game_color = (50, 50, 50) if not has_save else (hover_color if load_game_rect.collidepoint(mouse_pos) else button_color)
        pygame.draw.rect(title_screen, load_game_color, load_game_rect)
        load_game_text = font.render("Load Game", True, (100, 100, 100) if not has_save else text_color)
        load_game_text_rect = load_game_text.get_rect(center=load_game_rect.center)
        title_screen.blit(load_game_text, load_game_text_rect)
        
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if new_game_rect.collidepoint(mouse_pos):
                    return "new_game"
                elif load_game_rect.collidepoint(mouse_pos) and has_save:
                    return "load_game"
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_n:
                    return "new_game"
                elif event.key == pygame.K_l and has_save:
                    return "load_game"
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
        
        # Display version and instructions
        version_text = font.render("v0.5.5", True, WHITE)
        title_screen.blit(version_text, (20, DUNGEON_SCREEN_HEIGHT - 30))
        
        help_text = font.render("Press N for New Game, L to Load Game, ESC to Quit", True, WHITE)
        help_rect = help_text.get_rect(center=(DUNGEON_SCREEN_WIDTH//2, DUNGEON_SCREEN_HEIGHT - 30))
        title_screen.blit(help_text, help_rect)
        
        pygame.display.flip()

# === Main Game Loop with Proper Monster Reaction ===
# =============================================================================

# Show title screen and get user choice
title_choice = show_title_screen()

if title_choice == "load_game":
    # Load a saved game
    print("Loading saved game...")
    loaded_data = load_game()
    
    if loaded_data:
        print("Found saved game - loading it")
        player, dungeon_data, game_state, saved_cm_turn = loaded_data # Unpack the four values
        common_b_s.in_dungeon = (game_state == "dungeon")
        
        # Player object is created/returned by load_game.
        # Dungeon object is reconstructed from dungeon_data dictionary after this.
        # (Code for dungeon reconstruction follows...)

        # >>> Add these lines <<<
        from Data.condition_system import condition_manager
        condition_manager.current_turn = saved_cm_turn
        # >>> End of added lines <<<
        
        # Check if dungeon_data is a dictionary (new format) or a Dungeon instance (old format)
        if isinstance(dungeon_data, dict):
            print("Constructing dungeon from saved data")
            # Create a new dungeon with the saved dimensions
            game_dungeon = Dungeon(dungeon_data.get("width", 20), dungeon_data.get("height", 15))
            
            # Load tiles
            if dungeon_data.get("tiles"):
                for x, row in enumerate(dungeon_data["tiles"]):
                    if x < game_dungeon.width:
                        for y, tile_data in enumerate(row):
                            if y < game_dungeon.height:
                                tile_type = tile_data.get("type", "wall")
                                game_dungeon.tiles[x][y].type = tile_type
                                game_dungeon.tiles[x][y].discovered = tile_data.get("discovered", False)
                                
                                # Make sure the tile gets the proper sprite based on its type
                                if tile_type in ('floor', 'corridor'):
                                    game_dungeon.tiles[x][y].sprite = load_sprite(assets_data["sprites"]["tiles"]["floor"])
                                elif tile_type == 'stair_up':
                                    game_dungeon.tiles[x][y].sprite = load_sprite(assets_data["sprites"]["tiles"]["stair_up"])
                                elif tile_type == 'stair_down':
                                    game_dungeon.tiles[x][y].sprite = load_sprite(assets_data["sprites"]["tiles"]["stair_down"])
            
            # Load doors
            if dungeon_data.get("doors"):
                for door_data in dungeon_data["doors"]:
                    x = door_data.get("x", 0)
                    y = door_data.get("y", 0)
                    if x < game_dungeon.width and y < game_dungeon.height:
                        is_locked = door_data.get("is_locked", False)
                        door = Door(x, y, is_locked)
                        game_dungeon.doors[(x, y)] = door
            
            # Load chests
            if dungeon_data.get("chests"):
                for chest_data in dungeon_data["chests"]:
                    x = chest_data.get("x", 0)
                    y = chest_data.get("y", 0)
                    if x < game_dungeon.width and y < game_dungeon.height:
                        chest = Chest(x, y)
                        chest.is_locked = chest_data.get("is_locked", False)
                        chest.is_trapped = chest_data.get("is_trapped", False)
                        chest.difficulty = chest_data.get("difficulty", 10)
                        chest.is_open = chest_data.get("is_open", False)
                        chest.gold = chest_data.get("gold", 0)
                        
                        # Load chest items
                        if chest_data.get("items"):
                            for item_name in chest_data["items"]:
                                item = create_item(item_name)
                                if item:
                                    chest.items.append(item)
                        
                        game_dungeon.chests[(x, y)] = chest
            
            # Load monsters
            game_dungeon.monsters = []
            if dungeon_data.get("monsters"):
                for monster_data in dungeon_data["monsters"]:
                    name = monster_data.get("name", "Unknown")
                    x = monster_data.get("x", 0)
                    y = monster_data.get("y", 0)
                    
                    # Create monster by name
                    monster = None
                    for m_data in monsters_data:
                        if m_data.get("name") == name:
                            # Create a monster using the constructor format from the Monster class
                            monster = Monster(
                                name=m_data.get("name", "Unknown"),
                                hit_points=m_data.get("hit_points", 10),
                                to_hit=m_data.get("to_hit", 0),
                                ac=m_data.get("ac", 10),
                                move=m_data.get("move", 1),
                                dam=m_data.get("dam", "1d4"),
                                sprites=m_data.get("sprites", {"live": None, "dead": None}),
                                monster_type=m_data.get("monster_type", "beast"),
                                level=m_data.get("level", 1),
                                cr=m_data.get("cr", 1)
                            )
                            # Set monster position
                            monster.position = (x, y)
                            break
                    
                    if monster and x < game_dungeon.width and y < game_dungeon.height:
                        # Update monster stats from saved data
                        monster.hit_points = monster_data.get("hit_points", monster.hit_points)
                        monster.max_hit_points = monster_data.get("max_hit_points", monster.max_hit_points)
                        # Only set these attributes if the monster has them
                        if hasattr(monster, "experience"):
                            monster.experience = monster_data.get("experience", getattr(monster, "experience", 0))
                        if hasattr(monster, "gold"):
                            monster.gold = monster_data.get("gold", getattr(monster, "gold", 0))
                        monster.items = []
                        
                        # Load monster items
                        if monster_data.get("items"):
                            for item_name in monster_data["items"]:
                                item = create_item(item_name)
                                if item:
                                    monster.items.append(item)
                        
                        game_dungeon.monsters.append(monster)
            
            # Load dropped items
            game_dungeon.dropped_items = []
            if dungeon_data.get("dropped_items"):
                for item_data in dungeon_data["dropped_items"]:
                    item = create_item(item_data)
                    if item:
                        position = item_data.get("position", [0, 0])
                        game_dungeon.dropped_items.append({
                            "item": item,
                            "position": position
                        })
        else:
            # Old format where dungeon_data is already a Dungeon instance
            game_dungeon = dungeon_data
        
        # Use the saved player
        player_initialized = True
        add_message(f"Welcome back, {player.name}! Your game has been loaded. CM Turn: {condition_manager.current_turn}", category=MessageCategory.SYSTEM)
    else:
        # Fallback if load fails
        print("Failed to load saved game - creating new character. Transitioning to new character creation screen...")
        # Call the new character creation screen
        player_common, game_dungeon_common = character_creation_screen(screen, clock) # Renamed to avoid confusion
        if player_common is None or game_dungeon_common is None:
            print("Character creation was cancelled during fallback. Exiting.")
            pygame.quit()
            sys.exit()
        else:
            # Convert common_b_s.Player to blade_sigil_v5_5.Player
            class_lower = player_common.char_class.lower()
            sprite_path = assets_data["sprites"]["heroes"][class_lower]["live"]
            player_sprite = load_sprite(sprite_path)

            game_player = Player( # This is blade_sigil_v5_5.Player
                name=player_common.name,
                race=player_common.race,
                char_class=player_common.char_class,
                start_position=game_dungeon_common.start_position,
                sprite=player_sprite,
                abilities=player_common.abilities
            )
            if hasattr(player_common, 'gold'): # Preserve gold from character creation
                game_player.gold = player_common.gold

            player = game_player # Reassign player to the game-specific instance

            game_state = "hub"  # Start in the hub for new characters
            common_b_s.in_dungeon = False  # Not in dungeon at start
            add_message(f"Welcome, {player.name}! Your journey begins in the hub.")
            add_message("Press 'h' for Help to see all available commands.")
            player_initialized = True
else:  # New Game
    print("Creating new character via character_creation_screen...")
    # Call the new character creation screen
    player_common, game_dungeon_common = character_creation_screen(screen, clock) # Renamed

    if player_common is None or game_dungeon_common is None:
        print("Character creation was cancelled. Exiting.")
        pygame.quit()
        sys.exit()
    else:
        # Convert common_b_s.Player to blade_sigil_v5_5.Player
        class_lower = player_common.char_class.lower()
        sprite_path = assets_data["sprites"]["heroes"][class_lower]["live"]
        player_sprite = load_sprite(sprite_path)

        game_player = Player( # This is blade_sigil_v5_5.Player
            name=player_common.name,
            race=player_common.race,
            char_class=player_common.char_class,
            start_position=game_dungeon_common.start_position,
            sprite=player_sprite,
            abilities=player_common.abilities
        )
        if hasattr(player_common, 'gold'): # Preserve gold from character creation
            game_player.gold = player_common.gold

        player = game_player # Reassign player to the game-specific instance
        game_dungeon = game_dungeon_common # Use the dungeon returned

        # Player and dungeon were created, proceed with game setup
        game_state = "hub"  # Start in the hub for new characters
        common_b_s.in_dungeon = False
        add_message(f"Welcome, {player.name}! Your journey begins in the hub.")
        add_message("Press 'h' for Help to see all available commands.")
        player_initialized = True # Ensure this flag is set

combat_occurred = False

# If no game state was defined yet, default to hub
if 'game_state' not in locals() or not game_state:
    game_state = "hub"

# Set a flag to track if player data has been initialized
player_initialized = True

running = True
last_debug_update = 0  # For tracking periodic debug messages

# Add debug messages to the debug console instead of printing
add_message(f"Starting main game loop with state: {game_state}, in_dungeon: {common_b_s.in_dungeon}", (150, 255, 150), MessageCategory.DEBUG)
add_message(f"Player spell points: {player.spell_points}", (150, 255, 150), MessageCategory.DEBUG)
print(f"DEBUG: T key handler is enabled")

current_event_for_activation = None # Will be set in the event loop

while running:
    key_states = pygame.key.get_pressed()

    # Update key state dictionary for diagnostics display (can be simplified later if only used by moved logic)
    debug_system.key_state["F1"] = key_states[pygame.K_F1]
    debug_system.key_state["F2"] = key_states[pygame.K_F2]
    debug_system.key_state["T"] = key_states[pygame.K_t]
    debug_system.key_state["1"] = key_states[pygame.K_1]
    debug_system.key_state["Enter"] = key_states[pygame.K_RETURN]
    debug_system.key_state["Shift"] = key_states[pygame.K_LSHIFT] or key_states[pygame.K_RSHIFT]
    debug_system.key_state["X"] = key_states[pygame.K_x]

    # Call test arena activation handler (key-based)
    # Pass current_event_for_activation which is updated in the event loop
    activated_dungeon, new_game_state, new_in_dungeon = handle_test_arena_activation(
        current_event_for_activation, key_states, player, screen, game_dungeon, game_state
    )
    if activated_dungeon:
        game_dungeon = activated_dungeon
        game_state = new_game_state
        common_b_s.in_dungeon = new_in_dungeon
        # Potentially skip rest of the loop iteration or reset current_event_for_activation
        current_event_for_activation = None # Consume the event if it triggered activation

    if game_state == "hub":
        # Temporarily set in_dungeon to False while in hub
        common_b_s.in_dungeon = False  # This makes sure the inventory and other functions know we're in the hub
        
        # Run the hub module via the novamagus_hub module.
        novamagus_hub.run_hub(screen, clock, player)
    
        # After the hub loop returns, check if the player has stepped on the dungeon entrance.
        print(f"DEBUG: After hub loop, checking transition_to_dungeon flag: {novamagus_hub.transition_to_dungeon}")
        if novamagus_hub.transition_to_dungeon:  
            print("DEBUG: transition_to_dungeon is True - preparing to generate dungeon...")
            
            try:
                # Transition: generate a new dungeon but preserve the player
                print("DEBUG: Creating new Dungeon(20, 15)...")
                game_dungeon = Dungeon(20, 15)
                
                # Update player position to the dungeon start position
                print(f"DEBUG: Setting player position to dungeon start: {game_dungeon.start_position}")
                player.position = game_dungeon.start_position
                
                # TEST ONLY: Give player 1000 HP for testing purposes
                player.hit_points = 1000
                player.max_hit_points = 1000
                add_message("TEST MODE: Player has 1000 HP for indestructible testing!")
                print(f"TEST MODE: Player HP set to {player.hit_points}/{player.max_hit_points}")
                
                # Update game state
                print("DEBUG: Changing game_state from 'hub' to 'dungeon'")
                game_state = "dungeon"
                
                # Set in_dungeon to True when entering dungeon
                print(f"DEBUG: Setting common_b_s.in_dungeon = True (current: {common_b_s.in_dungeon})")
                common_b_s.in_dungeon = True
                
                # --- Reset the transition flag ---
                print("DEBUG: Resetting transition_to_dungeon flag to False")
                novamagus_hub.transition_to_dungeon = False  
                print("DEBUG: Transition to dungeon complete!")
            except Exception as e:
                # If there's an error during dungeon generation, log it
                print(f"ERROR: Exception during dungeon transition: {e}")
                import traceback
                traceback.print_exc()
        else:
            # If not transitioning, simply continue the loop.
            continue
    
    # We're now in the dungeon - ensure in_dungeon is True
    if game_state == "dungeon":
        common_b_s.in_dungeon = True
    
    # Update and process the message queue
    update_message_queue()
    
    current_event_for_activation = None # Reset before event loop
    for event in pygame.event.get():
        current_event_for_activation = event # Store current event for handle_test_arena_activation

        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            # Handle teleport button click
            activated_dungeon_btn, new_game_state_btn, new_in_dungeon_btn = handle_teleport_button_click(
                event.pos, player, game_dungeon, screen
            )
            if activated_dungeon_btn:
                game_dungeon = activated_dungeon_btn
                game_state = new_game_state_btn
                common_b_s.in_dungeon = new_in_dungeon_btn
                # current_event_for_activation = None # Consume event
                continue # Skip other MOUSEBUTTONDOWN processing if teleported

            # ... (other MOUSEBUTTONDOWN logic, if any, can go here)

        elif event.type == pygame.USEREVENT + 1:
            levelup_sound.play()
            pygame.time.set_timer(pygame.USEREVENT + 1, 0)  # Disable timer after sound
            
        # Removed timer-based condition processing

        elif event.type == pygame.KEYDOWN:
            # Key-based test arena activation is now handled by handle_test_arena_activation at the start of the loop
            # However, some specific key down events (like T for test arena message, D for debug) might still be here
            # or moved entirely if they are part of the activation logic.

            key_name = pygame.key.name(event.key)
            debug_system.test_arena_logger.debug(f"Key pressed: {key_name}")
            
            debug_system.keys_pressed.append(key_name)
            if len(debug_system.keys_pressed) > 10: 
                debug_system.keys_pressed.pop(0)
                
            if event.key == pygame.K_d:
                debug_console.toggle()
                add_message("Debug console toggled", WHITE, MessageCategory.DEBUG)
                
            if debug_console.visible:
                if debug_console.handle_scroll(event):
                    # current_event_for_activation = None # Consume event
                    continue
            
            # The T key press for "Loading Test Arena..." message logic was part of the activation
            # and is now inside handle_test_arena_activation if that specific message is still desired
            # For simple key presses like 't' that are not combos, direct key_states check is often enough
            # but if it's tied to a specific message display upon PRESS, it might be here.
            # For now, assuming the main activation handles the T key messages.
            # if key_name == 't' and not (key_states[pygame.K_LSHIFT] or key_states[pygame.K_RSHIFT] or key_states[pygame.K_RETURN]):
            #    # This is a standalone T press, not part of a combo handled by activation function
            #    debug_system.test_arena_logger.info("Standalone T KEY DETECTED (outside combos)!")
            #    # (Decide if any action needed for standalone T press, or if it's fully covered)


            handle_scroll_events(event)
            moved = False

            # Player movement and other actions
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
                
                # Debug player position and target tile before moving
                player_tile_x = player.position[0] // TILE_SIZE
                player_tile_y = player.position[1] // TILE_SIZE
                target_tile_x = (player.position[0] + dx) // TILE_SIZE
                target_tile_y = (player.position[1] + dy) // TILE_SIZE
                
                # Check what's at the target position
                if 0 <= target_tile_x < game_dungeon.width and 0 <= target_tile_y < game_dungeon.height:
                    target_tile = game_dungeon.tiles[target_tile_x][target_tile_y]
                    
                    # Check if it's a door
                    target_coords = (target_tile_x, target_tile_y)
                    if target_coords in game_dungeon.doors:
                        door = game_dungeon.doors[target_coords]
                
                # Use the updated move method which returns more information
                move_result = player.move(dx, dy, game_dungeon)
                
                # Unpack the results based on the number of values
                if len(move_result) == 3:
                    success, transition_type, message = move_result
                    destination_map = None
                elif len(move_result) == 4:
                    success, transition_type, destination_map, message = move_result
                else:
                    success, transition_type, message = move_result[0], "", move_result[1]
                    destination_map = None
                    
                # Process a game turn when player successfully moves
                if success:
                    process_game_turn(player, game_dungeon)
                
                # Calculate player tile position
                player_tile_x = player.position[0] // TILE_SIZE
                player_tile_y = player.position[1] // TILE_SIZE
                
                # Failsafe: check if player tile matches any door locations
                for coords, door in game_dungeon.doors.items():
                    if (player_tile_x, player_tile_y) == coords:
                        # Force transition for map door
                        if door.door_type == "map_transition" and hasattr(door, "destination_map"):
                            transition_type = "map_transition"
                            destination_map = door.destination_map
                            message = f"You found a passage to another area! (Map {door.destination_map})"
                
                # Handle map transition doors
                if success and transition_type == "map_transition" and destination_map is not None:
                    # Roll for number of maps on this level
                    maps_on_level = max(1, random.randint(1, 6) - 1)  # 0-5 maps plus starting map
                    
                    # Create the new dungeon map
                    new_dungeon = Dungeon(
                        game_dungeon.width,
                        game_dungeon.height,
                        level=game_dungeon.level,
                        map_number=destination_map,
                        max_maps=maps_on_level
                    )
                    
                    # Update the dungeon
                    game_dungeon = new_dungeon
                    
                    # Update player position
                    player.position = game_dungeon.start_position.copy()
                    
                    # Update message
                    add_message(f"You enter a new area of the dungeon! (Map {destination_map} of Level {game_dungeon.level})")
                    add_message(f"There are {maps_on_level} areas to explore on this level.")
                    
                # Handle level transition doors
                elif success and transition_type == "level_transition":
                    # Roll 1d6 to determine if difficulty increases
                    difficulty_roll = random.randint(1, 6)
                    
                    # Track current dungeon level for display purposes
                    if not hasattr(player, 'dungeon_depth'):
                        player.dungeon_depth = 1
                    
                    # Determine if difficulty increases (only on roll of 1)
                    if difficulty_roll == 1:
                        # Increase the actual difficulty level
                        new_level = game_dungeon.level + 1
                        # Increase the displayed dungeon depth
                        player.dungeon_depth += 1
                        
                        # Roll for number of maps on this level (higher levels have more maps)
                        maps_on_next_level = max(1, random.randint(1, 6) - 1 + min(3, new_level // 2))
                        
                        # Roll for difficulty increases
                        max_rooms_modifier = random.randint(0, 2)  # 0-2 more rooms per level
                        size_modifier = random.randint(0, 1)  # 0-1 larger room size per level
                        
                        # Force a level up instead of just adding XP
                        # This guarantees a level up when reaching a new dungeon level
                        current_level = player.level
                        player.level_up()  # Directly call level_up method
                        
                        # Play level up sound
                        levelup_sound.play()
                        
                        # Success message for new level and level up
                        add_message(f"You made it to level {player.dungeon_depth}!")
                        add_message(f"The challenge empowers you! You advance to character level {player.level}!")
                    else:
                        # Continue at same difficulty level
                        new_level = game_dungeon.level
                        
                        # Roll for number of maps (same level, no bonus)
                        maps_on_next_level = max(1, random.randint(1, 6) - 1)
                        
                        # No difficulty increases
                        max_rooms_modifier = 0
                        size_modifier = 0
                        
                        # No XP for a level that's the same difficulty
                        
                        # Message for continuing at same difficulty
                        add_message(f"You continue to explore this level!")
                    
                    # Create the new dungeon section
                    game_dungeon = Dungeon(
                        game_dungeon.width, 
                        game_dungeon.height,
                        level=new_level,
                        max_rooms=game_dungeon.max_rooms + max_rooms_modifier,
                        min_room_size=game_dungeon.min_room_size,
                        max_room_size=game_dungeon.max_room_size + size_modifier,
                        map_number=1,  # Start with map 1 on the new section
                        max_maps=maps_on_next_level
                    )
                    
                    # Place the player at the start position of the new dungeon section
                    player.position = game_dungeon.start_position.copy()
                    
                    # Common message about the new area
                    add_message(f"There are {maps_on_next_level} areas to explore in this section.")
                    
                # Handle regular movement messages
                elif message and message.strip():  # Only add non-empty messages for regular moves
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
                # Pass the dungeon instance for turn processing
                manage_inventory(player, screen, clock, game_dungeon)
                
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
                
                # Process a game turn after combat
                process_game_turn(player, game_dungeon)

            elif event.key == pygame.K_n and combat_occurred:
                combat_occurred = False
            
            # === HELP SYSTEM ===
            elif event.key == pygame.K_h:
                # Display popup help screen
                display_help_screen(screen, clock)
            
            # === SAVE/LOAD SYSTEM ===
            elif event.key == pygame.K_F5:
                # Save game
                add_message("Saving game...")
                try:
                    if save_game(player, game_dungeon, game_state):
                        add_message("Game saved successfully!")
                    else:
                        add_message("Failed to save game - unknown error!")
                except Exception as e:
                    add_message(f"Error saving game: {str(e)}")
                    print(f"Error saving game: {e}")
                    
            elif event.key == pygame.K_F9:
                # Load game
                add_message("Loading game...")
                try:
                    loaded_data = load_game()
                    if loaded_data:
                        loaded_player, loaded_dungeon, loaded_game_state = loaded_data
                        player = loaded_player
                        game_dungeon = loaded_dungeon
                        game_state = loaded_game_state
                        common_b_s.in_dungeon = (game_state == "dungeon")
                        
                        # Explicitly show debug to know where we are
                        print(f"DEBUG: Loaded game with state: {game_state}, in_dungeon: {common_b_s.in_dungeon}")
                except Exception as e:
                    add_message(f"Error loading game: {str(e)}")
                    print(f"Error loading game: {e}")
                    
            # Test arena activation for 'T' key (non-combo) is handled by the main activation function if desired
            # The old specific block for K_t is removed as its logic is merged into handle_test_arena_activation.
            
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
                                
                                # Check if this is a transition door
                                if door.door_type == "level_transition":
                                    # Player is moving to the next dungeon level
                                    add_message("You found stairs leading deeper into the dungeon!")
                                    add_message("Congratulations! You've completed this level.")
                                    # For now, we'll just display this message
                                    # In a future version, we'd generate a new dungeon level here
                                    
                                elif door.door_type == "map_transition":
                                    # Player is moving to another map on the same level
                                    target_map = door.destination_map
                                    add_message(f"You found a passage to another area! (Map {target_map})")
                                    
                                    # Roll to see how many maps are on the next level
                                    maps_on_next_level = max(1, random.randint(1, 6) - 1)  # 0-5 plus starting map (1d6-1, min 1)
                                    
                                    # Create a new dungeon with the same dimensions
                                    new_dungeon = Dungeon(
                                        game_dungeon.width,
                                        game_dungeon.height,
                                        level=game_dungeon.level,
                                        map_number=target_map,
                                        max_maps=maps_on_next_level
                                    )
                                    
                                    # Update the current dungeon to the new one
                                    game_dungeon = new_dungeon
                                    
                                    # Reset player position to the start position of the new dungeon
                                    player.position = game_dungeon.start_position.copy()
                                    
                                    # Add a message indicating what map they're on
                                    add_message(f"You are now on Map {target_map} of Level {game_dungeon.level}")
                                    add_message(f"There are {maps_on_next_level} areas on this level.")
                            
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
                                
                                # Check if this is a transition door
                                if door.door_type == "level_transition":
                                    # Player is moving to the next dungeon level
                                    add_message("You found stairs leading deeper into the dungeon!")
                                    add_message("Congratulations! You've completed this level.")
                                    # For now, we'll just display this message
                                    # In a future version, we'd generate a new dungeon level here
                                    
                                elif door.door_type == "map_transition":
                                    # Player is moving to another map on the same level
                                    target_map = door.destination_map
                                    add_message(f"You found a passage to another area! (Map {target_map})")
                                    
                                    # Roll to see how many maps are on the next level
                                    maps_on_next_level = max(1, random.randint(1, 6) - 1)  # 0-5 plus starting map (1d6-1, min 1)
                                    
                                    # Create a new dungeon with the same dimensions
                                    new_dungeon = Dungeon(
                                        game_dungeon.width,
                                        game_dungeon.height,
                                        level=game_dungeon.level,
                                        map_number=target_map,
                                        max_maps=maps_on_next_level
                                    )
                                    
                                    # Update the current dungeon to the new one
                                    game_dungeon = new_dungeon
                                    
                                    # Reset player position to the start position of the new dungeon
                                    player.position = game_dungeon.start_position.copy()
                                    
                                    # Add a message indicating what map they're on
                                    add_message(f"You are now on Map {target_map} of Level {game_dungeon.level}")
                                    add_message(f"There are {maps_on_next_level} areas on this level.")
                                
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
                                
                                # Check if this is a transition door
                                if door.door_type == "level_transition":
                                    # Player is moving to the next dungeon level
                                    add_message("You found stairs leading deeper into the dungeon!")
                                    add_message("Congratulations! You've completed this level.")
                                    # For now, we'll just display this message
                                    # In a future version, we'd generate a new dungeon level here
                                    
                                elif door.door_type == "map_transition":
                                    # Player is moving to another map on the same level
                                    target_map = door.destination_map
                                    add_message(f"You found a passage to another area! (Map {target_map})")
                                    
                                    # Roll to see how many maps are on the next level
                                    maps_on_next_level = max(1, random.randint(1, 6) - 1)  # 0-5 plus starting map (1d6-1, min 1)
                                    
                                    # Create a new dungeon with the same dimensions
                                    new_dungeon = Dungeon(
                                        game_dungeon.width,
                                        game_dungeon.height,
                                        level=game_dungeon.level,
                                        map_number=target_map,
                                        max_maps=maps_on_next_level
                                    )
                                    
                                    # Update the current dungeon to the new one
                                    game_dungeon = new_dungeon
                                    
                                    # Reset player position to the start position of the new dungeon
                                    player.position = game_dungeon.start_position.copy()
                                    
                                    # Add a message indicating what map they're on
                                    add_message(f"You are now on Map {target_map} of Level {game_dungeon.level}")
                                    add_message(f"There are {maps_on_next_level} areas on this level.")
                                
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
                # Use the enhanced spell dialog from spell_bridge if available
                try:
                    print("DEBUG: Attempting to import update_spells_dialogue...")
                    from Data.spell_bridge import update_spells_dialogue # Use absolute package import
                    print("DEBUG: Imported update_spells_dialogue successfully")
                    
                    # Call the enhanced UI function
                    selected_spell = update_spells_dialogue(screen, player, clock)
                except Exception as e:
                    # Fall back to the original implementation
                    print(f"DEBUG: Error using enhanced UI: {e}")
                    # Ensure spells_dialogue is available if update_spells_dialogue fails
                    # This might require an import for spells_dialogue from common_b_s if not already global
                    # For now, assuming spells_dialogue from common_b_s is accessible
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
                    
                    # Process a game turn after casting a spell
                    process_game_turn(player, game_dungeon)
            
                if moved:
                    # We now process conditions in process_game_turn() after specific player actions
                    # So we don't need to process them here
                        
                    # Process monster turns
                    for monster in game_dungeon.monsters:
                        if monster.hit_points > 0 or getattr(monster, 'pending_death_from_dot', False):
                            # Check if monster is poisoned before calling handle_monster_turn
                            is_poisoned = False
                            if hasattr(monster, 'conditions') and monster.conditions:
                                for cond in monster.conditions:
                                    if cond.condition_type == ConditionType.POISONED:
                                        is_poisoned = True
                                        break
                            if is_poisoned:
                                debug_system.logger.debug(f"Monster {monster.name} is POISONED. Starting its turn. Calling handle_monster_turn.")
                            
                            debug_system.logger.debug(f"Main loop: Processing turn for {monster.name} (HP: {monster.hit_points}, Pending DoT Death: {getattr(monster, 'pending_death_from_dot', False)}). Calling handle_monster_turn.")
                            # REMOVED NESTED IF: Monster gets its turn if outer condition is met.
                            # handle_monster_turn itself should check if the monster can act (e.g. if HP > 0, not stunned, etc.)
                            handle_monster_turn(monster, player, game_dungeon)

                            if getattr(monster, 'pending_death_from_dot', False) and monster.hit_points <= 0:
                                death_messages = process_monster_death(monster, player, game_dungeon)
                                if death_messages: 
                                    for msg in death_messages:
                                        add_message(msg)
                                
                                if hasattr(monster, 'pending_death_from_dot'):
                                    delattr(monster, 'pending_death_from_dot')
                                # Monster is now fully processed for death, might be removed from game_dungeon.monsters

            # === PLAYER SHOOTS AN ARROW (ARCHER) ===
            elif event.key == pygame.K_a and player.char_class == "Archer":
                if game_dungeon.monsters and game_dungeon.monsters[0].hit_points > 0:
                    spell_messages = cast_spell(player, game_dungeon.monsters[0], "Arrow Shot", game_dungeon)
                    for msg in spell_messages:
                        add_message(msg)
                    moved = True
                    
                    # Process a game turn after using the archer ability
                    process_game_turn(player, game_dungeon)

            if moved:
                # We now process conditions in process_game_turn() after specific player actions
                # So we don't need to process them again here
                    
                # Process monster turns
                for monster in game_dungeon.monsters: # Iterate over a copy if process_monster_death modifies the list
                    if monster.hit_points > 0 or getattr(monster, 'pending_death_from_dot', False):
                        # Check if monster is poisoned before calling handle_monster_turn
                        is_poisoned = False
                        if hasattr(monster, 'conditions') and monster.conditions:
                            for cond in monster.conditions:
                                if cond.condition_type == ConditionType.POISONED:
                                    is_poisoned = True
                                    break
                        if is_poisoned:
                            debug_system.logger.debug(f"Monster {monster.name} is POISONED. Starting its turn (after player action). Calling handle_monster_turn.")
                        
                        debug_system.logger.debug(f"Main loop: Processing turn for {monster.name} (HP: {monster.hit_points}, Pending DoT Death: {getattr(monster, 'pending_death_from_dot', False)}) after player action. Calling handle_monster_turn.")
                        # REMOVED NESTED IF: Monster gets its turn if outer condition is met.
                        # handle_monster_turn itself should check if the monster can act (e.g. if HP > 0, not stunned, etc.)
                        handle_monster_turn(monster, player, game_dungeon)
                        
                        if getattr(monster, 'pending_death_from_dot', False) and monster.hit_points <= 0:
                            death_messages = process_monster_death(monster, player, game_dungeon)
                            if death_messages:
                                for msg in death_messages:
                                    add_message(msg)
                            
                            if hasattr(monster, 'pending_death_from_dot'):
                                delattr(monster, 'pending_death_from_dot')
                            # Monster is now fully processed for death

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
            
    # === DRAW TELEPORT TO ARENA BUTTON (more subtle) ===
    teleport_button = pygame.Rect(DUNGEON_SCREEN_WIDTH - 150, 10, 140, 30)
    pygame.draw.rect(screen, (100, 100, 200), teleport_button)
    pygame.draw.rect(screen, (200, 200, 255), teleport_button, 2)
    draw_text(screen, "Teleport to Arena", BLACK, DUNGEON_SCREEN_WIDTH - 145, 15)

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
        
    if debug_system.DEBUG_MODE: # Use debug_system.DEBUG_MODE
        # Call the function from debug_system module
        # Arguments: screen, player, dungeon, font
        debug_system.draw_debug_info(screen, player, game_dungeon, font)
    
    # Draw the key diagnostics overlay
    # Call the function from debug_system module
    # Arguments: screen, font, small_font, DUNGEON_SCREEN_WIDTH
    debug_system.draw_key_diagnostics(screen, font, small_font, DUNGEON_SCREEN_WIDTH)
    
    # Just draw a subtle hint at the bottom
    draw_text(screen, "Press F1 for Test Arena", WHITE, 
              DUNGEON_SCREEN_WIDTH - 200, DUNGEON_SCREEN_HEIGHT - 20)
    
    # Periodically add debug information to the debug console
    current_time = pygame.time.get_ticks()
    if current_time - last_debug_update > 5000:  # Every 5 seconds
        if debug_console.visible:
            # Add performance and state information
            fps = clock.get_fps()
            memory_info = get_memory_usage()
            add_message(f"FPS: {fps:.1f}, {memory_info}", (150, 150, 255), MessageCategory.DEBUG)
            
            # Add game state information
            if player and hasattr(player, 'health') and hasattr(player, 'max_health'):
                add_message(f"Player: HP {player.health}/{player.max_health}, SP {player.spell_points}/{player.max_spell_points}", 
                          (200, 255, 200), MessageCategory.DEBUG)
                
            # Add entity counts if in dungeon
            if game_state == "dungeon" and game_dungeon and hasattr(game_dungeon, 'monsters'):
                monster_count = len(game_dungeon.monsters) if hasattr(game_dungeon, 'monsters') else 0
                # Check if items attribute exists before trying to access it
                item_count = len(game_dungeon.items) if hasattr(game_dungeon, 'items') else 0
                chest_count = len(game_dungeon.chests) if hasattr(game_dungeon, 'chests') else 0
                add_message(f"Entities: {monster_count} monsters, {chest_count} chests", 
                          (200, 200, 255), MessageCategory.DEBUG)
        
        last_debug_update = current_time
    
    # Draw debug console if visible
    debug_console.draw(screen)
    
    pygame.display.flip()

pygame.quit()
sys.exit()


# In[ ]:




