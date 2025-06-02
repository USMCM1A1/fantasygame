import pygame
import os
import logging

# --- Logging Setup ---
# Basic configuration for logging
logging.basicConfig(
    level=logging.DEBUG,  # Capture all debug messages
    filename="game_debug.log",  # Log to this file
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"  # Include timestamp, logger name, level, and message
)

# Module-level logger for general debug messages within this module
# When used in debug_system.py, __name__ will be 'debug_system'
logger = logging.getLogger(__name__)

# Specific logger for test arena functionality, can be configured independently
test_arena_logger = logging.getLogger("test_arena")
test_arena_logger.setLevel(logging.DEBUG)  # Ensure it captures DEBUG level messages

logger.info("Debug System logging initialized.")
# --- End Logging Setup ---

# Global debug-related variables
DEBUG_MODE = False  # Set this to False to disable the in-game debug overlay
KEY_DIAGNOSTIC_ENABLED = False  # Set to False to hide the key diagnostics overlay
keys_pressed = []  # List of recently pressed keys (for display)
key_state = {}     # Dictionary to track key states for combinations

# Note: font, small_font, DUNGEON_SCREEN_WIDTH, DUNGEON_SCREEN_HEIGHT
# will be passed as arguments or imported if they are constants from a shared module later.

def draw_debug_info(screen, player, dungeon, font): # DEBUG_MODE removed from params
    """Draw debug information on screen, including player and dungeon state."""
    if not DEBUG_MODE: # Uses module-level DEBUG_MODE
        return

    # Create a semi-transparent overlay for debug info
    debug_surface = pygame.Surface((400, 300), pygame.SRCALPHA)
    debug_surface.fill((0, 0, 0, 180))  # Semi-transparent black

    # Title
    title_text = "DEBUG INFO"
    title_surface = font.render(title_text, True, (255, 255, 0))
    debug_surface.blit(title_surface, (10, 10))

    # Player info
    y_pos = 40
    player_info = [
        f"Player: {player.name} ({player.race} {player.char_class})",
        f"Position: {player.position}",
        f"HP: {player.hit_points}/{player.max_hit_points}",
        f"SP: {player.spell_points}",
    ]

    for info in player_info:
        text_surface = font.render(info, True, (200, 200, 255))
        debug_surface.blit(text_surface, (10, y_pos))
        y_pos += 20

    # Dungeon info
    y_pos += 10
    try:
        dungeon_info = [
            f"Dungeon: {getattr(dungeon, 'level', 0)}",
            f"Map: {getattr(dungeon, 'map_number', 0)}/{getattr(dungeon, 'max_maps', 0)}",
            f"Monsters: {len(getattr(dungeon, 'monsters', []))}",
            f"Doors: {len(getattr(dungeon, 'doors', {}))}",
        ]

        for info in dungeon_info:
            text_surface = font.render(info, True, (200, 255, 200))
            debug_surface.blit(text_surface, (10, y_pos))
            y_pos += 20
    except:
        # If any attribute access fails, just show a simple message
        error_text = "Dungeon data unavailable"
        text_surface = font.render(error_text, True, (255, 100, 100))
        debug_surface.blit(text_surface, (10, y_pos))

    # Position the debug overlay at the top-left corner
    screen.blit(debug_surface, (10, 10))

def draw_key_diagnostics(screen, font, small_font, DUNGEON_SCREEN_WIDTH): # KEY_DIAGNOSTIC_ENABLED, keys_pressed, key_state removed
    if not KEY_DIAGNOSTIC_ENABLED: # Uses module-level KEY_DIAGNOSTIC_ENABLED
        return

    # Create a more visible overlay
    overlay_width = 350
    overlay_height = 270
    overlay = pygame.Surface((overlay_width, overlay_height), pygame.SRCALPHA)
    overlay.fill((0, 0, 50, 230))  # More opaque, blue tint

    # Draw border with flashing effect based on time
    border_flash = abs(pygame.time.get_ticks() % 1000 - 500) / 500  # 0.0 to 1.0 oscillation
    border_color = (
        int(255 * border_flash),  # R: pulsing
        255,                      # G: always high
        int(255 * (1 - border_flash))  # B: inverse pulsing
    )
    pygame.draw.rect(overlay, border_color, (0, 0, overlay_width, overlay_height), 3)

    # Title with shadow
    title = font.render("KEY DIAGNOSTICS", True, (255, 255, 0))
    # Shadow effect
    title_shadow = font.render("KEY DIAGNOSTICS", True, (0, 0, 0))
    overlay.blit(title_shadow, (12, 12))
    overlay.blit(title, (10, 10))

    # Last keys pressed
    y_pos = 40
    if keys_pressed: # Uses module-level keys_pressed
        header = font.render("Recent Keys:", True, (255, 200, 200))
        overlay.blit(header, (10, y_pos))
        y_pos += 25

        # Show last keys with timestamp
        for i, key in enumerate(keys_pressed[-5:]): # Uses module-level keys_pressed
            text_color = (200, 255, 255)  # Bright cyan
            overlay.blit(small_font.render(f"> {key}", True, text_color), (20, y_pos + i*20))
        y_pos += len(keys_pressed[-5:]) * 20 + 15
    else:
        msg = small_font.render("No keys detected yet - press any key", True, (255, 100, 100))
        overlay.blit(msg, (10, y_pos))
        y_pos += 30

    # Draw test arena activation instructions
    pygame.draw.rect(overlay, (50, 100, 50), (10, y_pos, overlay_width - 20, 30))
    activation_text = small_font.render("TEST ARENA: F1 or SHIFT+T", True, (255, 255, 0))
    overlay.blit(activation_text, (20, y_pos + 8))
    y_pos += 40

    # Current key states with visual indicators
    overlay.blit(font.render("Active Keys:", True, (255, 200, 200)), (10, y_pos))
    y_pos += 25

    # Define important keys to show
    important_keys = ["F1", "F2", "Shift", "T", "Enter", "1", "X"]

    # Create a grid layout for key states (2 columns)
    col_width = (overlay_width - 30) // 2
    row_height = 25
    col = 0
    row = 0

    for key in important_keys:
        state = key_state.get(key, False) # Uses module-level key_state
        # Calculate position
        x_pos = 15 + (col * col_width)
        y_offset = y_pos + (row * row_height)

        # Draw key indicator
        indicator_color = (0, 255, 0) if state else (255, 0, 0)  # Green/red
        pygame.draw.rect(overlay, indicator_color, (x_pos, y_offset, 15, 15))

        # Draw key label with bright color when active
        text_color = (255, 255, 255) if state else (180, 180, 180)
        overlay.blit(small_font.render(f"{key}", True, text_color), (x_pos + 20, y_offset))

        # Update column/row position
        col += 1
        if col >= 2:
            col = 0
            row += 1

    # Position overlay in top-right corner for better visibility
    screen.blit(overlay, (DUNGEON_SCREEN_WIDTH - overlay_width - 10, 10))
