import pygame
import os
import logging
from collections import deque # For storing console messages

# --- Logging Setup ---
logging.basicConfig(
    level=logging.DEBUG,
    filename="game_debug.log",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
test_arena_logger = logging.getLogger("test_arena")
test_arena_logger.setLevel(logging.DEBUG)
logger.info("Debug System logging initialized.")

# --- Global Debug Variables ---
DEBUG_MODE = False
KEY_DIAGNOSTIC_ENABLED = False
keys_pressed = []
key_state = {}

# --- Debug Console Class ---
class DebugConsole:
    def __init__(self, font=None, max_lines=15, screen_width=800, screen_height=600): # Added screen dimensions for positioning
        self.messages = deque(maxlen=max_lines)
        self.font = font
        self.visible = False
        self.rect = pygame.Rect(10, 10, screen_width - 20, 200) # Default position and size
        self.text_color = (255, 255, 255)
        self.bg_color = (0, 0, 0, 180) # Semi-transparent black
        self.scroll_offset = 0
        self.line_height = 20 # Default, updated if font is set

    def set_font(self, font):
        self.font = font
        if font:
            self.line_height = font.get_linesize()

    def add_message(self, text, color=None): # Simplified color handling for now
        # Store message with its original color, or default if none provided
        self.messages.append({'text': str(text), 'color': color or self.text_color})

    def toggle(self):
        self.visible = not self.visible

    def handle_scroll(self, event):
        if not self.visible:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_PAGEUP:
                self.scroll_offset = min(self.scroll_offset + 1, len(self.messages) - (self.rect.height // self.line_height) if self.line_height > 0 else 0)
                return True
            elif event.key == pygame.K_PAGEDOWN:
                self.scroll_offset = max(0, self.scroll_offset - 1)
                return True
        return False

    def draw(self, screen):
        if not self.visible or not self.font:
            return

        temp_surface = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        temp_surface.fill(self.bg_color)

        y_pos = self.rect.height - self.line_height # Start drawing from the bottom

        # Calculate how many lines can fit
        num_visible_lines = self.rect.height // self.line_height if self.line_height > 0 else 0

        # Get messages to display (considering scroll)
        #deque doesn't directly support negative slicing for offset like list
        #So we convert to list then slice
        msg_list = list(self.messages)

        # Determine the slice of messages to show based on scroll_offset
        # Scroll_offset means how many lines we've scrolled UP from the bottom
        # End index is len(msg_list) - scroll_offset
        # Start index is max(0, end_index - num_visible_lines)

        end_idx = len(msg_list) - self.scroll_offset
        start_idx = max(0, end_idx - num_visible_lines)

        display_messages = msg_list[start_idx:end_idx]

        for msg_data in reversed(display_messages): # Draw newest messages at the bottom
            if y_pos < 0: # Stop if we run out of space
                break
            try:
                text_surface = self.font.render(msg_data['text'], True, msg_data['color'])
                temp_surface.blit(text_surface, (5, y_pos))
                y_pos -= self.line_height
            except Exception as e:
                print(f"Error rendering debug console message: {e}")
                # Fallback for the problematic message
                try:
                    error_surface = self.font.render(f"Error rendering: {e}", True, (255,0,0))
                    temp_surface.blit(error_surface, (5, y_pos))
                    y_pos -= self.line_height
                except: # If even that fails, just skip
                    pass


        screen.blit(temp_surface, self.rect.topleft)

# --- Global Debug Console Instance ---
# Initialized without a font initially. Font set by initialize_debug_console.
debug_console = DebugConsole()

def initialize_debug_console(font, screen_width=800, screen_height=600):
    """Initializes or reinitializes the global debug_console with a font and screen dimensions."""
    global debug_console
    debug_console.set_font(font)
    # Update rect based on screen dimensions, e.g., make it occupy top third
    console_height = screen_height // 3
    debug_console.rect = pygame.Rect(10, 10, screen_width - 20, console_height)
    if font:
        debug_console.line_height = font.get_linesize()
    logger.info(f"Debug console initialized with font. Visible: {debug_console.visible}")


# --- Existing Debug Functions ---
def draw_debug_info(screen, player, dungeon, font):
    if not DEBUG_MODE:
        return
    debug_surface = pygame.Surface((400, 300), pygame.SRCALPHA)
    debug_surface.fill((0, 0, 0, 180))
    title_text = "DEBUG INFO"
    title_surface = font.render(title_text, True, (255, 255, 0))
    debug_surface.blit(title_surface, (10, 10))
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
        error_text = "Dungeon data unavailable"
        text_surface = font.render(error_text, True, (255, 100, 100))
        debug_surface.blit(text_surface, (10, y_pos))
    screen.blit(debug_surface, (10, 10))

def draw_key_diagnostics(screen, font, small_font, DUNGEON_SCREEN_WIDTH):
    if not KEY_DIAGNOSTIC_ENABLED:
        return
    overlay_width = 350
    overlay_height = 270
    overlay = pygame.Surface((overlay_width, overlay_height), pygame.SRCALPHA)
    overlay.fill((0, 0, 50, 230))
    border_flash = abs(pygame.time.get_ticks() % 1000 - 500) / 500
    border_color = (int(255 * border_flash), 255, int(255 * (1 - border_flash)))
    pygame.draw.rect(overlay, border_color, (0, 0, overlay_width, overlay_height), 3)
    title = font.render("KEY DIAGNOSTICS", True, (255, 255, 0))
    title_shadow = font.render("KEY DIAGNOSTICS", True, (0, 0, 0))
    overlay.blit(title_shadow, (12, 12))
    overlay.blit(title, (10, 10))
    y_pos = 40
    if keys_pressed:
        header = font.render("Recent Keys:", True, (255, 200, 200))
        overlay.blit(header, (10, y_pos))
        y_pos += 25
        for i, key in enumerate(keys_pressed[-5:]):
            text_color = (200, 255, 255)
            overlay.blit(small_font.render(f"> {key}", True, text_color), (20, y_pos + i*20))
        y_pos += len(keys_pressed[-5:]) * 20 + 15
    else:
        msg = small_font.render("No keys detected yet - press any key", True, (255, 100, 100))
        overlay.blit(msg, (10, y_pos))
        y_pos += 30
    pygame.draw.rect(overlay, (50, 100, 50), (10, y_pos, overlay_width - 20, 30))
    activation_text = small_font.render("TEST ARENA: F1 or SHIFT+T", True, (255, 255, 0))
    overlay.blit(activation_text, (20, y_pos + 8))
    y_pos += 40
    overlay.blit(font.render("Active Keys:", True, (255, 200, 200)), (10, y_pos))
    y_pos += 25
    important_keys = ["F1", "F2", "Shift", "T", "Enter", "1", "X"]
    col_width = (overlay_width - 30) // 2
    row_height = 25
    col = 0
    row = 0
    for key in important_keys:
        state = key_state.get(key, False)
        x_pos = 15 + (col * col_width)
        y_offset = y_pos + (row * row_height)
        indicator_color = (0, 255, 0) if state else (255, 0, 0)
        pygame.draw.rect(overlay, indicator_color, (x_pos, y_offset, 15, 15))
        text_color = (255, 255, 255) if state else (180, 180, 180)
        overlay.blit(small_font.render(f"{key}", True, text_color), (x_pos + 20, y_offset))
        col += 1
        if col >= 2:
            col = 0
            row += 1
    screen.blit(overlay, (DUNGEON_SCREEN_WIDTH - overlay_width - 10, 10))

# Functions to toggle debug modes (can be called from game loop via key press)
def toggle_debug_mode():
    global DEBUG_MODE
    DEBUG_MODE = not DEBUG_MODE
    # Using logger for internal debug system messages, not game's add_message
    logger.info(f"Debug mode {'enabled' if DEBUG_MODE else 'disabled'}.")
    return DEBUG_MODE

def toggle_key_diagnostic():
    global KEY_DIAGNOSTIC_ENABLED
    KEY_DIAGNOSTIC_ENABLED = not KEY_DIAGNOSTIC_ENABLED
    logger.info(f"Key diagnostic mode {'enabled' if KEY_DIAGNOSTIC_ENABLED else 'disabled'}.")
    return KEY_DIAGNOSTIC_ENABLED

def add_key_press(key_name):
    """Records a key press for diagnostic display."""
    keys_pressed.append(key_name)
    if len(keys_pressed) > 10: # Keep only the last 10
        keys_pressed.pop(0)

def update_key_state(key_name, is_pressed):
    """Updates the state of a specific key for diagnostic display."""
    key_state[key_name] = is_pressed

logger.info("Debug System module fully loaded.")
