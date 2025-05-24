#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pygame
pygame.init()
import sys

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
    add_message, update_message_queue, roll_dice_expression, roll_ability_helper,
    can_equip_item, handle_targeting, compute_fov, get_valid_equipment_slots,
    swap_equipment, unequip_item, get_clicked_equipment_slot, shop_interaction,
    Item, Weapon, WeaponBlade, WeaponBlunt, Armor, Shield, Jewelry, Consumable,
    Character, Player, Tile,
)
import common_b_s  # Import full module if needed
in_dungeon = False

# (Optional) Ensure the display mode is set.
screen = pygame.display.set_mode((HUB_SCREEN_WIDTH, HUB_SCREEN_HEIGHT))
SCREEN_WIDTH = HUB_SCREEN_WIDTH
SCREEN_HEIGHT = HUB_SCREEN_HEIGHT
TILE_SIZE = HUB_TILE_SIZE

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
    assets = load_hub_assets()
    grid = create_grid()
    hub_scale = HUB_SCALE  # Use the hub scale constant
    rows = len(grid)
    cols = len(grid[0])
    
    # Initialize player position in the bottom center of the hub (using grid coordinates)
    # This ensures the player starts at a valid position regardless of previous state
    player_pos = [cols // 2, 0]  # Bottom row, middle column (grid coordinates)
    # The actual pixel position will be calculated when drawing the player

    hub_running = True
    while hub_running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                prev_pos = player_pos.copy()
                
                # Get current grid position (player_pos is already in grid coordinates)
                curr_grid_x = player_pos[0]
                curr_grid_y = player_pos[1]
                
                # Calculate new position based on key press
                new_grid_x, new_grid_y = curr_grid_x, curr_grid_y
                
                if event.key == pygame.K_RIGHT:
                    new_grid_x += 1
                elif event.key == pygame.K_LEFT:
                    new_grid_x -= 1
                elif event.key == pygame.K_UP:
                    new_grid_y += 1  # Up in grid coordinates
                elif event.key == pygame.K_DOWN:
                    new_grid_y -= 1  # Down in grid coordinates
                
                # Calculate the corresponding row in the grid (grid is stored top-to-bottom)
                new_row = (rows - 1) - new_grid_y
                new_col = new_grid_x
                
                # Check if the new position is valid
                if new_row < 0 or new_row >= rows or new_col < 0 or new_col >= cols:
                    print(f"Movement blocked: out of bounds! Attempted grid pos: ({new_grid_x}, {new_grid_y})")
                    # Keep the previous position
                else:
                    # Update the player position in grid coordinates
                    player_pos = [new_grid_x, new_grid_y]
                    # The actual pixel position will be calculated when drawing the player
                    
                    # Check for special tile interactions
                    current_tile = grid[new_row][new_col]
                    print(f"Player moved to {current_tile} tile at grid pos ({new_grid_x}, {new_grid_y}), row/col ({new_row}, {new_col})")
                    
                    if current_tile == "dungeon_entrance":
                        print("DEBUG: Dungeon entrance detected!")
                        print(f"DEBUG: Setting transition_to_dungeon = True (current value: {transition_to_dungeon})")
                        transition_to_dungeon = True
                        print(f"DEBUG: Setting common_b_s.in_dungeon = True (current value: {common_b_s.in_dungeon})")
                        common_b_s.in_dungeon = True  # Update the module variable
                        # Access the global in_dungeon variable
                        global in_dungeon
                        print(f"DEBUG: Setting global in_dungeon = True (current value: {in_dungeon})")
                        in_dungeon = True
                        print(f"DEBUG: Setting hub_running = False to exit hub loop (current value: {hub_running})")
                        hub_running = False
                        print("DEBUG: Exiting hub mode now...")
                    elif current_tile == "shop":
                        shop_interaction(screen, clock, player)
                    elif current_tile == "inn":
                        # Show a message for inn interaction
                        add_message("Resting at the inn restores your health and spell points!")
                        player.hit_points = player.max_hit_points
                        player.spell_points = player.calculate_spell_points()
                        print("Player rested at the inn and recovered!")

        # --- Drawing Section ---
        screen.fill((0, 0, 0))
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
        # Make sure player sprite exists before trying to scale it
        if player.sprite:
            # Use the hub scale to determine tile size
            tile_size = HUB_TILE_SIZE * hub_scale
            
            # Make sure tiles will fit within the playable area
            if tile_size * cols > HUB_PLAYABLE_AREA_WIDTH or tile_size * rows > HUB_PLAYABLE_AREA_HEIGHT:
                # If not, calculate a suitable size that fits
                max_tile_width = HUB_PLAYABLE_AREA_WIDTH / cols
                max_tile_height = HUB_PLAYABLE_AREA_HEIGHT / rows
                tile_size = min(max_tile_width, max_tile_height)
            
            # Scale the player sprite to match the calculated tile size
            scaled_player_sprite = pygame.transform.smoothscale(
                player.sprite, (int(tile_size), int(tile_size))
            )
            
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
            player.position = [draw_x, draw_y]
            
            # Debug output to help diagnose positioning
            print(f"Player at grid: ({player_grid_x}, {player_grid_y}), drawing at: ({draw_x}, {draw_y})")

        pygame.display.flip()
        clock.tick(HUB_FPS)

# A global flag to signal when to leave the hub:
transition_to_dungeon = False


# In[ ]:




