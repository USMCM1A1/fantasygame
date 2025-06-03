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
    
    # Base and derived item classes
    Item, Weapon, WeaponBlade, WeaponBlunt, Armor, Shield, Jewelry, Consumable,
    
    # Spell Casting
    bresenham, has_line_of_sight, spells_dialogue, cast_spell, 
 
    #Combat
    draw_attack_prompt, handle_monster_turn, process_monster_death,
    handle_scroll_events,
    
    # Game Classes
    Character, Player, Tile, Door, Chest, Monster, Dungeon, # Added Player, Monster, Dungeon
    
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
# common_b_s.in_dungeon will be managed by game_state_manager's set_game_state

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
# The Character, Player, Monster, and Dungeon classes are now fully defined in common_b_s.py and imported from there
# (Player class was moved from here to common_b_s.py)
# Monster class definition was moved to common_b_s.py

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
    activated_dungeon_instance, new_arena_game_state, new_arena_in_dungeon = handle_test_arena_activation(
        current_event_for_activation, key_states, player, screen, game_dungeon, game_state
    )
    if activated_dungeon_instance:
        game_dungeon, game_state = handle_test_arena_teleport(
            player, screen, activated_dungeon_instance, new_arena_game_state, new_arena_in_dungeon
        )
        current_event_for_activation = None # Consume the event

    if game_state == "hub":
        game_state = set_game_state("hub")
        
        novamagus_hub.run_hub(screen, clock, player)
    
        if novamagus_hub.transition_to_dungeon:
            game_dungeon = transition_from_hub_to_dungeon(player, screen, clock)
            game_state = "dungeon"
            
    elif game_state == "dungeon":
        game_state = set_game_state("dungeon")
        # The following check is mostly redundant now due to set_game_state
        # if not common_b_s.in_dungeon:
        #     print("DEBUG: Correcting in_dungeon to True for dungeon state.")
        #     common_b_s.in_dungeon = True
    
    update_message_queue()
    
    current_event_for_activation = None
    for event in pygame.event.get():
        current_event_for_activation = event

        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            # Handle teleport button click
            activated_dungeon_btn, new_game_state_btn, new_in_dungeon_btn = handle_teleport_button_click(
                event.pos, player, game_dungeon, screen
            )
            if activated_dungeon_btn:
                game_dungeon, game_state = handle_test_arena_teleport(
                    player, screen, activated_dungeon_btn, new_game_state_btn, new_in_dungeon_btn
                )
                continue

        elif event.type == pygame.USEREVENT + 1:
            levelup_sound.play()
            pygame.time.set_timer(pygame.USEREVENT + 1, 0)

        elif event.type == pygame.KEYDOWN:
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
                    continue
            
            handle_scroll_events(event)
            moved = False

            if event.key in [pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN]:
                dx, dy = 0, 0
                if event.key == pygame.K_LEFT: dx = -TILE_SIZE
                elif event.key == pygame.K_RIGHT: dx = TILE_SIZE
                elif event.key == pygame.K_UP: dy = -TILE_SIZE
                elif event.key == pygame.K_DOWN: dy = TILE_SIZE
                
                move_result = player.move(dx, dy, game_dungeon)
                
                if len(move_result) == 3:
                    success, transition_type, message = move_result
                    destination_map = None
                elif len(move_result) == 4:
                    success, transition_type, destination_map, message = move_result
                else:
                    success, transition_type, message = move_result[0], "", move_result[1]
                    destination_map = None
                    
                if success:
                    process_game_turn(player, game_dungeon)
                
                player_tile_x = player.position[0] // TILE_SIZE
                player_tile_y = player.position[1] // TILE_SIZE
                
                for coords, door_obj in game_dungeon.doors.items(): # Renamed door to door_obj
                    if (player_tile_x, player_tile_y) == coords:
                        if door_obj.door_type == "map_transition" and hasattr(door_obj, "destination_map"):
                            transition_type = "map_transition"
                            destination_map = door_obj.destination_map
                            message = f"You found a passage to another area! (Map {door_obj.destination_map})"
                
                if success and transition_type == "map_transition" and destination_map is not None:
                    game_dungeon = handle_dungeon_map_transition(player, game_dungeon, destination_map)
                elif success and transition_type == "level_transition":
                    game_dungeon = handle_dungeon_level_transition(player, game_dungeon)
                elif message and message.strip():
                    add_message(message)
                moved = success

            elif event.key == pygame.K_i:
                current_game_state_before_inventory = game_state
                game_state = set_game_state(game_state)
                manage_inventory(player, screen, clock, game_dungeon)
                game_state = set_game_state(current_game_state_before_inventory)
                
            elif event.key == pygame.K_y and combat_occurred:
                combat_messages = combat(player, game_dungeon.monsters[0], game_dungeon)
                for msg in combat_messages: add_message(msg)
                combat_occurred = False
                moved = True
                process_game_turn(player, game_dungeon)

            elif event.key == pygame.K_n and combat_occurred:
                combat_occurred = False
            
            elif event.key == pygame.K_h:
                display_help_screen(screen, clock)
            
            elif event.key == pygame.K_F5:
                add_message("Saving game...")
                try:
                    if save_game(player, game_dungeon, game_state):
                        add_message("Game saved successfully!")
                    else:
                        add_message("Failed to save game - unknown error!")
                except Exception as e:
                    add_message(f"Error saving game: {str(e)}")
            elif event.key == pygame.K_F9:
                add_message("Loading game...")
                try:
                    loaded_data = load_game()
                    if loaded_data:
                        loaded_player, loaded_dungeon_data, loaded_game_state_str, saved_cm_turn = loaded_data
                        player = loaded_player
                        if isinstance(loaded_dungeon_data, dict):
                            game_dungeon = Dungeon(loaded_dungeon_data.get("width", 20), loaded_dungeon_data.get("height", 15))
                            add_message("Warning: Simplified dungeon load via F9. Full state may not be restored.", RED)
                            # Full reconstruction logic from initialize_game_after_title would be needed here for complete F9 load
                        else:
                            game_dungeon = loaded_dungeon_data
                        game_state = set_game_state(loaded_game_state_str)
                        condition_manager.current_turn = saved_cm_turn
                        print(f"DEBUG: Loaded game with state: {game_state}, in_dungeon: {common_b_s.in_dungeon}")
                except Exception as e:
                    add_message(f"Error loading game: {str(e)}")
            
            elif event.key == pygame.K_o:
                player_tile_x = player.position[0] // TILE_SIZE
                player_tile_y = player.position[1] // TILE_SIZE
                adjacent_coords = [(player_tile_x - 1, player_tile_y), (player_tile_x + 1, player_tile_y), (player_tile_x, player_tile_y - 1), (player_tile_x, player_tile_y + 1)]
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
                                game_dungeon.tiles[door_x][door_y].type = 'door'
                                game_dungeon.tiles[door_x][door_y].sprite = door.sprite
                                if door.door_type == "level_transition":
                                    game_dungeon = handle_dungeon_level_transition(player, game_dungeon)
                                elif door.door_type == "map_transition":
                                    game_dungeon = handle_dungeon_map_transition(player, game_dungeon, door.destination_map)
                            door_found = True
                            moved = True
                            break
                if not door_found: add_message("There is no door nearby to open.")
            
            elif event.key == pygame.K_p:
                player_tile_x = player.position[0] // TILE_SIZE
                player_tile_y = player.position[1] // TILE_SIZE
                adjacent_coords = [(player_tile_x - 1, player_tile_y), (player_tile_x + 1, player_tile_y), (player_tile_x, player_tile_y - 1), (player_tile_x, player_tile_y + 1)]
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
                                game_dungeon.tiles[door_x][door_y].type = 'door'
                                game_dungeon.tiles[door_x][door_y].sprite = door.sprite
                                if door.door_type == "level_transition":
                                    game_dungeon = handle_dungeon_level_transition(player, game_dungeon)
                                elif door.door_type == "map_transition":
                                    game_dungeon = handle_dungeon_map_transition(player, game_dungeon, door.destination_map)
                            locked_door_found = True
                            moved = True
                            break
                if not locked_door_found:
                    chest_found = False
                    for chest_x, chest_y in adjacent_coords:
                        if (chest_x, chest_y) in game_dungeon.chests:
                            chest = game_dungeon.chests[(chest_x, chest_y)]
                            if chest.locked and not chest.open:
                                success, message = chest.try_pick_lock(player)
                                add_message(message)
                                if success: add_message(f"The chest contains {len(chest.contents)} items and {chest.gold} gold!")
                                chest_found = True
                                moved = True
                                break
                    if not chest_found: add_message("There is nothing nearby to pick.")
                    
            elif event.key == pygame.K_u:
                player_tile_x = player.position[0] // TILE_SIZE
                player_tile_y = player.position[1] // TILE_SIZE
                adjacent_coords = [(player_tile_x - 1, player_tile_y), (player_tile_x + 1, player_tile_y), (player_tile_x, player_tile_y - 1), (player_tile_x, player_tile_y + 1)]
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
                                game_dungeon.tiles[door_x][door_y].type = 'door'
                                game_dungeon.tiles[door_x][door_y].sprite = door.sprite
                                if door.door_type == "level_transition":
                                    game_dungeon = handle_dungeon_level_transition(player, game_dungeon)
                                elif door.door_type == "map_transition":
                                    game_dungeon = handle_dungeon_map_transition(player, game_dungeon, door.destination_map)
                            locked_door_found = True
                            moved = True
                            break
                if not locked_door_found:
                    chest_found = False
                    for chest_x, chest_y in adjacent_coords:
                        if (chest_x, chest_y) in game_dungeon.chests:
                            chest = game_dungeon.chests[(chest_x, chest_y)]
                            if chest.locked and not chest.open:
                                success, message = chest.try_magic_unlock(player)
                                add_message(message)
                                if success: add_message(f"The chest contains {len(chest.contents)} items and {chest.gold} gold!")
                                chest_found = True
                                moved = True
                                break
                    if not chest_found: add_message("There is nothing nearby to unlock with magic.")

            elif event.key == pygame.K_x:
                try:
                    from Data.spell_bridge import update_spells_dialogue
                    selected_spell = update_spells_dialogue(screen, player, clock)
                except Exception as e:
                    print(f"DEBUG: Error using enhanced UI: {e}")
                    selected_spell = spells_dialogue(screen, player, clock)
                
                if selected_spell is None: continue
                elif selected_spell["name"] in ["Cure Light Wounds", "Light", "Mage Armor", "Wicked Weapon"]: target = player
                else: target = game_dungeon.monsters[0] if game_dungeon.monsters else None
                            
                if target and target.hit_points > 0:
                    spell_messages = cast_spell(player, target, selected_spell["name"], game_dungeon)
                    for msg in spell_messages: add_message(msg)
                    moved = True
                    process_game_turn(player, game_dungeon)
            
                if moved: # Monster turn processing after spell
                    for monster in game_dungeon.monsters:
                        if monster.hit_points > 0 or getattr(monster, 'pending_death_from_dot', False):
                            handle_monster_turn(monster, player, game_dungeon)
                            if getattr(monster, 'pending_death_from_dot', False) and monster.hit_points <= 0:
                                death_messages = process_monster_death(monster, player, game_dungeon)
                                if death_messages: 
                                    for msg in death_messages: add_message(msg)
                                if hasattr(monster, 'pending_death_from_dot'): delattr(monster, 'pending_death_from_dot')

            elif event.key == pygame.K_a and player.char_class == "Archer":
                if game_dungeon.monsters and game_dungeon.monsters[0].hit_points > 0:
                    spell_messages = cast_spell(player, game_dungeon.monsters[0], "Arrow Shot", game_dungeon)
                    for msg in spell_messages: add_message(msg)
                    moved = True
                    process_game_turn(player, game_dungeon)

            if moved: # General monster turn processing if player action caused a turn
                for monster in game_dungeon.monsters:
                    if monster.hit_points > 0 or getattr(monster, 'pending_death_from_dot', False):
                        handle_monster_turn(monster, player, game_dungeon)
                        if getattr(monster, 'pending_death_from_dot', False) and monster.hit_points <= 0:
                            death_messages = process_monster_death(monster, player, game_dungeon)
                            if death_messages:
                                for msg in death_messages: add_message(msg)
                            if hasattr(monster, 'pending_death_from_dot'): delattr(monster, 'pending_death_from_dot')

    # === DRAW GAME STATE ===
    screen.fill(BLACK)
    if player_initialized and game_dungeon:
        draw_playable_area(screen, game_dungeon, player)

    # === HANDLE ITEM PICKUPS (Fixed) ===
    if player_initialized and game_dungeon:
        player_tile_x = player.position[0] // TILE_SIZE
        player_tile_y = player.position[1] // TILE_SIZE

        for drop in game_dungeon.dropped_items[:]:
            drop_tile_x = drop['position'][0] // TILE_SIZE
            drop_tile_y = drop['position'][1] // TILE_SIZE
            if player_tile_x == drop_tile_x and player_tile_y == drop_tile_y:
                player.pickup_item(drop['item'])
                game_dungeon.dropped_items.remove(drop)

        chest_coords = (player_tile_x, player_tile_y)
        if chest_coords in game_dungeon.chests:
            chest = game_dungeon.chests[chest_coords]
            if chest.open and (len(chest.contents) > 0 or chest.gold > 0):
                if len(chest.contents) > 0:
                    for item in chest.contents[:]:
                        player.pickup_item(item)
                        add_message(f"You picked up {item.name} from the chest!")
                if chest.gold > 0:
                    player.gold += chest.gold
                    add_message(f"You found {chest.gold} gold in the chest!")
                chest.contents = []
                chest.gold = 0

    # === HANDLE MONSTER ATTACK PROMPT ===
    if player_initialized and game_dungeon and game_dungeon.monsters and game_dungeon.monsters[0].hit_points > 0:
        monster_tile_x = game_dungeon.monsters[0].position[0] // TILE_SIZE
        monster_tile_y = game_dungeon.monsters[0].position[1] // TILE_SIZE
        player_tile_x = player.position[0] // TILE_SIZE # Ensure player_tile_x is defined here too
        player_tile_y = player.position[1] // TILE_SIZE # Ensure player_tile_y is defined here too
        if abs(player_tile_x - monster_tile_x) + abs(player_tile_y - monster_tile_y) == 1:
            draw_attack_prompt(screen, game_dungeon.monsters[0].name)
            combat_occurred = True
            
    # === DRAW TELEPORT TO ARENA BUTTON (more subtle) ===
    teleport_button = pygame.Rect(DUNGEON_SCREEN_WIDTH - 150, 10, 140, 30)
    pygame.draw.rect(screen, (100, 100, 200), teleport_button)
    pygame.draw.rect(screen, (200, 200, 255), teleport_button, 2)
    draw_text(screen, "Teleport to Arena", BLACK, DUNGEON_SCREEN_WIDTH - 145, 15)

    # === DRAW UI PANELS ===
    if player_initialized:
        draw_right_panel(
            screen, player, DUNGEON_PLAYABLE_AREA_WIDTH, DUNGEON_PLAYABLE_AREA_HEIGHT,
            DUNGEON_RIGHT_PANEL_WIDTH, offset_x=0
        )
        draw_bottom_panel(
            screen, DUNGEON_PLAYABLE_AREA_HEIGHT, DUNGEON_SCREEN_WIDTH,
            DUNGEON_BOTTOM_PANEL_HEIGHT, offset_y=0
        )
        
    if debug_system.DEBUG_MODE:
        if player_initialized and game_dungeon:
            debug_system.draw_debug_info(screen, player, game_dungeon, font)
    
    debug_system.draw_key_diagnostics(screen, font, small_font, DUNGEON_SCREEN_WIDTH)
    
    draw_text(screen, "Press F1 for Test Arena", WHITE, 
              DUNGEON_SCREEN_WIDTH - 200, DUNGEON_SCREEN_HEIGHT - 20)
    
    current_time = pygame.time.get_ticks()
    if current_time - last_debug_update > 5000:
        if debug_console.visible:
            fps = clock.get_fps()
            memory_info = get_memory_usage()
            add_message(f"FPS: {fps:.1f}, {memory_info}", (150, 150, 255), MessageCategory.DEBUG)
            if player and hasattr(player, 'hit_points') and hasattr(player, 'max_hit_points'):
                add_message(f"Player: HP {player.hit_points}/{player.max_hit_points}, SP {player.spell_points}/{getattr(player, 'max_spell_points', 'N/A')}",
                          (200, 255, 200), MessageCategory.DEBUG)
            if game_state == "dungeon" and game_dungeon and hasattr(game_dungeon, 'monsters'):
                monster_count = len(game_dungeon.monsters) if hasattr(game_dungeon, 'monsters') else 0
                item_count = len(game_dungeon.dropped_items) if hasattr(game_dungeon, 'dropped_items') else 0
                chest_count = len(game_dungeon.chests) if hasattr(game_dungeon, 'chests') else 0
                add_message(f"Entities: {monster_count} monsters, {item_count} items, {chest_count} chests",
                          (200, 200, 255), MessageCategory.DEBUG)
        last_debug_update = current_time
    
    debug_console.draw(screen)
    
    pygame.display.flip()

pygame.quit()
sys.exit()


# In[ ]:
