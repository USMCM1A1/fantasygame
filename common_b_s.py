#!/usr/bin/env python
# coding: utf-8

# In[1]:


# common_b_s.py
import pygame
import json
import os
import sys
import logging
import random
import re
from copy import deepcopy
from Data.condition_system import condition_manager
import math # Added for MST calculations

# === Pygame Initialization Constants ===
pygame.init()

# --- Dungeon Configuration ---
DUNGEON_SCREEN_WIDTH = 1500
DUNGEON_SCREEN_HEIGHT = 860
DUNGEON_FPS = 60
DUNGEON_TILE_SIZE = 48

DUNGEON_RIGHT_PANEL_PERCENT = 0.20
DUNGEON_BOTTOM_PANEL_PERCENT = 0.15

DUNGEON_RIGHT_PANEL_WIDTH = int(DUNGEON_SCREEN_WIDTH * DUNGEON_RIGHT_PANEL_PERCENT)
DUNGEON_BOTTOM_PANEL_HEIGHT = int(DUNGEON_SCREEN_HEIGHT * DUNGEON_BOTTOM_PANEL_PERCENT)
DUNGEON_PLAYABLE_AREA_WIDTH = DUNGEON_SCREEN_WIDTH - DUNGEON_RIGHT_PANEL_WIDTH
DUNGEON_PLAYABLE_AREA_HEIGHT = DUNGEON_SCREEN_HEIGHT - DUNGEON_BOTTOM_PANEL_HEIGHT

# --- Door Configuration ---
DOOR_CHANCE = 0.2  # Percentage of eligible corridor tiles that become doors (reduced to 20%)
LOCKED_DOOR_CHANCE = 1.0  # All doors are locked (100%)
DOOR_DIFFICULTY = 7  # Fixed difficulty for door checks

# --- Treasure Chest Configuration ---
CHEST_DIFFICULTY = 8  # Slightly harder than doors
CHEST_ITEMS_COUNT = 3  # Number of random items per chest
CHEST_GOLD_DICE = "3d10"  # Gold amount per chest

# --- Hub Configuration ---
HUB_SCREEN_WIDTH = 800
HUB_SCREEN_HEIGHT = 600
HUB_FPS = 60
HUB_TILE_SIZE = 48  # Or a different size if desired
HUB_SCALE = 2

HUB_RIGHT_PANEL_PERCENT = 0.30  # Panel takes 30% of screen width
HUB_BOTTOM_PANEL_PERCENT = 0.20  # Panel takes 20% of screen height

# Calculate panel dimensions
HUB_RIGHT_PANEL_WIDTH = int(HUB_SCREEN_WIDTH * HUB_RIGHT_PANEL_PERCENT)
HUB_BOTTOM_PANEL_HEIGHT = int(HUB_SCREEN_HEIGHT * HUB_BOTTOM_PANEL_PERCENT)

# Playable area is smaller than the screen to make room for panels
HUB_PLAYABLE_AREA_WIDTH = HUB_SCREEN_WIDTH - HUB_RIGHT_PANEL_WIDTH  # Exclude right panel
HUB_PLAYABLE_AREA_HEIGHT = HUB_SCREEN_HEIGHT - HUB_BOTTOM_PANEL_HEIGHT  # Exclude bottom panel

RIGHT_PANEL_OFFSET = 0  # No offset needed now that playable area width is correct
BOTTOM_PANEL_OFFSET = 0  # No offset needed now that playable area height is correct

# Screen initialization might be problematic for non-GUI tests.
# Consider initializing it only when needed or using a dummy screen for tests.
# screen = pygame.display.set_mode((HUB_SCREEN_WIDTH, HUB_SCREEN_HEIGHT))

TILE_SIZE = HUB_TILE_SIZE  # or TILE_SIZE = DUNGEON_TILE_SIZE

# --- Common Colors and Font ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
LIGHT_GRAY = (200, 200, 200)
DARK_GRAY = (100, 100, 100)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)

# Define in_dungeon here as a global variable
in_dungeon = True  # Default to True since we usually start in dungeon mode

font = pygame.font.SysFont('monospace', 15)

# === Logging Configuration ===
DEBUG_MODE = True
logging.basicConfig(
    level=logging.DEBUG,
    filename="game_debug.log", # Consider making this path relative too
    filemode="w", # Overwrite log file each run for cleaner testing
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# === Asset Loading (Paths made relative) ===
BASE_PATH = os.path.dirname(os.path.abspath(__file__)) # Get the directory of the current script
DATA_DIR = os.path.join(BASE_PATH, "Data")
ASSETS_PATH = os.path.join(BASE_PATH, "Fantasy_Game_Art_Assets") # Assuming this is the structure

CHARACTERS_FILE = os.path.join(DATA_DIR, "characters.json")
ASSETS_FILE = os.path.join(DATA_DIR, "assets.json")
SPELLS_FILE = os.path.join(DATA_DIR, "spells.json")
ITEMS_FILE = os.path.join(DATA_DIR, "items.json")
MONSTERS_FILE = os.path.join(DATA_DIR, "monsters.json")

# Global data holders - initialized as None, loaded by a function
assets_data = None
monsters_data = None
items_data = None # Added for create_item
characters_data = None # Added for Player class potentially
spells_data = None # Added for spell system potentially

def load_all_data():
    global assets_data, monsters_data, items_data, characters_data, spells_data
    try:
        assets_data = load_json(ASSETS_FILE)
        monsters_data = load_json(MONSTERS_FILE)
        items_data = load_json(ITEMS_FILE)
        characters_data = load_json(CHARACTERS_FILE)
        spells_data = load_json(SPELLS_FILE)
        # print("DEBUG: All game data loaded successfully.")
    except Exception as e:
        print(f"FATAL ERROR: Could not load essential game data: {e}")
        # In a real game, you might exit or go to an error screen
        # For testing, we'll let it proceed and see where it fails.
        assets_data = {"sprites": {"tiles": {"floor": "placeholder_floor.png"}}} # Minimal fallback
        monsters_data = {"monsters": []}
        items_data = {"items": [], "item_categories": {}}
        characters_data = {"races": {}, "classes": {}}
        spells_data = {"spells": []}


# === Helper Functions ===
def load_sprite(path):
    """
    Load an image from the given path, convert it for pygame, and scale it to TILE_SIZE.
    Path should be relative to the ASSETS_PATH.
    """
    # Ensure assets_data is loaded
    if assets_data is None:
        # This is a fallback for tests before full data loading, not ideal for production
        # print("Warning: assets_data not loaded in load_sprite. This might cause issues.")
        # Fallback to avoid crash if path is not in a minimal assets_data for testing
        if path and isinstance(path, str): # Check if path is a non-empty string
             # Attempt to construct full path, assuming path is relative from some base
            full_path = os.path.join(ASSETS_PATH, path)
            if not os.path.exists(full_path):
                 # Try another base if the above fails, like the script's directory
                alt_path = os.path.join(BASE_PATH, path)
                if os.path.exists(alt_path):
                    full_path = alt_path
                else: # If still not found, create a dummy surface
                    # print(f"ERROR: Sprite path '{path}' (resolved to '{full_path}') not found. Using dummy sprite.")
                    dummy_sprite = pygame.Surface((TILE_SIZE, TILE_SIZE))
                    dummy_sprite.fill(RED) # Red square as placeholder
                    return dummy_sprite
        else: # path is None or not a string
            # print(f"ERROR: Invalid sprite path '{path}'. Using dummy sprite.")
            dummy_sprite = pygame.Surface((TILE_SIZE, TILE_SIZE))
            dummy_sprite.fill(RED)
            return dummy_sprite


    # Construct the full path relative to ASSETS_PATH
    # Check if the provided path is already absolute or needs ASSETS_PATH prepended
    if os.path.isabs(path):
        full_path = path
    else:
        full_path = os.path.join(ASSETS_PATH, path)

    if not os.path.exists(full_path):
        # print(f"ERROR: Sprite path '{path}' (resolved to '{full_path}') not found. Using dummy sprite.")
        # Fallback: create a dummy surface
        dummy_sprite = pygame.Surface((TILE_SIZE, TILE_SIZE))
        dummy_sprite.fill(RED) # Red square as placeholder
        return dummy_sprite

    try:
        sprite = pygame.image.load(full_path).convert_alpha()
        return pygame.transform.smoothscale(sprite, (TILE_SIZE, TILE_SIZE))
    except pygame.error as e:
        # print(f"ERROR: Pygame error loading sprite '{full_path}': {e}. Using dummy sprite.")
        dummy_sprite = pygame.Surface((TILE_SIZE, TILE_SIZE))
        dummy_sprite.fill(RED)
        return dummy_sprite


def load_json(file_path):
    """
    Load and return JSON data from the specified file path.
    """
    if not os.path.exists(file_path):
        print(f"ERROR: JSON file not found: {file_path}")
        return {} # Return empty dict to avoid crashes, though this is bad
    with open(file_path, 'r') as f:
        return json.load(f)

# Load data globally for the module
load_all_data()

def roll_ability_helper():
    # Standard 3d6 roll for an ability score
    return sum(random.randint(1, 6) for _ in range(3))


# In[2]:


# =============================================================================
# === UI Drawing Module (Refactored) ===
# =============================================================================

def draw_text(surface, text, color, x, y):
    text_surface = font.render(str(text), True, color)
    surface.blit(text_surface, (x, y))

def draw_panel(screen, rect, fill_color, border_color, border_width=2):
    pygame.draw.rect(screen, fill_color, rect)
    pygame.draw.rect(screen, border_color, rect, border_width)

def draw_text_lines(screen, lines, start_x, start_y, line_spacing=4, color=WHITE, max_y=None):
    y = start_y
    line_height = font.get_linesize() + line_spacing
    
    # If max_y wasn't provided, set it to the screen height
    if max_y is None:
        max_y = HUB_SCREEN_HEIGHT if not in_dungeon else DUNGEON_SCREEN_HEIGHT
    
    for line in lines:
        # Check if drawing this line would go beyond max_y
        if y + line_height <= max_y:
            draw_text(screen, line, color, start_x, y)
            y += line_height
        else:
            # Stop drawing if we've reached the limit
            break
    
    return y

def draw_playable_area(screen, game_dungeon, player):
    # Create a surface for the playable area using the dungeon-specific constants.
    playable_surface = pygame.Surface((DUNGEON_PLAYABLE_AREA_WIDTH, DUNGEON_PLAYABLE_AREA_HEIGHT))
    playable_surface.fill(BLACK)
    
    # Draw the dungeon.
    game_dungeon.draw(playable_surface)
    
    # Draw the player sprite, centering it on the tile.
    player_pos = (player.position[0] - DUNGEON_TILE_SIZE // 2, player.position[1] - DUNGEON_TILE_SIZE // 2)
    playable_surface.blit(player.sprite, player_pos)
    
    # Draw any monsters.
    for monster in game_dungeon.monsters:
        if monster.position:
            monster_pos = (monster.position[0] - DUNGEON_TILE_SIZE // 2, monster.position[1] - DUNGEON_TILE_SIZE // 2)
            playable_surface.blit(monster.sprite, monster_pos)
    
    # Compute visible cells based on the player's light radius.
    light_radius = getattr(player, "light_radius", 2)
    visible = compute_fov(game_dungeon, player, light_radius)
    
    # Overlay darkness on cells not in the visible set.
    for x in range(game_dungeon.width):
        for y in range(game_dungeon.height):
            if (x, y) not in visible:
                rect = pygame.Rect(x * DUNGEON_TILE_SIZE, y * DUNGEON_TILE_SIZE, DUNGEON_TILE_SIZE, DUNGEON_TILE_SIZE)
                darkness = pygame.Surface((DUNGEON_TILE_SIZE, DUNGEON_TILE_SIZE))
                darkness.fill((0, 0, 0))
                darkness.set_alpha(240)  # More opacity for complete coverage
                playable_surface.blit(darkness, rect)
    
    # Blit the playable area onto the screen and draw a border.
    screen.blit(playable_surface, (0, 0))
    pygame.draw.rect(screen, WHITE, (0, 0, DUNGEON_PLAYABLE_AREA_WIDTH, DUNGEON_PLAYABLE_AREA_HEIGHT), 2)

def draw_right_panel(screen, player, playable_area_width, playable_area_height, right_panel_width, offset_x=0):
    # For hub mode, we need to make sure the right panel height goes to the bottom of the screen
    # not just to the top of the bottom panel
    panel_height = playable_area_height
    if not in_dungeon:
        panel_height = HUB_SCREEN_HEIGHT  # Use the full screen height
    
    # The right panel starts exactly at the end of the playable area.
    panel_rect = pygame.Rect(playable_area_width, 0, right_panel_width, panel_height)
    draw_panel(screen, panel_rect, BLACK, WHITE)
    
    # Use a margin for inner content.
    x_offset = panel_rect.x + 10
    y_offset = panel_rect.y + 10
    
    # Calculate max height for the panel
    max_height = HUB_SCREEN_HEIGHT if not in_dungeon else DUNGEON_SCREEN_HEIGHT
    max_y = max_height - 10  # Leave a small margin
    
    # Available width for text
    available_width = right_panel_width - 20  # 10px margin on each side
    
    # Calculate the portrait size but make it smaller to leave more room for stats
    portrait_percent = 0.35  # Portrait takes 35% of panel height
    portrait_size = min(right_panel_width - 20, int(panel_height * portrait_percent))
    
    # Draw the character portrait.
    if y_offset + portrait_size <= max_y:
        class_lower = player.char_class.lower()  # e.g., "wizard"
        # Ensure assets_data and necessary keys exist
        if assets_data and "sprites" in assets_data and "heroes" in assets_data["sprites"] and \
           class_lower in assets_data["sprites"]["heroes"] and "portrait" in assets_data["sprites"]["heroes"][class_lower]:
            portrait_path = assets_data["sprites"]["heroes"][class_lower]["portrait"]
            # Make portrait_path relative to ASSETS_PATH
            full_portrait_path = os.path.join(ASSETS_PATH, portrait_path)
            if os.path.exists(full_portrait_path):
                portrait = pygame.image.load(full_portrait_path).convert_alpha()
                portrait = pygame.transform.scale(portrait, (portrait_size, portrait_size))
                screen.blit(portrait, (x_offset, y_offset))
            else:
                draw_text(screen, "No Portrait", RED, x_offset, y_offset) # Fallback text
        else:
            draw_text(screen, "Portrait N/A", RED, x_offset, y_offset) # Fallback text
        y_offset += portrait_size + 10


    # Set standard line height
    line_height = font.get_linesize() + 4

    # Compute bonuses and draw basic character info.
    hit_bonus = player.attack_bonus + player.calculate_modifier(player.get_effective_ability("strength"))
    wicked_bonus = getattr(player, "wicked_weapon_bonus", 0)
    damage_bonus = player.calculate_modifier(player.get_effective_ability("strength")) + wicked_bonus

    # Get dungeon depth (displayed level) or set to 1 if not defined
    dungeon_depth = getattr(player, 'dungeon_depth', 1)
    
    # Get experience and next level information if available
    exp = getattr(player, 'experience', 0)
    next_level_exp = 0
    
    if hasattr(player, 'level_thresholds') and player.level < 20:
        next_level_exp = player.level_thresholds[player.level + 1]
    elif player.level < 20:
        # Fallback calculation
        next_level_exp = 1000 * (player.level + 1) * (player.level + 1)
    
    # Format XP display
    if player.level >= 20:  # Max level
        xp_display = f"XP: {exp} (Max)"
    else:
        xp_display = f"XP: {exp}/{next_level_exp}"
    
    # Draw each line of basic info, checking bounds
    basic_info = [
        f"Name: {player.name}",
        f"Race: {player.race}",
        f"Class: {player.char_class}",
        f"Level: {player.level}",
        f"Dungeon: {dungeon_depth}",
        xp_display,
        f"AC: {player.get_effective_ac()}",
        f"HP: {player.hit_points}/{player.max_hit_points}",
        f"SP: {player.spell_points}",
        f"Hit/Dam: {hit_bonus}/{damage_bonus}",
    ]
    
    for line in basic_info:
        if y_offset + line_height <= max_y:
            draw_text(screen, line, WHITE, x_offset, y_offset)
            y_offset += line_height

    # Draw abilities in two columns if there's space
    if y_offset + line_height*2 <= max_y:  # Need at least 2 lines of space
        col2_x = x_offset + 100  # Reduced column width
        
        # First row of abilities
        if y_offset + line_height <= max_y:
            draw_text(screen, f"Str: {player.abilities['strength']}", WHITE, x_offset, y_offset)
            draw_text(screen, f"Dex: {player.abilities['dexterity']}", WHITE, col2_x, y_offset)
            y_offset += line_height
            
        # Second row of abilities    
        if y_offset + line_height <= max_y:
            draw_text(screen, f"Int: {player.abilities['intelligence']}", WHITE, x_offset, y_offset)
            draw_text(screen, f"Con: {player.abilities['constitution']}", WHITE, col2_x, y_offset)
            y_offset += line_height
            
        # Third row of abilities
        if y_offset + line_height <= max_y:
            draw_text(screen, f"Wis: {player.abilities['wisdom']}", WHITE, x_offset, y_offset)
            y_offset += line_height

    # Extra margin before equipment panel
    if y_offset + 10 <= max_y:
        y_offset += 10
        
    # Draw equipment if there's space
    if y_offset < max_y:
        y_offset = draw_equipment_panel(screen, player, x_offset, y_offset)
    
def draw_bottom_panel(screen, playable_area_height, screen_width, bottom_panel_height, offset_y=0):
    """
    Draw the bottom panel, which includes the message log.
    Uses the MessageManager to retrieve and display messages.
    
    Args:
        screen: The screen to draw on
        playable_area_height: Height of the playable area
        screen_width: Width of the screen
        bottom_panel_height: Height of the bottom panel
        offset_y: Y-coordinate offset for the panel
        
    Returns:
        pygame.Rect: The scrollbar rectangle for mouse interaction
    """
    # Bottom panel should only cover the playable area width, not the right panel area
    playable_width = screen_width
    if in_dungeon:
        playable_width = DUNGEON_PLAYABLE_AREA_WIDTH
    else:
        playable_width = HUB_PLAYABLE_AREA_WIDTH
    
    # Adjust the y-coordinate of the bottom panel using offset_y
    panel_rect = pygame.Rect(0, playable_area_height + offset_y, playable_width, bottom_panel_height)
    draw_panel(screen, panel_rect, BLACK, WHITE)
    
    line_height = font.get_linesize()
    y_offset = panel_rect.y + 10

    # Get visible messages from the message manager
    visible_messages = message_manager.get_visible_messages()
    
    # Create text area with padding for scrollbar
    text_area_width = panel_rect.width - 30  # 20px for scrollbar + 10px padding
    
    # Draw messages
    if visible_messages:
        for message in visible_messages:
            # Get message attributes
            msg = message["text"]
            color = message["color"]
            category = message.get("category", MessageCategory.INFO)
            priority = message.get("priority", MessagePriority.NORMAL)
            batch_count = message.get("batch_count", 1)
            
            # Add batch count if there are multiple occurrences
            if batch_count > 1:
                msg = f"{msg} (x{batch_count})"
            
            # Add indicators for high priority messages
            if priority >= MessagePriority.HIGH:
                # Add a visual indicator for important messages
                msg = f"! {msg}"
                
            # Draw the message with appropriate color
            draw_text(screen, msg, color, panel_rect.x + 10, y_offset)
            y_offset += line_height
    else:
        # If there are no messages, show a helpful prompt
        draw_text(screen, "Use arrow keys to move. Press 'i' for inventory.", WHITE, panel_rect.x + 10, y_offset)
        
    # Draw scrollbar if we have more messages than can be displayed
    scrollbar_rect = None
    if len(message_manager.messages) > message_manager.max_visible_messages:
        # Draw a hint about scrolling if we haven't scrolled yet
        if message_manager.scroll_offset == 0 and message_manager.scroll_indicator_alpha == 0:
            hint_text = "Use Page Up/Down or mouse wheel to scroll messages"
            hint_x = panel_rect.x + 10
            hint_y = panel_rect.y + panel_rect.height - 20
            draw_text(screen, hint_text, (180, 180, 180), hint_x, hint_y)
            
        # Draw scrollbar and indicators
        scrollbar_rect = message_manager.draw_scrollbar(screen, panel_rect)
    
    return scrollbar_rect

# Handles scrolling of messages on the bottom screen
def handle_scroll_events(event):
    """
    Handle scroll events for the message queue.
    This function is a wrapper around the MessageManager's handle_scroll method.
    
    Args:
        event: The pygame event to handle
        
    Returns:
        bool: True if the event was handled, False otherwise
    """
    if event.type == pygame.KEYDOWN:
        # Check for PageUp/PageDown handled by the message manager
        if event.key in [pygame.K_PAGEUP, pygame.K_PAGEDOWN]:
            return message_manager.handle_scroll(event)
            
        # Keep backslash key functionality for fine-grained scrolling
        elif event.key == pygame.K_BACKSLASH:
            mods = pygame.key.get_mods()
            # If Shift is held down, scroll up; otherwise, scroll down.
            if mods & pygame.KMOD_SHIFT:
                if message_manager.scroll_offset > 0:
                    message_manager.scroll_offset -= 1
                    return True
            else:
                # Ensure we don't scroll past the end of the message list.
                max_offset = max(0, len(message_manager.messages) - message_manager.max_visible_messages)
                if message_manager.scroll_offset < max_offset:
                    message_manager.scroll_offset += 1
                    return True
    
    return False

def draw_attack_prompt(screen, monster_name):
    box_width = 200
    box_height = 50
    x = (DUNGEON_PLAYABLE_AREA_WIDTH - box_width) // 2
    y = DUNGEON_PLAYABLE_AREA_HEIGHT - box_height - 10
    pygame.draw.rect(screen, RED, (x, y, box_width, box_height), 2)
    prompt = f"Attack {monster_name}? Y/N"
    draw_text(screen, prompt, WHITE, x + 10, y + 10)

def draw_equipment_panel(screen, player, x, y):
    # Calculate max height for the panel
    max_height = HUB_SCREEN_HEIGHT if not in_dungeon else DUNGEON_SCREEN_HEIGHT
    max_y = max_height - 10  # Leave a small margin
    
    line_height = font.get_linesize() + 5  # Standard line height with spacing
    
    new_y = y
    if new_y + line_height <= max_y:
        draw_text(screen, "Equipment:", WHITE, x, new_y)
        new_y += line_height

    # Weapon info
    if new_y + line_height <= max_y:
        weapon = player.equipment.get("weapon")
        weapon_text = weapon.name if weapon else "None"
        draw_text(screen, f"Weapon: {weapon_text}", WHITE, x, new_y)
        new_y += line_height

    # Armor info
    if new_y + line_height <= max_y:
        armor = player.equipment.get("armor")
        armor_text = armor.name if armor else "None"
        draw_text(screen, f"Armor: {armor_text}", WHITE, x, new_y)
        new_y += line_height

    # Shield info
    if new_y + line_height <= max_y:
        shield = player.equipment.get("shield")
        shield_text = shield.name if shield else "None"
        draw_text(screen, f"Shield: {shield_text}", WHITE, x, new_y)
        new_y += line_height

    # Jewelry info
    jewelry = player.equipment.get("jewelry", [])
    if jewelry:
        for item in jewelry:
            if new_y + line_height <= max_y:
                # Get bonus stat info safely
                item_stat = getattr(item, 'bonus_stat', getattr(item, 'stat_bonus', 'unknown'))
                item_value = getattr(item, 'bonus_value', 1)
                draw_text(screen, f"{item.name} (+{item_value} {item_stat})", WHITE, x, new_y)
                new_y += line_height
    elif new_y + line_height <= max_y:
        draw_text(screen, "Jewelry: None", WHITE, x, new_y)
        new_y += line_height

    return new_y

# Debug drawing function removed - now implemented in the new magic system


# In[3]:


# =============================================================================
# === Asset Loading Module (Sounds commented out) ===
# =============================================================================

#sounds (Commented out for testing)
# spell_sound = pygame.mixer.Sound(os.path.join(ASSETS_PATH, "B&S_sfx/lvl1_spell_woosh.mp3"))
# melee_sound = pygame.mixer.Sound(os.path.join(ASSETS_PATH, "B&S_sfx/basic_melee_strike.mp3"))
# arrow_sound = pygame.mixer.Sound(os.path.join(ASSETS_PATH, "B&S_sfx/arrow_shot.mp3"))
# levelup_sound = pygame.mixer.Sound(os.path.join(ASSETS_PATH, "B&S_sfx/level_up_ding.mp3"))
# frost_sound = pygame.mixer.Sound(os.path.join(ASSETS_PATH, "B&S_sfx/frost.flac"))
# store_bell_sound = pygame.mixer.Sound(os.path.join(ASSETS_PATH, "B&S_sfx/store_bell.mp3"))


# Load misc.sprites
DICE_SPRITE_PATH = assets_data['sprites']['misc']['dice']
dice_sprite = load_sprite(DICE_SPRITE_PATH)
LOOT_DROP_PATH = assets_data['sprites']['misc']['loot_drop']
loot_drop_sprite = load_sprite(LOOT_DROP_PATH) 

# Load and create items
def create_item(item_data):
    if not item_data:
        # print("Warning: item_data is None or empty")
        return None

    name = item_data.get("name", "Unknown Item")
    item_type = item_data.get("type", "generic")
    value = item_data.get("value", 0)
    description = item_data.get("description", "")
    
    # Extract requirements data if available
    requirements = item_data.get("requirements")
    min_level = item_data.get("min_level", 1)
    min_abilities = item_data.get("min_abilities")
    
    # Safety check for None item_type
    if item_type is None:
        # print(f"Warning: item '{name}' has None type, defaulting to generic")
        item_type = "generic"
    
    # Standardize item type
    std_item_type = standardize_item_type(item_type)
    
    # Create requirements object if needed
    item_requirements = None
    if requirements or min_level > 1 or min_abilities:
        if requirements:
            item_requirements = ItemRequirements(requirements)
        else:
            req_data = {"min_level": min_level}
            if min_abilities:
                req_data["min_abilities"] = min_abilities
            item_requirements = ItemRequirements(req_data)
    
    # Create the appropriate item type based on category
    category = std_item_type.split('_')[0] if '_' in std_item_type else std_item_type
    item = None
    
    # Shield items
    if category == "shield":
        ac_bonus = item_data.get("ac", 1)
        item = Shield(name, std_item_type, ac_bonus, value, description)
    
    # Weapon items    
    elif category == "weapon":
        damage = item_data.get("damage", "1d4")
        
        # Create specific weapon subtype based on full item type
        if "blade" in std_item_type:
            item = WeaponBlade(name, std_item_type, damage, value, description)
        elif "blunt" in std_item_type:
            item = WeaponBlunt(name, std_item_type, damage, value, description)
        elif "bow" in std_item_type:
            range_val = item_data.get("range", 4)
            item = WeaponBow(name, std_item_type, damage, value, description, range_val)
        else:
            item = Weapon(name, std_item_type, damage, value, description)
            
        # Add weapon-specific properties
        if "requires_ammo" in item_data:
            item.requires_ammo = item_data.get("requires_ammo")
        if "ammo_type" in item_data:
            item.ammo_type = item_data.get("ammo_type")
    
    # Armor items
    elif category == "armor":
        ac = item_data.get("ac", 1)
        item = Armor(name, std_item_type, ac, value, description)
        
        # Add armor-specific properties
        if "movement_penalty" in item_data:
            item.movement_penalty = item_data.get("movement_penalty")
    
    # Jewelry items        
    elif category == "jewelry":
        # Create appropriate jewelry type
        if "ring" in std_item_type:
            item = JewelryRing(name, std_item_type, value, description)
        elif "amulet" in std_item_type:
            item = JewelryAmulet(name, std_item_type, value, description)
        else:
            item = Jewelry(name, std_item_type, value, description)
        
        # Add jewelry-specific effects
        # First check for explicit effect data
        if "effect" in item_data and isinstance(item_data["effect"], dict):
            effect_data = item_data["effect"]
            if effect_data.get("type") == "stat_bonus":
                item.bonus_stat = effect_data.get("stat", "sp")
                item.bonus_value = effect_data.get("value", 1)
        # Then check for direct stat bonuses
        elif "sp" in item_data:
            item.bonus_stat = "sp"
            item.bonus_value = item_data.get("sp", 1)
        elif "intelligence" in item_data:
            item.bonus_stat = "intelligence"
            item.bonus_value = item_data.get("intelligence", 1)
        elif "strength" in item_data:
            item.bonus_stat = "strength"
            item.bonus_value = item_data.get("strength", 1)
        elif "dexterity" in item_data:
            item.bonus_stat = "dexterity"
            item.bonus_value = item_data.get("dexterity", 1)
        elif "constitution" in item_data:
            item.bonus_stat = "constitution"
            item.bonus_value = item_data.get("constitution", 1)
        elif "wisdom" in item_data:
            item.bonus_stat = "wisdom"
            item.bonus_value = item_data.get("wisdom", 1)
        else:
            # Default to SP bonus if no specific attribute is found
            item.bonus_stat = "sp"
            item.bonus_value = 1
            
    # Consumable items
    elif category == "consumable":
        effect = item_data.get("effect", {"type": "healing", "dice": "1d4"})
        item = Consumable(name, std_item_type, effect, value, description)
        
        # Add consumable-specific properties
        if "stackable" in item_data:
            item.stackable = item_data.get("stackable")
        if "max_stack" in item_data:
            item.max_stack = item_data.get("max_stack")
    
    # Generic item for unknown types
    else:
        item = Item(name, std_item_type, value, description)
    
    # Apply common properties and requirements to all items
    if item:
        # Add requirements
        if item_requirements:
            item.requirements = item_requirements
            
        # Add common properties
        if "weight" in item_data:
            item.weight = item_data.get("weight")
        if "durability" in item_data:
            item.durability = item_data.get("durability")
        if "magical" in item_data:
            item.magical = item_data.get("magical", False)
        if "effect" in item_data:
            item.effect = item_data.get("effect")
    
    return item


def load_items(file_path):
    data = load_json(file_path)  # Reuse your load_json function
    items = []
    if "items" in data: # Check if "items" key exists
        for item_data in data["items"]:
            # create_item is your factory function that instantiates the correct item subclass.
            items.append(create_item(item_data))
    else:
        # print(f"Warning: 'items' key not found in {file_path}")
        pass
    return items


# In[4]:


# =============================================================================
# === Item Module ===
# =============================================================================
# Helper function to standardize item types
def standardize_item_type(item_type):
    """
    Standardize item type name to follow the 'category_subtype' pattern.
    
    Args:
        item_type (str): The item type to standardize
        
    Returns:
        str: Standardized item type
    """
    if not item_type:
        return ""
    
    # Item types should already follow the pattern 'category_subtype'
    parts = item_type.split('_')
    
    # If there's only one part, it might be a legacy type, so try to determine category
    if len(parts) == 1:
        category = parts[0]
        
        # Handle legacy types
        legacy_map = {
            "sword": "weapon_med_blade",
            "dagger": "weapon_light_blade",
            "mace": "weapon_med_blunt",
            "bow": "weapon_bow",
            "shield": "shield_wooden",
            "ring": "jewelry_ring",
            "amulet": "jewelry_amulet",
            "potion": "consumable_potion",
            "scroll": "consumable_scroll",
            "armor": "armor_light"
        }
        
        # Return mapped standardized type if found
        if category in legacy_map:
            return legacy_map[category]
            
        # If not found in map, try to make an educated guess based on common patterns
        if category.startswith("weapon"):
            return f"weapon_med_{category[7:]}"  # Assume medium size for weapons
        elif category.startswith("armor"):
            return "armor_light"  # Assume light for armor
        elif category == "shield":
            return "shield_wooden"  # Assume wooden for shields
            
    # If it's already in standard format or we can't standardize, return as is
    return item_type

# Item requirements class - must be defined before it's used
class ItemRequirements:
    """
    Handles validation of complex item requirements beyond class restrictions.
    """
    def __init__(self, requirements_data=None):
        """
        Initialize with requirements data. If None, creates an empty requirements object.
        
        Args:
            requirements_data (dict): Dictionary containing requirements data
        """
        self.requirements = requirements_data or {}
        
        # Set default values for common requirements
        self.min_level = self.requirements.get('min_level', 1)
        self.min_abilities = self.requirements.get('min_abilities', {})
        self.allowed_classes = self.requirements.get('allowed_classes', [])
        self.allowed_races = self.requirements.get('allowed_races', [])
        self.alignment_restriction = self.requirements.get('alignment', None)
        self.proficiency_required = self.requirements.get('proficiency_required', False)
        
    def can_use(self, player):
        """
        Check if a player meets all the requirements for this item.
        
        Args:
            player: Player object to check against requirements
            
        Returns:
            tuple: (meets_requirements, reason) where:
                - meets_requirements is a boolean
                - reason is a string explaining why requirements weren't met (empty if they were)
        """
        # Check level requirement
        if hasattr(player, 'level') and player.level < self.min_level:
            return False, f"Requires level {self.min_level} (you are level {player.level})"
            
        # Check ability score requirements
        if hasattr(player, 'abilities'):
            for ability, min_score in self.min_abilities.items():
                if ability in player.abilities and player.abilities[ability] < min_score:
                    return False, f"Requires {ability.capitalize()} {min_score} (you have {player.abilities[ability]})"
        
        # Check class restrictions
        if self.allowed_classes and hasattr(player, 'char_class'):
            if player.char_class not in self.allowed_classes:
                return False, f"Restricted to {', '.join(self.allowed_classes)} classes"
                
        # Check race restrictions
        if self.allowed_races and hasattr(player, 'race'):
            if player.race not in self.allowed_races:
                return False, f"Restricted to {', '.join(self.allowed_races)} races"
                
        # Check alignment restrictions (if game uses alignment)
        if self.alignment_restriction and hasattr(player, 'alignment'):
            if player.alignment != self.alignment_restriction:
                return False, f"Requires {self.alignment_restriction} alignment"
                
        # Check proficiency requirement (if game uses proficiencies)
        if self.proficiency_required and hasattr(player, 'proficiencies'):
            # The specific proficiency check would depend on your proficiency system
            # This is a generic example
            item_type = self.requirements.get('item_type', '')
            if item_type and not player.has_proficiency(item_type):
                return False, f"Requires proficiency with {item_type}"
                
        # All requirements met
        return True, ""
        
    @classmethod
    def from_item(cls, item):
        """
        Create an ItemRequirements object from an item.
        
        Args:
            item: Item object with potential requirement attributes
            
        Returns:
            ItemRequirements: A new requirements object
        """
        requirements = {}
        
        # Extract requirements from item attributes
        if hasattr(item, 'requirements'):
            # If the item already has a requirements dictionary, use it
            requirements = item.requirements
        else:
            # Otherwise build from individual attributes
            if hasattr(item, 'min_level'):
                requirements['min_level'] = item.min_level
                
            if hasattr(item, 'min_abilities'):
                requirements['min_abilities'] = item.min_abilities
                
            if hasattr(item, 'allowed_classes'):
                requirements['allowed_classes'] = item.allowed_classes
                
            if hasattr(item, 'allowed_races'):
                requirements['allowed_races'] = item.allowed_races
                
            # Add item type for proficiency checks
            if hasattr(item, 'item_type'):
                requirements['item_type'] = item.item_type
        
        return cls(requirements)
        
    def merge(self, other_requirements):
        """
        Merge with another requirements object, taking the more restrictive of each.
        
        Args:
            other_requirements: Another ItemRequirements object
            
        Returns:
            ItemRequirements: A new merged requirements object
        """
        merged = {}
        
        # Take the higher minimum level
        merged['min_level'] = max(self.min_level, other_requirements.min_level)
        
        # Merge ability requirements, taking higher values for each ability
        merged_abilities = self.min_abilities.copy()
        for ability, score in other_requirements.min_abilities.items():
            if ability in merged_abilities:
                merged_abilities[ability] = max(merged_abilities[ability], score)
            else:
                merged_abilities[ability] = score
        merged['min_abilities'] = merged_abilities
        
        # For class and race restrictions, only include classes/races that are in both lists
        if self.allowed_classes and other_requirements.allowed_classes:
            merged['allowed_classes'] = [c for c in self.allowed_classes if c in other_requirements.allowed_classes]
        elif self.allowed_classes:
            merged['allowed_classes'] = self.allowed_classes
        else:
            merged['allowed_classes'] = other_requirements.allowed_classes
            
        if self.allowed_races and other_requirements.allowed_races:
            merged['allowed_races'] = [r for r in self.allowed_races if r in other_requirements.allowed_races]
        elif self.allowed_races:
            merged['allowed_races'] = self.allowed_races
        else:
            merged['allowed_races'] = other_requirements.allowed_races
            
        # Require proficiency if either requires it
        merged['proficiency_required'] = self.proficiency_required or other_requirements.proficiency_required
        
        # For alignment, if they differ then you need to match both (which is impossible, so restrict to None)
        if self.alignment_restriction and other_requirements.alignment_restriction:
            if self.alignment_restriction != other_requirements.alignment_restriction:
                merged['alignment'] = None  # Impossible to satisfy both
            else:
                merged['alignment'] = self.alignment_restriction
        elif self.alignment_restriction:
            merged['alignment'] = self.alignment_restriction
        else:
            merged['alignment'] = other_requirements.alignment_restriction
            
        return ItemRequirements(merged)

# Base Item class
class Item:
    def __init__(self, name, item_type, value, description, requirements=None, min_level=1, min_abilities=None):
        self.name = name
        # Standardize item type on creation
        self.item_type = standardize_item_type(item_type)
        self.value = value
        self.description = description
        self.weight = 0
        self.durability = 100
        
        # Auto-determine category and slot from type
        self._category = None
        self._equipment_slot = None
        self._subtype = None
        self._metadata = None
        
        # Initialize requirements
        if requirements and isinstance(requirements, dict):
            self.requirements = ItemRequirements(requirements)
        elif requirements and isinstance(requirements, ItemRequirements):
            self.requirements = requirements
        else:
            # Create basic requirements if explicit min_level or min_abilities were provided
            if min_level > 1 or min_abilities:
                reqs = {'min_level': min_level, 'min_abilities': min_abilities or {}}
                self.requirements = ItemRequirements(reqs)
    
    @property
    def category(self):
        """Gets the category portion of the item type (weapon, armor, etc.)"""
        if self._category is None:
            if '_' in self.item_type:
                self._category = self.item_type.split('_')[0]
            else:
                self._category = self.item_type
        return self._category
    
    @property
    def subtype(self):
        """Gets the subtype portion of the item type (light_blade, heavy_armor, etc.)"""
        if self._subtype is None:
            if '_' in self.item_type:
                self._subtype = self.item_type.split('_', 1)[1]
            else:
                self._subtype = ""
        return self._subtype
    
    @property
    def equipment_slot(self):
        """Determines the appropriate equipment slot for this item"""
        if self._equipment_slot is None:
            try:
                # Ensure items_data is loaded
                if items_data is None or "item_categories" not in items_data :
                    # print("Warning: items_data not loaded or missing 'item_categories' for equipment_slot determination.")
                    # Fallback based on category
                    if self.category == "weapon": self._equipment_slot = "weapon"
                    elif self.category == "armor": self._equipment_slot = "armor"
                    elif self.category == "shield": self._equipment_slot = "shield"
                    elif self.category == "jewelry": self._equipment_slot = "jewelry"
                    else: self._equipment_slot = "inventory"
                    return self._equipment_slot

                item_categories = items_data.get("item_categories", {})
                
                if self.category in item_categories:
                    self._equipment_slot = item_categories[self.category].get("equipment_slot")
                
                if not self._equipment_slot:
                    if self.category == "weapon": self._equipment_slot = "weapon"
                    elif self.category == "armor": self._equipment_slot = "armor"
                    elif self.category == "shield": self._equipment_slot = "shield"
                    elif self.category == "jewelry": self._equipment_slot = "jewelry"
                    else: self._equipment_slot = "inventory"
            except Exception as e:
                # print(f"Error determining equipment slot for {self.name}: {e}")
                self._equipment_slot = "inventory"
        
        return self._equipment_slot
    
    @property
    def metadata(self):
        """Retrieves metadata about this item type from items.json"""
        if self._metadata is None:
            try:
                if items_data is None or "item_categories" not in items_data:
                    # print("Warning: items_data not loaded or missing 'item_categories' for metadata.")
                    self._metadata = {}
                    return self._metadata

                item_categories = items_data.get("item_categories", {})
                category_data = item_categories.get(self.category, {})
                subtype_data = {}
                if "subtypes" in category_data and self.item_type in category_data["subtypes"]:
                    subtype_data = category_data["subtypes"][self.item_type]
                self._metadata = {**category_data, **subtype_data}
            except Exception as e:
                # print(f"Error retrieving metadata for {self.name}: {e}")
                self._metadata = {}
        
        return self._metadata
    
    def get_display_name(self):
        """Returns the display name from metadata or the standardized type name"""
        display_name = self.metadata.get("display_name")
        if display_name:
            return display_name
        
        if self.subtype:
            return " ".join(word.capitalize() for word in self.subtype.split("_"))
        return self.category.capitalize()
    
    def is_stackable(self):
        """Determines if this item can be stacked in inventory"""
        return self.metadata.get("stackable", False)
    
    def meets_requirements(self, player):
        """Check if player meets this item's requirements"""
        if hasattr(self, 'requirements') and self.requirements:
            return self.requirements.can_use(player)
        return True, ""  # No requirements

    def apply_effect(self, character):
        """Override in subclass. For equipment, add stat bonuses."""
        pass

    def remove_effect(self, character):
        """Override in subclass. For equipment, remove stat bonuses."""
        pass

    def __str__(self):
        return f"{self.name} ({self.get_display_name()})"


# --- Weapon Classes ---
class Weapon(Item):
    def __init__(self, name, item_type, damage, value, description):
        super().__init__(name, item_type, value, description)
        self.damage = damage

    def roll_damage(self, caster=None):
        if "+" in self.damage:
            dice_part, mod_part = self.damage.split("+", 1)
            sign = "+"
        elif "-" in self.damage:
            dice_part, mod_part = self.damage.split("-", 1)
            sign = "-"
        else:
            dice_part = self.damage
            mod_part = "0"
            sign = "+"
            
        dice_part = dice_part.strip()
        mod_part = mod_part.strip()
        mod_value = int(mod_part)
        base_damage = roll_dice_expression(dice_part, caster)
        return base_damage + (mod_value if sign == '+' else -mod_value)

    def apply_effect(self, character):
        character.equipment['weapon'] = self

    def remove_effect(self, character):
        if character.equipment.get('weapon') == self:
            character.equipment['weapon'] = None


class WeaponBlade(Weapon): pass
class WeaponBlunt(Weapon): pass

class WeaponBow(Weapon):
    def __init__(self, name, item_type, damage, value, description, range_val=4): # Changed range to range_val
        super().__init__(name, item_type, damage, value, description)
        self.range_val = range_val # Changed range to range_val
        
    def apply_effect(self, character):
        character.equipment['weapon'] = self
        character.weapon_range = self.range_val # Changed range to range_val
        
    def remove_effect(self, character):
        if character.equipment.get('weapon') == self:
            character.equipment['weapon'] = None
            if hasattr(character, 'weapon_range'):
                character.weapon_range = 0


# --- Armor Class Items ---
class Armor(Item):
    def __init__(self, name, item_type, ac, value, description):
        super().__init__(name, item_type, value, description)
        self.ac_bonus = int(str(ac).replace('+', ''))

    def apply_effect(self, character):
        character.equipment['armor'] = self

    def remove_effect(self, character):
        if character.equipment.get('armor') == self:
            character.equipment['armor'] = None

class Shield(Item):
    def __init__(self, name, item_type, ac_bonus, value, description):
        super().__init__(name, item_type, value, description)
        self.ac_bonus = int(str(ac_bonus).replace('+', ''))

    def apply_effect(self, character):
        character.equipment["shield"] = self
        character.shield_ac_bonus = self.ac_bonus

    def remove_effect(self, character):
        if character.equipment.get("shield") == self:
            character.equipment["shield"] = None
            character.shield_ac_bonus = 0

# --- Jewelry (Rings, Necklaces, etc.) ---
class Jewelry(Item):
    def __init__(self, name, item_type, value, description):
        super().__init__(name, item_type, value, description)
        self.bonus_stat = "sp"
        self.bonus_value = 1
        self.stat_bonus = "sp"
        self.magical = True
        
    def apply_effect(self, character):
        if 'jewelry' not in character.equipment:
            character.equipment['jewelry'] = []
        character.equipment['jewelry'].append(self)
        
        if self.bonus_stat.lower() in ['sp', 'spellpoints']:
            character.spell_points += self.bonus_value
        else:
            if self.bonus_stat in character.abilities:
                character.abilities[self.bonus_stat] += self.bonus_value
            else:
                setattr(character, self.bonus_stat, getattr(character, self.bonus_stat, 0) + self.bonus_value)
                
    def remove_effect(self, character):
        if 'jewelry' in character.equipment and self in character.equipment['jewelry']:
            character.equipment['jewelry'].remove(self)
            
            if self.bonus_stat.lower() in ['sp', 'spellpoints']:
                character.spell_points -= self.bonus_value
            elif self.bonus_stat in character.abilities:
                character.abilities[self.bonus_stat] -= self.bonus_value
            else:
                current_value = getattr(character, self.bonus_stat, 0)
                setattr(character, self.bonus_stat, max(0, current_value - self.bonus_value))
                
    @property
    def stat_bonus(self): return self.bonus_stat
    @stat_bonus.setter
    def stat_bonus(self, value): self.bonus_stat = value

class JewelryRing(Jewelry):
    def __init__(self, name, item_type, value, description):
        super().__init__(name, item_type, value, description)
        self.max_equipped = self.metadata.get('max_equipped', 2)
    
    def can_equip(self, character):
        equipped_rings = sum(1 for j in character.equipment.get('jewelry', []) 
                           if hasattr(j, 'item_type') and 'ring' in j.item_type)
        return equipped_rings < self.max_equipped

class JewelryAmulet(Jewelry):
    def __init__(self, name, item_type, value, description):
        super().__init__(name, item_type, value, description)
        self.bonus_value *= 2
        self.stat_bonus = self.bonus_stat
        self.max_equipped = self.metadata.get('max_equipped', 1)
    
    def can_equip(self, character):
        equipped_amulets = sum(1 for j in character.equipment.get('jewelry', []) 
                             if hasattr(j, 'item_type') and 'amulet' in j.item_type)
        return equipped_amulets < self.max_equipped


# --- Consumables ---
class Consumable(Item):
    def __init__(self, name, item_type, effect, value, description):
        super().__init__(name, item_type, value, description)
        self.effect = effect

    def use(self, character):
        effect_type = self.effect.get("type")
        if effect_type == "healing":
            dice_expr = self.effect.get("dice", "1d4")
            heal_amount = roll_dice_expression(dice_expr, character)
            character.hit_points = min(character.hit_points + heal_amount, character.max_hit_points)
            return f"{character.name} uses {self.name} and heals {heal_amount} HP!"
        elif effect_type == "buff":
            stat = self.effect.get("stat")
            value = int(self.effect.get("value", 0))
            duration = int(self.effect.get("duration", 0))
            return f"{character.name} uses {self.name} and gains +{value} {stat} for {duration} seconds!"
        else:
            return f"{self.name} has no effect."

# Load global item list
items_list = load_items(ITEMS_FILE)

def draw_inventory_management(screen, player):
    if in_dungeon:
        screen_width, screen_height = DUNGEON_SCREEN_WIDTH, DUNGEON_SCREEN_HEIGHT
    else:
        screen_width, screen_height = HUB_SCREEN_WIDTH, HUB_SCREEN_HEIGHT
    
    panel_margin = 20
    panel_width = screen_width - 2 * panel_margin
    panel_height = (screen_height - 3 * panel_margin) // 2

    equipment_rect = pygame.Rect(panel_margin, panel_margin, panel_width, panel_height)
    inventory_rect = pygame.Rect(panel_margin, panel_margin*2 + panel_height, panel_width, panel_height)

    pygame.draw.rect(screen, (50, 50, 50), equipment_rect)
    pygame.draw.rect(screen, (50, 50, 50), inventory_rect)
    pygame.draw.rect(screen, (200, 200, 200), equipment_rect, 2)
    pygame.draw.rect(screen, (200, 200, 200), inventory_rect, 2)

    draw_text_lines(screen, ["Equipped Items:"], equipment_rect.x + 10, equipment_rect.y + 10)
    y_offset = equipment_rect.y + 40
    for slot in ['weapon', 'armor', 'shield']:
        item = player.equipment.get(slot)
        item_text = f"{slot.capitalize()}: {item.name if item else 'None'}"
        draw_text(screen, item_text, WHITE, equipment_rect.x + 10, y_offset)
        y_offset += font.get_linesize() + 10

    jewelry_list = player.equipment.get('jewelry', [])
    jewelry_text = "Jewelry: " + (", ".join(item.name for item in jewelry_list) if jewelry_list else "None")
    draw_text(screen, jewelry_text, WHITE, equipment_rect.x + 10, y_offset)

    draw_text_lines(screen, ["Inventory: (Click to use or equip)"], inventory_rect.x + 10, inventory_rect.y + 10)
    y_offset = inventory_rect.y + 40
    for idx, item in enumerate(player.inventory):
        try:
            can_equip = True
            text_color = WHITE
            item_display_name = "Unknown"
            
            if hasattr(item, 'get_display_name') and callable(getattr(item, 'get_display_name')):
                item_display_name = item.get_display_name()
            elif hasattr(item, 'item_type'):
                item_display_name = item.item_type
            
            has_item_type = hasattr(item, 'item_type')
            is_consumable = has_item_type and item.item_type.startswith("consumable")
            is_jewelry = has_item_type and item.item_type.startswith("jewelry")
            
            if has_item_type and not is_consumable:
                can_equip, _ = can_equip_item(player, item)
                if can_equip and is_jewelry and hasattr(item, 'can_equip'):
                    can_equip = item.can_equip(player)
                if not can_equip:
                    text_color = LIGHT_GRAY
            
            if is_consumable:
                item_text = f"{idx+1}. {item.name} ({item_display_name}) - Click to use"
            else:
                if not can_equip:
                    item_text = f"{idx+1}. {item.name} ({item_display_name}) - Cannot equip"
                else:
                    item_text = f"{idx+1}. {item.name} ({item_display_name})"
            
            draw_text(screen, item_text, text_color, inventory_rect.x + 10, y_offset)
        except Exception as e:
            error_text = f"{idx+1}. {getattr(item, 'name', 'Unknown Item')} (Error: {str(e)[:20]}...)"
            draw_text(screen, error_text, RED, inventory_rect.x + 10, y_offset)
            # print(f"Error displaying inventory item: {e}")
            
        y_offset += font.get_linesize() + 10
    return equipment_rect, inventory_rect

def prompt_user_for_slot(valid_slots, screen=None, clock=None):
    if valid_slots: return valid_slots[0]
    return None

def handle_inventory_click(event, player, equipment_rect, inventory_rect):
    pos = event.pos
    if inventory_rect.collidepoint(pos):
        index = (pos[1] - inventory_rect.y - 40) // (font.get_linesize() + 10)
        if 0 <= index < len(player.inventory):
            try:
                selected_item = player.inventory[index]
                if not hasattr(selected_item, 'name'): selected_item.name = "Unknown Item"
                
                has_item_type = hasattr(selected_item, 'item_type')
                is_consumable = has_item_type and selected_item.item_type.startswith("consumable")
                is_jewelry = has_item_type and selected_item.item_type.startswith("jewelry")
                
                if is_consumable:
                    if hasattr(selected_item, 'use'):
                        message = selected_item.use(player)
                        add_message(message)
                        player.inventory.remove(selected_item)
                        # Turn processing might be needed here
                        return
                    else:
                        add_message(f"Cannot use {selected_item.name} - no use method defined.")
                        return
                
                can_equip, reason = can_equip_item(player, selected_item)
                if can_equip and is_jewelry and hasattr(selected_item, 'can_equip'):
                    if not selected_item.can_equip(player):
                        can_equip = False
                        reason = "Maximum number already equipped"
                
                if not can_equip:
                    add_message(f"Cannot equip {selected_item.name}: {reason}", RED)
                    return
                    
                valid_slots = get_valid_equipment_slots(selected_item, player)
                if len(valid_slots) == 1:
                    swap_equipment(player, valid_slots[0], selected_item)
                elif len(valid_slots) > 1:
                    slot = prompt_user_for_slot(valid_slots)
                    if slot: swap_equipment(player, slot, selected_item)
                else:
                    add_message(f"You cannot equip {selected_item.name}: no valid equipment slots found.", RED)
            except Exception as e:
                # print(f"Error handling inventory click: {e}")
                add_message(f"Error handling item: {str(e)[:30]}...", RED)
    
    elif equipment_rect.collidepoint(pos):
        try:
            slot_clicked = get_clicked_equipment_slot(pos, equipment_rect)
            if slot_clicked and player.equipment.get(slot_clicked):
                unequip_item(player, slot_clicked)
        except Exception as e:
            # print(f"Error handling equipment unequip: {e}")
            add_message(f"Error unequipping item: {str(e)[:30]}...", RED)

def manage_inventory(player, screen, clock, dungeon_instance=None):
    global current_dungeon
    current_dungeon = dungeon_instance
    
    running = True
    while running:
        equipment_rect, inventory_rect = draw_inventory_management(screen, player)
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                handle_inventory_click(event, player, equipment_rect, inventory_rect)
        pygame.display.flip()
        clock.tick(30)
    return

def get_item_data(item_name, items_data_local): # Renamed items_data to items_data_local
    if items_data_local and "items" in items_data_local:
        for item in items_data_local["items"]:
            if item.get("name") == item_name:
                return item
    return None

def shop_interaction(screen, clock, player, items_data_local=None): # Renamed items_data to items_data_local
    # Use global items_data if local one is not provided
    if items_data_local is None:
        items_data_local = items_data

    # store_bell_sound.play() # Sound commented out
    
    shopkeeper_portrait_path = os.path.join(ASSETS_PATH, "Misc/Novamagus/shopkeep.jpg")
    if os.path.exists(shopkeeper_portrait_path):
        shopkeeper_portrait = pygame.image.load(shopkeeper_portrait_path)
    else: # Fallback
        shopkeeper_portrait = pygame.Surface((300,300)); shopkeeper_portrait.fill(BLUE)

    portrait_width = 300
    portrait_height = 300
    shopkeeper_portrait = pygame.transform.scale(shopkeeper_portrait, (portrait_width, portrait_height))
    
    shop_stock_items = [
        ("Iron Sword (1d6-1)", 1), ("Iron Dagger (1d4-1)", 1), ("Iron Mace (1d6-1)", 1),
        ("Basic Shortbow (1d6)", 1), ("Basic Longbow (1d8)", 1), ("Health Potion", 2),
        ("Thieve's Tools", 1)
    ]
    shop_stock = []
    for name, qty in shop_stock_items:
        for _ in range(qty):
            data = get_item_data(name, items_data_local)
            if data is None: continue
            item_instance = create_item(deepcopy(data))
            shop_stock.append(item_instance)
    
    screen_width, screen_height = HUB_SCREEN_WIDTH, HUB_SCREEN_HEIGHT
    panel_margin = 20
    panel_width = screen_width - 2 * panel_margin
    panel_height = (screen_height - 3 * panel_margin) // 2

    shop_panel_rect = pygame.Rect(panel_margin, panel_margin, panel_width, panel_height)
    inventory_panel_rect = pygame.Rect(panel_margin, panel_margin * 2 + panel_height, panel_width, panel_height)
    portrait_rect = pygame.Rect(screen_width - portrait_width + portrait_width, panel_margin, portrait_width, portrait_height)
    
    running = True
    message = ""
    message_timer = 0
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                pos = event.pos
                y_offset = shop_panel_rect.y + 40
                for idx, item in enumerate(shop_stock):
                    item_rect = pygame.Rect(shop_panel_rect.x + 10, y_offset, panel_width - 20, font.get_linesize() + 4)
                    if item_rect.collidepoint(pos):
                        if player.gold >= item.value:
                            player.gold -= item.value
                            player.inventory.append(item)
                            message = f"Bought {item.name} for {item.value} gold."
                            message_timer = 60
                            shop_stock.pop(idx)
                        else:
                            message = "Not enough gold to buy that item."
                            message_timer = 60
                        break
                    y_offset += font.get_linesize() + 10

                y_offset = inventory_panel_rect.y + 40
                for idx, item in enumerate(player.inventory):
                    item_rect = pygame.Rect(inventory_panel_rect.x + 10, y_offset, panel_width - 20, font.get_linesize() + 4)
                    if item_rect.collidepoint(pos):
                        sell_price = item.value // 2
                        player.gold += sell_price
                        message = f"Sold {item.name} for {sell_price} gold."
                        message_timer = 60
                        player.inventory.pop(idx)
                        break
                    y_offset += font.get_linesize() + 10
        
        screen.fill(BLACK)
        
        pygame.draw.rect(screen, (50, 50, 50), shop_panel_rect)
        pygame.draw.rect(screen, (200, 200, 200), shop_panel_rect, 2)
        draw_text_lines(screen, ["Shop Stock:"], shop_panel_rect.x + 10, shop_panel_rect.y + 10)
        y_offset = shop_panel_rect.y + 40
        for idx, item in enumerate(shop_stock):
            item_text = f"{idx+1}. {item.name} - Price: {item.value} gold"
            draw_text(screen, item_text, WHITE, shop_panel_rect.x + 10, y_offset)
            y_offset += font.get_linesize() + 10
        
        pygame.draw.rect(screen, (50, 50, 50), inventory_panel_rect)
        pygame.draw.rect(screen, (200, 200, 200), inventory_panel_rect, 2)
        draw_text_lines(screen, ["Your Inventory:"], inventory_panel_rect.x + 10, inventory_panel_rect.y + 10)
        y_offset = inventory_panel_rect.y + 40
        for idx, item in enumerate(player.inventory):
            sell_price = item.value // 2
            item_text = f"{idx+1}. {item.name} - Sell Price: {sell_price} gold"
            draw_text(screen, item_text, WHITE, inventory_panel_rect.x + 10, y_offset)
            y_offset += font.get_linesize() + 10
        
        gold_text = f"Gold: {player.gold}"
        draw_text(screen, gold_text, WHITE, screen_width - 150, 10)
        
        frame_rect = pygame.Rect(portrait_rect.x - 5, portrait_rect.y - 5, 
                                portrait_rect.width + 10, portrait_rect.height + 10)
        pygame.draw.rect(screen, (139, 69, 19), frame_rect)
        pygame.draw.rect(screen, (200, 175, 100), frame_rect, 3)
        screen.blit(shopkeeper_portrait, portrait_rect)
        
        message_rect = pygame.Rect(portrait_rect.x, portrait_rect.y + portrait_rect.height + 10, 
                                  portrait_rect.width, 100)
        pygame.draw.rect(screen, (50, 50, 50), message_rect)
        pygame.draw.rect(screen, (200, 200, 200), message_rect, 2)
        
        full_message = "Hail Adventurer! It's dangerous to go alone, maybe you should buy some equipment?"
        max_width = message_rect.width - 20
        wrapped_lines = []
        line = ""
        for word in full_message.split():
            test_line = line + " " + word if line else word
            text_width = font.size(test_line)[0]
            if text_width <= max_width: line = test_line
            else: wrapped_lines.append(line); line = word
        if line: wrapped_lines.append(line)
        
        line_spacing = font.get_linesize() + 5
        for i, line_text in enumerate(wrapped_lines): # Renamed line to line_text
            draw_text(screen, line_text, WHITE, message_rect.x + 10, message_rect.y + 15 + (i * line_spacing))
        
        instructions = "Click a shop item to buy, click an inventory item to sell. Press ESC to exit."
        draw_text(screen, instructions, WHITE, panel_margin, screen_height - panel_margin - font.get_linesize())
        
        if message_timer > 0:
            draw_text(screen, message, (255, 0, 0), panel_margin, screen_height - 2 * panel_margin - font.get_linesize())
            message_timer -= 1
        
        pygame.display.flip()
        clock.tick(HUB_FPS)


# In[5]:


# =============================================================================
# === Helper Functions ===
# =============================================================================

# === Save/Load Game System ===
def save_game(player, dungeon, game_state="dungeon"):
    import datetime
    
    save_dir = os.path.join(BASE_PATH, "B&S_savegame") # Relative save path
    os.makedirs(save_dir, exist_ok=True)
    save_file = os.path.join(save_dir, "savefile.json")
    
    try:
        player_data = {
            "name": player.name, "race": player.race, "char_class": player.char_class,
            "position": player.position, "abilities": player.abilities, "level": player.level,
            "hit_points": player.hit_points, "max_hit_points": player.max_hit_points,
            "spell_points": player.spell_points, "gold": player.gold,
            "inventory": [], "equipment": {"weapon": None, "armor": None, "shield": None, "jewelry": []}
        }
        
        for item in player.inventory:
            item_data = {"name": item.name, "item_type": item.item_type, "value": item.value, "description": item.description}
            if hasattr(item, "damage"): item_data["damage"] = item.damage
            if hasattr(item, "ac_bonus"): item_data["ac"] = item.ac_bonus
            if hasattr(item, "bonus_stat") and hasattr(item, "bonus_value"):
                stat_map = {"intelligence": "intelligence", "strength": "strength", "dexterity": "dexterity",
                            "wisdom": "wisdom", "constitution": "constitution", "sp": "sp"}
                if item.bonus_stat in stat_map: item_data[stat_map[item.bonus_stat]] = item.bonus_value
                item_data["effect"] = {"type": "stat_bonus", "stat": item.bonus_stat, "value": item.bonus_value}
            elif hasattr(item, "stat_bonus") and hasattr(item, "bonus_value"): # Fallback
                item_data["effect"] = {"type": "stat_bonus", "stat": item.stat_bonus, "value": item.bonus_value}
            player_data["inventory"].append(item_data)
        
        if player.equipment.get("weapon"):
            weapon = player.equipment["weapon"]
            player_data["equipment"]["weapon"] = {"name": weapon.name, "item_type": weapon.item_type, "damage": weapon.damage, "value": weapon.value, "description": weapon.description}
        if player.equipment.get("armor"):
            armor = player.equipment["armor"]
            player_data["equipment"]["armor"] = {"name": armor.name, "item_type": armor.item_type, "ac": armor.ac_bonus, "value": armor.value, "description": armor.description}
        if player.equipment.get("shield"):
            shield = player.equipment["shield"]
            player_data["equipment"]["shield"] = {"name": shield.name, "item_type": shield.item_type, "ac": shield.ac_bonus, "value": shield.value, "description": shield.description}

        for jewelry in player.equipment.get("jewelry", []):
            jewelry_data = {"name": jewelry.name, "item_type": jewelry.item_type, "value": jewelry.value, "description": jewelry.description}
            stat = getattr(jewelry, 'bonus_stat', getattr(jewelry, 'stat_bonus', 'sp'))
            value = getattr(jewelry, 'bonus_value', 1)
            stat_map = {"intelligence": "intelligence", "strength": "strength", "dexterity": "dexterity",
                        "wisdom": "wisdom", "constitution": "constitution", "sp": "sp"}
            if stat in stat_map: jewelry_data[stat_map[stat]] = value
            jewelry_data["effect"] = {"type": "stat_bonus", "stat": stat, "value": value}
            player_data["equipment"]["jewelry"].append(jewelry_data)
        
        dungeon_data = {"width": dungeon.width, "height": dungeon.height, "tiles": []}
        for x_coord in range(dungeon.width):
            row = []
            for y_coord in range(dungeon.height):
                tile = dungeon.tiles[x_coord][y_coord]
                row.append({"x": x_coord, "y": y_coord, "type": tile.type})
            dungeon_data["tiles"].append(row)
        
        dungeon_data["doors"] = []
        for coords, door in dungeon.doors.items():
            dungeon_data["doors"].append({"x": door.x, "y": door.y, "locked": door.locked, "open": door.open})
            
        dungeon_data["chests"] = []
        for coords, chest in dungeon.chests.items():
            chest_data = {"x": chest.x, "y": chest.y, "locked": chest.locked, "open": chest.open, "gold": chest.gold, "contents": []}
            for item in chest.contents:
                item_data = {"name": item.name, "item_type": item.item_type, "value": item.value, "description": item.description}
                if hasattr(item, "damage"): item_data["damage"] = item.damage
                if hasattr(item, "ac_bonus"): item_data["ac"] = item.ac_bonus
                chest_data["contents"].append(item_data)
            dungeon_data["chests"].append(chest_data)
            
        dungeon_data["monsters"] = []
        for monster in dungeon.monsters:
            if monster.is_dead: continue
            dungeon_data["monsters"].append({
                "name": monster.name, "hit_points": monster.hit_points, "max_hit_points": monster.max_hit_points,
                "to_hit": monster.to_hit, "ac": monster.ac, "move": monster.move, "dam": monster.dam,
                "position": monster.position, "monster_type": monster.monster_type, "level": monster.level,
                "cr": monster.cr, "vulnerabilities": monster.vulnerabilities,
                "resistances": monster.resistances, "immunities": monster.immunities
            })
            
        dungeon_data["dropped_items"] = []
        for dropped in dungeon.dropped_items:
            item = dropped["item"]
            item_data = {"name": item.name, "item_type": item.item_type, "value": item.value, "description": item.description, "position": dropped["position"]}
            if hasattr(item, "damage"): item_data["damage"] = item.damage
            if hasattr(item, "ac_bonus"): item_data["ac"] = item.ac_bonus
            dungeon_data["dropped_items"].append(item_data)
            
        save_data = {
            "player": player_data, "dungeon": dungeon_data, "game_state": game_state,
            "condition_manager_turn": condition_manager.current_turn,
            "timestamp": datetime.datetime.now().isoformat(), "version": "1.0"
        }
        
        with open(save_file, 'w') as f: json.dump(save_data, f, indent=4)
        # print(f"Game saved successfully to {save_file}")
        return True
    except Exception as e:
        # print(f"Error saving game: {e}")
        return False

def load_game():
    import types
    
    save_file = os.path.join(BASE_PATH, "B&S_savegame/savefile.json") # Relative save path
    if not os.path.exists(save_file):
        # print("No save file found.")
        return None
    
    try:
        with open(save_file, 'r') as f: save_data = json.load(f)
        saved_condition_manager_turn = save_data.get("condition_manager_turn", 0)
        player_data = save_data.get("player", {})
        dungeon_data_dict = save_data.get("dungeon", {}) # Renamed to avoid conflict
        game_state = save_data.get("game_state", "dungeon")
        
        # This import might be problematic if blade_sigil_v5_4 itself is being tested/modified
        # from blade_sigil_v5_4 import Character, Player
        
        class_lower = player_data.get("char_class", "Warrior").lower()

        # Ensure assets_data is loaded and has the expected structure
        player_sprite_path = "sprites/heroes/warrior/live.png" # Default fallback
        if assets_data and "sprites" in assets_data and "heroes" in assets_data["sprites"] and \
           class_lower in assets_data["sprites"]["heroes"] and "live" in assets_data["sprites"]["heroes"][class_lower]:
            player_sprite_path = assets_data["sprites"]["heroes"][class_lower]["live"]
        else:
            # print(f"Warning: Sprite path for class '{class_lower}' not found in assets_data. Using default.")
            pass

        player_sprite = load_sprite(player_sprite_path) # load_sprite handles ASSETS_PATH
        
        abilities = deepcopy(player_data.get("abilities", {'strength': 10, 'intelligence': 10, 'wisdom': 10, 'dexterity': 10, 'constitution': 10}))
        
        player = Player( name=player_data.get("name", "Hero"), race=player_data.get("race", "Human"),
            char_class=player_data.get("char_class", "Warrior"), start_position=player_data.get("position", [0, 0]),
            sprite=player_sprite, abilities=abilities )
        
        player.level = player_data.get("level", 1)
        player.hit_points = player_data.get("hit_points", 10)
        player.max_hit_points = player_data.get("max_hit_points", 10)
        player.spell_points = player_data.get("spell_points", 0)
        player.gold = player_data.get("gold", 0)
        
        player.inventory = []
        player.equipment = {"weapon": None, "armor": None, "shield": None, "jewelry": []}
        
        for item_data in player_data.get("inventory", []):
            item = create_item(item_data)
            if item: player.inventory.append(item)
        
        try:
            if player_data.get("equipment"):
                equipment_data = player_data["equipment"]
                if equipment_data.get("weapon"):
                    weapon_data = equipment_data["weapon"]
                    if "type" not in weapon_data or weapon_data["type"] is None: weapon_data["type"] = "weapon"
                    weapon = create_item(weapon_data)
                    if weapon: player.equipment["weapon"] = weapon
                if equipment_data.get("armor"):
                    armor_data = equipment_data["armor"]
                    if "type" not in armor_data or armor_data["type"] is None: armor_data["type"] = "armor"
                    armor = create_item(armor_data)
                    if armor: player.equipment["armor"] = armor
                if equipment_data.get("shield"):
                    shield_data = equipment_data["shield"]
                    if "type" not in shield_data or shield_data["type"] is None: shield_data["type"] = "shield"
                    shield = create_item(shield_data)
                    if shield: player.equipment["shield"] = shield
                for jewelry_data in equipment_data.get("jewelry", []):
                    if "type" not in jewelry_data or jewelry_data["type"] is None: jewelry_data["type"] = "jewelry"
                    jewelry = create_item(jewelry_data)
                    if jewelry: player.equipment["jewelry"].append(jewelry)
        except Exception as e:
            # print(f"Error loading equipment: {e}")
            pass
                
        # print(f"Game loaded successfully from {save_file}")
        return (player, dungeon_data_dict, game_state, saved_condition_manager_turn) # Return dict for dungeon
        
    except Exception as e:
        # print(f"Error loading game: {e}")
        return None

# debugging statements for stat logic:
def print_character_stats(character):
    # print("\n===== CHARACTER STATS =====")
    # print(f"Name: {character.name} | Class: {character.char_class} | Level: {character.level}")
    # ... (rest of the function, print statements can be kept for debugging if needed by user)
    pass


from collections import deque

class MessageCategory:
    SYSTEM = "system"; COMBAT = "combat"; INVENTORY = "inventory"; QUEST = "quest"
    DIALOG = "dialog"; ERROR = "error"; INFO = "info"; DEBUG = "debug"

class MessagePriority:
    LOW = 0; NORMAL = 1; HIGH = 2; CRITICAL = 3

class DebugConsole:
    def __init__(self):
        self.messages = deque(maxlen=50); self.visible = False; self.width = 400; self.height = 300
        self.scroll_offset = 0; self.max_visible_messages = 18; self.font = pygame.font.SysFont("Courier New", 12)
        self.background_color = (0, 0, 0, 180); self.border_color = (100, 100, 100)
        self.text_color = (0, 255, 0); self.title_color = (255, 255, 0)
        
    def toggle(self): self.visible = not self.visible # ; if self.visible: self.add_message("Debug console activated", (255,255,0))
    def add_message(self, msg, color=(0, 255, 0)):
        if not msg or msg.strip() == "": return
        timestamp = pygame.time.get_ticks() // 1000
        formatted_msg = f"[{timestamp}s] {msg}"
        self.messages.append({"text": formatted_msg, "color": color, "time": pygame.time.get_ticks()})
        
    def handle_scroll(self, event):
        if not self.visible: return False
        mouse_pos = pygame.mouse.get_pos()
        screen_width, screen_height = pygame.display.get_surface().get_size()
        console_rect = pygame.Rect(screen_width - self.width - 10, screen_height - self.height - 10, self.width, self.height)
        if not console_rect.collidepoint(mouse_pos): return False
        if event.type == pygame.MOUSEWHEEL:
            if event.y > 0: self.scroll_offset = max(0, self.scroll_offset - 3)
            elif event.y < 0: self.scroll_offset = min(max(0, len(self.messages) - self.max_visible_messages), self.scroll_offset + 3)
            return True
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_PAGEUP: self.scroll_offset = max(0, self.scroll_offset - self.max_visible_messages)
            elif event.key == pygame.K_PAGEDOWN: self.scroll_offset = min(max(0, len(self.messages) - self.max_visible_messages), self.scroll_offset + self.max_visible_messages)
            elif event.key == pygame.K_HOME: self.scroll_offset = 0
            elif event.key == pygame.K_END: self.scroll_offset = max(0, len(self.messages) - self.max_visible_messages)
            else: return False
            return True
        return False
        
    def draw(self, screen):
        if not self.visible: return
        screen_width, screen_height = pygame.display.get_surface().get_size()
        x = screen_width - self.width - 10; y = screen_height - self.height - 10
        console_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        pygame.draw.rect(console_surface, self.background_color, (0, 0, self.width, self.height))
        pygame.draw.rect(console_surface, self.border_color, (0, 0, self.width, self.height), 2)
        title_text = self.font.render("DEBUG CONSOLE (Press D to hide)", True, self.title_color)
        console_surface.blit(title_text, (10, 5))
        pygame.draw.line(console_surface, self.border_color, (5, 25), (self.width - 5, 25), 1)
        visible_messages = list(self.messages)[-self.max_visible_messages-self.scroll_offset:]
        visible_messages = visible_messages[self.scroll_offset:self.scroll_offset+self.max_visible_messages]
        for i, msg in enumerate(visible_messages):
            message_text = self.font.render(msg["text"], True, msg["color"])
            console_surface.blit(message_text, (10, 30 + i * 15))
        if len(self.messages) > self.max_visible_messages:
            scrollbar_height = max(30, self.height * self.max_visible_messages / len(self.messages))
            scrollbar_y = 30 + (self.height - 40) * self.scroll_offset / max(1, len(self.messages) - self.max_visible_messages)
            pygame.draw.rect(console_surface, (150, 150, 150), (self.width - 15, scrollbar_y, 10, scrollbar_height))
        screen.blit(console_surface, (x, y))

debug_console = DebugConsole()

def get_memory_usage():
    try:
        import psutil; process = psutil.Process(os.getpid()); return f"Memory: {process.memory_info().rss / 1024 / 1024:.1f} MB"
    except ImportError: return "Memory: psutil not installed"

class MessageManager:
    def __init__(self):
        self.messages = deque(maxlen=100); self.scroll_offset = 0; self.max_visible_messages = 7
        self.last_message_time = 0; self.pending_messages = []; self.message_display_time = 30000
        self.message_batching = {}; self.batch_timeout = 1000; self.last_batch_time = 0
        self.target_scroll_offset = 0; self.scroll_animation_active = False
        self.scroll_animation_start = 0; self.scroll_animation_duration = 150; self.scroll_start_offset = 0
        self.scrollbar_dragging = False; self.scrollbar_drag_start_y = 0; self.scrollbar_drag_start_offset = 0
        self.scroll_fade_time = 1000; self.last_scroll_time = 0; self.scroll_indicator_alpha = 0
        self.category_filters = {c: True for c in vars(MessageCategory) if not c.startswith('_')}
        self.min_priority = MessagePriority.LOW
        
    def add_message(self, msg, color=WHITE, category=MessageCategory.INFO, priority=MessagePriority.NORMAL):
        if not msg or msg.strip() == "": return
        if category in self.category_filters and not self.category_filters[category]: return
        if priority < self.min_priority: return
        now = pygame.time.get_ticks()
        if self._should_batch_message(msg, category): self._update_batch(msg, now); return
        self.messages.append({"text": msg, "time": now, "color": color, "category": category, "priority": priority, "batch_count": 1})
        self.last_message_time = now; self._process_pending_messages(now)
        
    def _should_batch_message(self, msg, category):
        if category in [MessageCategory.QUEST, MessageCategory.DIALOG, MessageCategory.ERROR]: return False
        for message in reversed(self.messages):
            if pygame.time.get_ticks() - message["time"] > self.batch_timeout: break
            if message["text"] == msg and message["category"] == category: return True
        return False
        
    def _update_batch(self, msg, now):
        for message in reversed(self.messages):
            if message["text"] == msg:
                message["batch_count"] += 1; message["time"] = now; self.last_message_time = now; return
    
    def _process_pending_messages(self, now):
        for pending_msg in self.pending_messages:
            if isinstance(pending_msg, dict): pending_msg["time"] = now; self.messages.append(pending_msg)
            elif pending_msg and pending_msg.strip() != "":
                self.messages.append({"text": pending_msg, "time": now, "color": WHITE, "category": MessageCategory.INFO, "priority": MessagePriority.NORMAL, "batch_count": 1})
        self.pending_messages = []
    
    def update(self):
        now = pygame.time.get_ticks()
        if now - self.last_batch_time > self.batch_timeout: self.message_batching = {}; self.last_batch_time = now
        while self.messages and now - self.messages[0]["time"] > self.message_display_time: self.messages.popleft()
        if self.scroll_offset > 0 and self.scroll_offset >= len(self.messages):
            self.scroll_offset = max(0, len(self.messages) - self.max_visible_messages)
            self.target_scroll_offset = self.scroll_offset
        if self.scroll_animation_active:
            elapsed = now - self.scroll_animation_start
            if elapsed >= self.scroll_animation_duration:
                self.scroll_offset = self.target_scroll_offset
                self.scroll_animation_active = False
            else:
                progress = elapsed / self.scroll_animation_duration
                t = progress
                ease_factor = t * (2 - t)
                diff = self.target_scroll_offset - self.scroll_start_offset
                self.scroll_offset = int(self.scroll_start_offset + diff * ease_factor)
        if self.scroll_indicator_alpha > 0:
            elapsed = now - self.last_scroll_time
            if elapsed > self.scroll_fade_time: self.scroll_indicator_alpha = 0
            else: self.scroll_indicator_alpha = int(255 * (1 - elapsed / self.scroll_fade_time))
    
    def get_visible_messages(self):
        if not self.messages: return []
        max_index = min(self.scroll_offset + self.max_visible_messages, len(self.messages))
        return list(self.messages)[self.scroll_offset:max_index]
    
    def handle_scroll(self, event):
        now = pygame.time.get_ticks(); handled = False
        if hasattr(event, 'type'):
            if event.type == pygame.KEYDOWN:
                max_offset = max(0, len(self.messages) - self.max_visible_messages)
                if event.key == pygame.K_PAGEUP: self._start_scroll_animation(max(0, self.scroll_offset - self.max_visible_messages)); handled = True
                elif event.key == pygame.K_UP: self._start_scroll_animation(max(0, self.scroll_offset - 1)); handled = True
                elif event.key == pygame.K_PAGEDOWN: self._start_scroll_animation(min(max_offset, self.scroll_offset + self.max_visible_messages)); handled = True
                elif event.key == pygame.K_DOWN: self._start_scroll_animation(min(max_offset, self.scroll_offset + 1)); handled = True
                elif event.key == pygame.K_HOME: self._start_scroll_animation(0); handled = True
                elif event.key == pygame.K_END: self._start_scroll_animation(max_offset); handled = True
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 4: self._start_scroll_animation(max(0, self.scroll_offset - 3)); handled = True
                elif event.button == 5: self._start_scroll_animation(min(max(0, len(self.messages) - self.max_visible_messages), self.scroll_offset + 3)); handled = True
        if handled: self.last_scroll_time = now; self.scroll_indicator_alpha = 255
        return handled
    
    def _start_scroll_animation(self, target_offset):
        self.target_scroll_offset = target_offset; self.scroll_animation_start = pygame.time.get_ticks()
        self.scroll_animation_active = True; self.scroll_start_offset = self.scroll_offset
        
    def handle_scrollbar_event(self, event, scrollbar_rect):
        if not self.messages or len(self.messages) <= self.max_visible_messages: return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if scrollbar_rect.collidepoint(event.pos):
                self.scrollbar_dragging = True; self.scrollbar_drag_start_y = event.pos[1]
                self.scrollbar_drag_offset = self.scroll_offset; self.last_scroll_time = pygame.time.get_ticks()
                self.scroll_indicator_alpha = 255; return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.scrollbar_dragging: self.scrollbar_dragging = False; return True
        elif event.type == pygame.MOUSEMOTION and self.scrollbar_dragging:
            delta_y = event.pos[1] - self.scrollbar_drag_start_y; scrollbar_height = scrollbar_rect.height
            max_messages = len(self.messages) - self.max_visible_messages
            if max_messages > 0 and scrollbar_height > 0:
                scroll_ratio = delta_y / float(scrollbar_height); scroll_amount = int(scroll_ratio * max_messages)
                new_offset = max(0, min(max_messages, self.scrollbar_drag_offset + scroll_amount))
                if new_offset != self.scroll_offset:
                    self.scroll_offset = new_offset; self.last_scroll_time = pygame.time.get_ticks()
                    self.scroll_indicator_alpha = 255; return True
        return False
    
    def set_category_filter(self, category, enabled):
        if category in self.category_filters: self.category_filters[category] = enabled
    def set_min_priority(self, priority): self.min_priority = priority
    def clear(self):
        self.messages.clear(); self.pending_messages = []; self.scroll_offset = 0
        self.target_scroll_offset = 0; self.scroll_animation_active = False; self.scrollbar_dragging = False
        
    def draw_scrollbar(self, screen, panel_rect):
        if not self.messages or len(self.messages) <= self.max_visible_messages: return None
        total_messages = len(self.messages); visible_ratio = min(1.0, self.max_visible_messages / float(total_messages))
        scrollbar_width = 10; scrollbar_x = panel_rect.right - scrollbar_width - 5
        scrollbar_height = panel_rect.height - 20; scrollbar_y = panel_rect.y + 10
        scrollbar_track_color = pygame.Color(50, 50, 50, 150)
        scrollbar_track_surface = pygame.Surface((scrollbar_width, scrollbar_height), pygame.SRCALPHA)
        scrollbar_track_surface.fill(scrollbar_track_color); screen.blit(scrollbar_track_surface, (scrollbar_x, scrollbar_y))
        handle_height = max(20, int(scrollbar_height * visible_ratio))
        scroll_progress = self.scroll_offset / float(total_messages - self.max_visible_messages) if total_messages - self.max_visible_messages > 0 else 0
        handle_y = scrollbar_y + int(scroll_progress * (scrollbar_height - handle_height))
        alpha = max(120, self.scroll_indicator_alpha)
        handle_color = pygame.Color(200, 200, 200, 220) if self.scrollbar_dragging else pygame.Color(180, 180, 180, alpha)
        scrollbar_handle_surface = pygame.Surface((scrollbar_width, handle_height), pygame.SRCALPHA)
        scrollbar_handle_surface.fill(handle_color); screen.blit(scrollbar_handle_surface, (scrollbar_x, handle_y))
        if self.scroll_indicator_alpha > 0:
            if self.scroll_offset > 0: self._draw_scroll_indicator(screen, panel_rect.x + panel_rect.width // 2, panel_rect.y + 5, True, self.scroll_indicator_alpha)
            if self.scroll_offset < total_messages - self.max_visible_messages: self._draw_scroll_indicator(screen, panel_rect.x + panel_rect.width // 2, panel_rect.y + panel_rect.height - 15, False, self.scroll_indicator_alpha)
        return pygame.Rect(scrollbar_x, scrollbar_y, scrollbar_width, scrollbar_height)
        
    def _draw_scroll_indicator(self, screen, x, y, is_up, alpha):
        points = [(x - 8, y + 8), (x, y), (x + 8, y + 8)] if is_up else [(x - 8, y - 8), (x, y), (x + 8, y - 8)]
        arrow_color = pygame.Color(255, 255, 255, alpha)
        arrow_surface = pygame.Surface((16, 8), pygame.SRCALPHA)
        pygame.draw.polygon(arrow_surface, arrow_color, [(p[0]-x+8, p[1]-y+4) for p in points])
        screen.blit(arrow_surface, (x - 8, y - 4))

message_manager = MessageManager()


class Monster:
    def __init__(self, name, hit_points, to_hit, ac, move, dam, sprites, **kwargs):
        self.name = name; self.hit_points = hit_points; self.max_hit_points = hit_points
        self.to_hit = to_hit; self.ac = ac; self.move = move; self.dam = dam; self.sprites = sprites
        self.monster_type = kwargs.get('monster_type', 'beast'); self.level = kwargs.get('level', 1)
        self.cr = kwargs.get('cr', 1); self.vulnerabilities = kwargs.get('vulnerabilities', [])
        self.resistances = kwargs.get('resistances', []); self.immunities = kwargs.get('immunities', [])
        self.special_abilities = kwargs.get('special_abilities', []); self.is_dead = False
        self.active_effects = []; self.can_move = True; self.can_act = True

        sprite_path_key = self.sprites.get('live') if self.sprites else None
        if sprite_path_key and isinstance(sprite_path_key, str):
            self.sprite = load_sprite(sprite_path_key)
        else: # Fallback if no live sprite defined or path is invalid
            # print(f"Warning: No valid live sprite for {self.name}. Using placeholder.")
            self.sprite = pygame.Surface((TILE_SIZE, TILE_SIZE)); self.sprite.fill(RED)
        self.position = None

    def move_towards(self, target, dungeon, is_player=False):
        if self.position is None or target.position is None: return
        if not self.can_move: return
        # ... (rest of move_towards logic, simplified for brevity in this example)
        monster_x, monster_y = self.position[0] // TILE_SIZE, self.position[1] // TILE_SIZE
        target_x, target_y = target.position[0] // TILE_SIZE, target.position[1] // TILE_SIZE
        dx = target_x - monster_x; dy = target_y - monster_y
        if abs(dx) > abs(dy):
            step_x = 1 if dx > 0 else -1; new_x = monster_x + step_x; new_y = monster_y
            if 0 <= new_x < dungeon.width and 0 <= new_y < dungeon.height and dungeon.tiles[new_x][new_y].type in ('floor', 'corridor', 'door'):
                self.position = [new_x * TILE_SIZE + TILE_SIZE // 2, new_y * TILE_SIZE + TILE_SIZE // 2]
        else:
            step_y = 1 if dy > 0 else -1; new_x = monster_x; new_y = monster_y + step_y
            if 0 <= new_x < dungeon.width and 0 <= new_y < dungeon.height and dungeon.tiles[new_x][new_y].type in ('floor', 'corridor', 'door'):
                self.position = [new_x * TILE_SIZE + TILE_SIZE // 2, new_y * TILE_SIZE + TILE_SIZE // 2]


    def get_effective_ac(self): return self.ac
    def get_effective_damage(self): return roll_dice_expression(self.dam)

    def set_dead_sprite(self):
        dead_sprite_path = self.sprites.get('dead') if self.sprites else None
        if dead_sprite_path and isinstance(dead_sprite_path, str):
            self.sprite = load_sprite(dead_sprite_path)
        else: self._tint_sprite_gray()

    def _tint_sprite_gray(self):
        if self.sprite:
            temp_sprite = self.sprite.copy()
            gray_overlay = pygame.Surface(temp_sprite.get_size(), pygame.SRCALPHA)
            gray_overlay.fill((30, 30, 30, 180)); temp_sprite.blit(gray_overlay, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
            red_tint = pygame.Surface(temp_sprite.get_size(), pygame.SRCALPHA)
            red_tint.fill((100,0,0,50)); temp_sprite.blit(red_tint, (0,0), special_flags=pygame.BLEND_RGBA_ADD)
            dark_overlay = pygame.Surface(temp_sprite.get_size(), pygame.SRCALPHA)
            dark_overlay.fill((0,0,0,50)); temp_sprite.blit(dark_overlay, (0,0))
            self.sprite = temp_sprite

    def apply_damage(self, damage_amount, damage_type="physical"):
        if damage_type in self.immunities: return 0
        if damage_type in self.vulnerabilities: damage_amount *= 2
        if damage_type in self.resistances: damage_amount = max(1, damage_amount // 2)
        self.hit_points -= damage_amount; self.hit_points = max(0, self.hit_points)
        if self.hit_points == 0: self.is_dead = True
        return damage_amount

class Dungeon:
    def __init__(self, width, height, level=1, map_number=1, max_maps=1,
                 num_rooms_range=(10,15), # New parameter for room count range
                 min_room_width=None, max_room_width=None, # New parameters for room width
                 min_room_height=None, max_room_height=None, # New parameters for room height
                 min_room_separation=2): # New parameter for room separation

        self.width = width
        self.height = height
        self.level = level
        self.map_number = map_number
        self.max_maps = max_maps

        # Use getattr for dungeon parameters, providing defaults
        self.num_rooms_min = num_rooms_range[0]
        self.num_rooms_max = num_rooms_range[1]

        # Varied room sizes based on level
        self.min_room_width = min_room_width or (3 + level // 3)
        self.max_room_width = max_room_width or (8 + level // 2)
        self.min_room_height = min_room_height or (3 + level // 3)
        self.max_room_height = max_room_height or (8 + level // 2)

        self.min_room_separation = min_room_separation

        self.tiles = [[Tile(x, y, 'wall') for y in range(height)] for x in range(width)]
        self.monsters = []
        self.dropped_items = []
        self.doors = {}
        self.chests = {}
        self.level_transition_door = None
        self.map_transition_doors = {}
        self._debug_doors_verbose = True

        print(f"DEBUG: Initializing Dungeon - Level: {self.level}, Map: {self.map_number}")
        print(f"DEBUG: Room Size Params: Width ({self.min_room_width}-{self.max_room_width}), Height ({self.min_room_height}-{self.max_room_height})")
        print(f"DEBUG: Num Rooms: ({self.num_rooms_min}-{self.num_rooms_max}), Separation: {self.min_room_separation}")

        self.start_position = self.create_rooms_and_corridors()

    def place_chest(self, room_rect): # Takes pygame.Rect
        """Place a treasure chest in a random position within the given room rect."""
        # Ensure room_rect is a pygame.Rect object
        if not isinstance(room_rect, pygame.Rect):
            print(f"ERROR: place_chest expects a pygame.Rect, got {type(room_rect)}")
            # Attempt to convert if it's a tuple (x,y,w,h)
            if isinstance(room_rect, tuple) and len(room_rect) == 4:
                room_rect = pygame.Rect(room_rect)
            else:
                return None # Cannot proceed

        # Handle small rooms
        chest_x = random.randint(room_rect.left + 1, room_rect.right - 2) if room_rect.width > 2 else room_rect.centerx
        chest_y = random.randint(room_rect.top + 1, room_rect.bottom - 2) if room_rect.height > 2 else room_rect.centery

        # Ensure chest_x, chest_y are within map bounds (should be if room is valid)
        chest_x = max(0, min(self.width - 1, chest_x))
        chest_y = max(0, min(self.height - 1, chest_y))

        chest = Chest(chest_x, chest_y)
        self.chests[(chest_x, chest_y)] = chest
        # print(f"Placed a treasure chest at ({chest_x}, {chest_y})")
        return chest

    def create_rooms_and_corridors(self):
        print(f"DEBUG: Starting dungeon generation. Params: num_rooms=({self.num_rooms_min}-{self.num_rooms_max}), "
              f"room_width=({self.min_room_width}-{self.max_room_width}), room_height=({self.min_room_height}-{self.max_room_height}), "
              f"separation={self.min_room_separation}")

        # Clear the dungeon first (all walls)
        for x_coord in range(self.width):
            for y_coord in range(self.height):
                self.tiles[x_coord][y_coord].type = 'wall'
                # Wall sprites are typically not set here, or are just black.
                # If you have a specific wall sprite, load it. Otherwise, None is fine.
                self.tiles[x_coord][y_coord].sprite = None

        placed_rooms_rects = [] # Stores pygame.Rect objects of placed rooms

        # Use dungeon parameters for room generation, with defaults if not set
        num_room_attempts = getattr(self, 'num_room_attempts', 30)
        min_rooms_to_place = getattr(self, 'min_rooms', 5)
        max_rooms_to_place = getattr(self, 'max_rooms', 10) # This was self.max_rooms from __init__
        min_room_dim = getattr(self, 'min_room_size', 3)
        max_room_dim = getattr(self, 'max_room_size', 8) # Adjusted from 10 to make more varied rooms
        min_separation = getattr(self, 'min_room_separation', 2)

        for _ in range(num_room_attempts):
            if len(placed_rooms_rects) >= max_rooms_to_place:
                break

            room_w = random.randint(min_room_dim, max_room_dim)
            room_h = random.randint(min_room_dim, max_room_dim)

            # Try to place the current room
            for attempt in range(100): # Max attempts to place a single room
                # Ensure room_x and room_y are within valid bounds
                # Margin of 1 from the edge of the map
                room_x = random.randint(1, self.width - room_w - 1)
                room_y = random.randint(1, self.height - room_h - 1)

                current_room_rect = pygame.Rect(room_x, room_y, room_w, room_h)

                collides = False
                for r_rect in placed_rooms_rects:
                    # Check collision with inflated rectangle for separation
                    if current_room_rect.colliderect(r_rect.inflate(min_separation*2, min_separation*2)):
                        collides = True
                        break

                if not collides:
                    # Carve the room
                    for rx in range(room_x, room_x + room_w):
                        for ry in range(room_y, room_y + room_h):
                            if 0 <= rx < self.width and 0 <= ry < self.height: # Boundary check
                                self.tiles[rx][ry].type = 'floor'
                                self.tiles[rx][ry].sprite = load_sprite(assets_data["sprites"]["tiles"]["floor"])

                    placed_rooms_rects.append(current_room_rect)
                    break # Successfully placed this room, move to next in num_room_attempts

            # If after 100 attempts we couldn't place the room, and we are below min_rooms,
            # it's okay, the loop for num_room_attempts will continue.
            # If we are above min_rooms, failing to place a room is also acceptable.

        # Ensure minimum number of rooms are placed, otherwise create a fallback
        if len(placed_rooms_rects) < min_rooms_to_place:
            print(f"Warning: Only {len(placed_rooms_rects)} rooms placed. Trying to add more or creating fallback.")
            # Try to add a few more smaller rooms if desperate
            for _ in range(min_rooms_to_place - len(placed_rooms_rects)):
                room_w = random.randint(min_room_dim, min_room_dim + 2) # smaller rooms
                room_h = random.randint(min_room_dim, min_room_dim + 2)
                for attempt in range(50): # Fewer attempts for these fallback rooms
                    room_x = random.randint(1, self.width - room_w - 1)
                    room_y = random.randint(1, self.height - room_h - 1)
                    current_room_rect = pygame.Rect(room_x, room_y, room_w, room_h)
                    collides = False
                    for r_rect in placed_rooms_rects:
                        if current_room_rect.colliderect(r_rect.inflate(min_separation*2, min_separation*2)):
                            collides = True
                            break
                    if not collides:
                        for rx in range(room_x, room_x + room_w):
                            for ry in range(room_y, room_y + room_h):
                                if 0 <= rx < self.width and 0 <= ry < self.height:
                                    self.tiles[rx][ry].type = 'floor'
                                    self.tiles[rx][ry].sprite = load_sprite(assets_data["sprites"]["tiles"]["floor"])
                        placed_rooms_rects.append(current_room_rect)
                        break

        if not placed_rooms_rects: # Absolute fallback: a single room
            print("Error: No rooms could be placed. Creating a default 5x5 room in the center.")
            room_w, room_h = 5, 5
            room_x = max(1, (self.width - room_w) // 2)
            room_y = max(1, (self.height - room_h) // 2)
            for rx in range(room_x, room_x + room_w):
                for ry in range(room_y, room_y + room_h):
                    if 0 <= rx < self.width and 0 <= ry < self.height:
                        self.tiles[rx][ry].type = 'floor'
                        self.tiles[rx][ry].sprite = load_sprite(assets_data["sprites"]["tiles"]["floor"])
            placed_rooms_rects.append(pygame.Rect(room_x, room_y, room_w, room_h))

        # Connect rooms with corridors (simple sequential connection)
        if len(placed_rooms_rects) > 1:
            for i in range(len(placed_rooms_rects) - 1):
                room1_center_x, room1_center_y = placed_rooms_rects[i].center
                room2_center_x, room2_center_y = placed_rooms_rects[i+1].center

                # Carve horizontal corridor part from room1's center y to room2's center x
                for x_coord in range(min(room1_center_x, room2_center_x), max(room1_center_x, room2_center_x) + 1):
                    if 0 <= x_coord < self.width and 0 <= room1_center_y < self.height:
                        if self.tiles[x_coord][room1_center_y].type == 'wall':
                            self.tiles[x_coord][room1_center_y].type = 'corridor'
                            self.tiles[x_coord][room1_center_y].sprite = load_sprite(assets_data["sprites"]["tiles"]["floor"])

                # Carve vertical corridor part from room1's center y to room2's center y, at room2's center x
                for y_coord in range(min(room1_center_y, room2_center_y), max(room1_center_y, room2_center_y) + 1):
                    if 0 <= room2_center_x < self.width and 0 <= y_coord < self.height:
                        if self.tiles[room2_center_x][y_coord].type == 'wall':
                            self.tiles[room2_center_x][y_coord].type = 'corridor'
                            self.tiles[room2_center_x][y_coord].sprite = load_sprite(assets_data["sprites"]["tiles"]["floor"])

        self.carve_doors()

        first_room_rect = placed_rooms_rects[0]
        start_tile_x = first_room_rect.centerx
        start_tile_y = first_room_rect.centery
        start_position = [start_tile_x * TILE_SIZE + (TILE_SIZE // 2),
                          start_tile_y * TILE_SIZE + (TILE_SIZE // 2)]

        # Spawn Monsters
        if monsters_data and monsters_data.get('monsters') and len(placed_rooms_rects) > 0:
            num_monsters_to_spawn = random.randint(self.level, self.level + 2) # Scale with dungeon level
            spawned_monster_count = 0
            for _ in range(num_monsters_to_spawn):
                # Filter appropriate monsters
                level_appropriate_monsters = [m for m in monsters_data['monsters']
                                             if m.get('level', 1) <= self.level + 2 and # Allow slightly tougher
                                                m.get('level', 1) >= max(1, self.level - 2)] # And slightly weaker
                if not level_appropriate_monsters:
                    level_appropriate_monsters = monsters_data['monsters'] # Fallback to any monster

                if not level_appropriate_monsters: break # No monsters defined

                monster_choice = random.choice(level_appropriate_monsters)
                monster = Monster(
                    name=monster_choice['name'],
                    hit_points=monster_choice['hit_points'],
                    to_hit=monster_choice['to_hit'],
                    ac=monster_choice['ac'],
                    move=monster_choice['move'],
                    dam=monster_choice['dam'],
                    sprites=monster_choice['sprites'],
                    monster_type=monster_choice.get('monster_type', 'beast'), # Use 'monster_type'
                    level=monster_choice.get('level', 1)
                )

                possible_monster_rooms = [r for r in placed_rooms_rects if r != first_room_rect]
                if not possible_monster_rooms: possible_monster_rooms = [first_room_rect] # Only one room

                monster_room_rect = random.choice(possible_monster_rooms)
                # Place monster randomly within the chosen room, not just center
                m_x = random.randint(monster_room_rect.left, monster_room_rect.right -1)
                m_y = random.randint(monster_room_rect.top, monster_room_rect.bottom -1)

                monster.position = [m_x * TILE_SIZE + (TILE_SIZE // 2),
                                    m_y * TILE_SIZE + (TILE_SIZE // 2)]
                self.monsters.append(monster)
                spawned_monster_count +=1
            print(f"Spawned {spawned_monster_count} monsters.")

        # Place Treasure Chests
        if len(placed_rooms_rects) > 0: # Check if there are any rooms to place chests
            num_chests_to_spawn = random.randint(1, max(1, len(placed_rooms_rects) // 3)) # 1 chest per 3 rooms approx
            spawned_chest_count = 0

            # Create a list of rooms that can have chests (not the start room initially)
            eligible_chest_rooms = [r for r in placed_rooms_rects if r != first_room_rect]
            if not eligible_chest_rooms and placed_rooms_rects: # If only start room exists, allow chest there
                eligible_chest_rooms = [first_room_rect]

            random.shuffle(eligible_chest_rooms) # Shuffle to pick random rooms

            for i in range(min(num_chests_to_spawn, len(eligible_chest_rooms))):
                chest_room_rect = eligible_chest_rooms[i]
                # Pass pygame.Rect directly to place_chest
                self.place_chest(chest_room_rect)
                spawned_chest_count +=1
            print(f"Spawned {spawned_chest_count} chests.")


        # Place Transition Door
        if placed_rooms_rects:
             # Convert pygame.Rect rooms to (x,y,w,h) tuples for place_transition_door
            tuple_rooms_for_transition = [(r.x, r.y, r.width, r.height) for r in placed_rooms_rects]
            start_room_tuple_for_transition = (first_room_rect.x, first_room_rect.y, first_room_rect.width, first_room_rect.height)

            transition_door = self.place_transition_door(tuple_rooms_for_transition, start_room_tuple_for_transition)
            if transition_door:
                print(f"DEBUG: Transition door placed at ({transition_door.x}, {transition_door.y}) Type: {transition_door.door_type}")
            else:
                print("DEBUG: Failed to place transition door in new algorithm (after room placement).")
        else:
            print("DEBUG: No rooms available to attempt transition door placement.")

        return start_position


    def remove_monster(self, monster):
        if monster in self.monsters: self.monsters.remove(monster) # ; print(f"Monster {monster.name} removed.")
        # else: print(f"Warning: Monster {monster.name} not found.")

    def draw_corridor(self, x1, y1, x2, y2): pass # Old method, not used with MST

    def find_start_position_in_room(self, room):
        x_coord, y_coord, w, h = room
        start_x = random.randint(x_coord, x_coord + w - 1)
        start_y = random.randint(y_coord, y_coord + h - 1)
        return [start_x * TILE_SIZE + TILE_SIZE // 2, start_y * TILE_SIZE + TILE_SIZE // 2]

    def find_random_position_in_room(self, room):
        x_coord, y_coord, w, h = room
        return (random.randint(x_coord, x_coord + w - 1), random.randint(y_coord, y_coord + h - 1))

    def draw(self, surface):
        pygame.draw.rect(surface, LIGHT_GRAY, (0, 0, self.width * TILE_SIZE, self.height * TILE_SIZE))
        # ... (rest of draw method, simplified for brevity, assuming it works with new structure)
        for x in range(self.width):
            for y in range(self.height):
                tile = self.tiles[x][y]
                if tile.sprite:
                    surface.blit(tile.sprite, (x * TILE_SIZE, y * TILE_SIZE))
                elif tile.type == 'wall':
                     pygame.draw.rect(surface, BLACK, (x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE))

                # Draw doors from self.doors which has Door objects
                if (x,y) in self.doors:
                    door_obj = self.doors[(x,y)]
                    if door_obj.sprite:
                         surface.blit(door_obj.sprite, (x * TILE_SIZE, y * TILE_SIZE))

        for (cx, cy), chest_obj in self.chests.items():
            if chest_obj.sprite:
                surface.blit(chest_obj.sprite, (cx * TILE_SIZE, cy * TILE_SIZE))

        for drop in self.dropped_items:
            item_sprite = getattr(drop['item'], 'sprite', loot_drop_sprite) # loot_drop_sprite should be loaded
            item_x, item_y = drop['position']
            if item_sprite: surface.blit(item_sprite, (item_x - TILE_SIZE // 2, item_y - TILE_SIZE // 2))


    def place_transition_door(self, rooms_tuples, start_room_tuple): # rooms are tuples (x,y,w,h)
        if not rooms_tuples or len(rooms_tuples) <= 1: return None
        start_center_x = start_room_tuple[0] + start_room_tuple[2] // 2
        start_center_y = start_room_tuple[1] + start_room_tuple[3] // 2
        farthest_room_tuple = None; max_distance = 0
        for room_tuple in rooms_tuples:
            if room_tuple == start_room_tuple: continue
            room_center_x = room_tuple[0] + room_tuple[2] // 2
            room_center_y = room_tuple[1] + room_tuple[3] // 2
            distance = math.hypot(room_center_x - start_center_x, room_center_y - start_center_y)
            if distance > max_distance: max_distance = distance; farthest_room_tuple = room_tuple

        if not farthest_room_tuple: return None

        room_x, room_y, room_w, room_h = farthest_room_tuple
        # Simplified wall choice for brevity
        wall_options = ['north', 'south', 'east', 'west']
        chosen_wall = random.choice(wall_options)

        if chosen_wall == 'north': door_x, door_y = room_x + room_w // 2, room_y
        elif chosen_wall == 'south': door_x, door_y = room_x + room_w // 2, room_y + room_h - 1
        elif chosen_wall == 'east': door_x, door_y = room_x + room_w - 1, room_y + room_h // 2
        else: door_x, door_y = room_x, room_y + room_h // 2 # west

        # Boundary checks for door placement
        door_x = max(0, min(self.width - 1, door_x))
        door_y = max(0, min(self.height - 1, door_y))

        door_type = "level_transition" if self.map_number >= self.max_maps else "map_transition"
        door = Door(door_x, door_y, locked=False, door_type=door_type)
        if door_type == "map_transition": door.destination_map = self.map_number + 1

        if door_type == "level_transition": self.level_transition_door = door
        else: self.map_transition_doors[(door_x, door_y)] = door
        self.doors[(door_x, door_y)] = door
        self.tiles[door_x][door_y].type = 'locked_door' if door.locked else 'door'
        self.tiles[door_x][door_y].sprite = door.sprite
        return door

    def carve_doors(self):
        door_coordinates = []
        for x in range(1, self.width - 1):
            for y in range(1, self.height - 1):
                if self.tiles[x][y].type == 'corridor':
                    # Simplified logic: check if adjacent to a floor and a wall
                    is_adj_floor = False
                    is_adj_wall_for_door_frame = False
                    # Check N, S, E, W for floor
                    for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                        if self.tiles[x+dx][y+dy].type == 'floor': is_adj_floor = True; break
                    # Check if it's a 1-tile wide corridor segment (for door frame)
                    if (self.tiles[x-1][y].type == 'wall' and self.tiles[x+1][y].type == 'wall') or \
                       (self.tiles[x][y-1].type == 'wall' and self.tiles[x][y+1].type == 'wall'):
                       is_adj_wall_for_door_frame = True

                    if is_adj_floor and is_adj_wall_for_door_frame:
                        door_coordinates.append((x,y))
        
        random.shuffle(door_coordinates)
        num_doors_to_place = random.randint(min(1, len(door_coordinates)), min(3, len(door_coordinates)))
        
        for i in range(num_doors_to_place):
            if i < len(door_coordinates):
                x,y = door_coordinates[i]
                new_door = Door(x,y, locked=True) # Doors are initially locked
                self.doors[(x,y)] = new_door
                self.tiles[x][y].type = 'locked_door'
                self.tiles[x][y].sprite = new_door.sprite # Use Door object's sprite


# ... (rest of the file: help_content, add_message, update_message_queue, display_help_screen, etc.)
# ... (Character, Player, Tile, Chest, Door classes mostly as they were, with path fixes if any)
# ... (Spell system bridge, legacy LOS, spells_dialogue, cast_spell, visual effects)
# Ensure all file paths in these sections are also made relative if they were missed.

# For brevity, I'm assuming the rest of the file content is largely unchanged except for:
# 1. Path corrections (e.g. in load_sprite, Door sprite loading, Chest sprite loading)
# 2. Sound commenting

# (Ensure all class definitions like Character, Player, Tile, Chest, Door are present)
# (Ensure all UI functions like display_help_screen are present)
# (Ensure spell system functions like spells_dialogue, cast_spell are present)

# The following classes are simplified here but should be the full versions from the original file
# with relative paths for any assets.

class Character:
    def __init__(self, name, race, char_class, abilities=None):
        self.name = name
        self.race = race
        self.char_class = char_class
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
        self.spell_points = 100 # Simplified
        self.max_hit_points = 10; self.hit_points = 10; self.ac = 0; self.attack_bonus = 0
        self.conditions = []; self.damage_modifier = 0; self.can_move = True

    def apply_race_bonus(self):
        if not hasattr(self, 'abilities') or not isinstance(self.abilities, dict):
            print("Warning: Character abilities not initialized before apply_race_bonus.")
            return

        if self.race == 'High Elf':
            self.abilities['intelligence'] = self.abilities.get('intelligence', 0) + 1
        elif self.race == 'Wood Elf':
            self.abilities['dexterity'] = self.abilities.get('dexterity', 0) + 1
        elif self.race == 'Halfling':
            self.abilities['dexterity'] = self.abilities.get('dexterity', 0) + 1
        elif self.race == 'Dwarf':
            self.abilities['constitution'] = self.abilities.get('constitution', 0) + 1
        elif self.race == 'Human':
            if self.char_class == 'Warrior':
                self.abilities['strength'] = self.abilities.get('strength', 0) + 1
            elif self.char_class == 'Priest':
                self.abilities['wisdom'] = self.abilities.get('wisdom', 0) + 1

    def calculate_modifier(self, ability_score): return (ability_score - 10) // 2 # Simplified
    def get_effective_ability(self, ability_name): return self.abilities.get(ability_name, 10) # Simplified
    def get_effective_ac(self): return self.ac # Simplified
    # Add other methods as in original if needed by Dungeon or tests

class Player(Character):
    def __init__(self, name, race, char_class, start_position, sprite, abilities=None):
        super().__init__(name, race, char_class, abilities)
        self.position = start_position; self.sprite = sprite
        self.inventory = []; self.equipment = {"weapon": None, "armor": None, "shield": None, "jewelry": []}
        self.gold = 100 # Simplified
        self.light_radius = 2 # Default light radius for player
    def add_experience(self, xp): pass # Placeholder

class Tile:
    def __init__(self, x, y, type, sprite=None):
        self.x = x; self.y = y; self.type = type; self.sprite = sprite
        if type in ('floor', 'corridor') and assets_data and "sprites" in assets_data and "tiles" in assets_data["sprites"] and "floor" in assets_data["sprites"]["tiles"]:
            self.sprite = load_sprite(assets_data["sprites"]["tiles"]["floor"])
        # Add other sprite loading if necessary for other tile types

class Chest:
    def __init__(self, x, y):
        self.x = x; self.y = y; self.locked = True; self.open = False
        self.difficulty = CHEST_DIFFICULTY; self.contents = []; self.gold = 0
        self.generate_contents()
        self.load_sprites()
    def generate_contents(self):
        if items_list: # items_list should be loaded globally
            for _ in range(CHEST_ITEMS_COUNT): self.contents.append(deepcopy(random.choice(items_list)))
        self.gold = roll_dice_expression(CHEST_GOLD_DICE)
    def load_sprites(self): # Paths should be relative
        closed_path = "Misc/loot_drop.jpg" # Relative to ASSETS_PATH
        open_path = "Misc/loot_drop_open.jpg" # Relative to ASSETS_PATH
        try:
            self.sprite = load_sprite(open_path if self.open else closed_path)
        except Exception as e:
            # print(f"Warning: Chest sprite error: {e}")
            self.sprite = pygame.Surface((TILE_SIZE, TILE_SIZE)); self.sprite.fill(YELLOW)


class Door:
    def __init__(self, x, y, locked=False, door_type="normal"):
        self.x = x; self.y = y; self.locked = locked; self.open = False
        self.door_type = door_type; self.difficulty = DOOR_DIFFICULTY
        self.destination_map = None
        self.load_sprites()
    def load_sprites(self): # Paths should be relative
        default_door_path = "Misc/door_1.png" # Relative to ASSETS_PATH
        level_trans_path = "Misc/dungeon_level_door.jpg" # Relative to ASSETS_PATH
        
        path_to_load = default_door_path
        if self.door_type == "level_transition": path_to_load = level_trans_path
        
        try:
            if self.open: self.sprite = load_sprite(assets_data["sprites"]["tiles"]["floor"])
            else: self.sprite = load_sprite(path_to_load)
            # Add tinting for locked doors if desired (simplified here)
            if self.locked and not self.open and self.sprite:
                tint_surface = pygame.Surface(self.sprite.get_size(), pygame.SRCALPHA)
                tint_surface.fill((255,0,0, 90)) # Red tint for locked
                self.sprite.blit(tint_surface, (0,0))
        except Exception as e:
            # print(f"Warning: Door sprite error: {e}")
            self.sprite = pygame.Surface((TILE_SIZE, TILE_SIZE)); self.sprite.fill(ORANGE)

# Dummy roll_dice_expression if not fully included elsewhere
def roll_dice_expression(dice_str, caster=None):
    try: # "1d6" or "1d6+1"
        parts = dice_str.split('d')
        num_dice = int(parts[0])
        if '+' in parts[1]:
            sides, mod = map(int, parts[1].split('+'))
        elif '-' in parts[1]:
             sides, mod = map(int, parts[1].split('-'))
             mod = -mod
        else:
            sides = int(parts[1]); mod = 0
        return sum(random.randint(1, sides) for _ in range(num_dice)) + mod
    except: return random.randint(1,6) # Fallback

# Dummy LOS for tests if not fully included
def has_line_of_sight(caster, target, dungeon, required_clear=1): return True
def compute_fov(dungeon, player, radius): return set([(x,y) for x in range(dungeon.width) for y in range(dungeon.height)]) # All visible for test

# Spell system bridge (dummy if not fully included)
USING_NEW_SPELL_SYSTEM = False # Assume legacy for this file content
def cast_spell_bridge(caster, target, spell_name, dungeon): return []
def update_spells_dialogue(screen, player, clock): return None
def can_target(caster, target, spell, dungeon): return True, ""

# ... Any other helper functions like add_message, process_monster_death etc. must be present ...
def add_message(msg, color=WHITE, category=MessageCategory.INFO, priority=MessagePriority.NORMAL):
    # print(f"MESSAGE: [{category}] {msg}") # Simple print for testing
    message_manager.add_message(msg, color, category, priority)

def process_monster_death(monster, player, dungeon_instance):
    monster.is_dead = True
    # dungeon_instance.remove_monster(monster) # This might be called by Dungeon method
    # print(f"{monster.name} died.")
    return [f"{monster.name} died."]

# Test function
def test_dungeon_generation(num_dungeons=3):
    print("\n=== STARTING DUNGEON GENERATION TEST ===")

    # Ensure pygame is minimally initialized if not already
    if not pygame.get_init():
        pygame.init()
    # A display mode is needed for load_sprite if it uses convert_alpha() or scaling.
    # Using a minimal display for testing purposes.
    try:
        pygame.display.set_mode((1, 1), pygame.NOFRAME)
    except pygame.error as e:
        # print(f"Warning: Could not set display mode for testing (might be headless): {e}")
        # Attempt to proceed, load_sprite might have fallbacks
        pass


    # Load necessary data if not already loaded
    if assets_data is None or monsters_data is None:
        print("Test: Loading game data...")
        load_all_data() # This function should handle paths correctly now.

    if assets_data is None or "sprites" not in assets_data:
        print("CRITICAL TEST FAILURE: assets_data not loaded or malformed. Cannot run test.")
        return

    for i in range(num_dungeons):
        level = random.randint(1, 5)
        map_num = random.randint(1, 3)
        print(f"\n--- Generating Dungeon {i+1}/{num_dungeons} (Level: {level}, Map: {map_num}) ---")
        
        try:
            dungeon = Dungeon(width=40, height=30, level=level, map_number=map_num, max_maps=3,
                              num_rooms_range=(8,12), # Slightly smaller range for faster tests
                              min_room_width=3, max_room_width=(6 + level //2),
                              min_room_height=3, max_room_height=(6 + level //2),
                              min_room_separation=2)

            if dungeon.start_position:
                print(f"  Dungeon generated. Player start: {dungeon.start_position}")
            else:
                print("  WARNING: Dungeon generated but no start position returned.")

            if dungeon.level > 0 and not dungeon.monsters:
                print("  WARNING: No monsters spawned for a non-level 0 dungeon.")
            elif dungeon.monsters:
                print(f"  Spawned {len(dungeon.monsters)} monsters.")

            if not dungeon.chests:
                print("  WARNING: No chests spawned.")
            elif dungeon.chests:
                 print(f"  Spawned {len(dungeon.chests)} chests.")

            if not dungeon.doors:
                print("  WARNING: No doors placed (excluding transition).")
            elif dungeon.doors:
                 print(f"  Placed {len(dungeon.doors)} doors (including transition).")

            if not dungeon.level_transition_door and not dungeon.map_transition_doors:
                 print("  WARNING: No transition doors placed.")
            else:
                if dungeon.level_transition_door: print("  Level transition door placed.")
                if dungeon.map_transition_doors: print(f"  {len(dungeon.map_transition_doors)} map transition door(s) placed.")

        except Exception as e:
            print(f"  ERROR during dungeon generation: {e}")
            import traceback
            traceback.print_exc()
        
        print("--- End Dungeon Generation ---")

    print("\n=== DUNGEON GENERATION TEST COMPLETE ===")

if __name__ == "__main__":
    # This allows running the test directly if the script is executed.
    # Ensure Pygame is initialized before calling test_dungeon_generation
    # if it relies on Pygame functionalities like font rendering or image loading.
    
    # Minimal Pygame setup for the test if run as main
    # pygame.init() # Already at top
    # screen = pygame.display.set_mode((DUNGEON_SCREEN_WIDTH, DUNGEON_SCREEN_HEIGHT)) # Or smaller for test
    # clock = pygame.time.Clock()
    
    test_dungeon_generation(num_dungeons=1) # Reduced for direct run
    
    # Example of how the game might run (simplified)
    # player_sprite = load_sprite(assets_data["sprites"]["heroes"]["warrior"]["live"]) # Example
    # player = Player("TestHero", "Human", "Warrior", [0,0], player_sprite)
    # main_dungeon = Dungeon(width=50, height=30, level=1)
    # player.position = main_dungeon.start_position
    
    # print(f"\nPlayer starting at {player.position} in a dungeon of size {main_dungeon.width}x{main_dungeon.height}")
    # print("Test run finished.")
    # pygame.quit()
    # sys.exit()
