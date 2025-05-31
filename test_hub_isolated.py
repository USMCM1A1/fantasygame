# test_hub_isolated.py
import pygame
import sys
import os

# Assuming common_b_s.py and novamagus_hub.py are in the same directory
# Add current directory to sys.path for imports if needed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Minimal Pygame setup
pygame.init()
try:
    # Try to set a display mode, required by some Pygame functions even if not drawing heavily
    screen = pygame.display.set_mode((800, 600))
except pygame.error as e:
    print(f"Warning: Pygame display error in test_hub_isolated: {e}. Trying NOFRAME.", flush=True)
    try:
        screen = pygame.display.set_mode((1,1), pygame.NOFRAME)
    except Exception as e2:
        print(f"CRITICAL: Could not initialize Pygame display at all: {e2}", flush=True)
        sys.exit(1) # Cannot proceed if display fails completely

pygame.display.set_caption("Isolated Hub Test")
clock = pygame.time.Clock()

# Import necessary components
# common_b_s needs to be imported first to load its data, then novamagus_hub
try:
    print("Attempting to import common_b_s...", flush=True)
    from common_b_s import Player, load_sprite, assets_data, message_manager, add_message, HUB_SCREEN_WIDTH, HUB_SCREEN_HEIGHT, HUB_FPS
    print("common_b_s imported successfully.", flush=True)

    # Ensure assets_data is loaded (it should be by common_b_s import, but double check)
    if assets_data is None:
        print("CRITICAL: assets_data is None after importing common_b_s. Attempting to load all data.", flush=True)
        from common_b_s import load_all_data
        load_all_data()
        if assets_data is None:
            print("CRITICAL: assets_data still None after explicit load_all_data(). Exiting.", flush=True)
            sys.exit(1)

    print("Attempting to import novamagus_hub...", flush=True)
    from novamagus_hub import run_hub
    print("novamagus_hub imported successfully.", flush=True)

except ImportError as e:
    print(f"CRITICAL IMPORT ERROR in test_hub_isolated.py: {e}", flush=True)
    sys.exit(1)
except Exception as e:
    print(f"CRITICAL UNEXPECTED ERROR during imports in test_hub_isolated.py: {e}", flush=True)
    sys.exit(1)

# Create a mock player object
print("Creating mock player...", flush=True)
player_sprite_path = None
if assets_data and "sprites" in assets_data and "heroes" in assets_data["sprites"] and    "warrior" in assets_data["sprites"]["heroes"] and "live" in assets_data["sprites"]["heroes"]["warrior"]:
    player_sprite_path = assets_data["sprites"]["heroes"]["warrior"]["live"]
else:
    print("Warning: Default warrior sprite path not found in assets_data. Player sprite might be missing.", flush=True)

if player_sprite_path:
    try:
        player_sprite = load_sprite(player_sprite_path) # load_sprite handles relative path from ASSETS_PATH
    except Exception as e:
        print(f"Error loading player sprite '{player_sprite_path}': {e}. Using placeholder.", flush=True)
        player_sprite = pygame.Surface((48,48)); player_sprite.fill((0,0,255)) # Blue square
else:
    print("Using placeholder sprite for player as path was not found.", flush=True)
    player_sprite = pygame.Surface((48,48)); player_sprite.fill((0,0,255)) # Blue square


mock_abilities = {'strength': 10, 'dexterity': 10, 'intelligence': 10, 'constitution': 10, 'wisdom': 10}
player = Player(name="TestHubPlayer", race="Human", char_class="Warrior",
                start_position=[HUB_SCREEN_WIDTH // 2, HUB_SCREEN_HEIGHT // 2], # Dummy start pos
                sprite=player_sprite, abilities=mock_abilities)
print("Mock player created.", flush=True)

# Test add_message and message_manager.update() directly
print("Testing message_manager directly...", flush=True)
try:
    add_message("Test message before hub loop.", (255,255,0))
    message_manager.update()
    print("Direct message_manager test successful.", flush=True)
    # Check if message was added (optional, relies on internal state)
    if message_manager.messages and message_manager.messages[-1]['text'] == "Test message before hub loop.":
        print("  Message correctly added to manager.", flush=True)
    else:
        print("  Warning: Test message not found as expected in manager.", flush=True)

except Exception as e:
    print(f"ERROR during direct message_manager test: {e}", flush=True)

# Run the hub for a very short duration
print("Starting run_hub (will be modified to run briefly)...", flush=True)
try:
    run_hub(screen, clock, player) # novamagus_hub.py will be modified to make this exit quickly
    print("run_hub completed.", flush=True)
except Exception as e:
    print(f"ERROR during run_hub: {e}", flush=True)
    import traceback
    print(traceback.format_exc(), flush=True)

print("Isolated hub test script finished.", flush=True)
pygame.quit()
# sys.exit(0) # Not strictly necessary for subtask, but good practice
