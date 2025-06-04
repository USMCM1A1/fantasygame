import pygame
import json
import os
import random
from game_config import TILE_SIZE # Import TILE_SIZE from game_config

# Initialize pygame.font if not already done (needed for font rendering in some utils if they were to use it)
# However, these specific utils (load_json, load_sprite, roll_dice_expression) don't directly use fonts.
# pygame.font.init() # Best to keep pygame.init() and font.init() in the main script.

def load_json(file_path):
    """
    Load and return JSON data from the specified file path.
    """
    with open(file_path, 'r') as f:
        return json.load(f)

def load_sprite(path, tile_size_override=None):
    """
    Load an image from the given path, convert it for pygame, and scale it.
    Uses TILE_SIZE from game_config by default for scaling.
    """
    final_tile_size = tile_size_override if tile_size_override is not None else TILE_SIZE
    sprite = pygame.image.load(path).convert_alpha()
    return pygame.transform.smoothscale(sprite, (final_tile_size, final_tile_size))

def roll_dice_expression(dice_str, caster=None):
    """
    Parses a dice string (e.g., "1d6+2" or "1d4+int_modifier") and returns the total.
    If the modifier is not a number, it is assumed to refer to an ability modifier on the caster.
    Caster needs 'abilities' dict and 'calculate_modifier' method if ability mods are used.
    """
    parts = dice_str.split("d")
    if len(parts) != 2:
        # Check if it's a flat number (e.g. "5")
        try:
            return int(dice_str)
        except ValueError:
            raise ValueError("Invalid dice string format. Expected format like '1d6+2' or '5'.")

    num_dice = int(parts[0])

    mod_value = 0
    if '+' in parts[1]:
        sides_str, mod_str = parts[1].split('+', 1)
        sides = int(sides_str)
        try:
            mod_value = int(mod_str)
        except ValueError:
            if caster and hasattr(caster, 'abilities') and hasattr(caster, 'calculate_modifier'):
                ability = mod_str.replace("_modifier", "").strip().lower()
                ability_map = {"str": "strength", "int": "intelligence",
                               "wis": "wisdom", "dex": "dexterity", "con": "constitution"}
                mapped_ability = ability_map.get(ability, ability)
                if mapped_ability in caster.abilities:
                    mod_value = caster.calculate_modifier(caster.abilities[mapped_ability])
                else: # Modifier string is not a recognized ability or "int_modifier" etc.
                    raise ValueError(f"Unknown ability modifier string: {mod_str}")
            elif caster is None and not mod_str.isdigit():
                 raise ValueError(f"Caster object required for ability modifier '{mod_str}', but caster is None.")
            else: # Not an int, caster doesn't have abilities/calc_mod, or mod_str is invalid
                 raise ValueError(f"Invalid modifier string: {mod_str}")

    elif '-' in parts[1]: # Handle negative modifiers
        sides_str, mod_str = parts[1].split('-', 1)
        sides = int(sides_str)
        try:
            mod_value = -int(mod_str) # Negative modifier
        except ValueError: # Similar logic for negative ability modifiers if needed, though less common in D&D dice strings
            raise ValueError(f"Invalid negative modifier string: {mod_str}")
    else:
        sides = int(parts[1])
        mod_value = 0

    total = sum(random.randint(1, sides) for _ in range(num_dice)) + mod_value
    return total
