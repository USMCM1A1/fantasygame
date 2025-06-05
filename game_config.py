import pygame

# --- Pygame Initialization Constants ---
# pygame.init() # Initialization should happen in the main script

# --- Screen & Display Constants ---
DUNGEON_SCREEN_WIDTH = 1500
DUNGEON_SCREEN_HEIGHT = 860
DUNGEON_FPS = 60
HUB_SCREEN_WIDTH = 800
HUB_SCREEN_HEIGHT = 600
HUB_FPS = 60

TILE_SIZE = 48 # Default, can be overridden by HUB_TILE_SIZE if context is hub

# --- Panel Dimensions (derived from screen sizes) ---
DUNGEON_RIGHT_PANEL_PERCENT = 0.20
DUNGEON_BOTTOM_PANEL_PERCENT = 0.15
DUNGEON_RIGHT_PANEL_WIDTH = int(DUNGEON_SCREEN_WIDTH * DUNGEON_RIGHT_PANEL_PERCENT)
DUNGEON_BOTTOM_PANEL_HEIGHT = int(DUNGEON_SCREEN_HEIGHT * DUNGEON_BOTTOM_PANEL_PERCENT)
DUNGEON_PLAYABLE_AREA_WIDTH = DUNGEON_SCREEN_WIDTH - DUNGEON_RIGHT_PANEL_WIDTH
DUNGEON_PLAYABLE_AREA_HEIGHT = DUNGEON_SCREEN_HEIGHT - DUNGEON_BOTTOM_PANEL_HEIGHT

HUB_TILE_SIZE = 48
HUB_SCALE = 2
HUB_RIGHT_PANEL_PERCENT = 0.30
HUB_BOTTOM_PANEL_PERCENT = 0.20
HUB_RIGHT_PANEL_WIDTH = int(HUB_SCREEN_WIDTH * HUB_RIGHT_PANEL_PERCENT)
HUB_BOTTOM_PANEL_HEIGHT = int(HUB_SCREEN_HEIGHT * HUB_BOTTOM_PANEL_PERCENT)
HUB_PLAYABLE_AREA_WIDTH = HUB_SCREEN_WIDTH - HUB_RIGHT_PANEL_WIDTH
HUB_PLAYABLE_AREA_HEIGHT = HUB_SCREEN_HEIGHT - HUB_BOTTOM_PANEL_HEIGHT

RIGHT_PANEL_OFFSET = 0
BOTTOM_PANEL_OFFSET = 0

# --- Colors ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
LIGHT_GRAY = (200, 200, 200)
DARK_GRAY = (100, 100, 100)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)

# --- Font ---
# Font initialization requires pygame.font.init(), which should be called after pygame.init()
# So, we define the name and size, and expect font object to be created in main/common_b_s
DEFAULT_FONT_NAME = 'monospace'
DEFAULT_FONT_SIZE = 15
SMALL_FONT_SIZE = 12 # For debug console or smaller text

# --- Message Categories ---
class MessageCategory:
    SYSTEM = "system"
    COMBAT = "combat"
    INVENTORY = "inventory"
    QUEST = "quest"
    DIALOG = "dialog"
    ERROR = "error"
    INFO = "info"
    DEBUG = "debug"
    GAME_EVENT = "game_event"
    ITEM = "item"

# --- Door & Chest Configuration ---
DOOR_CHANCE = 0.2
LOCKED_DOOR_CHANCE = 1.0
DOOR_DIFFICULTY = 7
CHEST_DIFFICULTY = 8
CHEST_ITEMS_COUNT = 3
CHEST_GOLD_DICE = "3d10"

# --- Data File Paths ---
# Relative paths from the root of the project
DATA_DIR_CONFIG_PATH = "Data"
CHARACTERS_FILE_CONFIG_PATH = "characters.json" # Relative to DATA_DIR_CONFIG_PATH
ASSETS_FILE_CONFIG_PATH = "assets.json"         # Relative to DATA_DIR_CONFIG_PATH
SPELLS_FILE_CONFIG_PATH = "spells.json"         # Relative to DATA_DIR_CONFIG_PATH
ITEMS_FILE_CONFIG_PATH = "items.json"           # Relative to DATA_DIR_CONFIG_PATH
MONSTERS_FILE_CONFIG_PATH = "monsters.json"       # Relative to DATA_DIR_CONFIG_PATH

SOUND_EFFECTS_DIR_CONFIG_PATH = "B&S_sfx/" # Corrected relative path
ART_ASSETS_DIR_CONFIG_PATH = "Fantasy_Game_Art_Assets/"    # Corrected relative path

# This file is for constants. Font object creation, image loading, sound loading
# should happen in modules that initialize pygame and handle assets.
# `font` object itself will be created in `common_b_s.py` after pygame.font.init().
# Sound objects will be created in `game_effects.py`.
# Asset paths will be constructed using these constants in `common_b_s.py` or `game_utils.py`.
