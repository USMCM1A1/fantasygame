#!/usr/bin/env python
# coding: utf-8

# In[1]:


# common_b_s.py
import pygame
import json
import os
import sys
import logging # Add logging import
import random
import re
from copy import deepcopy
from Data.condition_system import condition_manager
from debug_system import DEBUG_MODE # Import DEBUG_MODE
import debug_system

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

screen = pygame.display.set_mode((HUB_SCREEN_WIDTH, HUB_SCREEN_HEIGHT))

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

import pygame
font = pygame.font.SysFont('monospace', 15)

# === Logging Configuration ===
# DEBUG_MODE is now imported from debug_system.
# logging.basicConfig is expected to be called once, now in debug_system.py.

# === Helper Functions ===
def load_sprite(path):
    """
    Load an image from the given path, convert it for pygame, and scale it to TILE_SIZE.
    """
    sprite = pygame.image.load(path).convert_alpha()
    return pygame.transform.smoothscale(sprite, (TILE_SIZE, TILE_SIZE))

def load_json(file_path):
    """
    Load and return JSON data from the specified file path.
    """
    with open(file_path, 'r') as f:
        return json.load(f)


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
        portrait_path = assets_data["sprites"]["heroes"][class_lower]["portrait"]
        portrait = pygame.image.load(portrait_path).convert_alpha()
        portrait = pygame.transform.scale(portrait, (portrait_size, portrait_size))
        screen.blit(portrait, (x_offset, y_offset))
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
# === Asset Loading Module ===
# =============================================================================

#sounds
spell_sound = pygame.mixer.Sound("/Users/williammarcellino/Documents/Fantasy_Game/B&S_sfx/lvl1_spell_woosh.mp3")
melee_sound = pygame.mixer.Sound("/Users/williammarcellino/Documents/Fantasy_Game/B&S_sfx/basic_melee_strike.mp3")
arrow_sound = pygame.mixer.Sound("/Users/williammarcellino/Documents/Fantasy_Game/B&S_sfx/arrow_shot.mp3")
levelup_sound = pygame.mixer.Sound("/Users/williammarcellino/Documents/Fantasy_Game/B&S_sfx/level_up_ding.mp3")
frost_sound = pygame.mixer.Sound("/Users/williammarcellino/Documents/Fantasy_Game/B&S_sfx/frost.flac")
store_bell_sound = pygame.mixer.Sound("/Users/williammarcellino/Documents/Fantasy_Game/B&S_sfx/store_bell.mp3")

def load_json(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

DATA_DIR = "/Users/williammarcellino/Documents/Fantasy_Game/Data"
CHARACTERS_FILE = os.path.join(DATA_DIR, "characters.json")
ASSETS_FILE = os.path.join(DATA_DIR, "assets.json")
SPELLS_FILE = os.path.join(DATA_DIR, "spells.json")
ITEMS_FILE = os.path.join(DATA_DIR, "items.json")
MONSTERS_FILE = os.path.join(DATA_DIR, "monsters.json") 


characters_data = load_json(CHARACTERS_FILE)
assets_data = load_json(ASSETS_FILE)
spells_data = load_json(SPELLS_FILE)
items_data = load_json(ITEMS_FILE)
monsters_data = load_json(MONSTERS_FILE) 

def load_sprite(path):
    sprite = pygame.image.load(path).convert_alpha()
    return pygame.transform.smoothscale(sprite, (TILE_SIZE, TILE_SIZE))

# Load misc.sprites
DICE_SPRITE_PATH = assets_data['sprites']['misc']['dice']
dice_sprite = load_sprite(DICE_SPRITE_PATH)
LOOT_DROP_PATH = assets_data['sprites']['misc']['loot_drop']
loot_drop_sprite = load_sprite(LOOT_DROP_PATH) 

# Load and create items
def create_item(item_data):
    if not item_data:
        print("Warning: item_data is None or empty")
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
        print(f"Warning: item '{name}' has None type, defaulting to generic")
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
    for item_data in data["items"]:
        # create_item is your factory function that instantiates the correct item subclass.
        items.append(create_item(item_data))
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
                # Try to get slot from item_categories metadata
                item_categories = items_data.get("item_categories", {})
                
                # If the category exists in item_categories
                if self.category in item_categories:
                    self._equipment_slot = item_categories[self.category].get("equipment_slot")
                
                # Fallback to default slots based on category
                if not self._equipment_slot:
                    if self.category == "weapon":
                        self._equipment_slot = "weapon"
                    elif self.category == "armor":
                        self._equipment_slot = "armor"
                    elif self.category == "shield":
                        self._equipment_slot = "shield"
                    elif self.category == "jewelry":
                        self._equipment_slot = "jewelry"
                    else:
                        self._equipment_slot = "inventory"
            except Exception as e:
                print(f"Error determining equipment slot for {self.name}: {e}")
                self._equipment_slot = "inventory"
        
        return self._equipment_slot
    
    @property
    def metadata(self):
        """Retrieves metadata about this item type from items.json"""
        if self._metadata is None:
            try:
                item_categories = items_data.get("item_categories", {})
                
                # Get category metadata
                category_data = item_categories.get(self.category, {})
                
                # Get subtype metadata if it exists
                subtype_data = {}
                if "subtypes" in category_data and self.item_type in category_data["subtypes"]:
                    subtype_data = category_data["subtypes"][self.item_type]
                
                # Combine category and subtype data
                self._metadata = {**category_data, **subtype_data}
            except Exception as e:
                print(f"Error retrieving metadata for {self.name}: {e}")
                self._metadata = {}
        
        return self._metadata
    
    def get_display_name(self):
        """Returns the display name from metadata or the standardized type name"""
        display_name = self.metadata.get("display_name")
        if display_name:
            return display_name
        
        # Fallback to prettified item type
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
        # Save the damage string (e.g., "1d6-1")
        self.damage = damage

    def roll_damage(self, caster=None):
        """Parse and roll the damage dice expression."""
        # Handle damage strings like "1d6-1" or "1d4+2"
        if "+" in self.damage:
            dice_part, mod_part = self.damage.split("+", 1)
            sign = "+"
        elif "-" in self.damage:
            dice_part, mod_part = self.damage.split("-", 1)
            sign = "-"
        else:
            # If there's no modifier (e.g., just "1d6")
            dice_part = self.damage
            mod_part = "0"
            sign = "+"
            
        # Remove whitespace
        dice_part = dice_part.strip()
        mod_part = mod_part.strip()
        
        # Convert modifier to integer
        mod_value = int(mod_part)
        
        # Roll the dice using roll_dice_expression instead of roll_dice
        base_damage = roll_dice_expression(dice_part, caster)
        
        # Apply the modifier based on the sign
        return base_damage + (mod_value if sign == '+' else -mod_value)

    def apply_effect(self, character):
        # When a weapon is equipped, you might set the player's damage dice.
        # For example:
        character.equipment['weapon'] = self

    def remove_effect(self, character):
        if character.equipment.get('weapon') == self:
            character.equipment['weapon'] = None


class WeaponBlade(Weapon):
    # You could override or add behavior specific to bladed weapons.
    pass

class WeaponBlunt(Weapon):
    # For blunt weapons, you might have different critical rules etc.
    pass

class WeaponBow(Weapon):
    def __init__(self, name, item_type, damage, value, description, range=4):
        super().__init__(name, item_type, damage, value, description)
        # Store the range of the bow in tiles
        self.range = range
        
    def apply_effect(self, character):
        # When a bow is equipped, update the player's equipment
        character.equipment['weapon'] = self
        # Also store the range for use in ranged attacks
        character.weapon_range = self.range
        
    def remove_effect(self, character):
        if character.equipment.get('weapon') == self:
            character.equipment['weapon'] = None
            # Reset the weapon range when bow is unequipped
            if hasattr(character, 'weapon_range'):
                character.weapon_range = 0


# --- Armor Class Items ---
class Armor(Item):
    def __init__(self, name, item_type, ac, value, description):
        super().__init__(name, item_type, value, description)
        # Armor Class bonus can be stored as an integer.
        self.ac_bonus = int(str(ac).replace('+', ''))

    def apply_effect(self, character):
        # Depending on your design, you may have different armor slots.
        # For simplicity, assume character has an 'armor' slot.
        character.equipment['armor'] = self

    def remove_effect(self, character):
        if character.equipment.get('armor') == self:
            character.equipment['armor'] = None

class Shield(Item):
    def __init__(self, name, item_type, ac_bonus, value, description):
        super().__init__(name, item_type, value, description)
        self.ac_bonus = int(str(ac_bonus).replace('+', ''))

    def apply_effect(self, character):
        # Equip the shield in the dedicated 'shield' slot.
        character.equipment["shield"] = self
        # Update the character's shield bonus.
        character.shield_ac_bonus = self.ac_bonus

    def remove_effect(self, character):
        if character.equipment.get("shield") == self:
            character.equipment["shield"] = None
            # Reset the shield bonus.
            character.shield_ac_bonus = 0

# --- Jewelry (Rings, Necklaces, etc.) ---
class Jewelry(Item):
    def __init__(self, name, item_type, value, description):
        """Initialize a jewelry item with default values for stat bonus"""
        super().__init__(name, item_type, value, description)
        self.bonus_stat = "sp"  # Default to spell points
        self.bonus_value = 1    # Default bonus value
        self.stat_bonus = "sp"  # Add this for backward compatibility with existing code
        self.magical = True     # Most jewelry is magical
        
    def apply_effect(self, character):
        # Allow multiple jewelry items to be equipped.
        if 'jewelry' not in character.equipment:
            character.equipment['jewelry'] = []
        character.equipment['jewelry'].append(self)
        
        # If the bonus is for spell points, update spell_points.
        if self.bonus_stat.lower() in ['sp', 'spellpoints']:
            character.spell_points += self.bonus_value
        else:
            # If the ability is stored in the abilities dictionary, update it.
            if self.bonus_stat in character.abilities:
                character.abilities[self.bonus_stat] += self.bonus_value
            else:
                # Otherwise, fall back to setting it as an attribute.
                setattr(character, self.bonus_stat, getattr(character, self.bonus_stat, 0) + self.bonus_value)
                
    def remove_effect(self, character):
        # Remove self from character's jewelry list if it exists
        if 'jewelry' in character.equipment and self in character.equipment['jewelry']:
            character.equipment['jewelry'].remove(self)
            
            # Remove the stat bonus
            if self.bonus_stat.lower() in ['sp', 'spellpoints']:
                character.spell_points -= self.bonus_value
            elif self.bonus_stat in character.abilities:
                character.abilities[self.bonus_stat] -= self.bonus_value
            else:
                # Remove attribute bonus if it exists
                current_value = getattr(character, self.bonus_stat, 0)
                setattr(character, self.bonus_stat, max(0, current_value - self.bonus_value))
                
    # Ensure any code that uses stat_bonus still works by making it a property
    @property
    def stat_bonus(self):
        return self.bonus_stat
        
    @stat_bonus.setter
    def stat_bonus(self, value):
        self.bonus_stat = value

class JewelryRing(Jewelry):
    """Specialized class for rings, which can have different effects and stacking rules"""
    def __init__(self, name, item_type, value, description):
        super().__init__(name, item_type, value, description)
        # Rings have specific metadata from item_categories
        self.max_equipped = self.metadata.get('max_equipped', 2) # Default to 2 rings max
    
    def can_equip(self, character):
        """Check if character can equip another ring"""
        # Count how many rings are already equipped
        equipped_rings = sum(1 for j in character.equipment.get('jewelry', []) 
                           if hasattr(j, 'item_type') and 'ring' in j.item_type)
        
        return equipped_rings < self.max_equipped

class JewelryAmulet(Jewelry):
    """Specialized class for amulets/necklaces, which are usually more powerful and limited to one"""
    def __init__(self, name, item_type, value, description):
        super().__init__(name, item_type, value, description)
        # Amulets typically have higher bonuses
        self.bonus_value *= 2  # Double the standard bonus
        # Make sure both attributes are set for backward compatibility
        self.stat_bonus = self.bonus_stat  # This will use the property to keep them in sync
        self.max_equipped = self.metadata.get('max_equipped', 1) # Default to 1 amulet max
    
    def can_equip(self, character):
        """Check if character can equip another amulet"""
        # Count how many amulets are already equipped
        equipped_amulets = sum(1 for j in character.equipment.get('jewelry', []) 
                             if hasattr(j, 'item_type') and 'amulet' in j.item_type)
        
        return equipped_amulets < self.max_equipped



# --- Consumables ---
class Consumable(Item):
    def __init__(self, name, item_type, effect, value, description):
        super().__init__(name, item_type, value, description)
        # effect is a dictionary containing effect details
        self.effect = effect

    def use(self, character):
        effect_type = self.effect.get("type")
        if effect_type == "healing":
            # Use the provided dice expression to calculate healing
            dice_expr = self.effect.get("dice", "1d4")
            heal_amount = roll_dice_expression(dice_expr, character)
            character.hit_points = min(character.hit_points + heal_amount, character.max_hit_points)
            return f"{character.name} uses {self.name} and heals {heal_amount} HP!"
        elif effect_type == "buff":
            # For example, a temporary buff to AC, strength, etc.
            stat = self.effect.get("stat")
            value = int(self.effect.get("value", 0))
            duration = int(self.effect.get("duration", 0))
            # Here you would add code to apply a temporary buff to the character.
            # This might involve adding the buff to a list along with its expiration time.
            return f"{character.name} uses {self.name} and gains +{value} {stat} for {duration} seconds!"
        else:
            return f"{self.name} has no effect."

# Load global item list
items_list = load_items(ITEMS_FILE)

def draw_inventory_management(screen, player):
    # Use constants directly rather than importing from the modules
    # This avoids circular imports that could restart the game
    
    # Debug the state
    print(f"DEBUG: draw_inventory_management - in_dungeon = {in_dungeon}")
    
    # Determine which screen dimensions to use based on current game state
    if in_dungeon:
        screen_width, screen_height = DUNGEON_SCREEN_WIDTH, DUNGEON_SCREEN_HEIGHT
        print(f"DEBUG: Using dungeon dimensions: {DUNGEON_SCREEN_WIDTH}x{DUNGEON_SCREEN_HEIGHT}")
    else:
        screen_width, screen_height = HUB_SCREEN_WIDTH, HUB_SCREEN_HEIGHT
        print(f"DEBUG: Using hub dimensions: {HUB_SCREEN_WIDTH}x{HUB_SCREEN_HEIGHT}")
    
    # Define panel dimensions
    panel_margin = 20
    panel_width = screen_width - 2 * panel_margin
    panel_height = (screen_height - 3 * panel_margin) // 2

    # Define the rectangles for each panel
    equipment_rect = pygame.Rect(panel_margin, panel_margin, panel_width, panel_height)
    inventory_rect = pygame.Rect(panel_margin, panel_margin*2 + panel_height, panel_width, panel_height)

    # Draw panel backgrounds
    pygame.draw.rect(screen, (50, 50, 50), equipment_rect)
    pygame.draw.rect(screen, (50, 50, 50), inventory_rect)
    pygame.draw.rect(screen, (200, 200, 200), equipment_rect, 2)
    pygame.draw.rect(screen, (200, 200, 200), inventory_rect, 2)

    # Draw Equipped Items Panel
    draw_text_lines(screen, ["Equipped Items:"], equipment_rect.x + 10, equipment_rect.y + 10)
    y_offset = equipment_rect.y + 40
    for slot in ['weapon', 'armor', 'shield']:
        item = player.equipment.get(slot)
        item_text = f"{slot.capitalize()}: {item.name if item else 'None'}"
        draw_text(screen, item_text, WHITE, equipment_rect.x + 10, y_offset)
        y_offset += font.get_linesize() + 10

    # For jewelry, assume there can be multiple items.
    jewelry_list = player.equipment.get('jewelry', [])
    jewelry_text = "Jewelry: " + (", ".join(item.name for item in jewelry_list) if jewelry_list else "None")
    draw_text(screen, jewelry_text, WHITE, equipment_rect.x + 10, y_offset)

    # Draw Inventory Items Panel
    draw_text_lines(screen, ["Inventory: (Click to use or equip)"], inventory_rect.x + 10, inventory_rect.y + 10)
    y_offset = inventory_rect.y + 40
    for idx, item in enumerate(player.inventory):
        try:
            # Default values
            can_equip = True
            text_color = WHITE
            item_display_name = "Unknown"
            
            # Get the item's display name safely
            if hasattr(item, 'get_display_name') and callable(getattr(item, 'get_display_name')):
                item_display_name = item.get_display_name()
            elif hasattr(item, 'item_type'):
                item_display_name = item.item_type
            
            # Check if the item has the necessary type attribute
            has_item_type = hasattr(item, 'item_type')
            is_consumable = has_item_type and item.item_type.startswith("consumable")
            is_jewelry = has_item_type and item.item_type.startswith("jewelry")
            
            # For equipment items, check if the player can equip them
            if has_item_type and not is_consumable:
                can_equip, _ = can_equip_item(player, item)
                
                # For jewelry, also check item-specific limitations
                if can_equip and is_jewelry and hasattr(item, 'can_equip'):
                    can_equip = item.can_equip(player)
                
                # Gray out items that can't be equipped
                if not can_equip:
                    text_color = LIGHT_GRAY
            
            # Show differently for consumables
            if is_consumable:
                item_text = f"{idx+1}. {item.name} ({item_display_name}) - Click to use"
            else:
                # Add a "(Cannot equip)" indicator for items that can't be equipped
                if not can_equip:
                    item_text = f"{idx+1}. {item.name} ({item_display_name}) - Cannot equip"
                else:
                    item_text = f"{idx+1}. {item.name} ({item_display_name})"
            
            draw_text(screen, item_text, text_color, inventory_rect.x + 10, y_offset)
        except Exception as e:
            # Fallback for items with missing attributes or other errors
            error_text = f"{idx+1}. {getattr(item, 'name', 'Unknown Item')} (Error: {str(e)[:20]}...)"
            draw_text(screen, error_text, RED, inventory_rect.x + 10, y_offset)
            print(f"Error displaying inventory item: {e}")
            
        y_offset += font.get_linesize() + 10

    # Return the panel rectangles to help with click detection
    return equipment_rect, inventory_rect

def prompt_user_for_slot(valid_slots, screen=None, clock=None):
    """
    Simple function to select the first valid slot when multiple slots are available.
    In a more sophisticated implementation, this would present a UI for the user to choose.
    """
    if valid_slots:
        return valid_slots[0]  # Just return the first slot for now
    return None

def handle_inventory_click(event, player, equipment_rect, inventory_rect):
    pos = event.pos
    # Check if click is in the inventory panel
    if inventory_rect.collidepoint(pos):
        # Determine which inventory item was clicked
        index = (pos[1] - inventory_rect.y - 40) // (font.get_linesize() + 10)
        if 0 <= index < len(player.inventory):
            try:
                selected_item = player.inventory[index]
                
                # Check if item has the required attributes
                if not hasattr(selected_item, 'name'):
                    selected_item.name = "Unknown Item"
                
                # Safely check item_type
                has_item_type = hasattr(selected_item, 'item_type')
                is_consumable = has_item_type and selected_item.item_type.startswith("consumable")
                is_jewelry = has_item_type and selected_item.item_type.startswith("jewelry")
                
                # Special handling for consumable items
                if is_consumable:
                    # Use the item directly instead of equipping it
                    if hasattr(selected_item, 'use'):
                        message = selected_item.use(player)
                        add_message(message)
                        # Remove the item from inventory after use
                        player.inventory.remove(selected_item)
                        
                        # Use the process_game_turn function to advance the turn counter

                        # Since we're in common_b_s, we need to find the current dungeon
                        # The calling function should pass the current dungeon instance
                        if 'dungeon_instance' in locals() or 'dungeon_instance' in globals():
                            dungeon = dungeon_instance
                        elif 'current_dungeon' in locals() or 'current_dungeon' in globals():
                            dungeon = current_dungeon
                        else:
                            # If we can't find a dungeon reference, we'll have to skip turn processing
                            add_message("NOTE: Couldn't process turn after item use (no dungeon found)")
                            return
                            
                        # Process the turn after using an item
                        process_game_turn(player, dungeon)
                        return  # Exit after using the consumable
                    else:
                        add_message(f"Cannot use {selected_item.name} - no use method defined.")
                        return
                
                # For equipment items, first check if the player can equip this item
                can_equip, reason = can_equip_item(player, selected_item)
                
                # For jewelry, also check item-specific limitations
                if can_equip and is_jewelry and hasattr(selected_item, 'can_equip'):
                    if not selected_item.can_equip(player):
                        can_equip = False
                        reason = "Maximum number already equipped"
                
                if not can_equip:
                    add_message(f"Cannot equip {selected_item.name}: {reason}", RED)
                    return
                    
                # If we can equip it, proceed as before
                valid_slots = get_valid_equipment_slots(selected_item, player)
                # For simplicity, if there's one valid slot, equip automatically
                if len(valid_slots) == 1:
                    slot = valid_slots[0]
                    swap_equipment(player, slot, selected_item)
                elif len(valid_slots) > 1:
                    # If multiple valid slots exist, use our simple slot selection
                    slot = prompt_user_for_slot(valid_slots)
                    if slot:
                        swap_equipment(player, slot, selected_item)
                else:
                    add_message(f"You cannot equip {selected_item.name}: no valid equipment slots found.", RED)
            
            except Exception as e:
                # Handle any exceptions that might occur during inventory click processing
                print(f"Error handling inventory click: {e}")
                add_message(f"Error handling item: {str(e)[:30]}...", RED)
    
    # Check if click is in the equipment panel for unequipping.
    elif equipment_rect.collidepoint(pos):
        try:
            # For simplicity, assume each equipment slot has a defined clickable area.
            slot_clicked = get_clicked_equipment_slot(pos, equipment_rect)
            if slot_clicked and player.equipment.get(slot_clicked):
                unequip_item(player, slot_clicked)
        except Exception as e:
            print(f"Error handling equipment unequip: {e}")
            add_message(f"Error unequipping item: {str(e)[:30]}...", RED)

def manage_inventory(player, screen, clock, dungeon_instance=None):
    """
    Displays the unified inventory management screen.
    Press Escape to exit the mode.
    Uses mouse clicks to equip, unequip, or swap items.
    
    Args:
        player: The player character
        screen: The pygame screen
        clock: The pygame clock
        dungeon_instance: The current dungeon (needed for turn processing)
    """
    # No need for global keyword since we're accessing the global variable directly
    
    print("DEBUG: Entered manage_inventory")
    print(f"DEBUG: manage_inventory - in_dungeon = {in_dungeon}")
    
    # Store the dungeon instance as a global for other functions
    global current_dungeon
    current_dungeon = dungeon_instance
    
    running = True
    while running:
        # Draw the inventory management UI and get the panel rectangles.
        equipment_rect, inventory_rect = draw_inventory_management(screen, player)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False  # Instead of quitting, just close inventory mode
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False  # Close inventory mode
            elif event.type == pygame.MOUSEBUTTONDOWN:
                handle_inventory_click(event, player, equipment_rect, inventory_rect)
        
        pygame.display.flip()
        clock.tick(30)
    
    print(f"DEBUG: manage_inventory ending - in_dungeon = {in_dungeon}")
    
    return  # Ensure function exits cleanly back to main game loop

def get_item_data(item_name, items_data):
    """
    Helper function to locate an item's data in the loaded JSON data.
    'items_data' is expected to be a dict with an "items" list.
    Returns the dictionary for the matching item, or None if not found.
    """
    for item in items_data.get("items", []):
        if item.get("name") == item_name:
            return item
    return None

def shop_interaction(screen, clock, player, items_data=items_data):
    """
    Graphical shop interaction where the player can buy and sell items.
    
    Shop Stock is defined as:
      - 1 x "Iron Sword (1d6-1)"
      - 1 x "Iron Dagger (1d4-1)"
      - 1 x "Iron Mace (1d6-1)"
      - 2 x "Health Potion"
      
    In the shop screen:
      - The upper panel displays the shop's stock.
      - The lower panel displays the player's inventory.
      - The player's gold is shown at the top.
      - Click on a shop item to purchase it (if you have enough gold).
      - Click on an inventory item to sell it (receiving half its value).
      - Press ESC to exit the shop.
    """
    # Play the store bell sound when entering the shop
    store_bell_sound.play()
    
    # Load shopkeeper portrait
    shopkeeper_portrait = pygame.image.load("/Users/williammarcellino/Documents/Fantasy_Game/Fantasy_Game_Art_Assets/Misc/Novamagus/shopkeep.jpg")
    portrait_width = 300  # Double the portrait width (was 150)
    portrait_height = 300  # Double the portrait height (was 150)
    shopkeeper_portrait = pygame.transform.scale(shopkeeper_portrait, (portrait_width, portrait_height))
    
    # Helper function to locate item data by name.
    def get_item_data(item_name, items_data):
        for item in items_data.get("items", []):
            if item.get("name") == item_name:
                return item
        return None

    # Build the shop stock from items.json.
    shop_stock_items = [
        ("Iron Sword (1d6-1)", 1),
        ("Iron Dagger (1d4-1)", 1),
        ("Iron Mace (1d6-1)", 1),
        ("Basic Shortbow (1d6)", 1),
        ("Basic Longbow (1d8)", 1),
        ("Health Potion", 2),
        ("Thieve's Tools", 1)
    ]
    shop_stock = []
    for name, qty in shop_stock_items:
        for _ in range(qty):
            data = get_item_data(name, items_data)
            if data is None:
                print(f"Error: {name} not found in items data.")
                continue
            item_instance = create_item(deepcopy(data))
            shop_stock.append(item_instance)
    
    # Use your hub configuration for screen dimensions.
    screen_width, screen_height = HUB_SCREEN_WIDTH, HUB_SCREEN_HEIGHT
    panel_margin = 20
    panel_width = screen_width - 2 * panel_margin
    panel_height = (screen_height - 3 * panel_margin) // 2

    # Define two panels: one for shop stock (upper panel) and one for player's inventory (lower panel).
    shop_panel_rect = pygame.Rect(panel_margin, panel_margin, panel_width, panel_height)
    inventory_panel_rect = pygame.Rect(panel_margin, panel_margin * 2 + panel_height, panel_width, panel_height)
    
    # Define the portrait placement in the upper right corner - moved right by its full width
    portrait_rect = pygame.Rect(screen_width - portrait_width + portrait_width, panel_margin, portrait_width, portrait_height)
    
    running = True
    message = ""      # Temporary message string for feedback.
    message_timer = 0 # Timer (in frames) to display the message.
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                pos = event.pos
                # Process clicks in the shop panel.
                y_offset = shop_panel_rect.y + 40  # Starting vertical offset for shop items.
                for idx, item in enumerate(shop_stock):
                    # Each shop item gets a clickable rectangle.
                    item_rect = pygame.Rect(shop_panel_rect.x + 10, y_offset, panel_width - 20, font.get_linesize() + 4)
                    if item_rect.collidepoint(pos):
                        if player.gold >= item.value:
                            player.gold -= item.value
                            player.inventory.append(item)
                            message = f"Bought {item.name} for {item.value} gold."
                            message_timer = 60  # Display for 60 frames.
                            shop_stock.pop(idx)
                        else:
                            message = "Not enough gold to buy that item."
                            message_timer = 60
                        break  # Process only one click per event.
                    y_offset += font.get_linesize() + 10

                # Process clicks in the inventory panel to sell items.
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
        
        # Clear the screen.
        screen.fill(BLACK)
        
        # --- Draw Shop Panel ---
        pygame.draw.rect(screen, (50, 50, 50), shop_panel_rect)
        pygame.draw.rect(screen, (200, 200, 200), shop_panel_rect, 2)
        draw_text_lines(screen, ["Shop Stock:"], shop_panel_rect.x + 10, shop_panel_rect.y + 10)
        y_offset = shop_panel_rect.y + 40
        for idx, item in enumerate(shop_stock):
            item_text = f"{idx+1}. {item.name} - Price: {item.value} gold"
            draw_text(screen, item_text, WHITE, shop_panel_rect.x + 10, y_offset)
            y_offset += font.get_linesize() + 10
        
        # --- Draw Inventory Panel ---
        pygame.draw.rect(screen, (50, 50, 50), inventory_panel_rect)
        pygame.draw.rect(screen, (200, 200, 200), inventory_panel_rect, 2)
        draw_text_lines(screen, ["Your Inventory:"], inventory_panel_rect.x + 10, inventory_panel_rect.y + 10)
        y_offset = inventory_panel_rect.y + 40
        for idx, item in enumerate(player.inventory):
            sell_price = item.value // 2
            item_text = f"{idx+1}. {item.name} - Sell Price: {sell_price} gold"
            draw_text(screen, item_text, WHITE, inventory_panel_rect.x + 10, y_offset)
            y_offset += font.get_linesize() + 10
        
        # --- Draw Player Gold ---
        gold_text = f"Gold: {player.gold}"
        draw_text(screen, gold_text, WHITE, screen_width - 150, 10)
        
        # --- Draw Shopkeeper Portrait ---
        # Draw frame around the portrait
        frame_rect = pygame.Rect(portrait_rect.x - 5, portrait_rect.y - 5, 
                                portrait_rect.width + 10, portrait_rect.height + 10)
        pygame.draw.rect(screen, (139, 69, 19), frame_rect)  # Brown frame
        pygame.draw.rect(screen, (200, 175, 100), frame_rect, 3)  # Gold border
        
        # Draw the portrait
        screen.blit(shopkeeper_portrait, portrait_rect)
        
        # Draw shopkeeper message with a larger message box
        message_rect = pygame.Rect(portrait_rect.x, portrait_rect.y + portrait_rect.height + 10, 
                                  portrait_rect.width, 100)
        pygame.draw.rect(screen, (50, 50, 50), message_rect)
        pygame.draw.rect(screen, (200, 200, 200), message_rect, 2)
        
        # Full message text
        full_message = "Hail Adventurer! It's dangerous to go alone, maybe you should buy some equipment?"
        
        # Calculate max width for text wrapping (with margin)
        max_width = message_rect.width - 20  # 10px margin on each side
        
        # Wrap text to fit within the box
        wrapped_lines = []
        line = ""
        for word in full_message.split():
            test_line = line + " " + word if line else word
            # Measure the width of the test line
            text_width = font.size(test_line)[0]
            if text_width <= max_width:
                line = test_line
            else:
                wrapped_lines.append(line)
                line = word
        # Add the last line
        if line:
            wrapped_lines.append(line)
        
        # Draw the wrapped text
        line_spacing = font.get_linesize() + 5  # Added extra 5 pixels between lines
        for i, line in enumerate(wrapped_lines):
            draw_text(screen, line, WHITE, message_rect.x + 10, message_rect.y + 15 + (i * line_spacing))
        
        # --- Draw Instructions ---
        instructions = "Click a shop item to buy, click an inventory item to sell. Press ESC to exit."
        draw_text(screen, instructions, WHITE, panel_margin, screen_height - panel_margin - font.get_linesize())
        
        # --- Draw Feedback Message ---
        if message_timer > 0:
            draw_text(screen, message, (255, 0, 0), panel_margin, screen_height - 2 * panel_margin - font.get_linesize())
            message_timer -= 1
        
        pygame.display.flip()
        clock.tick(HUB_FPS)


# In[5]:


# =============================================================================
# === Helper Functions ===
# =============================================================================

# Save/Load functions have been moved to game_state_manager.py

# debugging statements for stat logic:
def print_character_stats(character):
    """ Prints character stats and explains their calculation. """
    print("\n===== CHARACTER STATS =====")
    print(f"Name: {character.name} | Class: {character.char_class} | Level: {character.level}")

    # Spell Points
    spell_points = character.spell_points
    sp_explanation = (
        "Wizards/Priests: 4 + 1 per level. "
        "Spell Blades: 2 at level 1, then +1 at levels 3, 6, 9, 12, 15, 18, 19, and 20."
    )
    print(f"Spell Points: {spell_points} ({sp_explanation})")

    # Armor Class (Base + Dexterity Modifier)
    base_ac = character.ac  # Base AC from class progression
    dex_mod = character.calculate_modifier(character.get_effective_ability("dexterity"))
    effective_ac = base_ac + dex_mod  # Apply Dex modifier
    ac_explanation = (
        f"Base AC depends on class. Warriors gain +1 per 2 levels, Thieves every 3, "
        f"Priests/Archers every 3, Wizards/Spell Blades every 4. "
        f"Dexterity modifier ({dex_mod}) is applied."
    )
    print(f"Armor Class: {effective_ac} (Base: {base_ac}, Dex: {dex_mod}). {ac_explanation}")

    # Hit Points
    hp = character.hit_points
    max_hp = character.max_hit_points
    con_mod = character.calculate_modifier(character.abilities.get("constitution", 10))
    hp_explanation = (
        f"HP is based on hit dice per class (Warrior: d10, Priest/Spell Blade: d8, Archer/Thief: d6, Wizard: d4). "
        f"At level-up, HP roll is adjusted by Constitution modifier ({con_mod})."
    )
    print(f"Hit Points: {hp}/{max_hp}. {hp_explanation}")

    # Attack Bonus (To-Hit)
    attack_bonus = character.attack_bonus
    to_hit_explanation = (
        "Group A (Warrior, Wizard, Archer) gains bonuses at levels 3, 6, 9, 12, 15, 18, 19, 20. "
        "Group B (Priest, Spell Blade, Thief) at levels 4, 8, 12, 16, 20."
    )
    print(f"Attack Bonus (To-Hit): +{attack_bonus}. {to_hit_explanation}")

    # Damage Bonus
    strength_mod = character.calculate_modifier(character.get_effective_ability("strength"))
    if character.equipment.get("weapon"):
        damage_explanation = f"Weapon ({character.equipment['weapon'].name}) determines damage."
        damage_value = character.get_effective_damage()
    else:
        damage_explanation = f"No weapon equipped. Default: 1d2 + Strength ({strength_mod})."
        damage_value = f"1d2 + {strength_mod}"

    print(f"Damage Bonus: {damage_value}. {damage_explanation}")
    print("=" * 30)

# Import the deque for efficient queue operations
from collections import deque

# Message categories
class MessageCategory:
    SYSTEM = "system"      # System messages (saving, loading, etc.)
    COMBAT = "combat"      # Combat messages (attacks, damage, etc.)
    INVENTORY = "inventory" # Inventory changes, item usage
    QUEST = "quest"        # Quest-related messages
    DIALOG = "dialog"      # NPC dialog
    ERROR = "error"        # Error messages
    INFO = "info"          # General information
    DEBUG = "debug"        # Debug messages (only shown in debug console)

# Message priority levels
class MessagePriority:
    LOW = 0        # Background info, flavor text
    NORMAL = 1     # Standard gameplay information
    HIGH = 2       # Important gameplay events
    CRITICAL = 3   # Critical information that should not be missed

# Debug Console class
class DebugConsole:
    def __init__(self):
        self.messages = deque(maxlen=50)  # Store debug messages with fixed max length
        self.visible = False  # Default to hidden
        self.width = 400  # Width of debug console
        self.height = 300  # Height of debug console
        self.scroll_offset = 0  # Index of the first visible message
        self.max_visible_messages = 18  # Maximum number of messages to display at once
        self.font = pygame.font.SysFont("Courier New", 12)  # Monospaced font for debugging
        self.background_color = (0, 0, 0, 180)  # Semi-transparent black
        self.border_color = (100, 100, 100)  # Gray border
        self.text_color = (0, 255, 0)  # Green text for debug messages
        self.title_color = (255, 255, 0)  # Yellow for title
        
    def toggle(self):
        """Toggle the visibility of the debug console"""
        self.visible = not self.visible
        if self.visible:
            self.add_message("Debug console activated", (255, 255, 0))
        
    def add_message(self, msg, color=(0, 255, 0)):
        """Add a message to the debug console"""
        if not msg or msg.strip() == "":
            return
            
        # Add timestamp
        timestamp = pygame.time.get_ticks() // 1000  # seconds
        formatted_msg = f"[{timestamp}s] {msg}"
        
        self.messages.append({
            "text": formatted_msg,
            "color": color,
            "time": pygame.time.get_ticks()
        })
        
    def handle_scroll(self, event):
        """Handle scrolling in the debug console"""
        if not self.visible:
            return False
            
        # Check if mouse is over the debug console
        mouse_pos = pygame.mouse.get_pos()
        screen_width, screen_height = pygame.display.get_surface().get_size()
        console_rect = pygame.Rect(
            screen_width - self.width - 10, 
            screen_height - self.height - 10, 
            self.width, 
            self.height
        )
        
        if not console_rect.collidepoint(mouse_pos):
            return False
            
        # Handle mouse wheel scrolling
        if event.type == pygame.MOUSEWHEEL:
            if event.y > 0:  # Scroll up
                self.scroll_offset = max(0, self.scroll_offset - 3)
            elif event.y < 0:  # Scroll down
                max_scroll = max(0, len(self.messages) - self.max_visible_messages)
                self.scroll_offset = min(max_scroll, self.scroll_offset + 3)
            return True
            
        # Handle key scrolling
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_PAGEUP:
                self.scroll_offset = max(0, self.scroll_offset - self.max_visible_messages)
                return True
            elif event.key == pygame.K_PAGEDOWN:
                max_scroll = max(0, len(self.messages) - self.max_visible_messages)
                self.scroll_offset = min(max_scroll, self.scroll_offset + self.max_visible_messages)
                return True
            elif event.key == pygame.K_HOME:
                self.scroll_offset = 0
                return True
            elif event.key == pygame.K_END:
                self.scroll_offset = max(0, len(self.messages) - self.max_visible_messages)
                return True
                
        return False
        
    def draw(self, screen):
        """Draw the debug console if visible"""
        if not self.visible:
            return
            
        # Get screen dimensions and calculate console position
        screen_width, screen_height = pygame.display.get_surface().get_size()
        x = screen_width - self.width - 10
        y = screen_height - self.height - 10
        
        # Create a semi-transparent surface
        console_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        pygame.draw.rect(console_surface, self.background_color, (0, 0, self.width, self.height))
        pygame.draw.rect(console_surface, self.border_color, (0, 0, self.width, self.height), 2)
        
        # Draw title
        title_text = self.font.render("DEBUG CONSOLE (Press D to hide)", True, self.title_color)
        console_surface.blit(title_text, (10, 5))
        
        # Draw a separator line
        pygame.draw.line(console_surface, self.border_color, (5, 25), (self.width - 5, 25), 1)
        
        # Draw messages
        visible_messages = list(self.messages)[-self.max_visible_messages-self.scroll_offset:]
        visible_messages = visible_messages[self.scroll_offset:self.scroll_offset+self.max_visible_messages]
        
        for i, msg in enumerate(visible_messages):
            message_text = self.font.render(msg["text"], True, msg["color"])
            console_surface.blit(message_text, (10, 30 + i * 15))
            
        # Draw scrollbar if needed
        if len(self.messages) > self.max_visible_messages:
            scrollbar_height = max(30, self.height * self.max_visible_messages / len(self.messages))
            scrollbar_y = 30 + (self.height - 40) * self.scroll_offset / max(1, len(self.messages) - self.max_visible_messages)
            pygame.draw.rect(console_surface, (150, 150, 150), 
                             (self.width - 15, scrollbar_y, 10, scrollbar_height))
        
        # Blit the console to the screen
        screen.blit(console_surface, (x, y))

# Create a global debug console instance
debug_console = DebugConsole()

# Helper function to get memory usage for debug purposes
def get_memory_usage():
    """Get current memory usage of the process in MB"""
    try:
        import psutil
        import os
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        return f"Memory: {memory_mb:.1f} MB"
    except ImportError:
        return "Memory: psutil not installed"

# Message Manager class
class MessageManager:
    def __init__(self):
        self.messages = deque(maxlen=100)  # Store more messages but with fixed max length
        self.scroll_offset = 0             # Index of the first visible message
        self.max_visible_messages = 7      # Maximum number of messages to display at once
        self.last_message_time = 0         # Timestamp (in ms) when the last message was added
        self.pending_messages = []         # Messages waiting to be added
        self.message_display_time = 30000  # Time in ms to keep messages in queue (30 seconds)
        
        # Group similar messages with a cooldown timer (in ms)
        self.message_batching = {}         # Store message text to count of occurrences
        self.batch_timeout = 1000          # Timeout for batching similar messages
        self.last_batch_time = 0           # Last time batches were processed
        
        # Scrolling Animation
        self.target_scroll_offset = 0      # Target scroll position for smooth scrolling
        self.scroll_animation_active = False  # Whether a scroll animation is in progress
        self.scroll_animation_start = 0    # Start time of the scroll animation
        self.scroll_animation_duration = 150  # Duration of scroll animation in ms
        self.scroll_start_offset = 0       # Starting scroll offset for animation
        
        # Scrollbar properties
        self.scrollbar_dragging = False    # Whether the scrollbar is being dragged
        self.scrollbar_drag_start_y = 0    # Starting Y position for scrollbar drag
        self.scrollbar_drag_start_offset = 0  # Starting scroll offset for scrollbar drag
        
        # UI feedback
        self.scroll_fade_time = 1000        # Time in ms that scroll indicators remain visible
        self.last_scroll_time = 0           # Last time the user scrolled
        self.scroll_indicator_alpha = 0     # Alpha transparency for scroll indicators (0-255)
        
        # Filter settings
        self.category_filters = {
            MessageCategory.SYSTEM: True,
            MessageCategory.COMBAT: True,
            MessageCategory.INVENTORY: True,
            MessageCategory.QUEST: True,
            MessageCategory.DIALOG: True,
            MessageCategory.ERROR: True,
            MessageCategory.INFO: True
        }
        self.min_priority = MessagePriority.LOW  # Show all messages by default
        
    def add_message(self, msg, color=WHITE, category=MessageCategory.INFO, priority=MessagePriority.NORMAL):
        """
        Add a message to the queue with priority and category.
        
        Args:
            msg (str): The message text
            color (tuple): RGB color tuple
            category (str): Message category from MessageCategory
            priority (int): Priority level from MessagePriority
        """
        # Skip empty messages
        if not msg or msg.strip() == "":
            return
            
        # Skip filtered categories
        if category in self.category_filters and not self.category_filters[category]:
            return
            
        # Skip low priority messages if filter is active
        if priority < self.min_priority:
            return
        
        # Check if this message should be batched (for similar messages in a short time)
        now = pygame.time.get_ticks()
        
        # Handle message batching
        if self._should_batch_message(msg, category):
            # Update batch count instead of adding a new message
            self._update_batch(msg, now)
            return
        
        # Add a new message
        self.messages.append({
            "text": msg,
            "time": now,
            "color": color,
            "category": category,
            "priority": priority,
            "batch_count": 1  # Start with 1 for a single message
        })
        
        self.last_message_time = now
        
        # Process pending messages
        self._process_pending_messages(now)
        
    def _should_batch_message(self, msg, category):
        """Determine if the message should be batched with similar ones"""
        # Don't batch critical messages, dialog, or quest messages
        if (category in [MessageCategory.QUEST, MessageCategory.DIALOG] or 
            category == MessageCategory.ERROR):
            return False
            
        # Check if we have a similar message recently added
        for message in reversed(self.messages):
            # Only check recent messages (within batch timeout)
            if pygame.time.get_ticks() - message["time"] > self.batch_timeout:
                break
                
            # Simple batching rule: exact same text = same message
            # Could be made more sophisticated with similarity checks
            if message["text"] == msg and message["category"] == category:
                return True
                
        return False
        
    def _update_batch(self, msg, now):
        """Update the batch count for similar messages"""
        # Find the similar message and update its count
        for message in reversed(self.messages):
            if message["text"] == msg:
                message["batch_count"] += 1
                message["time"] = now  # Reset the time for this batch
                self.last_message_time = now
                return
    
    def _process_pending_messages(self, now):
        """Process any pending messages"""
        for pending_msg in self.pending_messages:
            if isinstance(pending_msg, dict):
                # If it's already a message dict, use it as is
                pending_msg["time"] = now
                self.messages.append(pending_msg)
            elif pending_msg and pending_msg.strip() != "":
                # If it's just a string, create a basic message
                self.messages.append({
                    "text": pending_msg,
                    "time": now,
                    "color": WHITE,
                    "category": MessageCategory.INFO,
                    "priority": MessagePriority.NORMAL,
                    "batch_count": 1
                })
        
        self.pending_messages = []  # Clear pending messages
    
    def update(self):
        """Update the message queue, removing expired messages and handling animations"""
        now = pygame.time.get_ticks()
        
        # Update the batch cooldown
        if now - self.last_batch_time > self.batch_timeout:
            self.message_batching = {}  # Clear batching data
            self.last_batch_time = now
            
        # Remove expired messages (from the left/oldest side of the deque)
        while self.messages and now - self.messages[0]["time"] > self.message_display_time:
            self.messages.popleft()
            
        # If we've removed messages, adjust scroll offset
        if self.scroll_offset > 0 and self.scroll_offset >= len(self.messages):
            self.scroll_offset = max(0, len(self.messages) - self.max_visible_messages)
            self.target_scroll_offset = self.scroll_offset  # Update target too
            
        # Update smooth scrolling animation
        if self.scroll_animation_active:
            # Calculate elapsed time for the animation
            elapsed = now - self.scroll_animation_start
            
            if elapsed >= self.scroll_animation_duration:
                # Animation is complete, set to target position
                self.scroll_offset = self.target_scroll_offset
                self.scroll_animation_active = False
            else:
                # Calculate interpolated position
                progress = elapsed / self.scroll_animation_duration
                # Use ease-out cubic function for smooth animation
                # t * (2 - t) is a simple ease-out function
                t = progress
                ease_factor = t * (2 - t)
                
                # Calculate new scroll position
                diff = self.target_scroll_offset - self.scroll_start_offset
                self.scroll_offset = int(self.scroll_start_offset + diff * ease_factor)
        
        # Update scroll indicator fade effect
        if self.scroll_indicator_alpha > 0:
            # Fade out scroll indicators over time
            elapsed = now - self.last_scroll_time
            if elapsed > self.scroll_fade_time:
                self.scroll_indicator_alpha = 0
            else:
                # Linear fade from 255 to 0
                self.scroll_indicator_alpha = int(255 * (1 - elapsed / self.scroll_fade_time))
    
    def get_visible_messages(self):
        """Get the currently visible messages based on scroll offset"""
        if not self.messages:
            return []
            
        max_index = min(self.scroll_offset + self.max_visible_messages, len(self.messages))
        return list(self.messages)[self.scroll_offset:max_index]
    
    def handle_scroll(self, event):
        """Handle scrolling through the message history"""
        now = pygame.time.get_ticks()
        handled = False
        
        if hasattr(event, 'type'):
            # Handle keyboard scrolling
            if event.type == pygame.KEYDOWN:
                max_offset = max(0, len(self.messages) - self.max_visible_messages)
                
                if event.key == pygame.K_PAGEUP:
                    # Large scroll up (show older messages)
                    self._start_scroll_animation(max(0, self.scroll_offset - self.max_visible_messages))
                    handled = True
                elif event.key == pygame.K_UP:
                    # Small scroll up (show older messages)
                    self._start_scroll_animation(max(0, self.scroll_offset - 1))
                    handled = True
                elif event.key == pygame.K_PAGEDOWN:
                    # Large scroll down (show newer messages)
                    self._start_scroll_animation(min(max_offset, self.scroll_offset + self.max_visible_messages))
                    handled = True
                elif event.key == pygame.K_DOWN:
                    # Small scroll down (show newer messages)
                    self._start_scroll_animation(min(max_offset, self.scroll_offset + 1))
                    handled = True
                elif event.key == pygame.K_HOME:
                    # Scroll to the beginning (oldest messages)
                    self._start_scroll_animation(0)
                    handled = True
                elif event.key == pygame.K_END:
                    # Scroll to the end (newest messages)
                    self._start_scroll_animation(max_offset)
                    handled = True
                    
            # Handle mouse wheel events
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 4:  # Scroll up
                    max_offset = max(0, len(self.messages) - self.max_visible_messages)
                    self._start_scroll_animation(max(0, self.scroll_offset - 3))
                    handled = True
                elif event.button == 5:  # Scroll down
                    max_offset = max(0, len(self.messages) - self.max_visible_messages)
                    self._start_scroll_animation(min(max_offset, self.scroll_offset + 3))
                    handled = True
                elif event.button == 1:  # Left mouse button
                    # Check if clicked on scrollbar - handled in draw_scrollbar
                    pass
                    
        if handled:
            self.last_scroll_time = now
            self.scroll_indicator_alpha = 255  # Fully visible
            
        return handled
    
    def _start_scroll_animation(self, target_offset):
        """Start a smooth scrolling animation to the target offset"""
        self.target_scroll_offset = target_offset
        self.scroll_animation_start = pygame.time.get_ticks()
        self.scroll_animation_active = True
        self.scroll_start_offset = self.scroll_offset
        
    def handle_scrollbar_event(self, event, scrollbar_rect):
        """Handle mouse interaction with the scrollbar"""
        if not self.messages or len(self.messages) <= self.max_visible_messages:
            return False
            
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Check if click is within scrollbar area
            if scrollbar_rect.collidepoint(event.pos):
                self.scrollbar_dragging = True
                self.scrollbar_drag_start_y = event.pos[1]
                self.scrollbar_drag_offset = self.scroll_offset
                self.last_scroll_time = pygame.time.get_ticks()
                self.scroll_indicator_alpha = 255  # Fully visible
                return True
                
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.scrollbar_dragging:
                self.scrollbar_dragging = False
                return True
                
        elif event.type == pygame.MOUSEMOTION and self.scrollbar_dragging:
            # Calculate new scroll position based on mouse movement
            delta_y = event.pos[1] - self.scrollbar_drag_start_y
            scrollbar_height = scrollbar_rect.height
            max_messages = len(self.messages) - self.max_visible_messages
            
            if max_messages > 0 and scrollbar_height > 0:
                # Calculate scroll position based on drag distance
                scroll_ratio = delta_y / float(scrollbar_height)
                scroll_amount = int(scroll_ratio * max_messages)
                new_offset = max(0, min(max_messages, self.scrollbar_drag_offset + scroll_amount))
                
                if new_offset != self.scroll_offset:
                    self.scroll_offset = new_offset
                    self.last_scroll_time = pygame.time.get_ticks()
                    self.scroll_indicator_alpha = 255  # Fully visible
                    return True
                    
        return False
    
    def set_category_filter(self, category, enabled):
        """Enable or disable a message category"""
        if category in self.category_filters:
            self.category_filters[category] = enabled
    
    def set_min_priority(self, priority):
        """Set the minimum priority level for messages to be displayed"""
        self.min_priority = priority
        
    def clear(self):
        """Clear all messages"""
        self.messages.clear()
        self.pending_messages = []
        self.scroll_offset = 0
        self.target_scroll_offset = 0
        self.scroll_animation_active = False
        self.scrollbar_dragging = False
        
    def draw_scrollbar(self, screen, panel_rect):
        """
        Draw the scrollbar and scroll indicators on the message panel.
        
        Args:
            screen: The pygame screen to draw on
            panel_rect: The rectangle of the message panel
            
        Returns:
            pygame.Rect: The scrollbar rectangle (for click detection)
        """
        if not self.messages or len(self.messages) <= self.max_visible_messages:
            return None  # No scrollbar needed
            
        total_messages = len(self.messages)
        visible_ratio = min(1.0, self.max_visible_messages / float(total_messages))
        
        # Scrollbar dimensions and position
        scrollbar_width = 10
        scrollbar_x = panel_rect.right - scrollbar_width - 5  # 5px padding
        scrollbar_height = panel_rect.height - 20  # 10px padding on top and bottom
        scrollbar_y = panel_rect.y + 10  # 10px padding from top
        
        # Create the scrollbar background (track)
        scrollbar_track = pygame.Rect(scrollbar_x, scrollbar_y, scrollbar_width, scrollbar_height)
        scrollbar_track_color = pygame.Color(50, 50, 50, 150)  # Semi-transparent dark gray
        
        # Draw the scrollbar track
        scrollbar_track_surface = pygame.Surface((scrollbar_width, scrollbar_height), pygame.SRCALPHA)
        scrollbar_track_surface.fill(scrollbar_track_color)
        screen.blit(scrollbar_track_surface, (scrollbar_x, scrollbar_y))
        
        # Create the scrollbar handle
        handle_height = max(20, int(scrollbar_height * visible_ratio))
        
        # Calculate handle position based on scroll offset
        if total_messages - self.max_visible_messages > 0:
            scroll_progress = self.scroll_offset / float(total_messages - self.max_visible_messages)
        else:
            scroll_progress = 0
        
        handle_y = scrollbar_y + int(scroll_progress * (scrollbar_height - handle_height))
        scrollbar_handle = pygame.Rect(scrollbar_x, handle_y, scrollbar_width, handle_height)
        
        # Determine handle color - brighter when active
        if self.scrollbar_dragging:
            handle_color = pygame.Color(200, 200, 200, 220)  # Bright, opaque
        else:
            # Use alpha based on scroll indicator fade
            alpha = max(120, self.scroll_indicator_alpha)  # Minimum visibility
            handle_color = pygame.Color(180, 180, 180, alpha)
        
        # Draw the scrollbar handle
        scrollbar_handle_surface = pygame.Surface((scrollbar_width, handle_height), pygame.SRCALPHA)
        scrollbar_handle_surface.fill(handle_color)
        screen.blit(scrollbar_handle_surface, (scrollbar_x, handle_y))
        
        # Draw scroll indicators if we have scrollable content
        if self.scroll_indicator_alpha > 0:
            # Only show indicators if we can scroll in that direction
            
            # Up indicator (for older messages)
            if self.scroll_offset > 0:
                self._draw_scroll_indicator(screen, panel_rect.x + panel_rect.width // 2, 
                                           panel_rect.y + 5, True, self.scroll_indicator_alpha)
            
            # Down indicator (for newer messages)
            if self.scroll_offset < total_messages - self.max_visible_messages:
                self._draw_scroll_indicator(screen, panel_rect.x + panel_rect.width // 2,
                                           panel_rect.y + panel_rect.height - 15, False, self.scroll_indicator_alpha)
        
        return scrollbar_track  # Return the clickable area
        
    def _draw_scroll_indicator(self, screen, x, y, is_up, alpha):
        """Draw a scroll indicator arrow"""
        # Create points for triangle
        if is_up:
            points = [(x - 8, y + 8), (x, y), (x + 8, y + 8)]
        else:
            points = [(x - 8, y - 8), (x, y), (x + 8, y - 8)]
            
        # Draw with alpha transparency
        arrow_color = pygame.Color(255, 255, 255, alpha)
        
        # Create a surface for the arrow
        arrow_surface = pygame.Surface((16, 8), pygame.SRCALPHA)
        # Draw the arrow on the surface
        pygame.draw.polygon(arrow_surface, arrow_color, [(p[0]-x+8, p[1]-y+4) for p in points])
        # Blit the surface to the screen
        screen.blit(arrow_surface, (x - 8, y - 4))

# Create a global message manager instance
message_manager = MessageManager()


# === Game Entity Classes ===

# Monster class (this is the more detailed version from blade_sigil_v5_5.py)
class Monster:
    def __init__(self, name, hit_points, to_hit, ac, move, dam, sprites, **kwargs):
        self.name = name
        self.hit_points = hit_points
        self.max_hit_points = hit_points
        self.to_hit = to_hit
        self.ac = ac
        self.move = move
        self.dam = dam
        self.sprites = sprites # This should be a dict like {"live": "path/to/live.png", "dead": "path/to/dead.png"}

        self.monster_type = kwargs.get('monster_type', 'beast')
        self.level = kwargs.get('level', 1)
        self.cr = kwargs.get('cr', 1)
        self.vulnerabilities = kwargs.get('vulnerabilities', [])
        self.resistances = kwargs.get('resistances', [])
        self.immunities = kwargs.get('immunities', [])
        self.special_abilities = kwargs.get('special_abilities', [])
        self.is_dead = False
        self.active_effects = []
        self.can_move = True
        self.can_act = True

        try:
            if self.sprites and self.sprites.get('live') and os.path.exists(self.sprites['live']):
                self.sprite = pygame.image.load(self.sprites['live']).convert_alpha()
                self.sprite = pygame.transform.smoothscale(self.sprite, (TILE_SIZE, TILE_SIZE))
            else:
                fallback_sprites = {
                    'beast': '/Users/williammarcellino/Documents/Fantasy_Game/Fantasy_Game_Art_Assets/Enemies/beast/giant_rat.jpg',
                    'humanoid': '/Users/williammarcellino/Documents/Fantasy_Game/Fantasy_Game_Art_Assets/Enemies/humanoids/goblin.png',
                    'undead': '/Users/williammarcellino/Documents/Fantasy_Game/Fantasy_Game_Art_Assets/Enemies/undead/skel_01.png',
                    # Add other types as needed or a more generic fallback
                    'default': '/Users/williammarcellino/Documents/Fantasy_Game/Fantasy_Game_Art_Assets/Enemies/monstrosity/green_slime.jpg'
                }
                fallback_path = fallback_sprites.get(self.monster_type, fallback_sprites['default'])
                self.sprite = pygame.image.load(fallback_path).convert_alpha()
                self.sprite = pygame.transform.smoothscale(self.sprite, (TILE_SIZE, TILE_SIZE))
        except (pygame.error, FileNotFoundError) as e:
            print(f"Error loading sprite for {self.name}: {e}. Using placeholder.")
            self.sprite = pygame.Surface((TILE_SIZE, TILE_SIZE))
            self.sprite.fill(RED)
        self.position = None

    def move_towards(self, target, dungeon, is_player=False):
        if self.position is None or target.position is None: return
        if not self.can_move: return

        monster_x, monster_y = self.position[0] // TILE_SIZE, self.position[1] // TILE_SIZE
        target_x, target_y = target.position[0] // TILE_SIZE, target.position[1] // TILE_SIZE
        dx = target_x - monster_x
        dy = target_y - monster_y

        new_pos_x, new_pos_y = monster_x, monster_y

        if abs(dx) > abs(dy):
            step_x = 1 if dx > 0 else -1
            if 0 <= monster_x + step_x < dungeon.width and dungeon.tiles[monster_x + step_x][monster_y].type in ('floor', 'corridor', 'door'):
                new_pos_x = monster_x + step_x
            elif dy != 0: # Try vertical if horizontal is blocked
                step_y = 1 if dy > 0 else -1
                if 0 <= monster_y + step_y < dungeon.height and dungeon.tiles[monster_x][monster_y + step_y].type in ('floor', 'corridor', 'door'):
                    new_pos_y = monster_y + step_y
        else: # abs(dy) >= abs(dx)
            step_y = 1 if dy > 0 else -1
            if 0 <= monster_y + step_y < dungeon.height and dungeon.tiles[monster_x][monster_y + step_y].type in ('floor', 'corridor', 'door'):
                new_pos_y = monster_y + step_y
            elif dx != 0: # Try horizontal if vertical is blocked
                step_x = 1 if dx > 0 else -1
                if 0 <= monster_x + step_x < dungeon.width and dungeon.tiles[monster_x + step_x][monster_y].type in ('floor', 'corridor', 'door'):
                    new_pos_x = monster_x + step_x

        if new_pos_x != monster_x or new_pos_y != monster_y:
            self.position = [new_pos_x * TILE_SIZE + TILE_SIZE // 2, new_pos_y * TILE_SIZE + TILE_SIZE // 2]

    def get_effective_ac(self):
        return self.ac

    def get_effective_damage(self):
        return roll_dice_expression(self.dam) # roll_dice_expression is in common_b_s

    def set_dead_sprite(self):
        if 'dead' in self.sprites and self.sprites['dead'] and os.path.exists(self.sprites['dead']):
            try:
                self.sprite = pygame.image.load(self.sprites['dead']).convert_alpha()
                self.sprite = pygame.transform.smoothscale(self.sprite, (TILE_SIZE, TILE_SIZE))
            except (pygame.error, FileNotFoundError): self._tint_sprite_gray()
        else: self._tint_sprite_gray()

    def _tint_sprite_gray(self):
        if self.sprite:
            temp_sprite = self.sprite.copy()
            gray_overlay = pygame.Surface(temp_sprite.get_size(), pygame.SRCALPHA)
            gray_overlay.fill((30, 30, 30, 180))
            temp_sprite.blit(gray_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            red_tint = pygame.Surface(temp_sprite.get_size(), pygame.SRCALPHA)
            red_tint.fill((100, 0, 0, 50))
            temp_sprite.blit(red_tint, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            dark_overlay = pygame.Surface(temp_sprite.get_size(), pygame.SRCALPHA)
            dark_overlay.fill((0, 0, 0, 50))
            temp_sprite.blit(dark_overlay, (0, 0))
            self.sprite = temp_sprite

    def apply_damage(self, damage_amount, damage_type="physical"):
        if damage_type in self.immunities: return 0
        if damage_type in self.vulnerabilities: damage_amount *= 2
        if damage_type in self.resistances: damage_amount = max(1, damage_amount // 2)
        self.hit_points -= damage_amount
        self.hit_points = max(0, self.hit_points)
        if self.hit_points == 0: self.is_dead = True
        return damage_amount

class Dungeon:
    def __init__(self, width, height, level=1, map_number=1, max_maps=1,
                 max_rooms=None, min_room_size=None, max_room_size=None):
        self.width = width
        self.height = height
        self.level = level  # Current dungeon level (increases as player descends)
        self.map_number = map_number  # Current map within this level (1-based)
        self.max_maps = max_maps  # Total number of maps on this level

        # Room generation parameters (can be modified as player progresses)
        self.max_rooms = max_rooms or (width // 4 + level)  # Default scales with level
        self.min_room_size = min_room_size or 3  # Default minimum room size
        self.max_room_size = max_room_size or (6 + level // 3)  # Default scales with level

        self.tiles = [[Tile(x, y, 'wall') for y in range(height)] for x in range(width)]
        self.monsters = []  # List to store spawned monsters
        self.dropped_items = []  # List for item drops
        self.doors = {}  # Dictionary to store door objects keyed by (x,y) coords
        self.chests = {}  # Dictionary to store chest objects keyed by (x,y) coords

        # --- Special Features ---
        # Transition points
        self.level_transition_door = None  # Door that leads to the next level
        self.map_transition_doors = {}  # Doors that lead to other maps on same level

        # Debug flag for verbose door reporting
        self._debug_doors_verbose = True

        # Create the dungeon structure and get starting position
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
        rooms = []
        max_attempts = self.max_rooms * 3  # Try more times than max_rooms to find spots

        for _ in range(max_attempts):
            if len(rooms) >= self.max_rooms:
                break

            # Generate random room dimensions
            room_w = random.randint(self.min_room_size, self.max_room_size)
            room_h = random.randint(self.min_room_size, self.max_room_size)

            # Generate random position within map bounds (with 1 tile margin)
            room_x = random.randint(1, self.width - room_w - 1)
            room_y = random.randint(1, self.height - room_h - 1)

            new_room = (room_x, room_y, room_w, room_h)

            # Check for overlap with existing rooms
            failed = False
            for other_room in rooms:
                # Add 1 tile buffer around room to ensure separation (except for corridors)
                # Check if rectangles overlap: (x1 < x2 + w2) and (x1 + w1 > x2) and ...
                # Using padding of 2 to ensure at least 1 wall between rooms
                if (room_x - 2 < other_room[0] + other_room[2] and
                    room_x + room_w + 2 > other_room[0] and
                    room_y - 2 < other_room[1] + other_room[3] and
                    room_y + room_h + 2 > other_room[1]):
                    failed = True
                    break

            if not failed:
                # Create the room
                rooms.append(new_room)

                # Carve room
                for rx in range(room_x, room_x + room_w):
                    for ry in range(room_y, room_y + room_h):
                        self.tiles[rx][ry].type = 'floor'
                        self.tiles[rx][ry].sprite = load_sprite(assets_data["sprites"]["tiles"]["floor"])

                # Connect to previous room (if any)
                if len(rooms) > 1:
                    prev_room = rooms[-2]

                    # Get center points
                    new_center_x, new_center_y = room_x + room_w // 2, room_y + room_h // 2
                    prev_center_x, prev_center_y = prev_room[0] + prev_room[2] // 2, prev_room[1] + prev_room[3] // 2

                    # Carve corridor (horizontal then vertical or vice versa)
                    if random.choice([True, False]):
                        # Horizontal first, then vertical
                        self._carve_h_corridor(prev_center_x, new_center_x, prev_center_y)
                        self._carve_v_corridor(prev_center_y, new_center_y, new_center_x)
                    else:
                        # Vertical first, then horizontal
                        self._carve_v_corridor(prev_center_y, new_center_y, prev_center_x)
                        self._carve_h_corridor(prev_center_x, new_center_x, new_center_y)

    def _carve_h_corridor(self, x1, x2, y):
        """Carve a horizontal corridor"""
        for x in range(min(x1, x2), max(x1, x2) + 1):
            if self.tiles[x][y].type != 'floor':
                self.tiles[x][y].type = 'corridor'
                self.tiles[x][y].sprite = load_sprite(assets_data["sprites"]["tiles"]["floor"])

    def _carve_v_corridor(self, y1, y2, x):
        """Carve a vertical corridor"""
        for y in range(min(y1, y2), max(y1, y2) + 1):
            if self.tiles[x][y].type != 'floor':
                self.tiles[x][y].type = 'corridor'
                self.tiles[x][y].sprite = load_sprite(assets_data["sprites"]["tiles"]["floor"])

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
            # Filter for monsters appropriate to dungeon level
            level_appropriate_monsters = [m for m in monsters_data['monsters']
                                         if m.get('level', 1) <= self.level + 1 and
                                            m.get('level', 1) >= max(1, self.level - 1)]

            if not level_appropriate_monsters:
                level_appropriate_monsters = monsters_data['monsters']  # Fallback if no appropriate monsters found

            monster_choice = random.choice(level_appropriate_monsters)
            print(f"Selected monster: {monster_choice['name']}, Level: {monster_choice.get('level', 1)}")

            monster = Monster(
                name=monster_choice['name'],
                hit_points=monster_choice['hit_points'],
                to_hit=monster_choice['to_hit'],
                ac=monster_choice['ac'],
                move=monster_choice['move'],
                dam=monster_choice['dam'],
                sprites=monster_choice['sprites'],
                monster_type=monster_choice.get('type', 'beast'),
                level=monster_choice.get('level', 1)
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

        # --- Place a transition door ---
        # Add a level/map transition door to a far room
        print(f"DEBUG: Placing transition door. Level: {self.level}, Map: {self.map_number}, Max Maps: {self.max_maps}")
        transition_door = self.place_transition_door(rooms, start_room)
        if transition_door:
            print(f"DEBUG: Transition door placed at ({transition_door.x}, {transition_door.y})")
            print(f"DEBUG: Door type: {transition_door.door_type}, Locked: {transition_door.locked}")
            if transition_door.door_type == "map_transition":
                print(f"DEBUG: Destination map: {transition_door.destination_map}")
        else:
            print("DEBUG: Failed to place transition door!")

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
                for x_coord in range(min(x1, x2), max(x1, x2) + 1): # Renamed x to x_coord
                    self.tiles[x_coord][y1].type = 'floor'
                for y_coord in range(min(y1, y2), max(y1, y2) + 1): # Renamed y to y_coord
                    self.tiles[x2][y_coord].type = 'floor'
            else:
                for y_coord in range(min(y1, y2), max(y1, y2) + 1): # Renamed y to y_coord
                    self.tiles[x1][y_coord].type = 'floor'
                for x_coord in range(min(x1, x2), max(x1, x2) + 1): # Renamed x to x_coord
                    self.tiles[x_coord][y2].type = 'floor'
        elif x1 == x2:
            for y_coord in range(min(y1, y2), max(y1, y2) + 1): # Renamed y to y_coord
                self.tiles[x1][y_coord].type = 'floor'
        else:
            for x_coord in range(min(x1, x2), max(x1, x2) + 1): # Renamed x to x_coord
                self.tiles[x_coord][y1].type = 'floor'

    def find_start_position_in_room(self, room):
        x_coord, y_coord, w, h = room # Renamed x,y to x_coord,y_coord
        start_x = random.randint(x_coord, x_coord + w - 1)
        start_y = random.randint(y_coord, y_coord + h - 1)
        return [start_x * TILE_SIZE + TILE_SIZE // 2, start_y * TILE_SIZE + TILE_SIZE // 2]

    def find_random_position_in_room(self, room):
        x_coord, y_coord, w, h = room # Renamed x,y to x_coord,y_coord
        return (random.randint(x_coord, x_coord + w - 1), random.randint(y_coord, y_coord + h - 1))

    def draw(self, surface):
        # Draw the background
        pygame.draw.rect(surface, LIGHT_GRAY, (0, 0, self.width * TILE_SIZE, self.height * TILE_SIZE))

        # Draw grid lines (optional)
        for x_coord in range(self.width + 1): # Renamed x to x_coord
            pygame.draw.line(surface, BLACK, (x_coord * TILE_SIZE, 0), (x_coord * TILE_SIZE, self.height * TILE_SIZE), 1)
        for y_coord in range(self.height + 1): # Renamed y to y_coord
            pygame.draw.line(surface, BLACK, (0, y_coord * TILE_SIZE), (self.width * TILE_SIZE, y_coord * TILE_SIZE), 1)

        # Collect door information for debug output
        door_count = 0
        transition_door_count = 0
        door_info = []

        # FIRST PASS: Draw regular tiles
        for x_coord in range(self.width): # Renamed x to x_coord
            for y_coord in range(self.height): # Renamed y to y_coord
                # Handle regular tiles first
                if self.tiles[x_coord][y_coord].type in ('floor', 'corridor') and self.tiles[x_coord][y_coord].sprite:
                    surface.blit(self.tiles[x_coord][y_coord].sprite, (x_coord * TILE_SIZE, y_coord * TILE_SIZE))
                    # Draw grid coordinates on floor tiles for debugging
                    debug_text = font.render(f"{x_coord},{y_coord}", True, (100, 100, 100))
                    surface.blit(debug_text, (x_coord * TILE_SIZE + 2, y_coord * TILE_SIZE + 2))
                elif self.tiles[x_coord][y_coord].type == 'wall':
                    pygame.draw.rect(surface, BLACK, (x_coord * TILE_SIZE, y_coord * TILE_SIZE, TILE_SIZE, TILE_SIZE))

        # SECOND PASS: Draw doors without special highlighting
        for x_coord in range(self.width): # Renamed x to x_coord
            for y_coord in range(self.height): # Renamed y to y_coord
                # Special handling for doors - draw them in a separate pass
                if self.tiles[x_coord][y_coord].type in ('door', 'locked_door'):
                    door_count += 1
                    current_door_coords = (x_coord, y_coord) # Renamed door_coords to current_door_coords

                    # Just draw the door sprite without any extra highlighting or labels
                    if current_door_coords in self.doors:
                        door = self.doors[current_door_coords]
                        door_sprite = door.sprite
                        surface.blit(door_sprite, (x_coord * TILE_SIZE, y_coord * TILE_SIZE))

                        # Collect debug info (but don't display it)
                        door_info.append(f"Door at ({x_coord}, {y_coord}): type={door.door_type}, locked={door.locked}")
                        if hasattr(door, "destination_map"):
                            door_info.append(f"  Destination map: {door.destination_map}")
                            transition_door_count += 1
                    # Otherwise, use the tile's sprite (fallback)
                    elif self.tiles[x_coord][y_coord].sprite:
                        surface.blit(self.tiles[x_coord][y_coord].sprite, (x_coord * TILE_SIZE, y_coord * TILE_SIZE))

        # Print summary of door information (only if we found doors)
        if door_count > 0:
            print(f"DEBUG: Found {door_count} doors total, {transition_door_count} are transition doors")
            print("DEBUG: Door details:")
            for info_line in door_info: # Renamed info to info_line
                print(f"  {info_line}")

        # Draw treasure chests
        for (chest_x, chest_y), chest in self.chests.items(): # Renamed x,y to chest_x, chest_y
            if chest.sprite:
                surface.blit(chest.sprite, (chest_x * TILE_SIZE, chest_y * TILE_SIZE))

                # If chest is locked, add a visual indicator
                if chest.locked and not chest.open:
                    # Draw a gold border around locked chests
                    pygame.draw.rect(surface, (255, 215, 0),
                                    (chest_x * TILE_SIZE, chest_y * TILE_SIZE, TILE_SIZE, TILE_SIZE), 2)

        # Now draw dropped items
        for drop in self.dropped_items:
            item_sprite = getattr(drop['item'], 'sprite', loot_drop_sprite)
            item_x, item_y = drop['position'] # Renamed x,y to item_x, item_y

            if item_sprite:
                # Draw the item sprite centered on its tile
                surface.blit(item_sprite, (item_x - TILE_SIZE // 2, item_y - TILE_SIZE // 2))
            else:
                # If no sprite, draw a fallback marker
                pygame.draw.circle(surface, RED, (item_x, item_y), 5)


    def place_transition_door(self, rooms, start_room):
        """Place a transition door in a room far from the start room."""
        # Skip if no rooms or only one room
        if not rooms or len(rooms) <= 1:
            print("Not enough rooms to place a transition door")
            return None

        # Calculate distances from start room to find the farthest room
        start_center_x = start_room[0] + start_room[2] // 2
        start_center_y = start_room[1] + start_room[3] // 2

        # Find the room farthest from start
        farthest_room = None
        max_distance = 0

        for room in rooms:
            if room == start_room:
                continue

            room_center_x = room[0] + room[2] // 2
            room_center_y = room[1] + room[3] // 2

            # Calculate Euclidean distance
            distance = ((room_center_x - start_center_x) ** 2 +
                       (room_center_y - start_center_y) ** 2) ** 0.5

            if distance > max_distance:
                max_distance = distance
                farthest_room = room

        if not farthest_room:
            print("Could not find a suitable room for transition door")
            return None

        # Place the door in the center of the far wall of the farthest room
        room_x_coord, room_y_coord, room_w, room_h = farthest_room # Renamed x,y,w,h

        # Choose one of the four walls randomly, prioritizing walls against the dungeon edge
        wall_options = []

        # North wall (top)
        if room_y_coord == 0 or all(self.tiles[i][room_y_coord-1].type == 'wall' for i in range(room_x_coord, room_x_coord+room_w)):
            wall_options.append(('north', 2))  # Higher weight for edge walls
        else:
            wall_options.append(('north', 1))

        # South wall (bottom)
        if room_y_coord+room_h >= self.height-1 or all(self.tiles[i][room_y_coord+room_h].type == 'wall' for i in range(room_x_coord, room_x_coord+room_w)):
            wall_options.append(('south', 2))
        else:
            wall_options.append(('south', 1))

        # East wall (right)
        if room_x_coord+room_w >= self.width-1 or all(self.tiles[room_x_coord+room_w][j].type == 'wall' for j in range(room_y_coord, room_y_coord+room_h)):
            wall_options.append(('east', 2))
        else:
            wall_options.append(('east', 1))

        # West wall (left)
        if room_x_coord == 0 or all(self.tiles[room_x_coord-1][j].type == 'wall' for j in range(room_y_coord, room_y_coord+room_h)):
            wall_options.append(('west', 2))
        else:
            wall_options.append(('west', 1))

        # Choose wall based on weights
        weights = [option[1] for option in wall_options]
        total_weight = sum(weights)

        print(f"DEBUG: Wall options: {wall_options}")
        print(f"DEBUG: Total weight: {total_weight}")

        if total_weight == 0:
            chosen_wall = random.choice(['north', 'south', 'east', 'west'])
            print(f"DEBUG: No valid walls, randomly chose: {chosen_wall}")
        else:
            # Random weighted choice
            r_val = random.uniform(0, total_weight) # Renamed r to r_val
            upto = 0
            for option, weight in wall_options:
                if upto + weight >= r_val:
                    chosen_wall = option
                    break
                upto += weight
            else:
                chosen_wall = wall_options[-1][0]  # Fallback
            print(f"DEBUG: Chose wall with weights: {chosen_wall}")

        # Place the door based on the chosen wall
        if chosen_wall == 'north':
            door_x = room_x_coord + room_w // 2
            door_y = room_y_coord
        elif chosen_wall == 'south':
            door_x = room_x_coord + room_w // 2
            door_y = room_y_coord + room_h - 1
        elif chosen_wall == 'east':
            door_x = room_x_coord + room_w - 1
            door_y = room_y_coord + room_h // 2
        else:  # west
            door_x = room_x_coord
            door_y = room_y_coord + room_h // 2

        # Determine door type based on map_number and roll
        # If we're on the last map of this level, this could be a level transition
        if self.map_number >= self.max_maps:
            door_type = "level_transition"
            print(f"Creating level transition door at ({door_x}, {door_y})")
        else:
            door_type = "map_transition"
            print(f"Creating map transition door at ({door_x}, {door_y})")

        # Create the transition door (always unlocked for easier progression)
        door = Door(door_x, door_y, locked=False, door_type=door_type)
        print(f"DEBUG: Created {door_type} door at ({door_x}, {door_y})")

        # If it's a map transition, set destination
        if door_type == "map_transition":
            door.destination_map = self.map_number + 1  # Next map in sequence
            print(f"DEBUG: Set destination map to {door.destination_map}")

        # Check sprite status
        if hasattr(door, "sprite") and door.sprite:
            print(f"DEBUG: Door has sprite: {type(door.sprite)}, dimensions: {door.sprite.get_size()}")
        else:
            print("DEBUG: WARNING - Door has no sprite!")

        # Add it to the appropriate collection
        if door_type == "level_transition":
            self.level_transition_door = door
        else:
            self.map_transition_doors[(door_x, door_y)] = door

        # Update the doors dictionary too
        self.doors[(door_x, door_y)] = door

        # Debug log the doors dictionary
        print(f"DEBUG: Doors dictionary now has {len(self.doors)} entries")
        for coords, door_obj in self.doors.items():
            print(f"DEBUG: Door at {coords}: type={door_obj.door_type}, locked={door_obj.locked}")
            if hasattr(door_obj, "destination_map") and door_obj.destination_map:
                print(f"DEBUG: Door at {coords} has destination map: {door_obj.destination_map}")

        # Update the tile based on door's locked state
        self.tiles[door_x][door_y].type = 'locked_door' if door.locked else 'door'
        self.tiles[door_x][door_y].sprite = door.sprite

        return door

    def carve_doors(self):
        """
        Create 1-3 locked doors in corridors connecting rooms,
        ensuring they're truly in corridor spaces.
        """
        # First, identify corridor tiles that are exactly at the transition point
        # between rooms and corridors
        door_coordinates = []

        # Check each corridor tile
        for x_coord in range(1, self.width - 1): # Renamed x to x_coord
            for y_coord in range(1, self.height - 1): # Renamed y to y_coord
                if self.tiles[x_coord][y_coord].type == 'corridor':
                    # Look at each cardinal direction
                    north = (x_coord, y_coord-1)
                    south = (x_coord, y_coord+1)
                    east = (x_coord+1, y_coord)
                    west = (x_coord-1, y_coord)

                    # Check if we're at a dead end connecting to a room
                    # This ensures the door is in the corridor, not the room
                    connects_to_room = False
                    connects_to_corridor = False

                    # Check north
                    if 0 <= north[1] < self.height:
                        if self.tiles[north[0]][north[1]].type == 'floor':
                            connects_to_room = True
                        elif self.tiles[north[0]][north[1]].type == 'corridor':
                            connects_to_corridor = True

                    # Check south
                    if 0 <= south[1] < self.height:
                        if self.tiles[south[0]][south[1]].type == 'floor':
                            connects_to_room = True
                        elif self.tiles[south[0]][south[1]].type == 'corridor':
                            connects_to_corridor = True

                    # Check east
                    if 0 <= east[0] < self.width:
                        if self.tiles[east[0]][east[1]].type == 'floor':
                            connects_to_room = True
                        elif self.tiles[east[0]][east[1]].type == 'corridor':
                            connects_to_corridor = True

                    # Check west
                    if 0 <= west[0] < self.width:
                        if self.tiles[west[0]][west[1]].type == 'floor':
                            connects_to_room = True
                        elif self.tiles[west[0]][west[1]].type == 'corridor':
                            connects_to_corridor = True

                    # A good door location connects to both a room and a corridor
                    if connects_to_room and connects_to_corridor:
                        # Count nearby wall tiles to ensure this is truly a corridor
                        wall_count = 0
                        for nx, ny in [north, south, east, west]:
                            if 0 <= nx < self.width and 0 <= ny < self.height:
                                if self.tiles[nx][ny].type == 'wall':
                                    wall_count += 1

                        # A corridor typically has walls on two sides
                        if wall_count >= 1:  # At least one wall nearby
                            door_coordinates.append((x_coord, y_coord))
                            print(f"Found door location at corridor ({x_coord}, {y_coord}) - connects room to corridor")

        # No valid door locations? Create a fallback door
        if not door_coordinates:
            print("No valid door locations found between rooms.")

            # Find any corridor tile that connects to a floor tile (room)
            for x_coord in range(1, self.width - 1): # Renamed x to x_coord
                for y_coord in range(1, self.height - 1): # Renamed y to y_coord
                    if self.tiles[x_coord][y_coord].type == 'corridor':
                        # Check all adjacent tiles for a floor
                        adjacent_coords = [(x_coord, y_coord-1), (x_coord, y_coord+1), (x_coord+1, y_coord), (x_coord-1, y_coord)]
                        for nx, ny in adjacent_coords:
                            if 0 <= nx < self.width and 0 <= ny < self.height:
                                if self.tiles[nx][ny].type == 'floor':
                                    door_coordinates.append((x_coord, y_coord))
                                    print(f"Found fallback door location at ({x_coord}, {y_coord})")
                                    break
                    if door_coordinates:
                        break
                if door_coordinates:
                    break

            # Still no valid door locations? Find any corridor
            if not door_coordinates:
                for x_coord in range(1, self.width - 1): # Renamed x to x_coord
                    for y_coord in range(1, self.height - 1): # Renamed y to y_coord
                        if self.tiles[x_coord][y_coord].type == 'corridor':
                            door_coordinates.append((x_coord, y_coord))
                            print(f"Found emergency fallback door at ({x_coord}, {y_coord})")
                            break
                    if door_coordinates:
                        break

        # Shuffle and limit to 1-3 doors total
        random.shuffle(door_coordinates)
        max_doors = min(3, len(door_coordinates))

        # Fix for the case when no valid door locations were found
        if max_doors < 1:
            print("WARNING: No valid door locations found. Skipping door creation.")
            return

        num_doors = random.randint(1, max_doors)

        print(f"Creating {num_doors} locked doors from {len(door_coordinates)} potential door locations")

        # Create the specified number of doors
        door_count = 0
        for x_coord, y_coord in door_coordinates: # Renamed x,y to x_coord,y_coord
            if door_count >= num_doors:
                break

            # Create the door object (always locked)
            new_door = Door(x_coord, y_coord, locked=True)

            # Add it to our doors dictionary
            self.doors[(x_coord, y_coord)] = new_door

            # Update the tile to be a locked door
            self.tiles[x_coord][y_coord].type = 'locked_door'

            # Use the door's sprite for rendering
            self.tiles[x_coord][y_coord].sprite = new_door.sprite

            door_count += 1
            print(f"Created locked door at ({x_coord}, {y_coord})")

        # Make all other potential door locations normal corridors
        for x_coord, y_coord in door_coordinates: # Renamed x,y to x_coord,y_coord
            if (x_coord, y_coord) not in self.doors:
                self.tiles[x_coord][y_coord].type = 'corridor'
                self.tiles[x_coord][y_coord].sprite = load_sprite(assets_data["sprites"]["tiles"]["floor"])


# Help screen content
help_content = [
    "=== GAME CONTROLS ===",
    "",
    "MOVEMENT",
    "  Arrow keys - Move character",
    "",
    "COMBAT",
    "  y - Confirm attack when next to enemy",
    "  n - Decline attack",
    "  a - Shoot arrows (Archer class with bow equipped)",
    "",
    "INVENTORY & ITEMS",
    "  i - Open inventory to equip/use items",
    "  g - Pick up items from the ground",
    "",
    "DOORS & CHESTS",
    "  o - Open/force door (Warriors/Priests)",
    "  p - Pick lock (Thieves/Archers with Thieve's Tools)",
    "  u - Magic unlock (Wizards/Spellblades)",
    "",
    "MAGIC",
    "  x - Cast spells (Wizards/Priests/Spellblades)",
    "",
    "TESTING",
    "  t - Testing Mode (1000 HP/SP)",
    "",
    "SAVE & LOAD",
    "  F5 - Save game",
    "  F9 - Load game",
    "",
    "EQUIPMENT",
    "  Bows - Only usable by Archers, required for ranged attacks",
    "  Shortbow - 4 tile range, 1d6 damage",
    "  Longbow - 6 tile range, 1d8 damage",
    "",
    "NAVIGATION",
    "  h - Show this help screen",
    "  PageUp/PageDown - Scroll message history",
    "  ESC - Close menus/screens",
]


def add_message(msg, color=WHITE, category=MessageCategory.INFO, priority=MessagePriority.NORMAL):
    """
    Add a message to the message queue with category and priority.
    This function is a wrapper around the MessageManager's add_message method.
    
    Args:
        msg (str): The message to add
        color (tuple): RGB color tuple, defaults to WHITE
        category (str): Message category, defaults to INFO
        priority (int): Message priority, defaults to NORMAL
    """
    # If it's a debug message, send it to the debug console
    if category == MessageCategory.DEBUG:
        debug_console.add_message(msg, color)
        return
        
    # Use the global message manager for non-debug messages
    message_manager.add_message(msg, color, category, priority)

def update_message_queue():
    """
    Updates the message queue, removing expired messages.
    This function is a wrapper around the MessageManager's update method.
    """
    message_manager.update()

def display_help_screen(screen, clock):
    """
    Display a popup help screen with game controls and instructions.
    The player can exit by pressing ESC.
    """
    # Define help panel properties
    panel_width = 600
    panel_height = 500
    screen_width, screen_height = screen.get_size()
    panel_rect = pygame.Rect(
        (screen_width - panel_width) // 2,
        (screen_height - panel_height) // 2,
        panel_width, 
        panel_height
    )
    
    # Colors
    panel_bg_color = (30, 30, 50)  # Dark blue-gray
    panel_border_color = (200, 200, 255)  # Light blue
    title_color = (255, 255, 200)  # Light yellow
    text_color = WHITE
    highlight_color = (200, 255, 200)  # Light green
    
    # Initial setup
    help_font = pygame.font.SysFont('monospace', 16)
    title_font = pygame.font.SysFont('monospace', 22, bold=True)
    
    # Help scrolling
    scroll_offset = 0
    line_height = help_font.get_linesize()
    max_visible_lines = (panel_height - 80) // line_height
    
    # Run the help screen loop
    running = True
    while running:
        # Process events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_PAGEUP:
                    scroll_offset = max(0, scroll_offset - 3)
                elif event.key == pygame.K_PAGEDOWN:
                    max_scroll = max(0, len(help_content) - max_visible_lines)
                    scroll_offset = min(max_scroll, scroll_offset + 3)
        
        # Draw the semi-transparent background overlay
        overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))  # Black with alpha
        screen.blit(overlay, (0, 0))
        
        # Draw the help panel
        pygame.draw.rect(screen, panel_bg_color, panel_rect)
        pygame.draw.rect(screen, panel_border_color, panel_rect, 3)
        
        # Draw the title
        title_surface = title_font.render("BLADE & SIGIL HELP", True, title_color)
        screen.blit(title_surface, (panel_rect.x + (panel_width - title_surface.get_width()) // 2, panel_rect.y + 20))
        
        # Draw the help content
        y = panel_rect.y + 60
        for i, line in enumerate(help_content[scroll_offset:scroll_offset + max_visible_lines]):
            # Highlight section headers
            if line and not line.startswith("  "):
                color = highlight_color
            else:
                color = text_color
                
            # Render the line
            text_surface = help_font.render(line, True, color)
            screen.blit(text_surface, (panel_rect.x + 30, y))
            y += line_height
        
        # Draw scroll indicators if needed
        if scroll_offset > 0:
            pygame.draw.polygon(screen, WHITE, [
                (panel_rect.x + panel_width // 2, panel_rect.y + 40),
                (panel_rect.x + panel_width // 2 - 10, panel_rect.y + 50),
                (panel_rect.x + panel_width // 2 + 10, panel_rect.y + 50)
            ])
        
        if scroll_offset + max_visible_lines < len(help_content):
            pygame.draw.polygon(screen, WHITE, [
                (panel_rect.x + panel_width // 2, panel_rect.y + panel_height - 30),
                (panel_rect.x + panel_width // 2 - 10, panel_rect.y + panel_height - 40),
                (panel_rect.x + panel_width // 2 + 10, panel_rect.y + panel_height - 40)
            ])
        
        # Draw instructions at the bottom
        instructions = help_font.render("Press ESC to close, PageUp/PageDown to scroll", True, text_color)
        screen.blit(instructions, (panel_rect.x + (panel_width - instructions.get_width()) // 2, 
                                  panel_rect.y + panel_height - 25))
        
        pygame.display.flip()
        clock.tick(30)

def process_monster_death(monster, player, dungeon_instance):
    messages = []  # ✅ Ensure messages is always defined first!

    # Check if we're dealing with a player (this shouldn't happen, but just in case)
    if not hasattr(monster, 'monster_type'):
        messages.append(f"{monster.name} has been defeated!")
        return messages

    # Ensure monster hit points do not go negative.
    monster.hit_points = 0

    # Use the monster's built-in method to set the dead sprite
    monster.set_dead_sprite()

    # Mark the monster as dead
    monster.is_dead = True

    # Remove the monster from the active list of monsters in the dungeon
    if dungeon_instance is not None:
        dungeon_instance.remove_monster(monster)
    
    messages.append(f"A {monster.name} has died.")
    
    # Determine loot quality based on monster CR
    cr = getattr(monster, 'cr', 1)
    num_items = min(3, max(1, cr))  # More powerful monsters drop more items
    drop_chance = min(0.99, 0.7 + (cr * 0.05))  # Better monsters have better drop rates
    
    # Handle item drop
    for i in range(num_items):
        if random.random() < drop_chance and items_list:
            dropped_item = random.choice(items_list)
            if hasattr(dropped_item, "name"):
                drop_position = monster.position[:]  # Use the monster's current position
                dungeon_instance.dropped_items.append({'item': dropped_item, 'position': drop_position})
                messages.append(f"The {monster.name} dropped a {dropped_item.name}!")

    # Calculate and award XP based on monster CR but don't trigger level up
    cr = getattr(monster, 'cr', 1)
    xp_gained = cr * 50  # Base XP is 50 per CR
    
    # Award XP but don't trigger level up yet (just add to total)
    if hasattr(player, 'add_experience'):
        player.add_experience(xp_gained)
        messages.append(f"{player.name} gains {xp_gained} XP from defeating the {monster.name}!")

    return messages  # ✅ Now messages is always defined!


def get_monster_info(monster_name, monsters_data):
    """Return the monster data dictionary for the given monster name (case-insensitive)."""
    for m in monsters_data['monsters']:
        if m['name'].lower() == monster_name.lower():
            return m
    return None

def handle_monster_turn(monster, player, dungeon):
    # Check if the monster was incapacitated at the start of its turn processing
    if getattr(monster, '_was_incapacitated_this_turn', False):
        logging.debug(f"Monster {monster.name} was incapacitated at the start of this turn. Skipping action.")
        # ORANGE is globally defined, add_message should also be globally available
        if 'add_message' in globals() and callable(globals()['add_message']):
            add_message(f"{monster.name} is still recovering and cannot act this turn.", ORANGE)
        else:
            # Fallback logging if add_message is somehow not available
            logging.warning(f"add_message not found. Monster {monster.name} incapacitated message not shown to player.")
        # The flag _was_incapacitated_this_turn will now be reset by ConditionManager.process_turn
        # at the start of the next full game turn cycle for this monster.
        return # Monster skips its turn

    logging.debug(f"--- Handling turn for monster: {monster.name} ---")
    can_act = True
    if monster.hit_points <= 0:
        logging.debug(f"Monster {monster.name} is dead (HP: {monster.hit_points}). Skipping turn.")
        return  # Dead monsters do nothing

    # Check if the monster can take actions (e.g., not paralyzed or stunned)
    # This check should ideally be comprehensive, considering various conditions.
    # For now, we rely on a 'can_take_actions' method if it exists, or assume true.
    if hasattr(monster, 'can_take_actions') and callable(monster.can_take_actions):
        can_act = monster.can_take_actions()
        logging.debug(f"Monster {monster.name} can_take_actions() returned: {can_act}")
    elif hasattr(monster, 'conditions'): # Fallback to checking common conditions if method not present
        from Data.condition_system import ConditionType # Import here to avoid circular dependency at top level
        paralyzing_conditions = [ConditionType.PARALYZED, ConditionType.STUNNED]
        for cond in monster.conditions:
            if cond.condition_type in paralyzing_conditions:
                can_act = False
                logging.debug(f"Monster {monster.name} has paralyzing condition: {cond.name}. Cannot act.")
                break
    
    if not can_act:
        # Optionally, get a more specific message if the condition itself provides one
        # For now, a generic message is fine.
        add_message(f"{monster.name} is unable to act!", ORANGE) # ORANGE color is (255, 165, 0)
        logging.debug(f"Monster {monster.name} is unable to act. Skipping rest of turn.")
        return

    # Log active conditions
    if hasattr(monster, 'conditions') and monster.conditions:
        condition_names = [cond.name for cond in monster.conditions]
        logging.debug(f"Monster {monster.name} active conditions: {condition_names}")
    else:
        logging.debug(f"Monster {monster.name} has no active conditions.")

    # Handle frost slow effect if present
    if hasattr(monster, 'slow_turns_remaining') and monster.slow_turns_remaining > 0:
        # Decrease remaining turns of the slow effect
        monster.slow_turns_remaining -= 1
        
        # If slow effect expires, restore original speed
        if monster.slow_turns_remaining <= 0:
            if hasattr(monster, 'original_speed'):
                monster.speed = monster.original_speed
                delattr(monster, 'original_speed')
                delattr(monster, 'slow_turns_remaining')
                add_message(f"{monster.name} is no longer slowed by frost.", (100, 200, 255), MessageCategory.COMBAT)
        
        # Chance to skip turn based on slow severity
        if hasattr(monster, 'original_speed') and monster.original_speed > 0:
            slow_severity = 1 - (monster.speed / monster.original_speed)
            skip_chance = slow_severity * 0.6  # 60% chance to skip at maximum slow
            if random.random() < skip_chance:
                add_message(f"{monster.name} is too frozen to move!", (150, 200, 255), MessageCategory.COMBAT)
                return  # Skip turn due to frost effect
    
    # Check if the monster has a clear line of sight to the player
    if not has_line_of_sight(monster, player, dungeon):
        # Optionally, you might implement wandering behavior here
        return

    monster_tile_x = monster.position[0] // TILE_SIZE
    monster_tile_y = monster.position[1] // TILE_SIZE
    player_tile_x = player.position[0] // TILE_SIZE
    player_tile_y = player.position[1] // TILE_SIZE

    distance = abs(player_tile_x - monster_tile_x) + abs(player_tile_y - monster_tile_y)

    if distance == 1:
        # Attack logic
        logging.debug(f"Monster {monster.name} is adjacent to player. Attempting to attack.")
        # Placeholder for actual attack call. If combat() is called here, logging should be inside combat().
        # For now, assume attack happens here or is called from here.
        # Example: messages = combat(monster, player, dungeon)
        # for msg in messages: add_message(msg)
        pass  # Actual attack logic would be here
    else:
        # If slowed, visual indicator for debugging
        if hasattr(monster, 'slow_turns_remaining') and monster.slow_turns_remaining > 0:
            add_message(f"{monster.name} slowly trudges forward.", (150, 200, 255), MessageCategory.DEBUG)
        
        logging.debug(f"Monster {monster.name} is not adjacent. Attempting to move towards player.")
        monster.move_towards(player, dungeon)
    logging.debug(f"--- Finished turn for monster: {monster.name} ---")

        
# ability rolls
def roll_ability_helper():
    roll = sum(random.randint(1, 6) for _ in range(3))
    while roll == 3:  # re-roll if all dice are 1's
        roll = sum(random.randint(1, 6) for _ in range(3))
    return roll

def roll_dice_expression(dice_str, caster=None):
    """
    Parses a dice string (e.g., "1d6+2" or "1d4+int_modifier") and returns the total.
    If the modifier is not a number, it is assumed to refer to an ability modifier on the caster.
    """
    # Split the string at 'd'
    parts = dice_str.split("d")
    if len(parts) != 2:
        raise ValueError("Invalid dice string format. Expected format like '1d6+2'.")
    num_dice = int(parts[0])
    
    # Check for modifier presence
    if '+' in parts[1]:
        sides_str, mod_str = parts[1].split('+', 1)
        sides = int(sides_str)
        try:
            mod_value = int(mod_str)
        except ValueError:
            # Assume the modifier string refers to an ability modifier (e.g., "int_modifier")
            ability = mod_str.replace("_modifier", "").strip().lower()
            ability_map = {"str": "strength", "int": "intelligence", 
                           "wis": "wisdom", "dex": "dexterity", "con": "constitution"}
            ability = ability_map.get(ability, ability)
            if caster is None or ability not in caster.abilities:
                mod_value = 0
            else:
                mod_value = caster.calculate_modifier(caster.abilities[ability])
    else:
        # No modifier present
        sides = int(parts[1])
        mod_value = 0

    total = sum(random.randint(1, sides) for _ in range(num_dice)) + mod_value
    return total

# Equipment rules by class - data-driven system
# Define equipment rules for each class
EQUIPMENT_RULES = {
    # Format: 'Class': {'category': ['allowed_item_types']}
    # Universal equipment that any class can use
    'Universal': {
        'consumable': ['consumable_potion', 'consumable_scroll', 'consumable_food'],
        'jewelry': ['jewelry_ring', 'jewelry_amulet', 'jewelry_bracelet'],
        'generic': ['generic']
    },
    'Warrior': {
        'armor': ['armor_light', 'armor_med', 'armor_heavy'],  # All armor types
        'shield': ['shield_wooden', 'shield_metal', 'shield_tower'],  # All shield types
        'weapon': ['weapon_light_blade', 'weapon_med_blade', 'weapon_heavy_blade', 
                  'weapon_light_blunt', 'weapon_med_blunt', 'weapon_heavy_blunt'],
        # Bows are excluded
    },
    'Priest': {
        'armor': ['armor_light', 'armor_med', 'armor_heavy'],  # All armor types
        'shield': ['shield_wooden', 'shield_metal'],  # No tower shields
        'weapon': ['weapon_light_blunt', 'weapon_med_blunt', 'weapon_heavy_blunt'],  # Only blunt weapons
    },
    'Spellblade': {
        'armor': ['armor_light'],  # Only light armor
        'shield': [],  # No shields
        'weapon': ['weapon_light_blade', 'weapon_med_blade', 'weapon_heavy_blade', 
                  'weapon_light_blunt', 'weapon_med_blunt', 'weapon_heavy_blunt'],
    },
    'Thief': {
        'armor': ['armor_light'],  # Only light armor
        'shield': [],  # No shields
        'weapon': ['weapon_light_blade', 'weapon_med_blade', 'weapon_med_blunt'],
    },
    'Archer': {
        'armor': ['armor_light', 'armor_med'],  # Light and medium armor
        'shield': [],  # No shields (need hands for bow)
        'weapon': ['weapon_light_blade', 'weapon_med_blade', 'weapon_light_blunt', 
                  'weapon_med_blunt', 'weapon_bow'],  # Including bows
    },
    'Wizard': {
        'armor': [],  # No armor
        'shield': [],  # No shields
        'weapon': ['weapon_light_blade', 'weapon_light_blunt'],  # Only light weapons
    },
    'Mage': {
        'armor': [],  # No armor
        'shield': [],  # No shields
        'weapon': ['weapon_light_blade', 'weapon_light_blunt'],  # Only light weapons
    }
}

# Equipment functions
def can_equip_item(character, item):
    """
    Check if a character can equip the given item based on class restrictions
    and other requirements.
    
    Args:
        character: The character attempting to equip the item
        item: The item to equip
        
    Returns:
        (bool, str): Tuple of (can_equip, reason)
    """
    if not item:
        return False, "Item does not exist"
        
    # Standardize the item type with proper attribute checking
    if hasattr(item, 'item_type'):
        item_type = standardize_item_type(item.item_type)
    elif hasattr(item, 'type'):
        # Legacy fallback
        item_type = standardize_item_type(item.type)
    else:
        # Default fallback if neither attribute exists
        return False, "Item has no type information"
    
    # Check if item has specific requirements and use them
    if hasattr(item, 'requirements') and item.requirements:
        can_use, reason = item.requirements.can_use(character)
        if not can_use:
            return False, reason
    
    # Get the allowed equipment based on character class
    # Support both char_class and character_class attributes for backwards compatibility
    char_class = None
    if hasattr(character, 'char_class'):
        char_class = character.char_class
    elif hasattr(character, 'character_class'):
        char_class = character.character_class
    
    if not char_class or char_class not in EQUIPMENT_RULES:
        # Default to warrior if class not found in rules
        char_class = "Warrior"
    
    # Extract the item category from standardized type
    if "_" in item_type:
        category, subtype = item_type.split("_", 1)
    else:
        category = item_type
    
    # Check if this category is allowed for the character's class
    class_rules = EQUIPMENT_RULES.get(char_class, {})
    allowed_items = class_rules.get(category, [])
    
    # Some universal items can be used by all
    universal_items = EQUIPMENT_RULES.get("Universal", {})
    universal_allowed = universal_items.get(category, [])
    
    # If the item type appears in allowed lists or is in universal items
    if item_type in allowed_items or item_type in universal_allowed:
        return True, ""
    else:
        return False, f"Your class cannot use this type of {category}"

# Targeting function for spells
def handle_targeting(caster, target, spell, dungeon, message_queue=None):
    """
    Handle the targeting logic for abilities/spells and display appropriate messages.
    Returns True if targeting is valid, False otherwise.
    
    Args:
        caster: The entity casting the spell
        target: The target of the spell
        spell: The spell being cast
        dungeon: The dungeon instance
        message_queue: Legacy parameter (no longer used)
        
    Returns:
        bool: True if targeting is valid, False otherwise
    """
    valid, reason = can_target_spell(caster, target, spell, dungeon)
    
    if not valid:
        # Use the new message manager system with appropriate category and priority
        add_message(
            reason, 
            RED, 
            category=MessageCategory.COMBAT, 
            priority=MessagePriority.HIGH
        )
        return False
    
    return True

def can_target_spell(caster, target, spell, dungeon):
    """
    Handles targeting logic based on the spell's range type.
    Returns a tuple (valid, message) where valid is a boolean.
    
    This function forwards to the new targeting system if available.
    """
    if USING_NEW_SPELL_SYSTEM:
        # Use the new targeting system
        return can_target(caster, target, spell, dungeon)
    
    # Fall back to the original implementation
    caster_x, caster_y = caster.position[0] // TILE_SIZE, caster.position[1] // TILE_SIZE
    target_x, target_y = target.position[0] // TILE_SIZE, target.position[1] // TILE_SIZE
    distance = abs(caster_x - target_x) + abs(caster_y - target_y)
    
    if spell.get("range_type") == "self":
        if caster != target:
            return False, f"{spell['name']} can only be cast on oneself."
        return True, ""
    elif spell.get("range_type") == "ranged":
        # Example range limit; could also be stored in the JSON.
        max_range = spell.get("max_range", 2)
        if distance > max_range:
            return False, f"{caster.name} is too far away to cast {spell['name']}."
        if not has_line_of_sight(caster, target, dungeon, required_clear=1):
            return False, f"{caster.name} does not have a clear line of sight to {target.name}."
        return True, ""
    else:
        return False, f"Range type {spell.get('range_type')} not recognized."

def compute_fov(dungeon, player, radius):
    """
    Compute the player's field of vision (visible cells).
    
    This function now uses the targeting system's area of effect function
    if available, or falls back to the original implementation.
    """
    if USING_NEW_SPELL_SYSTEM:
        # Use the new targeting system
        targeting_system.set_dungeon(dungeon)
        
        # Get all tiles in a circle around the player
        center = player.position
        area_tiles = targeting_system.get_area_of_effect(center, radius, "circle")
        
        # Filter to visible tiles (with line of sight)
        visible_cells = set()
        for x, y in area_tiles:
            # Ensure the player's own tile is always visible
            player_tile = targeting_system.pixel_to_tile(player.position)
            if (x, y) == player_tile:
                visible_cells.add((x, y))
                continue
                
            # Create a position for this tile
            tile_position = (x * TILE_SIZE + TILE_SIZE // 2, y * TILE_SIZE + TILE_SIZE // 2)
            
            # Check line of sight
            if targeting_system.has_line_of_sight(player, tile_position):
                visible_cells.add((x, y))
                
        return visible_cells
    
    # Fall back to the original implementation
    visible_cells = set()
    player_tile_x = player.position[0] // TILE_SIZE
    player_tile_y = player.position[1] // TILE_SIZE
    for x in range(max(0, player_tile_x - radius), min(dungeon.width, player_tile_x + radius + 1)):
        for y in range(max(0, player_tile_y - radius), min(dungeon.height, player_tile_y + radius + 1)):
            if (x - player_tile_x) ** 2 + (y - player_tile_y) ** 2 <= radius ** 2:
                # Ensure the player's own tile is always visible.
                if (x, y) == (player_tile_x, player_tile_y):
                    visible_cells.add((x, y))
                else:
                    target_dummy = type('Dummy', (), {})()
                    target_dummy.position = [x * TILE_SIZE + TILE_SIZE // 2, y * TILE_SIZE + TILE_SIZE // 2]
                    if has_line_of_sight(player, target_dummy, dungeon, required_clear=1):
                        visible_cells.add((x, y))
    return visible_cells

            
    # If it's already in standard format or we can't standardize, return as is
    return item_type
    
def get_valid_equipment_slots(item, player):
    """
    Given an item, return a list of valid equipment slots for it.
    Uses the Item class's equipment_slot property to determine the appropriate slot.
    """
    valid_slots = []
    
    # Safety check for None items
    if not item:
        print(f"Warning: Item is None in get_valid_equipment_slots")
        return valid_slots
    
    try:
        # Check if the item has the necessary attributes
        if hasattr(item, 'equipment_slot') and callable(getattr(item, 'equipment_slot', None)):
            # Use the item's equipment_slot property to determine the slot
            slot = item.equipment_slot
            
            # Only return valid slots (not inventory)
            if slot and slot != "inventory":
                valid_slots.append(slot)
        elif hasattr(item, 'item_type'):
            # Fallback if equipment_slot property doesn't exist but item_type does
            item_type = item.item_type
            
            # Determine slot based on item_type
            if item_type.startswith('weapon'):
                valid_slots.append('weapon')
            elif item_type.startswith('armor'):
                valid_slots.append('armor')
            elif item_type.startswith('shield'):
                valid_slots.append('shield')
            elif item_type.startswith('jewelry'):
                valid_slots.append('jewelry')
        elif hasattr(item, 'type'):
            # Legacy fallback if only 'type' attribute exists
            item_type = item.type
            
            # Determine slot based on type
            if item_type.startswith('weapon'):
                valid_slots.append('weapon')
            elif item_type.startswith('armor'):
                valid_slots.append('armor')
            elif item_type.startswith('shield'):
                valid_slots.append('shield')
            elif item_type.startswith('jewelry'):
                valid_slots.append('jewelry')
            
    except Exception as e:
        print(f"Error in get_valid_equipment_slots: {e}")
        print(f"Item: {item}, Type: {type(item)}")
        if hasattr(item, 'name'):
            print(f"Item name: {item.name}")
    
    return valid_slots


def swap_equipment(player, slot, new_item):
    """
    Swap new_item into the given slot for the player.
    For non-jewelry slots, if an item is already equipped, it is removed (and added back to the inventory).
    For jewelry, we allow multiple pieces to be equipped (here we simply append).
    In both cases, new_item is removed from player.inventory and its effect applied.
    
    Checks item restrictions before equipping.
    """
    # First check if the player can equip this item
    can_equip, reason = can_equip_item(player, new_item)
    if not can_equip:
        add_message(f"Cannot equip {new_item.name}: {reason}", RED)
        return False
        
    # For jewelry, check item-specific equip limitations and allow multiple items
    if slot == "jewelry":
        # For jewelry items that have a can_equip method (like rings/amulets)
        if hasattr(new_item, 'can_equip') and not new_item.can_equip(player):
            add_message(f"Cannot equip {new_item.name}: Maximum number already equipped", RED)
            return False
            
        # If we can equip it, proceed
        if new_item in player.inventory:
            player.inventory.remove(new_item)
        new_item.apply_effect(player)
        add_message(f"Equipped {new_item.name}.", GREEN)
        return True
    else:
        # For single-slot equipment: if an item is already equipped, remove it first.
        if player.equipment.get(slot):
            old_item = player.equipment[slot]
            old_item.remove_effect(player)
            player.inventory.append(old_item)
        if new_item in player.inventory:
            player.inventory.remove(new_item)
        player.equipment[slot] = new_item
        new_item.apply_effect(player)
        add_message(f"Equipped {new_item.name}.", GREEN)
        return True


def unequip_item(player, slot):
    """
    Unequip the item from the given slot.
    For non-jewelry slots, the item is removed, its effect is undone,
    and it is added back to player.inventory.
    For jewelry (which is stored as a list), we remove one piece (for example, the first one).
    """
    if slot == "jewelry":
        # Remove one jewelry item from the list (if any)
        if player.equipment.get("jewelry") and len(player.equipment["jewelry"]) > 0:
            item = player.equipment["jewelry"].pop(0)
            item.remove_effect(player)
            player.inventory.append(item)
    else:
        if player.equipment.get(slot):
            item = player.equipment[slot]
            item.remove_effect(player)
            player.inventory.append(item)
            player.equipment[slot] = None


def get_clicked_equipment_slot(pos, equipment_rect):
    """
    Given the mouse position (pos) and the rectangle (equipment_rect)
    that defines the equipment panel, map the y-coordinate to a specific slot.
    
    For example, assume the equipment panel has:
      - A header taking up the top 40 pixels
      - Then one slot per line, each slot being (font.get_linesize() + 10) pixels tall
    Slots are mapped as follows:
      0 -> "weapon", 1 -> "armor", 2 -> "shield", 3 -> "jewelry"
    Returns the slot key if found, or None.
    """
    x, y = pos
    if not equipment_rect.collidepoint(pos):
        return None

    # Calculate the vertical position relative to the panel.
    relative_y = y - equipment_rect.y

    # Assume the first 40 pixels is the header.
    header_offset = 40
    slot_height = font.get_linesize() + 10  # Adjust if needed.
    
    # Determine which slot line was clicked.
    index = (relative_y - header_offset) // slot_height

    # Map index to slot keys.
    slot_keys = ["weapon", "armor", "shield", "jewelry"]
    if 0 <= index < len(slot_keys):
        return slot_keys[index]
    return None

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
        # Calculate regular spell points and add 100 for testing
        base_spell_points = self.calculate_spell_points()
        self.spell_points = base_spell_points + 100  # Extra spell points for testing
        
        self.max_hit_points = self.roll_hit_points()  # Roll HP with Constitution applied
        self.hit_points = self.max_hit_points  # Ensure current HP starts at max
        self.ac = self.calculate_ac()  # Base Armor Class (for level 1)
        self.attack_bonus = 0  # Initialize extra attack bonus (for leveling)
        
        # Initialize condition tracking
        self.conditions = []
        self.damage_modifier = 0  # Used by condition effects that modify damage
        self.can_move = True  # Can be toggled by paralysis conditions
    
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
    
    def add_condition(self, condition):
        """
        Add a condition to this character.
        Integrates with the condition_system framework.
        
        Args:
            condition: Condition object to apply
            
        Returns:
            str: Message describing the effect
        """
        # This will be handled by the condition_manager in condition_system.py
        from Data.condition_system import condition_manager
        return condition_manager.apply_condition(self, condition)
    
    def remove_condition(self, condition_type):
        """
        Remove a condition of the specified type from this character.
        
        Args:
            condition_type: ConditionType enum value
            
        Returns:
            bool: True if a condition was removed
        """
        from Data.condition_system import condition_manager
        return condition_manager.remove_condition(self, condition_type)
    
    def has_condition(self, condition_type):
        """
        Check if this character has a condition of the specified type.
        
        Args:
            condition_type: ConditionType enum value
            
        Returns:
            bool: True if the character has the condition
        """
        from Data.condition_system import condition_manager
        return condition_manager.has_condition(self, condition_type)
    
    def get_active_conditions(self):
        """
        Get a list of all conditions affecting this character.
        
        Returns:
            list: Condition objects
        """
        if not hasattr(self, 'conditions') or self.conditions is None:
            self.conditions = []
        return self.conditions
    
    def clear_conditions(self):
        """
        Remove all conditions from this character.
        
        Returns:
            int: Number of conditions cleared
        """
        from Data.condition_system import condition_manager
        return condition_manager.clear_conditions(self)
    
    def process_condition_effects(self, current_turn):
        """
        Process the effects of all conditions at the start of a turn.
        
        Args:
            current_turn: Current game turn number
            
        Returns:
            list: Messages describing condition effects
        """
        messages = []
        if not hasattr(self, 'conditions') or not self.conditions:
            return messages
        
        # Process each condition
        for condition in list(self.conditions):
            # Check if expired
            if condition.is_expired(current_turn):
                msg = condition.remove(self)
                if msg:
                    messages.append(msg)
                self.conditions.remove(condition)
                continue
            
            # Process turn effects
            msg = condition.process_turn(self, current_turn)
            if msg:
                messages.append(msg)
        
        return messages
    
    def can_take_actions(self):
        """
        Check if this character can take actions based on current conditions.
        
        Returns:
            bool: True if the character can take actions
        """
        if not hasattr(self, 'conditions'):
            return True
        
        from Data.condition_system import ConditionType
        # Check for paralyzing conditions
        for condition in self.conditions:
            if condition.condition_type in [
                ConditionType.PARALYZED, 
                ConditionType.STUNNED
            ]:
                return False
        return True

class Tile:
    def __init__(self, x, y, type, sprite=None):
        self.x = x
        self.y = y
        self.type = type  # 'floor', 'wall', 'door', etc.
        if type in ('floor', 'corridor'):
            # Get the floor sprite path from the assets_data JSON file
            floor_sprite_path = assets_data["sprites"]["tiles"]["floor"]
            self.sprite = load_sprite(floor_sprite_path)
        elif type == 'stair_up' and 'stair_up' in assets_data["sprites"]["tiles"]:
            self.sprite = load_sprite(assets_data["sprites"]["tiles"]["stair_up"])
        elif type == 'stair_down' and 'stair_down' in assets_data["sprites"]["tiles"]:
            self.sprite = load_sprite(assets_data["sprites"]["tiles"]["stair_down"])
        elif type == 'door' or type == 'locked_door':
            # Door sprites will be set later based on state
            self.sprite = None
        else:
            self.sprite = None

class Chest:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.locked = True
        self.open = False
        self.difficulty = CHEST_DIFFICULTY
        self.contents = []  # Will store the items
        self.gold = 0
        
        # Generate random loot
        self.generate_contents()
        
        # Load appropriate sprites based on state
        self.load_sprites()
    
    def generate_contents(self):
        """Generate random items and gold for the chest."""
        # Add random items
        global items_list
        if items_list:
            # Get 3 random items from the items list
            for _ in range(CHEST_ITEMS_COUNT):
                random_item = random.choice(items_list)
                self.contents.append(deepcopy(random_item))  # Use deepcopy to avoid modifying the original
        
        # Add gold
        self.gold = roll_dice_expression(CHEST_GOLD_DICE)
    
    def load_sprites(self):
        """Load chest sprites based on current state (closed/open)."""
        closed_sprite_path = "/Users/williammarcellino/Documents/Fantasy_Game/Fantasy_Game_Art_Assets/Misc/loot_drop.jpg"
        open_sprite_path = "/Users/williammarcellino/Documents/Fantasy_Game/Fantasy_Game_Art_Assets/Misc/loot_drop_open.jpg"
        
        try:
            if self.open:
                self.sprite = pygame.image.load(open_sprite_path).convert_alpha()
            else:
                self.sprite = pygame.image.load(closed_sprite_path).convert_alpha()
                
            # Scale sprite to tile size
            self.sprite = pygame.transform.smoothscale(self.sprite, (TILE_SIZE, TILE_SIZE))
            
        except (pygame.error, FileNotFoundError) as e:
            print(f"Warning: Could not load chest sprite. Error: {e}")
            # Create a fallback sprite
            self.sprite = pygame.Surface((TILE_SIZE, TILE_SIZE))
            if self.open:
                self.sprite.fill((139, 69, 19))  # Brown for open chest
            else:
                self.sprite.fill((205, 133, 63))  # Golden brown for closed chest
    
    def try_pick_lock(self, character):
        """Thieves and Archers can try to pick the chest lock."""
        if self.open:
            return True, "The chest is already open."
        
        if not self.locked:
            self.open = True
            self.load_sprites()
            return True, f"{character.name} opens the unlocked chest."
        
        # Only Thieves and Archers can pick locks
        if character.char_class not in ["Thief", "Archer"]:
            return False, f"{character.name} doesn't know how to pick locks."
        
        # Check if character has thieve's tools in inventory
        has_tools = False
        for item in character.inventory:
            if hasattr(item, 'name') and item.name == "Thieve's Tools":
                has_tools = True
                break
        
        if not has_tools:
            return False, f"{character.name} needs thieve's tools to pick this lock."
        
        # Calculate success chance based on level and dexterity
        dex_mod = character.calculate_modifier(character.abilities.get("dexterity", 10))
        level_bonus = character.level // 2
        roll = roll_dice_expression("1d20") + dex_mod + level_bonus
        
        if roll >= self.difficulty:
            self.locked = False
            self.open = True
            self.load_sprites()
            return True, f"{character.name} successfully picks the chest lock! (Roll: {roll})"
        else:
            return False, f"{character.name} fails to pick the chest lock. (Roll: {roll}, needed {self.difficulty})"
    
    def try_magic_unlock(self, character):
        """Wizards and Spellblades can cast magic to unlock chests."""
        if self.open:
            return True, "The chest is already open."
        
        if not self.locked:
            self.open = True
            self.load_sprites()
            return True, f"{character.name} opens the unlocked chest."
        
        # Only Wizards and Spellblades can use magic unlocking
        if character.char_class not in ["Wizard", "Spellblade"]:
            return False, f"{character.name} doesn't know the arcane secrets of unlocking."
        
        # Check if the character has spell points
        if character.spell_points < 1:
            return False, f"{character.name} doesn't have enough spell points to cast Open."
        
        # Unlock with magic (always succeeds but costs a spell point)
        character.spell_points -= 1
        self.locked = False
        self.open = True
        self.load_sprites()
        return True, f"{character.name} casts Open and the chest unlocks with a magical click!"

class Door:
    def __init__(self, x, y, locked=False, door_type="normal"):
        self.x = x
        self.y = y
        self.locked = locked
        self.open = False
        self.door_type = door_type  # "normal", "level_transition", or "map_transition"
        # Use the fixed difficulty value
        self.difficulty = DOOR_DIFFICULTY
        
        # Additional property for map transitions
        self.destination_map = None  # Will be set for map transitions
        
        # Load appropriate sprites based on state
        self.load_sprites()
    
    def load_sprites(self):
        """Load door sprites based on current state (closed, open, locked) and type"""
        # Default door sprite path
        door_sprite_path = "/Users/williammarcellino/Documents/Fantasy_Game/Fantasy_Game_Art_Assets/Misc/door_1.png"
        
        # Special door for level transitions
        if self.door_type == "level_transition":
            door_sprite_path = "/Users/williammarcellino/Documents/Fantasy_Game/Fantasy_Game_Art_Assets/Misc/dungeon_level_door.jpg"
        
        if self.open:
            # Open door uses the floor sprite
            self.sprite = load_sprite(assets_data["sprites"]["tiles"]["floor"])
        elif self.locked:
            # Locked door - use the door sprite with a red tint to indicate it's locked
            try:
                # Load the custom door sprite
                self.sprite = pygame.image.load(door_sprite_path).convert_alpha()
                self.sprite = pygame.transform.smoothscale(self.sprite, (TILE_SIZE, TILE_SIZE))
                
                # Make locked doors have a bright red tint for high visibility
                red_overlay = pygame.Surface(self.sprite.get_size(), pygame.SRCALPHA)
                red_overlay.fill((255, 0, 0, 150))  # More opaque red for better visibility
                temp_sprite = self.sprite.copy()
                temp_sprite.blit(red_overlay, (0, 0))
                self.sprite = temp_sprite
                
                # Add a prominent gold lock icon
                lock_size = TILE_SIZE//3  # Larger lock
                lock_icon = pygame.Surface((lock_size, lock_size), pygame.SRCALPHA)
                lock_icon.fill((255, 215, 0, 230))  # Brighter gold color
                # Position the lock in the center
                self.sprite.blit(lock_icon, (TILE_SIZE//2 - lock_size//2, TILE_SIZE//2 - lock_size//2))
                
            except (pygame.error, FileNotFoundError):
                # Fallback if the sprite can't be loaded
                print(f"Warning: Could not load door sprite {door_sprite_path}, using fallback")
                self.sprite = pygame.Surface((TILE_SIZE, TILE_SIZE))
                
                # Different colors based on door type
                if self.door_type == "level_transition":
                    self.sprite.fill((0, 0, 139))  # Dark blue for level transition
                    
                    # Add a staircase-like symbol beneath the lock
                    symbol_size = TILE_SIZE // 3
                    symbol_pos = (TILE_SIZE // 3, TILE_SIZE // 1.8)
                    pygame.draw.rect(self.sprite, (100, 100, 255), 
                                   (symbol_pos[0], symbol_pos[1], symbol_size, symbol_size // 3))
                    pygame.draw.rect(self.sprite, (100, 100, 255), 
                                   (symbol_pos[0] + symbol_size // 3, symbol_pos[1] + symbol_size // 3,
                                   symbol_size - symbol_size // 3, symbol_size // 3))
                    
                elif self.door_type == "map_transition":
                    self.sprite.fill((148, 0, 211))  # Purple for map transition
                    
                    # Add a portal-like symbol beneath the lock
                    center = (TILE_SIZE // 2, TILE_SIZE // 1.5)
                    radius = TILE_SIZE // 4
                    pygame.draw.circle(self.sprite, (200, 100, 200), center, radius, 2)
                    pygame.draw.circle(self.sprite, (200, 100, 200), center, radius // 2, 1)
                    
                else:
                    self.sprite.fill((139, 69, 19))  # Brown color for regular door
                
                # Draw the lock in all cases
                lock_rect = pygame.Rect(TILE_SIZE//3, TILE_SIZE//3, TILE_SIZE//3, TILE_SIZE//3)
                pygame.draw.rect(self.sprite, (255, 215, 0), lock_rect)  # Gold lock
        else:
            # Regular closed door
            try:
                self.sprite = pygame.image.load(door_sprite_path).convert_alpha()
                self.sprite = pygame.transform.smoothscale(self.sprite, (TILE_SIZE, TILE_SIZE))
                
                # Add a visual indicator for special doors
                if self.door_type == "level_transition":
                    # Add a blue glow and symbol for level transition
                    blue_overlay = pygame.Surface(self.sprite.get_size(), pygame.SRCALPHA)
                    blue_overlay.fill((0, 0, 255, 100))  # Semi-transparent blue
                    self.sprite.blit(blue_overlay, (0, 0))
                    
                    # Add a staircase-like symbol
                    symbol_size = TILE_SIZE // 2
                    symbol_pos = (TILE_SIZE // 4, TILE_SIZE // 4)
                    pygame.draw.rect(self.sprite, (0, 0, 200), 
                                    (symbol_pos[0], symbol_pos[1], symbol_size, symbol_size // 3))
                    pygame.draw.rect(self.sprite, (0, 0, 200), 
                                    (symbol_pos[0] + symbol_size // 3, symbol_pos[1] + symbol_size // 3,
                                    symbol_size - symbol_size // 3, symbol_size // 3))
                    
                elif self.door_type == "map_transition":
                    # Add a purple glow and symbol for map transition
                    purple_overlay = pygame.Surface(self.sprite.get_size(), pygame.SRCALPHA)
                    purple_overlay.fill((128, 0, 128, 100))  # Semi-transparent purple
                    self.sprite.blit(purple_overlay, (0, 0))
                    
                    # Add a portal-like symbol
                    center = (TILE_SIZE // 2, TILE_SIZE // 2)
                    radius = TILE_SIZE // 3
                    pygame.draw.circle(self.sprite, (200, 0, 200), center, radius, 3)
                    pygame.draw.circle(self.sprite, (200, 0, 200), center, radius // 2, 2)
                    
            except (pygame.error, FileNotFoundError):
                # Fallback if the sprite can't be loaded
                print(f"Warning: Could not load door sprite {door_sprite_path}, using fallback")
                self.sprite = pygame.Surface((TILE_SIZE, TILE_SIZE))
                
                if self.door_type == "level_transition":
                    self.sprite.fill((0, 0, 139))  # Dark blue for level transition
                    
                    # Add a staircase-like symbol
                    symbol_size = TILE_SIZE // 2
                    symbol_pos = (TILE_SIZE // 4, TILE_SIZE // 4)
                    pygame.draw.rect(self.sprite, (100, 100, 255), 
                                   (symbol_pos[0], symbol_pos[1], symbol_size, symbol_size // 3))
                    pygame.draw.rect(self.sprite, (100, 100, 255), 
                                   (symbol_pos[0] + symbol_size // 3, symbol_pos[1] + symbol_size // 3,
                                   symbol_size - symbol_size // 3, symbol_size // 3))
                    
                elif self.door_type == "map_transition":
                    self.sprite.fill((128, 0, 128))  # Purple for map transition
                    
                    # Add a portal-like symbol
                    center = (TILE_SIZE // 2, TILE_SIZE // 2)
                    radius = TILE_SIZE // 3
                    pygame.draw.circle(self.sprite, (200, 100, 200), center, radius, 3)
                    pygame.draw.circle(self.sprite, (200, 100, 200), center, radius // 2, 2)
                    
                else:
                    self.sprite.fill((160, 82, 45))  # Brown color for regular door
    
    def try_force_open(self, character):
        """Warriors and Priests can try to force a door open with Strength"""
        if self.open:
            return True, "The door is already open."
        
        if self.locked:
            # Only Warriors and Priests can force locked doors
            if character.char_class not in ["Warrior", "Priest"]:
                return False, f"{character.name} is not strong enough to force this locked door."
            
            # Roll strength check against door difficulty
            str_mod = character.calculate_modifier(character.abilities.get("strength", 10))
            roll = roll_dice_expression("1d20") + str_mod
            
            if roll >= self.difficulty:
                self.locked = False
                self.open = True
                self.load_sprites()
                return True, f"{character.name} forces the locked door open with brute strength!"
            else:
                return False, f"{character.name} fails to force the door open. (Roll: {roll}, needed {self.difficulty})"
        else:
            # Unlocked door - anyone can open it
            self.open = True
            self.load_sprites()
            return True, f"{character.name} opens the door."
    
    def try_pick_lock(self, character):
        """Thieves and Archers can try to pick locks"""
        if self.open:
            return True, "The door is already open."
        
        if not self.locked:
            self.open = True
            self.load_sprites()
            return True, f"{character.name} opens the unlocked door."
        
        # Only Thieves and Archers can pick locks
        if character.char_class not in ["Thief", "Archer"]:
            return False, f"{character.name} doesn't know how to pick locks."
        
        # Check if character has thieve's tools in inventory
        has_tools = False
        for item in character.inventory:
            if hasattr(item, 'name') and item.name == "Thieve's Tools":
                has_tools = True
                break
        
        if not has_tools:
            return False, f"{character.name} needs thieve's tools to pick this lock."
        
        # Calculate success chance based on level and dexterity
        dex_mod = character.calculate_modifier(character.abilities.get("dexterity", 10))
        level_bonus = character.level // 2
        roll = roll_dice_expression("1d20") + dex_mod + level_bonus
        
        if roll >= self.difficulty:
            self.locked = False
            self.open = True
            self.load_sprites()
            return True, f"{character.name} successfully picks the lock! (Roll: {roll})"
        else:
            return False, f"{character.name} fails to pick the lock. (Roll: {roll}, needed {self.difficulty})"
    
    def try_magic_unlock(self, character):
        """Wizards and Spellblades can cast magic to unlock doors"""
        if self.open:
            return True, "The door is already open."
        
        if not self.locked:
            self.open = True
            self.load_sprites()
            return True, f"{character.name} opens the unlocked door."
        
        # Only Wizards and Spellblades can use magic unlocking
        if character.char_class not in ["Wizard", "Spellblade"]:
            return False, f"{character.name} doesn't know the arcane secrets of unlocking."
        
        # Check if the character has spell points
        if character.spell_points < 1:
            return False, f"{character.name} doesn't have enough spell points to cast Open."
        
        # Unlock with magic (always succeeds but costs a spell point)
        character.spell_points -= 1
        self.locked = False
        self.open = True
        self.load_sprites()
        return True, f"{character.name} casts Open and the door unlocks with a magical click!"


# In[6]:


# =============================================================================
# === Spell System Module ===
# =============================================================================
# The spell system implementation has been moved to dedicated modules:
# - Data/spell_helpers.py - Helper functions for accessing spell data
# - Data/spell_system.py - Core spell casting framework
# - Data/condition_system.py - Status effects and conditions
# - Data/targeting_system.py - Line of sight and targeting

# Import the new modules
try:
    from Data.spell_bridge import cast_spell_bridge, update_spells_dialogue
    from Data.targeting_system import targeting_system, can_target
    USING_NEW_SPELL_SYSTEM = True
except ImportError:
    USING_NEW_SPELL_SYSTEM = False
    
# Legacy line of sight functions for backward compatibility
def bresenham(x0, y0, x1, y1):
    """Return list of grid cells (x,y) from (x0,y0) to (x1,y1) using Bresenham’s algorithm."""
    cells = []
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy

















































    
    while True:
        cells.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy
    return cells

def has_line_of_sight(caster, target, dungeon, required_clear=1):
    """
    Legacy line of sight function that uses either the new targeting system
    or falls back to the old implementation.
    """
    if USING_NEW_SPELL_SYSTEM:
        # Use the new targeting system
        targeting_system.set_dungeon(dungeon)
        return targeting_system.has_line_of_sight(caster, target)
    
    # Fall back to the original implementation
    cx, cy = caster.position[0] // TILE_SIZE, caster.position[1] // TILE_SIZE
    tx, ty = target.position[0] // TILE_SIZE, target.position[1] // TILE_SIZE
    # If target is the same or immediately adjacent, assume clear LOS.
    if abs(cx - tx) <= 1 and abs(cy - ty) <= 1:
        return True
    cells = bresenham(cx, cy, tx, ty)
    # Exclude the caster and target cells.
    cells_between = cells[1:-1]
    # If there are no intermediate cells, return True.
    if not cells_between:
        return True
    for (x, y) in cells_between:
        if dungeon.tiles[x][y].type in ('wall', 'door'):
            return False
    return True

def spells_dialogue(screen, player, clock):
    """
    Displays a dialogue panel with the spells available to the player's class and level.
    Waits for the player to press a number key (1-9) to select a spell.
    Returns the selected spell (a dict) or None if cancelled.
    """
    if USING_NEW_SPELL_SYSTEM:
        # Use the enhanced dialogue from the new spell system
        return update_spells_dialogue(screen, player, clock)
    
    # Fall back to the original implementation
    # Use the title version of the player's class (e.g., "Wizard")
    class_key = player.char_class.title()
    # Filter spells: only those that include the class in their "classes" list and for which player.level is high enough.
    available_spells = [
        spell for spell in spells_data["spells"]
        if any(cls.title() == class_key for cls in spell["classes"]) and player.level >= spell["level"]
    ]
    
    # Define dialogue panel properties.
    dialogue_rect = pygame.Rect(50, 50, 400, 300)
    panel_color = (30, 30, 30)
    border_color = (200, 200, 200)
    font = pygame.font.Font(None, 24)
    
    selected_spell = None
    waiting = True
    while waiting:
        # Process events specific to the dialogue.
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                # Check if a number key 1-9 is pressed.
                if pygame.K_1 <= event.key <= pygame.K_9:
                    index = event.key - pygame.K_1
                    if index < len(available_spells):
                        selected_spell = available_spells[index]
                        waiting = False
                # Optionally, allow the player to cancel (e.g., with Escape)
                elif event.key == pygame.K_ESCAPE:
                    waiting = False
        
        # Draw the dialogue panel.
        pygame.draw.rect(screen, panel_color, dialogue_rect)
        pygame.draw.rect(screen, border_color, dialogue_rect, 2)
        
        # Header text.
        header = font.render("Select a Spell:", True, (255, 255, 255))
        screen.blit(header, (dialogue_rect.x + 10, dialogue_rect.y + 10))
        
        # List each spell with its number.
        y_offset = dialogue_rect.y + 40
        for i, spell in enumerate(available_spells):
            spell_text = f"{i+1}. {spell['name']} (Cost: {spell.get('sp_cost', '?')})"
            text_surface = font.render(spell_text, True, (255, 255, 255))
            screen.blit(text_surface, (dialogue_rect.x + 10, y_offset))
            y_offset += 30
        
        pygame.display.flip()
        clock.tick(30)
    
    return selected_spell

def cast_spell(caster, target, spell_name, dungeon):
    """
    Allows a spellcaster to perform an action using spells loaded from a JSON file.
    For example:
      - A Wizard casting "Magic Missile" will target an enemy at range.
      - A Priest casting "Cure Light Wounds" will heal themselves.
      - An Archer can perform "Arrow Shot" to shoot an enemy.
      
    This function forwards to the new spell system if available.
    """
    if USING_NEW_SPELL_SYSTEM:
        # Use the new spell system
        return cast_spell_bridge(caster, target, spell_name, dungeon)
    
    # Fall back to the original implementation
    messages = []  # This list will store all messages to be returned.
    
    # Use a consistent key for the caster's class.
    class_key = caster.char_class.title()
    
    # For non-archers, check if there are enough spell points.
    if class_key != "Archer" and caster.spell_points <= 0:
        messages.append(f"{caster.char_class} does not have enough spell points to cast {spell_name}.")
        return messages
    
    # Retrieve the spell definition from the JSON data.
    spell = None
    for s in spells_data["spells"]:
        # Check if this spell's name matches and the caster's class is allowed.
        if s["name"] == spell_name and any(cls.title() == class_key for cls in s["classes"]):
            spell = s
            break

    if not spell:
        messages.append(f"{caster.char_class}s do not know {spell_name}.")
        return messages
    
    # Get the spell cost from the JSON data (default to 1 if not provided)
    sp_cost = int(spell.get("sp_cost", 1))
    
    # --- Wizard's Magic Missile ---
    if class_key == "Wizard" and spell_name == "Magic Missile":
        valid, message = handle_targeting(caster, target, spell, dungeon)
        if not valid:
            messages.append(message)
            return messages  # Return early if targeting is invalid
        
        damage = roll_dice_expression(spell["damage_dice"], caster)
        target.hit_points -= damage
        caster.spell_points -= sp_cost
        main_message = f"{caster.name} casts Magic Missile at {target.name} for {damage} damage!"
        messages.append(main_message)
        spell_sound.play()
        
        if target.hit_points <= 0:
            # Process monster death.
            death_messages = process_monster_death(target, caster, dungeon)

            for msg in death_messages:  # ✅ Ensure each message is added individually
                messages.append(msg)
        
        return messages

    # --- Mage Armor ---
    elif (class_key == "Wizard" or class_key == "Spellblade") and spell_name == "Mage Armor":
        # Check for self-casting range
        valid, message = handle_targeting(caster, caster, spell, dungeon)  # Mage Armor is cast on self
        spell_sound.play()
        if not valid:
            messages.append(message)
            return messages
        
        ac_bonus = int(spell["ac"])
        caster.ac += ac_bonus  # Increase the caster's AC temporarily
        caster.spell_points -= sp_cost  # Deduct spell points
        messages.append(f"{caster.name} casts Mage Armor and gains {ac_bonus} AC!")
        return messages
        
    # --- Lesser Fireball (Wizard's AoE fire damage) ---
    elif class_key == "Wizard" and spell_name == "Lesser Fireball":
        valid, message = handle_targeting(caster, target, spell, dungeon)
        if not valid:
            messages.append(message)
            return messages  # Return early if targeting is invalid
        
        # Deduct spell points
        caster.spell_points -= sp_cost
        
        # Play sound effect
        spell_sound.play()
        
        # Add main cast message
        messages.append(f"{caster.name} casts Lesser Fireball at {target.name}!")
        
        # Get the visual effect path (if it exists)
        visual_effect_path = spell.get("visual_effect")
        visual_duration = spell.get("visual_duration", 0)
        
        # Display the visual effect if it exists
        try:
            if visual_effect_path:
                explosion_img = pygame.image.load(visual_effect_path).convert_alpha()
                # Get size based on area_size (3 squares = 3 * TILE_SIZE)
                effect_size = spell.get("area_size", 1) * TILE_SIZE * 2
                explosion_img = pygame.transform.scale(explosion_img, (effect_size, effect_size))
                
                # Calculate center position
                target_x, target_y = target.position
                effect_x = target_x - (effect_size // 2)
                effect_y = target_y - (effect_size // 2)
                
                # Display the effect
                for _ in range(int(visual_duration * 10) if visual_duration else 1):  # 10 frames per second
                    # Draw a partial game state
                    screen = pygame.display.get_surface()
                    draw_playable_area(screen, dungeon, caster)
                    screen.blit(explosion_img, (effect_x, effect_y))
                    pygame.display.flip()
                    pygame.time.delay(100)  # 1/10th of a second delay
        except Exception as e:
            messages.append(f"Visual effect error: {str(e)}")
        
        # Apply damage to target and any nearby monsters
        damage = roll_dice_expression(spell["damage_dice"], caster)
        area_size = spell.get("area_size", 1)
        
        # Damage the primary target
        target.hit_points -= damage
        messages.append(f"{target.name} takes {damage} fire damage!")
        
        # Find and damage other monsters in the area
        for monster in dungeon.monsters:
            if monster != target and monster.hit_points > 0:
                # Calculate distance to target
                target_x, target_y = target.position[0] // TILE_SIZE, target.position[1] // TILE_SIZE
                monster_x, monster_y = monster.position[0] // TILE_SIZE, monster.position[1] // TILE_SIZE
                distance = abs(target_x - monster_x) + abs(target_y - monster_y)
                
                # If within area size, deal damage
                if distance <= area_size:
                    # Could scale damage by distance for more realistic effect
                    monster_damage = damage
                    monster.hit_points -= monster_damage
                    messages.append(f"{monster.name} is caught in the blast for {monster_damage} damage!")
        
        # Check for deaths
        if target.hit_points <= 0:
            # Process monster death
            death_messages = process_monster_death(target, caster, dungeon)
            for msg in death_messages:
                messages.append(msg)
        
        # Check other monsters for deaths
        for monster in list(dungeon.monsters):  # Use a copy since we might modify the list
            if monster != target and monster.hit_points <= 0:
                death_messages = process_monster_death(monster, caster, dungeon)
                for msg in death_messages:
                    messages.append(msg)
                    
        return messages

  # --- Wicked Weapon ---
    # This spell should only be available to Spellblades.
    elif caster.char_class == "Spellblade" and spell_name == "Wicked Weapon":
        # Since Wicked Weapon is self-cast, we check targeting on the caster.
        valid, message = handle_targeting(caster, caster, spell, dungeon)
        spell_sound.play()  # Play the spell sound effect.
        if not valid:
            return [message]
        
        dam_bonus = int(spell["dam"])  # In this case, 2.
        # Apply the bonus. For example, you might store a temporary bonus on the caster.
        caster.wicked_weapon_bonus = dam_bonus  
        caster.spell_points -= sp_cost  # Deduct the spell points.
        return [f"{caster.name} casts Wicked Weapon and gains +{dam_bonus} damage on attacks!"]     

    # --- Priest's Cure Light Wounds ---
    elif class_key == "Priest" and spell_name == "Cure Light Wounds":
        healing = roll_dice_expression(spell["healing_dice"], caster)
        caster.hit_points = min(caster.hit_points + healing, caster.max_hit_points)
        caster.spell_points -= sp_cost
        messages.append(f"{caster.name} casts Cure Light Wounds and heals {healing} HP!")
        spell_sound.play()
        return messages
   
    # --- Frost Nova (Wizard's AoE frost damage with slow effect) ---
    elif class_key == "Wizard" and spell_name == "Frost Nova":
        # Frost Nova is self-centered, so we're essentially targeting ourselves
        valid, message = handle_targeting(caster, caster, spell, dungeon)
        if not valid:
            messages.append(message)
            return messages
        
        # Deduct spell points
        caster.spell_points -= sp_cost
        
        # Play frost sound effect
        frost_sound.play()
        
        # Add main cast message
        messages.append(f"{caster.name} unleashes a Frost Nova!")
        
        # Get the visual effect path from spell definition
        visual_effect_path = spell.get("visual_effect")
        visual_duration = spell.get("visual_duration", 2)
        
        # Debug messages for troubleshooting
        add_message(f"Frost Nova path: {visual_effect_path}", (150, 200, 255), MessageCategory.DEBUG)
        
        # Create a fallback visual effect that doesn't rely on the image file
        try:
            screen = pygame.display.get_surface()
            
            # Fallback effect - draw expanding circles
            area_size = spell.get("area_size", 3)
            max_radius = area_size * TILE_SIZE
            
            # Calculate position (centered on caster)
            caster_x, caster_y = caster.position
            
            # Draw expanding frost circles
            for radius in range(10, max_radius + 1, 10):
                # Draw base game state
                draw_playable_area(screen, dungeon, caster)
                
                # Draw a frost circle
                frost_color = (150, 200, 255, 150)  # Light blue with transparency
                frost_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(frost_surf, frost_color, (radius, radius), radius)
                
                # Draw circle centered on caster
                screen.blit(frost_surf, (caster_x - radius, caster_y - radius))
                pygame.display.flip()
                pygame.time.delay(50)
        except Exception as e:
            error_message = f"Visual effect error: {str(e)}"
            messages.append(error_message)
            add_message(error_message, (255, 0, 0), MessageCategory.DEBUG)
            import traceback
            add_message(f"Traceback: {traceback.format_exc()[:150]}...", (255, 0, 0), MessageCategory.DEBUG)
        
        # Apply damage to all monsters in the area
        damage = roll_dice_expression(spell["damage_dice"], caster)
        area_size = spell.get("area_size", 3)
        
        # Find and damage monsters in the area
        affected_monsters = []
        for monster in dungeon.monsters:
            if monster.hit_points > 0:
                # Calculate distance to caster
                caster_x, caster_y = caster.position[0] // TILE_SIZE, caster.position[1] // TILE_SIZE
                monster_x, monster_y = monster.position[0] // TILE_SIZE, monster.position[1] // TILE_SIZE
                distance = abs(caster_x - monster_x) + abs(caster_y - monster_y)
                
                # If within area size, deal damage
                if distance <= area_size:
                    # Scale damage by distance for more realistic effect
                    distance_factor = 1.0 - (distance / (area_size + 1))
                    monster_damage = max(1, int(damage * distance_factor))
                    monster.hit_points -= monster_damage
                    messages.append(f"{monster.name} is struck by ice for {monster_damage} cold damage!")
                    affected_monsters.append(monster)
                    
                    # Apply slow effect if monster is still alive
                    if monster.hit_points > 0 and hasattr(monster, 'speed'):
                        # Slow effect reduces speed by spell.get("slow_percent", 30)%
                        slow_percent = spell.get("slow_percent", 30)
                        original_speed = getattr(monster, 'original_speed', monster.speed)
                        if not hasattr(monster, 'original_speed'):
                            setattr(monster, 'original_speed', monster.speed)
                        
                        # Calculate slowed speed
                        slowed_speed = max(1, int(original_speed * (1 - slow_percent/100)))
                        monster.speed = slowed_speed
                        
                        # Set slow effect duration
                        slow_duration = spell.get("slow_duration", 3)  # Default 3 turns
                        setattr(monster, 'slow_turns_remaining', slow_duration)
                        
                        messages.append(f"{monster.name} is slowed by the frost!")
        
        # Check for monster deaths
        for monster in affected_monsters:
            if monster.hit_points <= 0:
                death_messages = process_monster_death(monster, caster, dungeon)
                for msg in death_messages:
                    messages.append(msg)
                    
        return messages
        
    # --- Light Spell ---
    elif (class_key == "Wizard" or class_key == "Priest") and spell_name == "Light":
        # Since Light is self-cast, check targeting on the caster.
        valid, message = handle_targeting(caster, caster, spell, dungeon)
        if not valid:
            messages.append(message)
            return messages
        
        # Retrieve the desired light radius from the spell JSON.
        # This sets a temporary attribute on the caster used in your FOV calculation.
        new_radius = int(spell.get("light_radius", "4"))
        caster.light_radius = new_radius
        
        # Deduct spell points (make sure to cast the sp_cost to int).
        caster.spell_points -= int(spell.get("sp_cost", 1))
        
        messages.append(f"{caster.name} casts Light, chasing away the dark!")
        # Optionally, you can set a timer or duration for this effect.
        spell_sound.play()
        return messages

    # --- Archer's Arrow Shot ---
    # This is kept for backward compatibility, but the new system handles this through perform_ranged_attack
    elif class_key == "Archer" and spell_name == "Arrow Shot":
        # Import within function to avoid circular imports
        try:
            from combat_system import perform_ranged_attack
            return perform_ranged_attack(caster, target, "arrow", dungeon)
        except ImportError:
            # Fallback to original implementation if combat_system isn't available
            cx, cy = caster.position[0] // TILE_SIZE, caster.position[1] // TILE_SIZE
            tx, ty = target.position[0] // TILE_SIZE, target.position[1] // TILE_SIZE
            manhattan_distance = abs(cx - tx) + abs(cy - ty)
            if manhattan_distance > 4:
                messages.append(f"{caster.name} is too far away to shoot an arrow.")
                return messages
            if not has_line_of_sight(caster, target, dungeon, required_clear=1):
                messages.append(f"{caster.name} does not have a clear shot at {target.name}.")
                return messages
            # To Hit: roll a d20 and add the Archer's Dexterity modifier.
            attack_roll = random.randint(1, 20) + caster.calculate_modifier(caster.abilities['dexterity'])
            if attack_roll >= target.ac:
                damage = roll_dice_expression("1d6", caster)
                target.hit_points -= damage
                arrow_message = f"{caster.name} shoots an arrow at {target.name} for {damage} damage!"
                messages.append(arrow_message)
                arrow_sound.play()
                
                if target.hit_points <= 0:
                    death_messages = process_monster_death(target, caster, dungeon) or []  # ✅ Ensure it's always a list
                    for msg in death_messages:
                        messages.append(msg)
            else:
                messages.append(f"{caster.name} shoots an arrow at {target.name} but misses!")
                return messages

    else:
        messages.append(f"{spell_name} is not yet implemented for {caster.char_class}s.")
        return messages


# In[ ]:

# Visual Effects
def display_visual_effect(effect_path, target_position, duration=1.0, size_multiplier=1.0, frames=10, 
                          screen=None, dungeon=None, caster=None):
    """
    Displays a visual effect at the target position.
    
    Args:
        effect_path (str): Path to the effect image file
        target_position (tuple): (x, y) position where the effect should be centered
        duration (float): Duration in seconds to display the effect
        size_multiplier (float): Size multiplier for the effect (1.0 = normal size)
        frames (int): Number of frames to display during the effect duration
        screen (Surface): Pygame screen to draw on, if None, gets current screen
        dungeon (Dungeon): Dungeon object for redrawing the game state
        caster (Character): Character who cast the spell, needed for redrawing
    
    Returns:
        bool: True if display was successful, False otherwise with error message
    """
    try:
        # Get the screen if not provided
        if screen is None:
            screen = pygame.display.get_surface()
            
        # Load and prepare the effect image
        effect_img = pygame.image.load(effect_path).convert_alpha()
        
        # Calculate the effect size (scaled according to tile size and multiplier)
        effect_size = int(TILE_SIZE * 2 * size_multiplier)
        effect_img = pygame.transform.scale(effect_img, (effect_size, effect_size))
        
        # Calculate center position
        target_x, target_y = target_position
        effect_x = target_x - (effect_size // 2)
        effect_y = target_y - (effect_size // 2)
        
        # Calculate frame delay based on duration and frames
        frame_delay = int(duration * 1000 / frames)
        
        # Display the effect for the specified duration
        for _ in range(frames):
            # Redraw the game state if dungeon and caster are provided
            if dungeon is not None and caster is not None:
                draw_playable_area(screen, dungeon, caster)
            
            # Draw the effect
            screen.blit(effect_img, (effect_x, effect_y))
            pygame.display.flip()
            pygame.time.delay(frame_delay)
            
        return True, None
    except Exception as e:
        return False, str(e)

# Create spell effect images for UI and icons
def create_frost_nova_image(size=256, save_path=None):
    """
    Creates an icy frost nova explosion image and saves it to the disk.
    
    Args:
        size (int): Size of the image in pixels
        save_path (str, optional): Path to save the image to
        
    Returns:
        str: Path to the created image file or default path if none provided
    """
    import math
    import os
    
    # Create a new surface with transparency
    img = pygame.Surface((size, size), pygame.SRCALPHA)
    
    # Define colors for the frost nova
    colors = [
        (255, 255, 255, 200),     # Bright white (center)
        (180, 230, 255, 180),     # Light blue (middle)
        (100, 150, 255, 160),     # Deep blue (outer)
        (50, 90, 200, 140)        # Dark blue (edge)
    ]
    
    # Draw concentric circles from outside in with crystalline effect
    for i, color in enumerate(reversed(colors)):
        radius = size // 2 - (i * size // 12)
        pygame.draw.circle(img, color, (size // 2, size // 2), radius)
        
        # Add crystalline patterns for each layer
        for j in range(8):  # 8 spikes per layer
            angle = j * 45  # Evenly spaced at 45 degrees
            spike_length = radius + (radius * 0.3)  # Spike extends 30% beyond circle
            end_x = int(size // 2 + math.cos(math.radians(angle)) * spike_length)
            end_y = int(size // 2 + math.sin(math.radians(angle)) * spike_length)
            start_x = int(size // 2 + math.cos(math.radians(angle)) * (radius * 0.8))
            start_y = int(size // 2 + math.sin(math.radians(angle)) * (radius * 0.8))
            pygame.draw.line(img, color, (start_x, start_y), (end_x, end_y), 3)
    
    # Add ice shard particles
    for _ in range(24):
        angle = random.random() * 360  # Random angle
        distance = random.randint(size // 4, size // 2 + 30)  # Random distance from center
        length = random.randint(10, 25)  # Random shard length
        thickness = random.randint(1, 3)  # Random shard thickness
        
        start_x = int(size // 2 + math.cos(math.radians(angle)) * distance)
        start_y = int(size // 2 + math.sin(math.radians(angle)) * distance)
        end_x = int(start_x + math.cos(math.radians(angle)) * length)
        end_y = int(start_y + math.sin(math.radians(angle)) * length)
        
        # Choose a color between light blue and white
        alpha = random.randint(150, 220)
        shard_color = (
            random.randint(180, 255),  # Red: high
            random.randint(230, 255),  # Green: very high
            255,                        # Blue: max
            alpha                       # Alpha: semi-transparent
        )
        
        pygame.draw.line(img, shard_color, (start_x, start_y), (end_x, end_y), thickness)
    
    # Add small ice crystal clusters
    for _ in range(16):
        angle = random.random() * 360
        distance = random.randint(size // 6, size // 2 + 20)
        crystal_size = random.randint(3, 8)
        
        x = int(size // 2 + math.cos(math.radians(angle)) * distance)
        y = int(size // 2 + math.sin(math.radians(angle)) * distance)
        
        # Crystal color - lighter blue with high transparency
        crystal_color = (220, 240, 255, random.randint(130, 190))
        
        # Draw a small cluster of dots to simulate a crystal
        pygame.draw.circle(img, crystal_color, (x, y), crystal_size)
        pygame.draw.circle(img, crystal_color, (x+2, y-2), crystal_size-1)
        pygame.draw.circle(img, crystal_color, (x-2, y+1), crystal_size-2)
    
    # Add frosting ground effect (horizontal lines at the bottom half)
    for i in range(10):
        y_pos = size // 2 + (i * 5)  # Start from the middle and go down
        line_length = int(size * 0.8 - (i * 8))  # Lines get shorter toward the bottom
        frost_color = (180, 230, 255, 120 - (i * 10))  # Fade out toward the bottom
        
        start_x = (size - line_length) // 2
        pygame.draw.line(img, frost_color, (start_x, y_pos), (start_x + line_length, y_pos), 2)
    
    # Add a bright flash at the center
    center_flash = pygame.Surface((size//3, size//3), pygame.SRCALPHA)
    center_x, center_y = size//2, size//2
    pygame.draw.circle(center_flash, (255, 255, 255, 220), (size//6, size//6), size//6)
    img.blit(center_flash, (center_x - size//6, center_y - size//6))
    
    # If no save path provided, use a default path
    if not save_path:
        # Get the base directory for the game
        base_dir = "/Users/williammarcellino/Documents/Fantasy_Game"
        save_path = os.path.join(base_dir, "Fantasy_Game_Art_Assets", "Misc", "spell_assets", "frost_nova.png")
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    # Save the image
    pygame.image.save(img, save_path)
    print(f"Created frost nova image at {save_path}")
    return save_path

def create_fireball_image(size=32, save_path=None):
    """
    Creates a simple fireball image surface to be used as an icon or UI element.
    Optionally saves the image to a file.
    
    Args:
        size (int): Size of the image in pixels
        save_path (str, optional): Path to save the image to
        
    Returns:
        str: Path to the created image file or default path if none provided
    """
    import math
    import os
    
    # Create a surface with alpha channel for transparency
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    
    # Calculate center and radius
    center = size // 2
    radius = (size // 2) - 2
    
    # Draw the outer glow (dark red/orange)
    pygame.draw.circle(surface, (200, 40, 10, 160), (center, center), radius)
    
    # Draw the main fire (orange)
    pygame.draw.circle(surface, (255, 100, 20, 220), (center, center), int(radius * 0.85))
    
    # Draw the inner fire (yellow-orange)
    pygame.draw.circle(surface, (255, 180, 50, 240), (center, center), int(radius * 0.6))
    
    # Draw the core (yellow-white)
    pygame.draw.circle(surface, (255, 240, 200, 255), (center, center), int(radius * 0.35))
    
    # Add some random sparks
    for _ in range(8):
        # Random angle and distance from center
        angle = random.uniform(0, 6.28)  # 0 to 2π
        distance = random.uniform(0.5, 0.9) * radius
        
        # Calculate spark position
        spark_x = int(center + distance * math.cos(angle))
        spark_y = int(center + distance * math.sin(angle))
        
        # Random spark size
        spark_size = random.randint(1, 3)
        
        # Draw the spark
        pygame.draw.circle(surface, (255, 255, 255, 255), (spark_x, spark_y), spark_size)
    
    # If no save path provided, use a default path
    if not save_path:
        # Get the base directory for the game
        base_dir = "/Users/williammarcellino/Documents/Fantasy_Game"
        save_path = os.path.join(base_dir, "Fantasy_Game_Art_Assets", "Misc", "spell_assets", "generated_fireball.png")
        # Ensure directory exists (create it if it doesn't)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    # Save the surface to a file
    try:
        pygame.image.save(surface, save_path)
        print(f"Saved fireball image to {save_path}")
    except Exception as e:
        print(f"Error saving fireball image: {e}")
        # Use the existing fireball image instead
        save_path = "/Users/williammarcellino/Documents/Fantasy_Game/Fantasy_Game_Art_Assets/Misc/spell_assets/fireball_explosion.png"
    
    return save_path

# Create a dynamic fireball explosion effect
def create_fireball_explosion(target_position, size=3, duration=2.0, frames=20, screen=None, dungeon=None, caster=None):
    """
    Creates a dynamic fireball explosion with animated concentric circles and random sparks.
    
    Args:
        target_position (tuple): (x, y) position where the explosion should be centered
        size (int): Size of the explosion in tiles
        duration (float): Duration in seconds for the explosion animation
        frames (int): Number of frames to display during the animation
        screen (Surface): Pygame screen to draw on, if None, gets current screen
        dungeon (Dungeon): Dungeon object for redrawing the game state
        caster (Character): Character who cast the spell, needed for redrawing
    """
    import math  # Add import for math functions
    
    try:
        # Get the screen if not provided
        if screen is None:
            screen = pygame.display.get_surface()
            
        # Calculate explosion parameters
        explosion_radius = TILE_SIZE * size
        frame_delay = int(duration * 1000 / frames)
        
        # Extract target position
        target_x, target_y = target_position
        
        # Create surfaces for the explosion
        for frame in range(frames):
            # Redraw the game state if dungeon and caster are provided
            if dungeon is not None and caster is not None:
                draw_playable_area(screen, dungeon, caster)
            
            # Create a transparent surface for the explosion
            explosion_surf = pygame.Surface((explosion_radius * 2, explosion_radius * 2), pygame.SRCALPHA)
            
            # Calculate current expansion (start small, grow, then shrink)
            progress = frame / frames
            if progress < 0.3:
                # Growing phase
                current_radius = explosion_radius * (progress / 0.3)
            else:
                # Stable/shrinking phase
                current_radius = explosion_radius * (1 - ((progress - 0.3) / 0.7) * 0.5)
            
            # Draw concentric circles for the explosion
            colors = [
                (255, 255, 200, 200),  # Yellow-white center
                (255, 200, 50, 180),   # Orange middle
                (255, 100, 20, 160),   # Red-orange outer
                (200, 40, 10, 140)     # Dark red edge
            ]
            
            # Divide the current radius among the circles
            for i, color in enumerate(colors):
                circle_radius = int(current_radius * (1 - i * 0.25))
                if circle_radius > 0:
                    pygame.draw.circle(
                        explosion_surf, 
                        color, 
                        (explosion_radius, explosion_radius), 
                        circle_radius
                    )
            
            # Add random sparks
            num_sparks = int(20 * (1 - progress))  # More sparks at the beginning
            for _ in range(num_sparks):
                # Random angle and distance from center
                angle = random.uniform(0, 6.28)  # 0 to 2π
                distance = random.uniform(0.1, 1.0) * current_radius
                
                # Calculate spark position
                spark_x = int(explosion_radius + distance * math.cos(angle))
                spark_y = int(explosion_radius + distance * math.sin(angle))
                
                # Random spark size and color
                spark_size = random.randint(2, 5)
                spark_color = random.choice([
                    (255, 255, 255, 255),  # White
                    (255, 255, 200, 255),  # Yellow-white
                    (255, 200, 100, 255)   # Orange-yellow
                ])
                
                # Draw the spark
                pygame.draw.circle(explosion_surf, spark_color, (spark_x, spark_y), spark_size)
            
            # Draw the explosion surface to the screen
            screen.blit(
                explosion_surf, 
                (target_x - explosion_radius, target_y - explosion_radius)
            )
            
            # Update display and delay
            pygame.display.flip()
            pygame.time.delay(frame_delay)
            
        return True, None
    except Exception as e:
        return False, str(e)


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
    debug_system.logger.info(f"process_game_turn: Using condition_manager (id: {id(condition_manager)}) with current_turn: {condition_manager.current_turn}")
    # Process all active conditions on player and monsters
    condition_messages = condition_manager.process_turn([player] + dungeon.monsters)

    # Add messages to the game message queue
    for msg in condition_messages:
        add_message(msg)
