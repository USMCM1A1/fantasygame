import pygame
import json
import os
import random
from game_config import TILE_SIZE, RED # Import TILE_SIZE and a color for placeholder

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
    Returns a placeholder Surface if the image file is not found.
    """
    final_tile_size = tile_size_override if tile_size_override is not None else TILE_SIZE
    try:
        sprite = pygame.image.load(path).convert_alpha()
        return pygame.transform.smoothscale(sprite, (final_tile_size, final_tile_size))
    except FileNotFoundError:
        print(f"Warning: Sprite file not found: '{path}'. Using placeholder.")
        placeholder_surface = pygame.Surface((final_tile_size, final_tile_size))
        placeholder_surface.fill(RED) # Fill with a noticeable color
        # Optionally, draw a small 'X' or something to indicate it's a placeholder
        if pygame.font.get_init(): # Check if font system is initialized
            try:
                font = pygame.font.SysFont('monospace', final_tile_size // 2)
                text_render = font.render('X', True, (255,255,255)) # Renamed to avoid conflict
                text_rect = text_render.get_rect(center=(final_tile_size // 2, final_tile_size // 2))
                placeholder_surface.blit(text_render, text_rect)
            except Exception: # Fallback if font rendering fails for any reason
                pass
        return placeholder_surface
    except pygame.error as e:
        print(f"Warning: Pygame error loading sprite '{path}': {e}. Using placeholder.")
        placeholder_surface = pygame.Surface((final_tile_size, final_tile_size))
        placeholder_surface.fill(RED)
        if pygame.font.get_init():
            try:
                font = pygame.font.SysFont('monospace', final_tile_size // 2)
                text_render = font.render('ERR', True, (255,255,255)) # Renamed
                text_rect = text_render.get_rect(center=(final_tile_size // 2, final_tile_size // 2))
                placeholder_surface.blit(text_render, text_rect)
            except Exception:
                pass
        return placeholder_surface


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

def roll_ability_helper():
    """Rolls 3d6 for an ability score."""
    return sum(random.randint(1, 6) for _ in range(3))

def draw_bordered_text(surface, text, center_x, center_y, font_obj, text_color, border_color=(0,0,0), border_thickness=1):
    """
    Draws text with a simple border.
    Args:
        surface: Pygame surface to draw on.
        text: The string to render.
        center_x: X coordinate for the center of the text.
        center_y: Y coordinate for the center of the text.
        font_obj: Pygame font object to use for rendering.
        text_color: Color for the text.
        border_color: Color for the border.
        border_thickness: Thickness of the border.
    """
    if not font_obj:
        print("Warning (draw_bordered_text): No font object provided.")
        # Fallback: try to render simple text without border
        try:
            fallback_font = pygame.font.Font(None, 24) # Default system font
            text_surf = fallback_font.render(text, True, text_color)
            text_rect = text_surf.get_rect(center=(center_x, center_y))
            surface.blit(text_surf, text_rect)
        except Exception as e:
            print(f"Error rendering fallback text in draw_bordered_text: {e}")
        return

    # Render the main text
    text_surface = font_obj.render(text, True, text_color)
    text_rect = text_surface.get_rect(center=(center_x, center_y))

    # Render the border by drawing the text slightly offset in each direction
    offsets = []
    for x_offset in range(-border_thickness, border_thickness + 1, border_thickness):
        for y_offset in range(-border_thickness, border_thickness + 1, border_thickness):
            if x_offset == 0 and y_offset == 0:
                continue # Skip the center (main text position)
            offsets.append((x_offset, y_offset))

    # Ensure diagonal offsets are included if thickness > 1 for a fuller border
    if border_thickness > 1: # This logic is a bit simplistic for thicker borders, might need refinement for aesthetics
        diag_offsets = [
            (-border_thickness, -border_thickness), (border_thickness, -border_thickness),
            (-border_thickness, border_thickness), (border_thickness, border_thickness)
        ]
        for do in diag_offsets:
            if do not in offsets:
                offsets.append(do)

    for dx, dy in offsets:
        border_surface = font_obj.render(text, True, border_color)
        surface.blit(border_surface, (text_rect.x + dx, text_rect.y + dy))

    # Draw the main text on top
    surface.blit(text_surface, text_rect)

def get_memory_usage():
    """Returns memory usage string (e.g., 'Mem: 123.4 MB'). Placeholder if psutil is not available."""
    try:
        import psutil # Import psutil here, only when function is called
        process = psutil.Process(os.getpid()) # os should already be imported in game_utils
        mem_info = process.memory_info()
        return f"Mem: {mem_info.rss / 1024**2:.1f} MB"
    except (ImportError, AttributeError, Exception) as e: # Catch potential errors if psutil is missing or fails
        print(f"Warning: Could not get memory usage (psutil might be missing or failed): {e}")
        return "Mem: N/A"

def print_character_stats(character):
    """Prints basic character stats to the console. Placeholder."""
    if not character:
        print("print_character_stats: No character data provided.")
        return

    print(f"\n--- Character Stats: {getattr(character, 'name', 'Unknown')} ---")
    print(f"  Race: {getattr(character, 'race', 'N/A')}, Class: {getattr(character, 'char_class', 'N/A')}")
    print(f"  Level: {getattr(character, 'level', 'N/A')}")
    print(f"  HP: {getattr(character, 'hit_points', 'N/A')} / {getattr(character, 'max_hit_points', 'N/A')}")
    print(f"  SP: {getattr(character, 'spell_points', 'N/A')}")
    print(f"  AC: {getattr(character, 'ac', 'N/A')}") # Or get_effective_ac() if it's a method

    if hasattr(character, 'abilities'):
        print("  Abilities:")
        for stat, value in character.abilities.items():
            print(f"    {stat.capitalize()}: {value}")
    else:
        print("  Abilities: N/A")

    if hasattr(character, 'equipment'):
        print("  Equipment:")
        for slot, item in character.equipment.items():
            item_name = getattr(item, 'name', 'None')
            if isinstance(item, list): # For jewelry list
                item_name = ", ".join([getattr(i, 'name', 'Jewel') for i in item]) if item else "None"
            print(f"    {slot.capitalize()}: {item_name}")
    else:
        print("  Equipment: N/A")
    print("-------------------------\n")
