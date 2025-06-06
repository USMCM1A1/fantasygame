#!/usr/bin/env python
# coding: utf-8

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

# =============================================================================
# === Initialization & Constants Module ===
# =============================================================================
pygame.init()

# IMPORTANT: Set display mode FIRST before loading any sprites
from game_config import DUNGEON_SCREEN_WIDTH, DUNGEON_SCREEN_HEIGHT
screen = pygame.display.set_mode((DUNGEON_SCREEN_WIDTH, DUNGEON_SCREEN_HEIGHT))
pygame.display.set_caption("Blade & Sigil v5.5")

# Now import everything else that might load sprites
from novamagus_hub import run_hub
from character_creation_ui import character_creation_screen
from game_loop import run_game_loop

# Define fonts to be used
small_font = pygame.font.SysFont('monospace', 16)

#sound mixer
pygame.mixer.init()

# Import from common_b_s
import common_b_s
import debug_system
from test_arena import create_test_arena, create_emergency_arena, handle_test_arena_activation, handle_teleport_button_click
from Data.condition_system import condition_manager, ConditionType

# Reset condition manager's turn counter at the start of the game
condition_manager.current_turn = 0

# Pygame font init
pygame.font.init()

# Initialize debug console
debug_system.initialize_debug_console(font=small_font, screen_width=DUNGEON_SCREEN_WIDTH, screen_height=DUNGEON_SCREEN_HEIGHT)

# Import game constants directly from game_config
from game_config import (
    DUNGEON_FPS, TILE_SIZE,
    DUNGEON_RIGHT_PANEL_WIDTH, DUNGEON_BOTTOM_PANEL_HEIGHT, DUNGEON_PLAYABLE_AREA_WIDTH, DUNGEON_PLAYABLE_AREA_HEIGHT,
    RIGHT_PANEL_OFFSET, BOTTOM_PANEL_OFFSET,
    DOOR_CHANCE, LOCKED_DOOR_CHANCE, DOOR_DIFFICULTY, 
    CHEST_DIFFICULTY, CHEST_ITEMS_COUNT, CHEST_GOLD_DICE,
    WHITE, BLACK, LIGHT_GRAY, RED, GREEN, BLUE
)

from common_b_s import (
    font,
    load_sprite, load_json, assets_data, characters_data, spells_data, items_data, monsters_data, dice_sprite,
    spell_sound, melee_sound, arrow_sound, levelup_sound,
    draw_text, draw_panel, draw_text_lines, draw_playable_area, draw_right_panel, draw_bottom_panel,
    draw_equipment_panel,
    add_message,
    loot_drop_sprite,
    Item, Weapon, WeaponBlade, WeaponBlunt, Armor, Shield, Jewelry, Consumable,
    bresenham, has_line_of_sight,
    Character, Tile, Door, Chest, Monster, Dungeon,
    debug_console, MessageCategory,
)

from game_utils import roll_ability_helper, get_memory_usage, print_character_stats
from game_logic_utils import (
    can_equip_item, handle_targeting, compute_fov, get_valid_equipment_slots,
    swap_equipment, unequip_item, get_clicked_equipment_slot,
    manage_inventory, display_help_screen
)
from player import Player

# Startup message
print("Blade & Sigil v5.5 starting up...")

# Add initial debug messages
add_message("Debug system initialized", (200, 200, 255), MessageCategory.DEBUG)
add_message("Press D to toggle debug console", (255, 255, 0), MessageCategory.DEBUG)

# Create spell effect images
import math
from game_effects import create_fireball_asset_image as create_fireball_image
from game_effects import create_frost_nova_asset_image as create_frost_nova_image
fireball_path = create_fireball_image()
frost_nova_path = create_frost_nova_image()

import novamagus_hub
clock = pygame.time.Clock()
FPS = 60

# =============================================================================
# === Title Screen with Load Game / New Character Options ===
# =============================================================================
from game_state_manager import (
    show_title_screen, save_game, load_game,
    initialize_game_after_title, transition_to_hub, transition_from_hub_to_dungeon,
    handle_dungeon_level_transition, handle_dungeon_map_transition,
    handle_test_arena_teleport, set_game_state
)

# Show title screen and get user choice
title_choice = show_title_screen()

# Initialize game based on title screen choice
player, game_dungeon, game_state = initialize_game_after_title(title_choice, screen, clock)

print(f"DEBUG: After initialize_game_after_title:")
print(f"  player: {player}")
print(f"  player_initialized: {player is not None}")
print(f"  game_state: {game_state}")
print(f"  common_b_s.in_dungeon: {common_b_s.in_dungeon}")

print(f"DEBUG: Before run_game_loop:")
print(f"  game_state type: {type(game_state)}")
print(f"  game_state value: {game_state}")

# Convert string game_state to GameState enum
from game_state_manager import GameState
if game_state == "hub":
    initial_state = GameState.HUB
elif game_state == "dungeon":
    initial_state = GameState.PLAYING
else:
    initial_state = GameState.HUB  # Default fallback

print(f"DEBUG: Converted game_state '{game_state}' to enum: {initial_state}")

# Ensure player_initialized is set if player is valid
player_initialized = player is not None

if player_initialized:
    print(f"DEBUG: Starting game loop with player: {player.name}")
    run_game_loop(screen, clock, player, game_dungeon, initial_state)
else:
    add_message("Player not initialized. Cannot start game loop.", RED, MessageCategory.ERROR)
    pygame.time.wait(3000)

pygame.quit()
sys.exit()
