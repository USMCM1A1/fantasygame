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
# import import_ipynb # Removed as it's for Jupyter notebook environments
from novamagus_hub import run_hub
from character_creation_ui import character_creation_screen # Import new character creation
from game_loop import run_game_loop # Import the new game loop

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

# Pygame font init
pygame.font.init() # Ensure font system is initialized
small_font = pygame.font.SysFont('monospace', 16)

# Import necessary constants from common_b_s for debug console initialization
# Note: common_b_s itself imports from game_config, so these are ultimately from game_config.
# This import must happen before initialize_debug_console
from common_b_s import DUNGEON_SCREEN_WIDTH, DUNGEON_SCREEN_HEIGHT

# Initialize debug console
debug_system.initialize_debug_console(font=small_font, screen_width=DUNGEON_SCREEN_WIDTH, screen_height=DUNGEON_SCREEN_HEIGHT)

# Import game constants directly from game_config
from game_config import (
    DUNGEON_FPS, TILE_SIZE, # Use TILE_SIZE instead of DUNGEON_TILE_SIZE
    DUNGEON_RIGHT_PANEL_WIDTH, DUNGEON_BOTTOM_PANEL_HEIGHT, DUNGEON_PLAYABLE_AREA_WIDTH, DUNGEON_PLAYABLE_AREA_HEIGHT,
    RIGHT_PANEL_OFFSET, BOTTOM_PANEL_OFFSET,
    DOOR_CHANCE, LOCKED_DOOR_CHANCE, DOOR_DIFFICULTY, 
    CHEST_DIFFICULTY, CHEST_ITEMS_COUNT, CHEST_GOLD_DICE,
    WHITE, BLACK, LIGHT_GRAY, RED, GREEN, BLUE # Colors
    # font object is initialized in common_b_s, so import it from there
)

from common_b_s import (
    # Dungeon-specific configurations
    # DUNGEON_SCREEN_WIDTH, DUNGEON_SCREEN_HEIGHT, # Already imported above
    # DUNGEON_FPS, DUNGEON_TILE_SIZE, # Moved to game_config
    # DUNGEON_RIGHT_PANEL_WIDTH, DUNGEON_BOTTOM_PANEL_HEIGHT, DUNGEON_PLAYABLE_AREA_WIDTH, DUNGEON_PLAYABLE_AREA_HEIGHT, # Moved
    # RIGHT_PANEL_OFFSET, BOTTOM_PANEL_OFFSET, # Moved

    # Door and Chest configuration
    # DOOR_CHANCE, LOCKED_DOOR_CHANCE, DOOR_DIFFICULTY, # Moved
    # CHEST_DIFFICULTY, CHEST_ITEMS_COUNT, CHEST_GOLD_DICE, # Moved
    
    # Colors and Font
    # WHITE, BLACK, LIGHT_GRAY, RED, GREEN, BLUE, # Moved to game_config
    font, # Font object is initialized in common_b_s
    
    # Asset loading and JSON utilities
    load_sprite, load_json, assets_data, characters_data, spells_data, items_data, monsters_data, dice_sprite,
    spell_sound, melee_sound, arrow_sound, levelup_sound,
    
    # UI Drawing functions (if used in dungeon mode)
    draw_text, draw_panel, draw_text_lines, draw_playable_area, draw_right_panel, draw_bottom_panel,
    draw_equipment_panel,
    
    # Helper and utility functions
    add_message,
    loot_drop_sprite,
    
    # Base and derived item classes (still needed by create_item, manage_inventory)
    Item, Weapon, WeaponBlade, WeaponBlunt, Armor, Shield, Jewelry, Consumable,
    
    # Spell Casting (spells_dialogue, cast_spell are now in game_loop. bresenham, has_line_of_sight might be too)
    # Keeping bresenham, has_line_of_sight for now if any other utility uses them.
    bresenham, has_line_of_sight, # spells_dialogue, cast_spell removed
 
    #Combat (These are now handled by game_loop)
    # draw_attack_prompt, handle_monster_turn, process_monster_death,
    # handle_scroll_events, # This was for the message log in the loop
    
    # Game Classes (Character, Tile, Door, Chest, Monster, Dungeon are fundamental)
    Character, Tile, Door, Chest, Monster, Dungeon,
    
    # Debug console
    debug_console, MessageCategory,
)
from game_utils import roll_ability_helper, get_memory_usage, print_character_stats # Import from game_utils
from game_logic_utils import (
    can_equip_item, handle_targeting, compute_fov, get_valid_equipment_slots,
    swap_equipment, unequip_item, get_clicked_equipment_slot,
    manage_inventory, display_help_screen
)
from player import Player # Player imported from player.py

# Startup message
print("Blade & Sigil v5.5 starting up...")

# Add initial debug messages
# These calls will use the debug_console instance which is now initialized with a font.
add_message("Debug system initialized", (200, 200, 255), MessageCategory.DEBUG)
add_message("Press D to toggle debug console", (255, 255, 0), MessageCategory.DEBUG)

# Create spell effect images
import math
# Import asset creation utilities from game_effects
from game_effects import create_fireball_asset_image as create_fireball_image
from game_effects import create_frost_nova_asset_image as create_frost_nova_image
fireball_path = create_fireball_image()
frost_nova_path = create_frost_nova_image()

import novamagus_hub  # Ensure the hub module is imported
SCREEN_HEIGHT = DUNGEON_SCREEN_HEIGHT
SCREEN_WIDTH = DUNGEON_SCREEN_WIDTH
# TILE_SIZE = DUNGEON_TILE_SIZE # This line is problematic as DUNGEON_TILE_SIZE is not defined here.
                                # TILE_SIZE is already imported from game_config.py and should be used directly.
# common_b_s.in_dungeon will be managed by game_state_manager's set_game_state

screen = pygame.display.set_mode((DUNGEON_SCREEN_WIDTH, DUNGEON_SCREEN_HEIGHT))
pygame.display.set_caption("Blade & Sigil v5.5")
clock = pygame.time.Clock()
FPS = 60

# Debug logging setup is now in debug_system.py

# Key diagnostics globals DEBUG_MODE, KEY_DIAGNOSTIC_ENABLED, keys_pressed, key_state
# are now defined in debug_system.py and debug_console is also initialized in debug_system.py


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
# The Character, Player, Monster, and Dungeon classes are now fully defined in common_b_s.py and imported from there
# (Player class was moved from here to common_b_s.py)
# Monster class definition was moved to common_b_s.py

# Dungeon and Monster class definitions are removed from here. They are now in common_b_s.py

# =============================================================================
# === Combat Module ===
# =============================================================================
# process_game_turn and combat functions are now in game_loop.py


# Removed Character Creation & Selection Functions as they are now in character_creation_ui.py

# In[ ]:


# =============================================================================
# === Title Screen with Load Game / New Character Options ===
# =============================================================================
from game_state_manager import (
    show_title_screen, save_game, load_game,
    initialize_game_after_title, transition_to_hub, transition_from_hub_to_dungeon,
    handle_dungeon_level_transition, handle_dungeon_map_transition,
    handle_test_arena_teleport, set_game_state # Added set_game_state
)

# === Main Game Loop with Proper Monster Reaction ===
# =============================================================================

# Show title screen and get user choice
title_choice = show_title_screen()

# Initialize game based on title screen choice
# This replaces the large block of if/else for new/load game
player, game_dungeon, game_state = initialize_game_after_title(title_choice, screen, clock)

# Ensure player_initialized is set if player is valid
player_initialized = player is not None


combat_occurred = False

# Fallback if somehow game_state wasn't set (should be handled by initialize_game_after_title)
if game_state is None: # Should ideally not be None if initialize_game_after_title is robust
    if player:
        game_state = transition_to_hub(player)
    else:
        print("CRITICAL ERROR: Player not initialized and game_state is None after title screen. Exiting.")
        pygame.quit()
        sys.exit()


running = True
last_debug_update = 0  # For tracking periodic debug messages

# Add debug messages to the debug console instead of printing
if player_initialized: # Ensure player exists before accessing attributes
    add_message(f"Starting main game loop with state: {game_state}, in_dungeon: {common_b_s.in_dungeon}", (150, 255, 150), MessageCategory.DEBUG)
    add_message(f"Player spell points: {player.spell_points}", (150, 255, 150), MessageCategory.DEBUG)
else:
    add_message(f"Starting main game loop with state: {game_state} (Player not initialized)", (150, 255, 150), MessageCategory.DEBUG)

print(f"DEBUG: T key handler is enabled")

# The old game loop is replaced by a call to run_game_loop
if player_initialized: # Ensure player and game_state are valid before starting the loop
    run_game_loop(screen, clock, player, game_dungeon, game_state)
else:
    # This case should ideally be handled by initialize_game_after_title ensuring
    # player is always initialized or game exits. If not, this is a fallback.
    add_message("Player not initialized. Cannot start game loop.", RED, MessageCategory.ERROR)
    pygame.time.wait(3000) # Wait a bit for user to see message if possible

pygame.quit()
sys.exit()


# In[ ]:
