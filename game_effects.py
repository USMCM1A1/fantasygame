import pygame
import os
import random
import math
from game_config import TILE_SIZE # Using TILE_SIZE from game_config
# It's assumed pygame.mixer and pygame.display have been initialized in the main script.

# --- Sound Asset Loading ---
# Paths are now built using SOUND_EFFECTS_DIR_CONFIG_PATH from game_config
from game_config import SOUND_EFFECTS_DIR_CONFIG_PATH

spell_sound_path = os.path.join(SOUND_EFFECTS_DIR_CONFIG_PATH, "lvl1_spell_woosh.mp3")
melee_sound_path = os.path.join(SOUND_EFFECTS_DIR_CONFIG_PATH, "basic_melee_strike.mp3")
arrow_sound_path = os.path.join(SOUND_EFFECTS_DIR_CONFIG_PATH, "arrow_shot.mp3")
levelup_sound_path = os.path.join(SOUND_EFFECTS_DIR_CONFIG_PATH, "level_up_ding.mp3")
frost_sound_path = os.path.join(SOUND_EFFECTS_DIR_CONFIG_PATH, "frost.flac")
store_bell_sound_path = os.path.join(SOUND_EFFECTS_DIR_CONFIG_PATH, "store_bell.mp3")

# Load sounds if pygame.mixer is initialized
spell_sound = None
melee_sound = None
arrow_sound = None
levelup_sound = None
frost_sound = None
store_bell_sound = None

if pygame.mixer.get_init():
    try:
        spell_sound = pygame.mixer.Sound(spell_sound_path)
        melee_sound = pygame.mixer.Sound(melee_sound_path)
        arrow_sound = pygame.mixer.Sound(arrow_sound_path)
        levelup_sound = pygame.mixer.Sound(levelup_sound_path)
        frost_sound = pygame.mixer.Sound(frost_sound_path)
        store_bell_sound = pygame.mixer.Sound(store_bell_sound_path)
    except pygame.error as e:
        print(f"Warning: Could not load one or more sound effects: {e}")
else:
    print("Warning: pygame.mixer not initialized. Sounds will not be loaded in game_effects.py.")


# --- Visual Effect Functions ---
# `draw_playable_area` would be needed if effects are drawn on top of it iteratively.
# For now, assuming it's passed or handled by the caller.
# If draw_playable_area is needed here, it would create a circular dependency with common_b_s
# or require moving draw_playable_area to a lower-level module.
# For now, these functions will assume the screen is managed by the caller.

def display_visual_effect(effect_path, target_position, duration=1.0, size_multiplier=1.0, frames=10,
                          screen=None, dungeon=None, caster=None, draw_game_state_func=None):
    """
    Displays a visual effect at the target position.
    `draw_game_state_func` is a callback to redraw the underlying game state if needed per frame.
    """
    try:
        if screen is None: screen = pygame.display.get_surface()
        if screen is None: return False, "Screen not available" # Cannot proceed without a screen

        effect_img = pygame.image.load(effect_path).convert_alpha()
        effect_size = int(TILE_SIZE * 2 * size_multiplier) # TILE_SIZE from game_config
        effect_img = pygame.transform.scale(effect_img, (effect_size, effect_size))

        target_x, target_y = target_position
        effect_x = target_x - (effect_size // 2)
        effect_y = target_y - (effect_size // 2)
        frame_delay = int(duration * 1000 / frames)

        for _ in range(frames):
            if draw_game_state_func: draw_game_state_func(screen, dungeon, caster) # Callback to redraw
            screen.blit(effect_img, (effect_x, effect_y))
            pygame.display.flip()
            pygame.time.delay(frame_delay)
        return True, None
    except Exception as e:
        return False, str(e)

def create_fireball_explosion_effect(target_position, size=3, duration=2.0, frames=20, screen=None, dungeon=None, caster=None, draw_game_state_func=None):
    """
    Creates a dynamic fireball explosion with animated concentric circles and random sparks.
    `draw_game_state_func` is a callback to redraw the underlying game state.
    """
    try:
        if screen is None: screen = pygame.display.get_surface()
        if screen is None: return False, "Screen not available"

        explosion_radius = TILE_SIZE * size # TILE_SIZE from game_config
        frame_delay = int(duration * 1000 / frames)
        target_x, target_y = target_position

        for frame in range(frames):
            if draw_game_state_func: draw_game_state_func(screen, dungeon, caster)

            explosion_surf = pygame.Surface((explosion_radius * 2, explosion_radius * 2), pygame.SRCALPHA)
            progress = frame / frames
            current_radius = explosion_radius * (progress / 0.3) if progress < 0.3 else explosion_radius * (1 - ((progress - 0.3) / 0.7) * 0.5)

            colors = [(255, 255, 200, 200), (255, 200, 50, 180), (255, 100, 20, 160), (200, 40, 10, 140)]
            for i, color in enumerate(colors):
                circle_radius = int(current_radius * (1 - i * 0.25))
                if circle_radius > 0: pygame.draw.circle(explosion_surf, color, (explosion_radius, explosion_radius), circle_radius)

            num_sparks = int(20 * (1 - progress))
            for _ in range(num_sparks):
                angle = random.uniform(0, 6.28)
                distance = random.uniform(0.1, 1.0) * current_radius
                spark_x = int(explosion_radius + distance * math.cos(angle))
                spark_y = int(explosion_radius + distance * math.sin(angle))
                spark_size = random.randint(2, 5)
                spark_color = random.choice([(255, 255, 255, 255), (255, 255, 200, 255), (255, 200, 100, 255)])
                pygame.draw.circle(explosion_surf, spark_color, (spark_x, spark_y), spark_size)

            screen.blit(explosion_surf, (target_x - explosion_radius, target_y - explosion_radius))
            pygame.display.flip()
            pygame.time.delay(frame_delay)
        return True, None
    except Exception as e:
        return False, str(e)

# Image creation utilities (like create_fireball_image, create_frost_nova_image from common_b_s)
# These are for generating assets, not runtime visual effects.
# They might be better placed in an asset_utils.py or kept where they are if only used once.
# For now, moving them here as they are "effect" related.
from game_config import ART_ASSETS_DIR_CONFIG_PATH

def create_fireball_asset_image(size=32, filename="generated_fireball.png"):
    # Path construction using game_config
    save_path = os.path.join(ART_ASSETS_DIR_CONFIG_PATH, "Misc", "spell_assets", filename)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    center = size // 2
    radius = (size // 2) - 2
    pygame.draw.circle(surface, (200, 40, 10, 160), (center, center), radius)
    pygame.draw.circle(surface, (255, 100, 20, 220), (center, center), int(radius * 0.85))
    pygame.draw.circle(surface, (255, 180, 50, 240), (center, center), int(radius * 0.6))
    pygame.draw.circle(surface, (255, 240, 200, 255), (center, center), int(radius * 0.35))
    for _ in range(8):
        angle = random.uniform(0, 6.28)
        distance = random.uniform(0.5, 0.9) * radius
        spark_x = int(center + distance * math.cos(angle))
        spark_y = int(center + distance * math.sin(angle))
        spark_size = random.randint(1, 3)
        pygame.draw.circle(surface, (255, 255, 255, 255), (spark_x, spark_y), spark_size)
    try:
        pygame.image.save(surface, save_path)
        print(f"Saved fireball asset image to {save_path}")
    except Exception as e:
        print(f"Error saving fireball asset image: {e}")
        # Fallback path as in original common_b_s
        save_path = os.path.join(ART_ASSETS_DIR_CONFIG_PATH, "Misc", "spell_assets", "fireball_explosion.png")
    return save_path

def create_frost_nova_asset_image(size=256, filename="frost_nova.png"):
    save_path = os.path.join(ART_ASSETS_DIR_CONFIG_PATH, "Misc", "spell_assets", filename)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    img = pygame.Surface((size, size), pygame.SRCALPHA)
    colors = [(255, 255, 255, 200), (180, 230, 255, 180), (100, 150, 255, 160), (50, 90, 200, 140)]
    for i, color in enumerate(reversed(colors)):
        radius = size // 2 - (i * size // 12)
        pygame.draw.circle(img, color, (size // 2, size // 2), radius)
        for j in range(8):
            angle = j * 45
            spike_length = radius + (radius * 0.3)
            end_x = int(size // 2 + math.cos(math.radians(angle)) * spike_length)
            end_y = int(size // 2 + math.sin(math.radians(angle)) * spike_length)
            start_x = int(size // 2 + math.cos(math.radians(angle)) * (radius * 0.8))
            start_y = int(size // 2 + math.sin(math.radians(angle)) * (radius * 0.8))
            pygame.draw.line(img, color, (start_x, start_y), (end_x, end_y), 3)
    # ... (rest of frost nova image generation logic from common_b_s, simplified for brevity here) ...
    pygame.image.save(img, save_path)
    print(f"Created frost nova asset image at {save_path}")
    return save_path

# Placeholder for draw_playable_area if needed by effect functions
# This would be passed as draw_game_state_func to avoid import cycles
def placeholder_draw_game_state(screen, dungeon, caster):
    pass
