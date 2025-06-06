#!/usr/bin/env python
# coding: utf-8

import pygame
pygame.init()
import sys
import os

# Import hub-specific configuration constants and functions from common_b_s.
from common_b_s import (
    HUB_SCREEN_WIDTH, HUB_SCREEN_HEIGHT, HUB_FPS, HUB_TILE_SIZE, HUB_SCALE,
    HUB_RIGHT_PANEL_WIDTH, HUB_BOTTOM_PANEL_HEIGHT, HUB_PLAYABLE_AREA_WIDTH, HUB_PLAYABLE_AREA_HEIGHT,
    RIGHT_PANEL_OFFSET, BOTTOM_PANEL_OFFSET,
    
    # Colors, font, asset loading functions, etc.
    WHITE, BLACK, LIGHT_GRAY, RED, GREEN, BLUE, font,
    
    # Asset and UI functions
    draw_text, draw_panel, draw_text_lines, draw_playable_area, draw_right_panel, draw_bottom_panel,
    handle_scroll_events, draw_attack_prompt, draw_equipment_panel,
    
    # Other helper functions and classes
    load_sprite, load_json, assets_data, characters_data, spells_data, items_data, monsters_data,
    add_message, update_message_queue, roll_dice_expression,
    Item, Weapon, WeaponBlade, WeaponBlunt, Armor, Shield, Jewelry, Consumable,
    Character, Tile,
)
from game_utils import roll_ability_helper
from game_logic_utils import (
    can_equip_item, handle_targeting, compute_fov, get_valid_equipment_slots,
    swap_equipment, unequip_item, get_clicked_equipment_slot, shop_interaction
)
from player import Player
import common_b_s
in_dungeon = False

# (Optional) Ensure the display mode is set.
screen = pygame.display.set_mode((HUB_SCREEN_WIDTH, HUB_SCREEN_HEIGHT))
SCREEN_WIDTH = HUB_SCREEN_WIDTH
SCREEN_HEIGHT = HUB_SCREEN_HEIGHT
TILE_SIZE = HUB_TILE_SIZE

def ensure_player_sprite(player):
    """Ensure the player has a proper sprite loaded for the hub."""
    if not player.sprite or player.sprite is None:
        print(f"DEBUG: Loading sprite for player class: {player.char_class}")
        
        # Get the sprite path from assets_data
        char_class_lower = player.char_class.lower()
        try:
            sprite_data = assets_data["sprites"]["heroes"].get(char_class_lower, 
                         assets_data["sprites"]["heroes"]["warrior"])  # Fallback to warrior
            relative_sprite_path = sprite_data["live"]
            full_sprite_path = os.path.join(common_b_s.ART_ASSETS_DIR_CONFIG_PATH, relative_sprite_path)
            
            print(f"DEBUG: Loading sprite from: {full_sprite_path}")
            player.sprite = load_sprite(full_sprite_path, HUB_TILE_SIZE)
            print(f"DEBUG: Player sprite loaded successfully: {player.sprite is not None}")
            
        except Exception as e:
            print(f"ERROR: Failed to load player sprite: {e}")
            # Create a placeholder sprite if loading fails
            player.sprite = pygame.Surface((HUB_TILE_SIZE, HUB_TILE_SIZE))
            player.sprite.fill((0, 255, 0))  # Green placeholder
            
    return player.sprite is not None

def load_hub_assets():
    """Load all art assets specific to Novamagus."""
    assets = {
        'cobble': load_sprite("/Users/williammarcellino/Documents/Fantasy_Game/Fantasy_Game_Art_Assets/Misc/Novamagus/cobblestones.png"),
        'vegetation': load_sprite("/Users/williammarcellino/Documents/Fantasy_Game/Fantasy_Game_Art_Assets/Misc/Novamagus/vegetation.png"),
        'inn': load_sprite("/Users/williammarcellino/Documents/Fantasy_Game/Fantasy_Game_Art_Assets/Misc/Novamagus/inn.png"),
        'shop': load_sprite("/Users/williammarcellino/Documents/Fantasy_Game/Fantasy_Game_Art_Assets/Misc/Novamagus/shop.png"),
        'dungeon_entrance': load_sprite("/Users/williammarcellino/Documents/Fantasy_Game/Fantasy_Game_Art_Assets/Misc/Novamagus/dungeon_entrance.png")
    }
    return assets

def create_grid():
    """Return a 2D list representing the Novamagus layout.
    Coordinates are given such that (0,0) corresponds to the bottom-left tile."""
    grid = [
        # Row 7 (top row)
        ["cobble", "cobble", "cobble", "vegetation", "cobble", "cobble", "cobble", "vegetation"],
        # Row 6
        ["vegetation", "cobble", "cobble", "cobble", "cobble", "dungeon_entrance", "cobble", "vegetation"],
        # Row 5
        ["cobble", "cobble", "inn", "cobble", "cobble", "cobble", "cobble", "vegetation"],
        # Row 4
        ["cobble", "cobble", "cobble", "cobble", "shop", "vegetation", "cobble", "vegetation"],
        # Row 3
        ["cobble", "cobble", "cobble", "cobble", "cobble", "cobble", "cobble", "vegetation"],
        # Row 2
        ["cobble", "vegetation", "cobble", "cobble", "cobble", "cobble", "cobble", "vegetation"],
        # Row 1 (bottom row, where the player starts)
        ["cobble", "cobble", "cobble", "vegetation", "cobble", "cobble", "cobble", "vegetation"]
    ]
    return grid

def draw_hub(screen, grid, assets, hub_scale):
    """Draw the hub grid, scaling each tile to fit within the playable area."""
    rows = len(grid)
    cols = len(grid[0])
    
    # Use the hub scale to determine tile size
    tile_size = HUB_TILE_SIZE * hub_scale
    
    # Make sure tiles will fit within the playable area
    if tile_size * cols > HUB_PLAYABLE_AREA_WIDTH or tile_size * rows > HUB_PLAYABLE_AREA_HEIGHT:
        # If not, calculate a suitable size that fits
        max_tile_width = HUB_PLAYABLE_AREA_WIDTH / cols
        max_tile_height = HUB_PLAYABLE_AREA_HEIGHT / rows
        tile_size = min(max_tile_width, max_tile_height)
    
    # Create a surface for the hub area
    hub_surface = pygame.Surface((HUB_PLAYABLE_AREA_WIDTH, HUB_PLAYABLE_AREA_HEIGHT))
    hub_surface.fill(BLACK)
    
    # Draw a border around the playable area
    pygame.draw.rect(screen, WHITE, (0, 0, HUB_PLAYABLE_AREA_WIDTH, HUB_PLAYABLE_AREA_HEIGHT), 1)
    
    # Calculate offsets to center the grid in the playable area
    offset_x = (HUB_PLAYABLE_AREA_WIDTH - (cols * tile_size)) / 2
    offset_y = (HUB_PLAYABLE_AREA_HEIGHT - (rows * tile_size)) / 2
    
    # Draw each tile
    for row_index in range(rows):
        for col_index in range(cols):
            tile_type = grid[row_index][col_index]
            asset = assets.get(tile_type, assets['cobble'])
            scaled_asset = pygame.transform.smoothscale(
                asset, (int(tile_size), int(tile_size))
            )
            x = offset_x + col_index * tile_size
            y = offset_y + row_index * tile_size
            hub_surface.blit(scaled_asset, (x, y))
    
    # Blit the hub surface to the screen
    screen.blit(hub_surface, (0, 0))

def run_hub(screen, clock, player):
    """Main loop for the Novamagus hub."""
    global transition_to_dungeon
    transition_to_dungeon = False  # Reset the transition flag
    
    print("DEBUG: Starting run_hub function")
    print(f"DEBUG: Player position: {player.position}")
    print(f"DEBUG: Player sprite: {player.sprite}")
    
    # Ensure player has a sprite
    if not ensure_player_sprite(player):
        print("ERROR: Could not load player sprite for hub")
    
    assets = load_hub_assets()
    grid = create_grid()
    hub_scale = HUB_SCALE
    rows = len(grid)
    cols = len(grid[0])
    
    # Initialize player position in the bottom center of the hub (using grid coordinates)
    player_pos = [cols // 2, 0]  # Bottom row, middle column (grid coordinates)
    print(f"DEBUG: Initial player grid position: {player_pos}")

    hub_running = True
    frame_count = 0
    
    while hub_running:
        frame_count += 1
        if frame_count % 60 == 0:  # Debug every second
            print(f"DEBUG: Hub running, frame {frame_count}, player at {player_pos}")
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                prev_pos = player_pos.copy()
                
                # Get current grid position
                curr_grid_x = player_pos[0]
                curr_grid_y = player_pos[1]
                
                # Calculate new position based on key press
                new_grid_x, new_grid_y = curr_grid_x, curr_grid_y
                
                if event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                    new_grid_x += 1
                elif event.key == pygame.K_LEFT or event.key == pygame.K_a:
                    new_grid_x -= 1
                elif event.key == pygame.K_UP or event.key == pygame.K_w:
                    new_grid_y += 1  # Up in grid coordinates
                elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                    new_grid_y -= 1  # Down in grid coordinates
                
                # Calculate the corresponding row in the grid (grid is stored top-to-bottom)
                new_row = (rows - 1) - new_grid_y
                new_col = new_grid_x
                
                # Check if the new position is valid
                if new_row < 0 or new_row >= rows or new_col < 0 or new_col >= cols:
                    print(f"Movement blocked: out of bounds! Attempted grid pos: ({new_grid_x}, {new_grid_y})")
                else:
                    # Update the player position in grid coordinates
                    player_pos = [new_grid_x, new_grid_y]
                    print(f"Player moved to grid pos ({new_grid_x}, {new_grid_y}), row/col ({new_row}, {new_col})")
                    
                    # Check for special tile interactions
                    current_tile = grid[new_row][new_col]
                    print(f"Player moved to {current_tile} tile")
                    
                    if current_tile == "dungeon_entrance":
                        print("DEBUG: Dungeon entrance detected!")
                        transition_to_dungeon = True
                        common_b_s.in_dungeon = True
                        global in_dungeon
                        in_dungeon = True
                        hub_running = False
                        print("DEBUG: Exiting hub mode now...")
                    elif current_tile == "shop":
                        shop_interaction(screen, clock, player)
                    elif current_tile == "inn":
                        add_message("Resting at the inn restores your health and spell points!")
                        player.hit_points = player.max_hit_points
                        player.spell_points = player.calculate_spell_points()
                        print("Player rested at the inn and recovered!")

        # --- Drawing Section ---
        screen.fill((0, 0, 0))
        
        print(f"DEBUG: Drawing hub, grid size: {rows}x{cols}")
        draw_hub(screen, grid, assets, hub_scale)

        # --- Draw Right and Bottom Panels ---
        draw_right_panel(
            screen,
            player,
            HUB_PLAYABLE_AREA_WIDTH,
            HUB_PLAYABLE_AREA_HEIGHT,
            HUB_RIGHT_PANEL_WIDTH,
            offset_x=RIGHT_PANEL_OFFSET
        )
        draw_bottom_panel(
            screen,
            HUB_PLAYABLE_AREA_HEIGHT,
            HUB_SCREEN_WIDTH,
            HUB_BOTTOM_PANEL_HEIGHT,
            offset_y=BOTTOM_PANEL_OFFSET
        )

        # --- Draw the Player Sprite ---
        if player.sprite:
            # Use the hub scale to determine tile size
            tile_size = HUB_TILE_SIZE * hub_scale
            
            # Make sure tiles will fit within the playable area
            if tile_size * cols > HUB_PLAYABLE_AREA_WIDTH or tile_size * rows > HUB_PLAYABLE_AREA_HEIGHT:
                max_tile_width = HUB_PLAYABLE_AREA_WIDTH / cols
                max_tile_height = HUB_PLAYABLE_AREA_HEIGHT / rows
                tile_size = min(max_tile_width, max_tile_height)
            
            # Scale the player sprite to match the calculated tile size
            try:
                scaled_player_sprite = pygame.transform.smoothscale(
                    player.sprite, (int(tile_size), int(tile_size))
                )
            except Exception as e:
                print(f"ERROR: Failed to scale player sprite: {e}")
                # Create a simple colored rectangle as fallback
                scaled_player_sprite = pygame.Surface((int(tile_size), int(tile_size)))
                scaled_player_sprite.fill((255, 255, 0))  # Yellow player
            
            # Get the player's grid coordinates
            player_grid_x = player_pos[0]
            player_grid_y = player_pos[1]
            
            # Calculate the offset to center the grid in the playable area
            offset_x = (HUB_PLAYABLE_AREA_WIDTH - (cols * tile_size)) / 2
            offset_y = (HUB_PLAYABLE_AREA_HEIGHT - (rows * tile_size)) / 2
            
            # Calculate screen pixel coordinates for drawing
            draw_x = offset_x + player_grid_x * tile_size
            draw_y = offset_y + (rows - 1 - player_grid_y) * tile_size
            
            # Draw the player sprite on top of the hub surface
            screen.blit(scaled_player_sprite, (draw_x, draw_y))
            
            # Store the pixel position in the player object for reference
            player.position = [int(draw_x + tile_size//2), int(draw_y + tile_size//2)]
            
            # Debug output
            if frame_count % 60 == 0:  # Only print every second to avoid spam
                print(f"Player drawn at pixel: ({draw_x}, {draw_y}), player.position updated to: {player.position}")
        else:
            print("ERROR: Player sprite is None, cannot draw player")
            # Draw a simple rectangle as fallback
            tile_size = HUB_TILE_SIZE * hub_scale
            if tile_size * cols > HUB_PLAYABLE_AREA_WIDTH or tile_size * rows > HUB_PLAYABLE_AREA_HEIGHT:
                max_tile_width = HUB_PLAYABLE_AREA_WIDTH / cols
                max_tile_height = HUB_PLAYABLE_AREA_HEIGHT / rows
                tile_size = min(max_tile_width, max_tile_height)
            
            offset_x = (HUB_PLAYABLE_AREA_WIDTH - (cols * tile_size)) / 2
            offset_y = (HUB_PLAYABLE_AREA_HEIGHT - (rows * tile_size)) / 2
            draw_x = offset_x + player_pos[0] * tile_size
            draw_y = offset_y + (rows - 1 - player_pos[1]) * tile_size
            
            pygame.draw.rect(screen, (255, 255, 0), (draw_x, draw_y, tile_size, tile_size))
            player.position = [int(draw_x + tile_size//2), int(draw_y + tile_size//2)]

        pygame.display.flip()
        clock.tick(HUB_FPS)

# A global flag to signal when to leave the hub:
transition_to_dungeon = False
