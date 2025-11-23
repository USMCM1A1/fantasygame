import pygame
import random
import math
import os
import debug_system
import common_b_s # Ensure common_b_s is imported directly for in_dungeon flag

from common_b_s import (
    Dungeon,
    Monster,
    assets_data,
    load_sprite,
    TILE_SIZE,
    DUNGEON_PLAYABLE_AREA_WIDTH,
    DUNGEON_PLAYABLE_AREA_HEIGHT,
    DUNGEON_TILE_SIZE,
    DUNGEON_SCREEN_WIDTH,
    DUNGEON_SCREEN_HEIGHT,
    draw_text,
    add_message,
    WHITE # Added WHITE for text drawing
)

# =============================================================================
# === Test Arena Function for Spell Testing ===
# =============================================================================
def create_test_arena(player, dungeon):
    """
    Creates a special test arena for spell testing.
    The arena is a large open room with multiple monsters for testing spells.
    
    Args:
        player: The player character
        dungeon: The current dungeon (to copy necessary configuration)
        
    Returns:
        A new Dungeon instance configured as a test arena
    """
    import math  # Keep math import here if it's only used locally
    
    debug_system.test_arena_logger.info("Creating test arena...")
    
    # Create a new dungeon with a large open area
    width, height = 30, 30
    debug_system.test_arena_logger.debug(f"Creating arena with dimensions {width}x{height}")
    arena = Dungeon(width, height, max_rooms=0)
    
    # Copy important properties from existing dungeon
    arena.dungeon_depth = getattr(dungeon, 'dungeon_depth', 1)
    arena.map_number = getattr(dungeon, 'map_number', 0)
    arena.max_maps = getattr(dungeon, 'max_maps', 3)
    debug_system.test_arena_logger.debug(f"Set dungeon properties: depth={arena.dungeon_depth}, map={arena.map_number}")
    
    # Fill the entire dungeon with floor tiles
    debug_system.test_arena_logger.debug("Filling dungeon with floor tiles...")
    for x_coord in range(width): 
        for y_coord in range(height): 
            if x_coord == 0 or x_coord == width-1 or y_coord == 0 or y_coord == height-1:
                arena.tiles[x_coord][y_coord].type = "wall"
            else:
                arena.tiles[x_coord][y_coord].type = "floor"
                floor_sprite_path = assets_data["sprites"]["tiles"]["floor"]
                arena.tiles[x_coord][y_coord].sprite = load_sprite(floor_sprite_path)
    
    player_x_tile, player_y_tile = width // 2, height // 2
    max_x_tile = (DUNGEON_PLAYABLE_AREA_WIDTH - DUNGEON_TILE_SIZE) // DUNGEON_TILE_SIZE
    max_y_tile = (DUNGEON_PLAYABLE_AREA_HEIGHT - DUNGEON_TILE_SIZE) // DUNGEON_TILE_SIZE
    player_x_tile = min(max(player_x_tile, 2), max_x_tile - 2)
    player_y_tile = min(max(player_y_tile, 2), max_y_tile - 2)
    player_x_px = player_x_tile * DUNGEON_TILE_SIZE + DUNGEON_TILE_SIZE // 2
    player_y_px = player_y_tile * DUNGEON_TILE_SIZE + DUNGEON_TILE_SIZE // 2
    arena.entrance = (player_x_px, player_y_px)
    arena.start_position = list(arena.entrance)
    player.position = list(arena.entrance)
    debug_system.test_arena_logger.debug(f"Positioned player in playable area at {player.position}")
    
    debug_system.test_arena_logger.debug("Creating test monsters (rats and spiders)")
    arena.monsters = []
    monster_types_data_list = [ 
        {"name": "Giant Rat", "hit_points": 8, "to_hit": 0, "ac": 9, "move": 2, "dam": "1d3", "color": (150, 100, 80), "monster_type": "beast", "level": 1, "cr": 0.5},
        {"name": "Giant Spider", "hit_points": 12, "to_hit": 1, "ac": 11, "move": 1, "dam": "1d6", "color": (30, 30, 30), "monster_type": "beast", "level": 1, "cr": 1, "vulnerabilities": ["Fire"]}
    ]
    monster_count = 5
    monster_positions = [
        (player_x_tile + 3, player_y_tile - 2), (player_x_tile + 4, player_y_tile), (player_x_tile + 3, player_y_tile + 2),
        (player_x_tile - 3, player_y_tile - 1), (player_x_tile - 3, player_y_tile + 1)
    ]
    for i in range(monster_count):
        monster_type_data = monster_types_data_list[i % len(monster_types_data_list)]
        monster = Monster(
            name=f"{monster_type_data['name']} #{i+1}", hit_points=monster_type_data["hit_points"], to_hit=monster_type_data["to_hit"],
            ac=monster_type_data["ac"], move=monster_type_data["move"], dam=monster_type_data["dam"],
            sprites={"live": "./Fantasy_Game_Art_Assets/Enemies/beast/giant_rat.jpg" if monster_type_data["name"] == "Giant Rat" else "./Fantasy_Game_Art_Assets/Enemies/beast/giant_spider.jpg", "dead": ""},
            monster_type=monster_type_data["monster_type"], level=monster_type_data["level"], cr=monster_type_data["cr"],
            vulnerabilities=monster_type_data.get("vulnerabilities", []), resistances=monster_type_data.get("resistances", []), immunities=monster_type_data.get("immunities", [])
        )
        monster_x_tile, monster_y_tile = monster_positions[i]
        monster_x_tile = min(max(monster_x_tile, 1), max_x_tile - 1)
        monster_y_tile = min(max(monster_y_tile, 1), max_y_tile - 1)
        monster_x_px = monster_x_tile * DUNGEON_TILE_SIZE + DUNGEON_TILE_SIZE // 2
        monster_y_px = monster_y_tile * DUNGEON_TILE_SIZE + DUNGEON_TILE_SIZE // 2
        monster.position = [monster_x_px, monster_y_px]
        arena.monsters.append(monster)
    debug_system.test_arena_logger.debug(f"Added {len(arena.monsters)} test monsters to the arena")
    
    player.hit_points = player.max_hit_points
    player.spell_points = player.calculate_spell_points() + 100 
    debug_system.test_arena_logger.debug(f"Player set to full health ({player.hit_points}/{player.max_hit_points}) and {player.spell_points} spell points")
    debug_system.test_arena_logger.info(f"Created test arena with {len(arena.monsters)} monsters.")
    return arena

# =============================================================================
# === Emergency Test Arena Function ===
# =============================================================================
def create_emergency_arena(player, screen):
    debug_system.test_arena_logger.info("CREATING EMERGENCY TEST ARENA")
    screen.fill((0, 0, 0))
    draw_text(screen, "CREATING EMERGENCY TEST ARENA...", (255, 255, 255), DUNGEON_SCREEN_WIDTH//2 - 150, DUNGEON_SCREEN_HEIGHT//2)
    pygame.display.flip()
    pygame.time.delay(500)
    try:
        width, height = 20, 20
        min_arena = Dungeon(width, height, max_rooms=0)
        for x in range(width):
            for y in range(height):
                min_arena.tiles[x][y].type = "floor"
                try:
                    floor_sprite_path = assets_data["sprites"]["tiles"]["floor"]
                    min_arena.tiles[x][y].sprite = load_sprite(floor_sprite_path)
                except:
                    fallback_sprite = pygame.Surface((DUNGEON_TILE_SIZE, DUNGEON_TILE_SIZE))
                    fallback_sprite.fill((100, 100, 100))
                    min_arena.tiles[x][y].sprite = fallback_sprite
        player_x, player_y = width // 2, height // 2  
        min_arena.start_position = [player_x * DUNGEON_TILE_SIZE + DUNGEON_TILE_SIZE // 2, player_y * DUNGEON_TILE_SIZE + DUNGEON_TILE_SIZE // 2]
        player.position = list(min_arena.start_position)
        test_monster = Monster(
            name="Test Monster", hit_points=10, to_hit=0, ac=10, move=1, dam="1d4",
            sprites={"live": "./Fantasy_Game_Art_Assets/Enemies/beast/giant_rat.jpg", "dead": ""},
            monster_type="beast"
        )
        test_monster.position = [player.position[0] + 5*DUNGEON_TILE_SIZE, player.position[1]]
        min_arena.monsters = [test_monster]
        player.spell_points = 200
        add_message("EMERGENCY TEST ARENA CREATED!")
        add_message("Press 'x' to cast spells")
        add_message(f"You have {player.spell_points} spell points")
        debug_system.test_arena_logger.info("Emergency test arena created successfully")
        return min_arena, "dungeon"
    except Exception as e:
        screen.fill((0, 0, 0))
        draw_text(screen, f"ERROR: {str(e)}", (255, 0, 0), 50, 50)
        pygame.display.flip()
        pygame.time.delay(3000)
        debug_system.test_arena_logger.error(f"EMERGENCY ARENA CREATION FAILED: {e}", exc_info=True)
        return None, None

# =============================================================================
# === Test Arena Activation Logic ===
# =============================================================================
def handle_test_arena_activation(event, key_states, player, screen, game_dungeon, game_state):
    f1_pressed = key_states[pygame.K_F1]
    f2_pressed = key_states[pygame.K_F2]
    t_key_pressed = key_states[pygame.K_t]
    one_key_pressed = key_states[pygame.K_1]
    enter_key_pressed = key_states[pygame.K_RETURN]
    shift_pressed = key_states[pygame.K_LSHIFT] or key_states[pygame.K_RSHIFT]

    activated = False
    arena_type = "emergency" # Default to emergency, '1' key forces this.

    if event and event.type == pygame.KEYDOWN:
        # T+Enter combination (requires event)
        if t_key_pressed and enter_key_pressed and event.key == pygame.K_RETURN: # Check event.key for Enter
            debug_system.test_arena_logger.info("Test arena activated via T+ENTER key")
            activated = True
            arena_type = "standard" # T+Enter implies standard test arena
        elif event.key == pygame.K_t and shift_pressed: # Shift+T (requires event for key mod)
            debug_system.test_arena_logger.info("Test arena activated via SHIFT+T key")
            activated = True
            arena_type = "standard" # Shift+T implies standard test arena
        elif event.key == pygame.K_1: # '1' key for emergency arena
            debug_system.test_arena_logger.info("Emergency test arena activated via 1 key")
            activated = True
            arena_type = "emergency"
        elif event.key == pygame.K_F1: # F1 key
            debug_system.test_arena_logger.info("Test arena activated via F1 key")
            activated = True
            arena_type = "emergency" # F1 is emergency
        elif event.key == pygame.K_F2: # F2 key
            debug_system.test_arena_logger.info("Test arena activated via F2 key")
            activated = True
            arena_type = "standard" # F2 is standard

    # Check for direct key presses (without event context, for keys that don't need combos like Enter)
    # This part is a bit redundant if event is always passed, but kept for robustness
    # if not activated:
    #     if f1_pressed:
    #         debug_system.test_arena_logger.info("Test arena activated via F1 key (direct state)")
    #         activated = True
    #         arena_type = "emergency"
    #     elif f2_pressed:
    #         debug_system.test_arena_logger.info("Test arena activated via F2 key (direct state)")
    #         activated = True
    #         arena_type = "standard"
    #     elif one_key_pressed and not (t_key_pressed or shift_pressed): # Ensure '1' isn't part of another combo
    #         debug_system.test_arena_logger.info("Emergency test arena activated via 1 key (direct state)")
    #         activated = True
    #         arena_type = "emergency"

    if activated:
        screen.fill((0,0,0)) # BLACK
        loading_message = "Loading Test Arena..." if arena_type == "standard" else "Loading Emergency Test Arena..."
        draw_text(screen, loading_message, WHITE, DUNGEON_SCREEN_WIDTH//2 - 150, DUNGEON_SCREEN_HEIGHT//2)
        pygame.display.flip()
        pygame.time.delay(100)

        new_dungeon = None
        new_game_state = None
        try:
            if arena_type == "standard":
                new_dungeon = create_test_arena(player, game_dungeon) # Pass current dungeon for context
            else: # Emergency
                # Emergency arena doesn't need current dungeon context in its simpler form
                emergency_result = create_emergency_arena(player, screen) 
                if emergency_result and emergency_result[0]:
                    new_dungeon = emergency_result[0]
                    # new_game_state is implicitly "dungeon" from create_emergency_arena
            
            if new_dungeon:
                debug_system.test_arena_logger.info(f"{arena_type.capitalize()} test arena created and activated")
                # add_message(f"{arena_type.capitalize()} test arena created!") # Done by create functions
                return new_dungeon, "dungeon", True
            else:
                # This case might happen if create_emergency_arena returns (None, None)
                debug_system.test_arena_logger.error(f"Failed to create {arena_type} arena (returned None)")
                add_message(f"ERROR: Failed to create {arena_type} arena.", (255,0,0))


        except Exception as e:
            error_msg = f"CRITICAL ERROR CREATING {arena_type.upper()} ARENA: {str(e)}"
            debug_system.test_arena_logger.error(error_msg, exc_info=True)
            screen.fill((0,0,0)) # BLACK
            draw_text(screen, f"ERROR CREATING {arena_type.upper()} ARENA:", (255,0,0), 100, 100) # RED
            draw_text(screen, str(e), (255,0,0), 100, 130) # RED
            draw_text(screen, "Check console for details", WHITE, 100, 160)
            pygame.display.flip()
            pygame.time.delay(3000)
    
    return None, None, None


def handle_teleport_button_click(event_pos, player, current_dungeon, screen):
    # Define the button rect here or ensure it's passed/accessible
    teleport_button_rect = pygame.Rect(DUNGEON_SCREEN_WIDTH - 150, 10, 140, 30)

    if teleport_button_rect.collidepoint(event_pos):
        debug_system.test_arena_logger.info("Teleport to Arena button clicked.")
        add_message("Teleporting to the spell testing arena...")
        try:
            new_dungeon = create_test_arena(player, current_dungeon)
            if new_dungeon:
                debug_system.test_arena_logger.info("Test arena created successfully via button click.")
                add_message("Welcome to the spell testing arena!")
                add_message("Press 'x' to cast spells on the monsters.")
                player.spell_points = player.calculate_spell_points() + 100
                add_message(f"You have {player.spell_points} spell points for testing.")
                return new_dungeon, "dungeon", True
            else:
                add_message("Error: Failed to create test arena from button.", (255,0,0))
                debug_system.test_arena_logger.error("Failed to create test arena from button (returned None).")

        except Exception as e:
            add_message(f"Error creating test arena: {str(e)}", (255,0,0)) # RED
            debug_system.test_arena_logger.error(f"Error creating test arena via button: {e}", exc_info=True)
            # Optionally, display error on screen as in key activation
            screen.fill((0,0,0)) # BLACK
            draw_text(screen, "ERROR CREATING TEST ARENA:", (255,0,0), 100, 100)
            draw_text(screen, str(e), (255,0,0), 100, 130)
            pygame.display.flip()
            pygame.time.delay(2000)
            
    return None, None, None
