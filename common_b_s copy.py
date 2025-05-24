#!/usr/bin/env python
# coding: utf-8

# In[1]:


# common_b_s.py
import pygame
import json
import os
import sys
import logging
import import_ipynb
import random
import re
from copy import deepcopy

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
DOOR_DIFFICULTY = 5  # Fixed difficulty for door checks (easier to break down or pick)

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

HUB_RIGHT_PANEL_PERCENT = 0.30  # For example, maybe a larger panel in the hub
HUB_BOTTOM_PANEL_PERCENT = 0.30

HUB_RIGHT_PANEL_WIDTH = int(HUB_SCREEN_WIDTH * HUB_RIGHT_PANEL_PERCENT)
HUB_BOTTOM_PANEL_HEIGHT = int(HUB_SCREEN_HEIGHT * HUB_BOTTOM_PANEL_PERCENT)
HUB_PLAYABLE_AREA_WIDTH = HUB_SCREEN_WIDTH
HUB_PLAYABLE_AREA_HEIGHT = HUB_SCREEN_HEIGHT

RIGHT_PANEL_OFFSET = -30  # Move the right panel X pixels to the right/left
BOTTOM_PANEL_OFFSET = 40  # Move the bottom panel x pixels down/up

screen = pygame.display.set_mode((HUB_SCREEN_WIDTH, HUB_SCREEN_HEIGHT))

TILE_SIZE = HUB_TILE_SIZE  # or TILE_SIZE = DUNGEON_TILE_SIZE

# --- Common Colors and Font ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
LIGHT_GRAY = (200, 200, 200)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

# Define in_dungeon here as a global variable
in_dungeon = True  # Default to True since we usually start in dungeon mode

import pygame
font = pygame.font.SysFont('monospace', 15)

# === Logging Configuration ===
DEBUG_MODE = True
logging.basicConfig(
    level=logging.DEBUG,
    filename="game_debug.log",
    format="%(asctime)s - %(levelname)s - %(message)s"
)

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

def draw_text_lines(screen, lines, start_x, start_y, line_spacing=4, color=WHITE):
    y = start_y
    for line in lines:
        draw_text(screen, line, color, start_x, y)
        y += font.get_linesize() + line_spacing
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
                darkness.set_alpha(200)  # Adjust transparency as needed.
                playable_surface.blit(darkness, rect)
    
    # Blit the playable area onto the screen and draw a border.
    screen.blit(playable_surface, (0, 0))
    pygame.draw.rect(screen, WHITE, (0, 0, DUNGEON_PLAYABLE_AREA_WIDTH, DUNGEON_PLAYABLE_AREA_HEIGHT), 2)

def draw_right_panel(screen, player, playable_area_width, playable_area_height, right_panel_width, offset_x=0):
    # The right panel starts exactly at the end of the playable area.
    panel_rect = pygame.Rect(playable_area_width, 0, right_panel_width, playable_area_height)
    draw_panel(screen, panel_rect, BLACK, WHITE)
    
    # Use a margin for inner content.
    x_offset = panel_rect.x + 10
    y_offset = panel_rect.y + 10

    # Draw the character portrait.
    class_lower = player.char_class.lower()  # e.g., "wizard"
    portrait_path = assets_data["sprites"]["heroes"][class_lower]["portrait"]
    portrait = pygame.image.load(portrait_path).convert_alpha()
    portrait_size = right_panel_width - 20  # 10px margin on each side
    portrait = pygame.transform.scale(portrait, (portrait_size, portrait_size))
    screen.blit(portrait, (x_offset, y_offset))
    
    y_offset += portrait_size + 10

    # Compute bonuses and draw basic character info.
    hit_bonus = player.attack_bonus + player.calculate_modifier(player.get_effective_ability("strength"))
    wicked_bonus = getattr(player, "wicked_weapon_bonus", 0)
    damage_bonus = player.calculate_modifier(player.get_effective_ability("strength")) + wicked_bonus

    basic_info = [
        f"Name: {player.name}",
        f"Race: {player.race}",
        f"Class: {player.char_class}",
        f"Level: {player.level}",
        f"AC: {player.get_effective_ac()}",
        f"HP: {player.hit_points}/{player.max_hit_points}",
        f"SP: {player.spell_points}",
        f"Hit/Dam Bonus: {hit_bonus}/{damage_bonus}",
    ]
    y_offset = draw_text_lines(screen, basic_info, x_offset, y_offset, 4, WHITE)

    # Draw abilities in two columns.
    col2_x = x_offset + 150
    draw_text(screen, f"Str: {player.abilities['strength']}", WHITE, x_offset, y_offset)
    draw_text(screen, f"Dex: {player.abilities['dexterity']}", WHITE, col2_x, y_offset)
    y_offset += font.get_linesize() + 4
    draw_text(screen, f"Int: {player.abilities['intelligence']}", WHITE, x_offset, y_offset)
    draw_text(screen, f"Con: {player.abilities['constitution']}", WHITE, col2_x, y_offset)
    y_offset += font.get_linesize() + 4
    draw_text(screen, f"Wis: {player.abilities['wisdom']}", WHITE, x_offset, y_offset)
    y_offset += font.get_linesize() + 4

    y_offset += 10  # Extra margin.
    y_offset = draw_equipment_panel(screen, player, x_offset, y_offset)
    
def draw_bottom_panel(screen, playable_area_height, screen_width, bottom_panel_height, offset_y=0):
    # Adjust the y-coordinate of the bottom panel using offset_y.
    panel_rect = pygame.Rect(0, playable_area_height + offset_y, screen_width, bottom_panel_height)
    draw_panel(screen, panel_rect, BLACK, WHITE)
    
    line_height = font.get_linesize()
    y_offset = panel_rect.y + 10

    # Draw any messages
    if len(message_queue) > 0:
        max_index = min(scroll_offset + max_visible_messages, len(message_queue))
        visible_messages = message_queue[scroll_offset:max_index]
        for msg, t in visible_messages:
            draw_text(screen, msg, WHITE, panel_rect.x + 10, y_offset)
            y_offset += line_height
    else:
        # If there are no messages, show a helpful prompt
        draw_text(screen, "Use arrow keys to move. Press 'i' for inventory.", WHITE, panel_rect.x + 10, y_offset)

# handles scrolling of events on bottom screen
def handle_scroll_events(event):
    global scroll_offset
    if event.type == pygame.KEYDOWN:
        # Check for the backslash key
        if event.key == pygame.K_BACKSLASH:
            mods = pygame.key.get_mods()
            # If Shift is held down, scroll up; otherwise, scroll down.
            if mods & pygame.KMOD_SHIFT:
                if scroll_offset > 0:
                    scroll_offset -= 1
            else:
                # Ensure we don't scroll past the end of the message list.
                if scroll_offset < len(message_queue) - max_visible_messages:
                    scroll_offset += 1

def draw_attack_prompt(screen, monster_name):
    box_width = 200
    box_height = 50
    x = (DUNGEON_PLAYABLE_AREA_WIDTH - box_width) // 2
    y = DUNGEON_PLAYABLE_AREA_HEIGHT - box_height - 10
    pygame.draw.rect(screen, RED, (x, y, box_width, box_height), 2)
    prompt = f"Attack {monster_name}? Y/N"
    draw_text(screen, prompt, WHITE, x + 10, y + 10)

def draw_equipment_panel(screen, player, x, y):
    new_y = y
    draw_text(screen, "Equipment:", WHITE, x, new_y)
    new_y += font.get_linesize() + 5

    # Weapon info
    weapon = player.equipment.get("weapon")
    weapon_text = weapon.name if weapon else "None"
    draw_text(screen, f"Weapon: {weapon_text}", WHITE, x, new_y)
    new_y += font.get_linesize() + 5

    # Armor info
    armor = player.equipment.get("armor")
    armor_text = armor.name if armor else "None"
    draw_text(screen, f"Armor: {armor_text}", WHITE, x, new_y)
    new_y += font.get_linesize() + 5

    # Shield info
    shield = player.equipment.get("shield")
    shield_text = shield.name if shield else "None"
    draw_text(screen, f"Shield: {shield_text}", WHITE, x, new_y)
    new_y += font.get_linesize() + 5

    # Jewelry info
    jewelry = player.equipment.get("jewelry", [])
    if jewelry:
        for item in jewelry:
            draw_text(screen, f"{item.name} (+{item.bonus_value} {item.stat_bonus})", WHITE, x, new_y)
            new_y += font.get_linesize() + 5
    else:
        draw_text(screen, "Jewelry: None", WHITE, x, new_y)
        new_y += font.get_linesize() + 5

    return new_y

def draw_debug_info(screen, player, dungeon):
    # Gather debug information as separate, short lines
    debug_lines = [
        f"Player Position: {player.position}",
        f"Player HP: {player.hit_points}/{player.max_hit_points}",
        f"Spell Points: {player.spell_points}",
        f"AC: {player.get_effective_ac()}",
    ]
    if dungeon.monsters:
        monster = dungeon.monsters[0]
        debug_lines += [
            f"Monster: {monster.name}",
            f"Monster Position: {monster.position}",
            f"Monster HP: {monster.hit_points}"
        ]
        # Determine the size of the overlay
    line_height = font.get_linesize()
    overlay_width = max(font.render(line, True, (255, 255, 255)).get_width() for line in debug_lines) + 20
    overlay_height = line_height * len(debug_lines) + 10
    
    # Create a semi-transparent background surface
    overlay = pygame.Surface((overlay_width, overlay_height))
    overlay.set_alpha(200)  # Adjust transparency (0-255)
    overlay.fill((0, 0, 0))  # Black background
    
    # Blit the overlay in the top-left corner of the screen
    screen.blit(overlay, (5, 5))
    
    # Draw each line of debug text in white
    for i, line in enumerate(debug_lines):
        draw_text(screen, line, (255, 255, 255), 10, 10 + i * line_height)


# In[3]:


# =============================================================================
# === Asset Loading Module ===
# =============================================================================

#sounds
spell_sound = pygame.mixer.Sound("/Users/williammarcellino/Documents/Fantasy_Game/B&S_sfx/lvl1_spell_woosh.mp3")
melee_sound = pygame.mixer.Sound("/Users/williammarcellino/Documents/Fantasy_Game/B&S_sfx/basic_melee_strike.mp3")
arrow_sound = pygame.mixer.Sound("/Users/williammarcellino/Documents/Fantasy_Game/B&S_sfx/arrow_shot.mp3")
levelup_sound = pygame.mixer.Sound("/Users/williammarcellino/Documents/Fantasy_Game/B&S_sfx/level_up_ding.mp3")
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
    # Read common fields:
    name = item_data.get("name")
    item_type = item_data.get("type")
    value = item_data.get("value")
    description = item_data.get("description")
    
def create_item(item_data):
    name = item_data.get("name")
    item_type = item_data.get("type")
    value = item_data.get("value")
    description = item_data.get("description")
    
    if item_type == "shield":
        ac_bonus = item_data.get("ac")
        return Shield(name, ac_bonus, value, description)
    elif item_type.startswith("weapon"):
        damage = item_data.get("damage")
        if item_type == "weapon_blade":
            return WeaponBlade(name, item_type, damage, value, description)
        elif item_type == "weapon_blunt":
            return WeaponBlunt(name, item_type, damage, value, description)
        else:
            return Weapon(name, item_type, damage, value, description)
    elif item_type.startswith("armor"):
        ac = item_data.get("ac")
        return Armor(name, item_type, ac, value, description)
    elif item_type.startswith("jewelry"):
        if "sp" in item_data:
            bonus_value = item_data.get("sp")
            return Jewelry(name, item_type, "sp", bonus_value, value, description)
        elif "intelligence" in item_data:
            bonus_value = item_data.get("intelligence")
            return Jewelry(name, item_type, "intelligence", bonus_value, value, description)
    elif item_type == "consumable":
        effect = item_data.get("effect", {})  # Get the effect object
        return Consumable(name, item_type, effect, value, description)
    
    return Item(name, item_type, value, description)
    
    # If type not recognized, return a generic item.
    return Item(name, item_type, value, description)


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
# Base Item class
class Item:
    def __init__(self, name, item_type, value, description):
        self.name = name
        self.item_type = item_type
        self.value = value
        self.description = description

    def apply_effect(self, character):
        """Override in subclass. For equipment, add stat bonuses."""
        pass

    def remove_effect(self, character):
        """Override in subclass. For equipment, remove stat bonuses."""
        pass

    def __str__(self):
        return f"{self.name} ({self.item_type})"


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
    def __init__(self, name, ac_bonus, value, description):
        super().__init__(name, "shield", value, description)
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
    def __init__(self, name, item_type, stat_bonus, bonus_value, value, description):
        """
        stat_bonus: a string like 'sp' or 'intelligence'
        bonus_value: a number representing the bonus
        """
        super().__init__(name, item_type, value, description)
        self.stat_bonus = stat_bonus  # e.g., 'sp' or 'intelligence'
        self.bonus_value = int(str(bonus_value).replace('+', ''))
        
    def apply_effect(self, character):
        # Allow multiple jewelry items to be equipped.
        if 'jewelry' not in character.equipment:
            character.equipment['jewelry'] = []
        character.equipment['jewelry'].append(self)
        
        # If the bonus is for spell points, update spell_points.
        if self.stat_bonus.lower() in ['sp', 'spellpoints']:
            character.spell_points += self.bonus_value
        else:
            # If the ability is stored in the abilities dictionary, update it.
            if self.stat_bonus in character.abilities:
                character.abilities[self.stat_bonus] += self.bonus_value
            else:
                # Otherwise, fall back to setting it as an attribute.
                setattr(character, self.stat_bonus, getattr(character, self.stat_bonus, 0) + self.bonus_value)



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
        # Show differently for consumables
        if item.item_type == "consumable":
            item_text = f"{idx+1}. {item.name} ({item.item_type}) - Click to use"
        else:
            item_text = f"{idx+1}. {item.name} ({item.item_type})"
        draw_text(screen, item_text, WHITE, inventory_rect.x + 10, y_offset)
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
            selected_item = player.inventory[index]
            
            # Special handling for consumable items
            if selected_item.item_type == "consumable":
                # Use the item directly instead of equipping it
                if hasattr(selected_item, 'use'):
                    message = selected_item.use(player)
                    add_message(message)
                    # Remove the item from inventory after use
                    player.inventory.remove(selected_item)
                    return  # Exit after using the consumable
                else:
                    add_message(f"Cannot use {selected_item.name} - no use method defined.")
                    return
            
            # For equipment items, proceed as before
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
                add_message(f"You cannot equip {selected_item.name}.")
    
    # Check if click is in the equipment panel for unequipping.
    elif equipment_rect.collidepoint(pos):
        # For simplicity, assume each equipment slot has a defined clickable area.
        slot_clicked = get_clicked_equipment_slot(pos, equipment_rect)
        if slot_clicked and player.equipment.get(slot_clicked):
            unequip_item(player, slot_clicked)

def manage_inventory(player, screen, clock):
    """
    Displays the unified inventory management screen.
    Press Escape to exit the mode.
    Uses mouse clicks to equip, unequip, or swap items.
    """
    # No need for global keyword since we're accessing the global variable directly
    
    print("DEBUG: Entered manage_inventory")
    print(f"DEBUG: manage_inventory - in_dungeon = {in_dungeon}")
    
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

# Global persistent message log
message_queue = []         # Stores all messages as (msg, timestamp)
scroll_offset = 0          # Index of the first visible message
max_visible_messages = 7   # Maximum number of messages to display
last_message_time = 0      # Timestamp (in ms) when the last message was added
pending_messages = []      # Messages waiting to be added
message_display_time = 30000  # Time in ms to keep messages in queue (30 seconds)

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
    "  a - Shoot arrows (Archer class only)",
    "",
    "INVENTORY & ITEMS",
    "  i - Open inventory to equip/use items",
    "",
    "DOORS & CHESTS",
    "  o - Open/force door (Warriors/Priests)",
    "  p - Pick lock (Thieves/Archers with Thieve's Tools)",
    "  u - Magic unlock (Wizards/Spellblades)",
    "",
    "MAGIC",
    "  x - Cast spells (Wizards/Priests/Spellblades)",
    "",
    "NAVIGATION",
    "  h - Show this help screen",
    "  PageUp/PageDown - Scroll message history",
    "  ESC - Close menus/screens",
]


def add_message(msg):
    """Add a message to the message queue and process pending messages."""
    global last_message_time, pending_messages, message_queue
    
    # Skip empty messages
    if not msg or msg.strip() == "":
        return
        
    # Always add the message immediately - we won't delay anymore
    now = pygame.time.get_ticks()
    message_queue.append((msg, now))
    last_message_time = now
    
    # Also process any pending messages
    for pending_msg in pending_messages:
        if pending_msg and pending_msg.strip() != "":
            message_queue.append((pending_msg, now))
    pending_messages = []  # Clear pending messages
    
    # Limit the queue to a maximum length to prevent memory issues
    if len(message_queue) > 50:
        message_queue = message_queue[-50:]  # Keep only the most recent 50 messages

def update_message_queue():
    """Removes messages that have been displayed longer than message_display_time."""
    now = pygame.time.get_ticks()
    # Remove from the beginning of the list (oldest messages first)
    while message_queue and now - message_queue[0][1] > message_display_time:
        message_queue.pop(0)

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

    # Ensure monster hit points do not go negative.
    monster.hit_points = 0

    # Look up the monster's info from monsters_data
    monster_info = get_monster_info(monster.name, monsters_data)
    if monster_info is not None and 'sprites' in monster_info and 'dead' in monster_info['sprites']:
        monster.sprite = load_sprite(monster_info['sprites']['dead'])
    else:
        print(f"Warning: Dead sprite not found for {monster.name}. Using live sprite instead.")
        if monster_info is not None and 'sprites' in monster_info and 'live' in monster_info['sprites']:
            monster.sprite = load_sprite(monster_info['sprites']['live'])

    # Mark the monster as dead
    monster.is_dead = True

    # Remove the monster from the active list of monsters in the dungeon
    if dungeon_instance is not None:
        dungeon_instance.remove_monster(monster)
    
    messages.append(f"A {monster.name} has died.")
    
    # Handle item drop: drop 3 items
    drop_chance = 0.99
    for i in range(3):
        if random.random() < drop_chance and items_list:
            dropped_item = random.choice(items_list)
            if hasattr(dropped_item, "name"):
                drop_position = monster.position[:]  # Use the monster's current position
                dungeon_instance.dropped_items.append({'item': dropped_item, 'position': drop_position})
                messages.append(f"The {monster.name} dropped a {dropped_item.name}!")

    # Handle player level-up
    player.level_up()
    messages.append(f"{player.name} feels empowered and levels up!")
    # Schedule a custom event (USEREVENT+1) to fire in 1000 ms (1 second)
    pygame.time.set_timer(pygame.USEREVENT + 1, 1000)

    return messages  # ✅ Now messages is always defined!


def get_monster_info(monster_name, monsters_data):
    """Return the monster data dictionary for the given monster name (case-insensitive)."""
    for m in monsters_data['monsters']:
        if m['name'].lower() == monster_name.lower():
            return m
    return None

def handle_monster_turn(monster, player, dungeon):
    if monster.hit_points <= 0:
        return  # Dead monsters do nothing

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
        # Attack logic...
        pass
    else:
        monster.move_towards(player, dungeon)

        
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

# Equipment rules by class
def can_equip_item(player, item):
    """
    Returns True if the player's class is allowed to equip the given item.
    The item’s type (a string) is used to determine what category it is.
    """
    # Armor rules
    if item.item_type.startswith("armor"):
        if player.char_class in ["Warrior", "Priest"]:
            return True  # Can wear any armor
        elif player.char_class in ["Spellblade", "Thief"]:
            return item.item_type == "armor_light"  # Only light armor allowed
        elif player.char_class == "Archer":
            return item.item_type in ["armor_light", "armor_med"]  # Light and medium allowed
        else:
            return False

    # Shield rules (only Warriors and Priests can equip shields)
    elif item.item_type.startswith("shield"):
        return player.char_class in ["Warrior", "Priest"]

    # Weapon rules
    elif item.item_type.startswith("weapon"):
        if player.char_class in ["Warrior", "Archer", "Spellblade"]:
            return True  # Can use any weapon
        elif player.char_class == "Thief":
            # Thieves can use blunt weapons and both light and medium blades.
            # (Adjust the allowed types as needed.)
            return item.item_type in ["weapon_med_blunt", "weapon_light_blade", "weapon_med_blade"]
        elif player.char_class == "Priest":
            # Priests can only use blunt weapons.
            return "blunt" in item.item_type  # checks if the item type contains 'blunt'
        elif player.char_class in ["Wizard", "Mage"]:
            # Mages can only use light blades and light blunt weapons.
            return item.item_type in ["weapon_light_blade", "weapon_light_blunt"]
        else:
            return False

    # Jewelry and consumables (or other items) can be used without restrictions.
    else:
        return True

# Spell Targeting Function   
def handle_targeting(caster, target, spell, dungeon):
    """
    Handles targeting logic based on the spell's range type.
    Returns a tuple (valid, message) where valid is a boolean.
    """
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

def get_valid_equipment_slots(item, player):
    """
    Given an item, return a list of valid equipment slots for it.
    For example, if the item type starts with "weapon", return ["weapon"].
    Shields go only to the "shield" slot, and jewelry goes to "jewelry".
    Consumables or unknown types return an empty list.
    """
    valid_slots = []
    if item.item_type.startswith("weapon"):
        valid_slots.append("weapon")
    elif item.item_type.startswith("armor"):
        valid_slots.append("armor")
    elif item.item_type == "shield":
        valid_slots.append("shield")
    elif item.item_type.startswith("jewelry"):
        valid_slots.append("jewelry")
    # Add additional checks if needed.
    return valid_slots


def swap_equipment(player, slot, new_item):
    """
    Swap new_item into the given slot for the player.
    For non-jewelry slots, if an item is already equipped, it is removed (and added back to the inventory).
    For jewelry, we allow multiple pieces to be equipped (here we simply append).
    In both cases, new_item is removed from player.inventory and its effect applied.
    """
    # For jewelry, allow multiple items.
    if slot == "jewelry":
        if new_item in player.inventory:
            player.inventory.remove(new_item)
        new_item.apply_effect(player)
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
        self.spell_points = self.calculate_spell_points()
        self.max_hit_points = self.roll_hit_points()  # Roll HP with Constitution applied
        self.hit_points = self.max_hit_points  # Ensure current HP starts at max
        self.ac = self.calculate_ac()  # Base Armor Class (for level 1)
        self.attack_bonus = 0  # Initialize extra attack bonus (for leveling)

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
        print(f"[DEBUG] Starting gold after dice roll: {self.gold}")

class Tile:
    def __init__(self, x, y, type, sprite=None):
        self.x = x
        self.y = y
        self.type = type  # 'floor', 'wall', 'door', etc.
        if type == 'floor':
            # Get the floor sprite path from the assets_data JSON file
            floor_sprite_path = assets_data["sprites"]["tiles"]["floor"]
            self.sprite = load_sprite(floor_sprite_path)
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
    def __init__(self, x, y, locked=False):
        self.x = x
        self.y = y
        self.locked = locked
        self.open = False
        # Use the fixed difficulty value
        self.difficulty = DOOR_DIFFICULTY
        
        # Load appropriate sprites based on state
        self.load_sprites()
    
    def load_sprites(self):
        """Load door sprites based on current state (closed, open, locked)"""
        door_sprite_path = "/Users/williammarcellino/Documents/Fantasy_Game/Fantasy_Game_Art_Assets/Misc/door_1.png"
        
        if self.open:
            # Open door uses the floor sprite
            self.sprite = load_sprite(assets_data["sprites"]["tiles"]["floor"])
        elif self.locked:
            # Locked door - use the door sprite but tint it red to indicate it's locked
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
                self.sprite.fill((139, 69, 19))  # Brown color for door
                lock_rect = pygame.Rect(TILE_SIZE//3, TILE_SIZE//3, TILE_SIZE//3, TILE_SIZE//3)
                pygame.draw.rect(self.sprite, (255, 215, 0), lock_rect)  # Gold lock
        else:
            # Regular closed door - use the door sprite as is
            try:
                self.sprite = pygame.image.load(door_sprite_path).convert_alpha()
                self.sprite = pygame.transform.smoothscale(self.sprite, (TILE_SIZE, TILE_SIZE))
            except (pygame.error, FileNotFoundError):
                # Fallback if the sprite can't be loaded
                print(f"Warning: Could not load door sprite {door_sprite_path}, using fallback")
                self.sprite = pygame.Surface((TILE_SIZE, TILE_SIZE))
                self.sprite.fill((160, 82, 45))  # Brown color for door
    
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
# === Spell Data & Spell Casting Module ===
# =============================================================================

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
    """
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
    elif class_key == "Archer" and spell_name == "Arrow Shot":
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




