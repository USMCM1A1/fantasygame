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
    handle_scroll_events, draw_attack_prompt, draw_equipment_panel, draw_debug_info,
    
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
    """Draw the hub grid, scaling each tile."""
    rows = len(grid)
    cols = len(grid[0])
    for row_index in range(rows):
        for col_index in range(cols):
            tile_type = grid[row_index][col_index]
            asset = assets.get(tile_type, assets['cobble'])
            scaled_asset = pygame.transform.smoothscale(
                asset, (TILE_SIZE * hub_scale, TILE_SIZE * hub_scale)
            )
            x = col_index * (TILE_SIZE * hub_scale)
            y = row_index * (TILE_SIZE * hub_scale)
            screen.blit(scaled_asset, (x, y))

def run_hub(screen, clock, player):
    """Main loop for the Novamagus hub."""
    global transition_to_dungeon
    assets = load_hub_assets()
    grid = create_grid()
    hub_scale = HUB_SCALE  # Use the hub scale constant
    rows = len(grid)
    cols = len(grid[0])
    # Use the player's current position as the starting point.
    player_pos = player.position.copy()

    hub_running = True
    while hub_running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                prev_pos = player_pos.copy()
                if event.key == pygame.K_RIGHT:
                    player_pos[0] += HUB_TILE_SIZE
                elif event.key == pygame.K_LEFT:
                    player_pos[0] -= HUB_TILE_SIZE
                elif event.key == pygame.K_UP:
                    player_pos[1] += HUB_TILE_SIZE
                elif event.key == pygame.K_DOWN:
                    player_pos[1] -= HUB_TILE_SIZE

                # Calculate grid cell (assuming (0,0) is the bottom-left)
                col = player_pos[0] // HUB_TILE_SIZE
                row = (rows - 1) - (player_pos[1] // HUB_TILE_SIZE)
                if row < 0 or row >= rows or col < 0 or col >= cols:
                    print("Movement blocked: out of bounds!")
                    player_pos = prev_pos.copy()
                else:
                    player.position = player_pos.copy()
                    current_tile = grid[row][col]
                    if current_tile == "dungeon_entrance":
                        transition_to_dungeon = True
                        in_dungeon = True
                        hub_running = False
                    elif current_tile == "shop":
                        shop_interaction(screen, clock, player)

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
        scaled_player_sprite = pygame.transform.smoothscale(
            player.sprite, (HUB_TILE_SIZE * hub_scale, HUB_TILE_SIZE * hub_scale)
        )
        player_grid_x = player_pos[0] // HUB_TILE_SIZE
        player_grid_y = player_pos[1] // HUB_TILE_SIZE
        draw_x = player_grid_x * HUB_TILE_SIZE * hub_scale
        draw_y = (rows - 1 - player_grid_y) * HUB_TILE_SIZE * hub_scale
        screen.blit(scaled_player_sprite, (draw_x, draw_y))

        pygame.display.flip()
        clock.tick(HUB_FPS)

# A global flag to signal when to leave the hub:
transition_to_dungeon = False


# In[ ]:




