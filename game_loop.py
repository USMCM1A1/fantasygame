import pygame
import sys
import os

# Import from our new utility/config files first
from game_config import *
from game_utils import roll_dice_expression, draw_bordered_text, get_memory_usage
from game_effects import spell_sound, melee_sound, arrow_sound, levelup_sound, frost_sound

# Import core game modules
import common_b_s
from common_b_s import (
    add_message, update_message_queue, MessageCategory,
    draw_attack_prompt, draw_right_panel, draw_bottom_panel,
    handle_scroll_events, loot_drop_sprite,
    cast_spell,
    spells_dialogue,
    Dungeon, items_list, load_sprite
)

import debug_system
from debug_system import debug_console

from game_state_manager import GameState, game_state_manager, \
                               transition_from_hub_to_dungeon, \
                               handle_dungeon_level_transition, \
                               handle_dungeon_map_transition, \
                               save_game, load_game

from player import Player
import novamagus_hub

from Data.condition_system import condition_manager
from Data.spell_bridge import update_spells_dialogue

from game_logic_utils import process_monster_death as util_process_monster_death, handle_monster_turn


def process_game_turn(player, dungeon):
    debug_console.add_message(f"game_loop.process_game_turn: Using condition_manager with current_turn: {condition_manager.current_turn}", "DEBUG")
    condition_messages = condition_manager.process_turn([player] + dungeon.monsters)
    for msg in condition_messages:
        add_message(msg)


def combat(player_char, monster_char, dungeon_instance_ref):
    combat_messages = []

    player_str_mod = player_char.calculate_modifier(player_char.get_effective_ability("strength"))
    monster_str_mod = monster_char.to_hit

    player_initiative = roll_dice_expression("1d10") + player_char.calculate_modifier(player_char.get_effective_ability("dexterity"))
    monster_initiative = roll_dice_expression("1d10") + monster_char.to_hit

    if player_initiative > monster_initiative:
        attacker, defender = player_char, monster_char
        combat_messages.append(f"{player_char.name} goes first!")
    else:
        attacker, defender = monster_char, player_char
        combat_messages.append(f"{monster_char.name} goes first!")

    while attacker.hit_points > 0 and defender.hit_points > 0:
        if attacker == player_char:
            attack_roll = roll_dice_expression("1d20") + player_char.calculate_modifier(player_char.get_effective_ability("strength"))
        else:
            attack_roll = roll_dice_expression("1d20") + monster_char.to_hit

        if attack_roll >= defender.get_effective_ac():
            if attacker == player_char:
                damage = player_char.get_effective_damage()
            else:
                damage = monster_char.get_effective_damage()

            defender.hit_points -= damage
            combat_messages.append(f"{attacker.name} hits {defender.name} for {damage} damage!")
            melee_sound.play()
        else:
            combat_messages.append(f"{attacker.name} misses {defender.name}!")

        attacker, defender = defender, attacker

    if player_char.hit_points <= 0:
        combat_messages.append("YOU have Died.")
        player_char.sprite = load_sprite(common_b_s.assets_data['sprites']['heroes']['warrior']['dead'])
        player_char.is_dead = True
        game_state_manager.set_state(GameState.GAME_OVER)
    elif monster_char.hit_points <= 0:
        monster_char.is_dead = True
        combat_messages.append(f"{monster_char.name} is defeated in direct combat!")

    return combat_messages

def run_game_loop(screen, clock, player, game_dungeon, initial_game_state_enum):
    running = True
    combat_occurred = False
    combat_occurred_prompt = False
    last_debug_update = 0

    # Set the initial state
    game_state_manager.set_state(initial_game_state_enum)

    while running:
        current_game_state_enum = game_state_manager.get_state()

        key_states = pygame.key.get_pressed()

        if hasattr(debug_system, 'key_state'):
            debug_system.key_state["F1"] = key_states[pygame.K_F1]
            debug_system.key_state["T"] = key_states[pygame.K_t]

        # Handle HUB state - this was missing proper handling
        if current_game_state_enum == GameState.HUB:
            print("DEBUG: Entering HUB state")
            
            # Switch to hub screen dimensions if needed
            current_width, current_height = screen.get_size()
            if current_width != HUB_SCREEN_WIDTH or current_height != HUB_SCREEN_HEIGHT:
                screen = pygame.display.set_mode((HUB_SCREEN_WIDTH, HUB_SCREEN_HEIGHT))
                print(f"DEBUG: Switched to hub screen size: {HUB_SCREEN_WIDTH}x{HUB_SCREEN_HEIGHT}")
            
            # Run the hub - this will handle its own event loop
            novamagus_hub.run_hub(screen, clock, player)
            
            # Check if we need to transition to dungeon
            if novamagus_hub.transition_to_dungeon:
                print("DEBUG: Transitioning from hub to dungeon")
                
                # Switch back to dungeon screen dimensions
                screen = pygame.display.set_mode((DUNGEON_SCREEN_WIDTH, DUNGEON_SCREEN_HEIGHT))
                print(f"DEBUG: Switched to dungeon screen size: {DUNGEON_SCREEN_WIDTH}x{DUNGEON_SCREEN_HEIGHT}")
                
                game_dungeon = transition_from_hub_to_dungeon(player, screen, clock)
                game_state_manager.set_state(GameState.PLAYING)
                
                # Reset the transition flag
                novamagus_hub.transition_to_dungeon = False
                continue

        update_message_queue()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.USEREVENT + 1:
                levelup_sound.play()
                pygame.time.set_timer(pygame.USEREVENT + 1, 0)

            if event.type == pygame.KEYDOWN:
                key_name = pygame.key.name(event.key)
                if hasattr(debug_system, 'test_arena_logger') and hasattr(debug_system.test_arena_logger, 'debug'):
                    debug_system.test_arena_logger.debug(f"Key pressed: {key_name}")
                if hasattr(debug_system, 'keys_pressed'):
                    debug_system.keys_pressed.append(key_name)
                    if len(debug_system.keys_pressed) > 10: 
                        debug_system.keys_pressed.pop(0)

                if event.key == pygame.K_d:
                    debug_console.toggle()
                    add_message("Debug console toggled", WHITE, MessageCategory.DEBUG)

                if debug_console.visible and debug_console.handle_scroll(event): 
                    continue

                handle_scroll_events(event)

                moved_this_turn = False
                current_loop_state_enum = game_state_manager.get_state()

                if current_loop_state_enum == GameState.PLAYING:
                    # Player movement and actions
                    action_taken_by_player = False
                    if event.key in [pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_w, pygame.K_s, pygame.K_a, pygame.K_d]:
                        dx, dy = 0,0
                        if event.key == pygame.K_UP or event.key == pygame.K_w: dy = -1
                        elif event.key == pygame.K_DOWN or event.key == pygame.K_s: dy = 1
                        elif event.key == pygame.K_LEFT or event.key == pygame.K_a: dx = -1
                        elif event.key == pygame.K_RIGHT or event.key == pygame.K_d: dx = 1

                        move_result = player.move(dx, dy, game_dungeon)

                        success, transition_type, message, destination_map = False, None, "", None
                        if len(move_result) == 4: 
                            success, transition_type, destination_map, message = move_result
                        elif len(move_result) == 3: 
                            success, transition_type, message = move_result

                        if success: action_taken_by_player = True
                        if message and message.strip(): add_message(message)

                        if success and transition_type == "map_transition" and destination_map is not None:
                            game_dungeon = handle_dungeon_map_transition(player, game_dungeon, destination_map)
                        elif success and transition_type == "level_transition":
                            game_dungeon = handle_dungeon_level_transition(player, game_dungeon)

                    elif event.key == pygame.K_SPACE:
                        action_taken_by_player = True
                        add_message(f"{player.name} waits.", MessageCategory.INFO)

                    elif event.key == pygame.K_i:
                        game_state_manager.set_state(GameState.INVENTORY)
                        add_message("Inventory Opened.", MessageCategory.GAME_EVENT)
                    elif event.key == pygame.K_c:
                        game_state_manager.set_state(GameState.CHARACTER_SHEET)
                        add_message("Character Sheet Opened.", MessageCategory.GAME_EVENT)
                    elif event.key == pygame.K_ESCAPE:
                        game_state_manager.set_state(GameState.PAUSE_MENU)
                        add_message("Pause Menu Opened.", MessageCategory.GAME_EVENT)

                    elif event.key == pygame.K_y and combat_occurred_prompt:
                        target_monster = None
                        player_tile_x = player.position[0] // TILE_SIZE
                        player_tile_y = player.position[1] // TILE_SIZE
                        for m in game_dungeon.monsters:
                            if hasattr(m, 'is_alive') and m.is_alive:
                                monster_tile_x = m.position[0] // TILE_SIZE
                                monster_tile_y = m.position[1] // TILE_SIZE
                                if abs(player_tile_x - monster_tile_x) + abs(player_tile_y - monster_tile_y) == 1:
                                    target_monster = m; break
                        if target_monster:
                            combat_log = combat(player, target_monster, game_dungeon)
                            for log_msg in combat_log: add_message(log_msg, MessageCategory.COMBAT)
                            action_taken_by_player = True
                        combat_occurred_prompt = False

                    elif event.key == pygame.K_n and combat_occurred_prompt:
                        combat_occurred_prompt = False
                        add_message("You chose not to attack.", MessageCategory.GAME_EVENT)

                    elif event.key == pygame.K_x:
                        selected_spell = None
                        try: 
                            selected_spell = update_spells_dialogue(screen, player, clock)
                        except Exception as e: 
                            debug_console.add_message(f"Spell UI Error: {e}", "ERROR")
                            selected_spell = spells_dialogue(screen, player, clock)

                        if selected_spell:
                            target_for_spell = player
                            # Simple targeting - find first living monster if spell isn't self-targeted
                            spell_name = selected_spell.get("name", "")
                            if "heal" not in spell_name.lower() and "armor" not in spell_name.lower():
                                target_for_spell = None
                                for m in game_dungeon.monsters:
                                    if hasattr(m, 'is_alive') and m.is_alive and not getattr(m, 'is_dead', False):
                                        target_for_spell = m
                                        break
                                if not target_for_spell: 
                                    add_message("No valid enemy targets for spell.", MessageCategory.INFO)
                                    continue

                            if target_for_spell:
                                spell_cast_messages = cast_spell(player, target_for_spell, selected_spell["name"], game_dungeon)
                                for msg in spell_cast_messages: add_message(msg)
                                action_taken_by_player = True

                    # Handle game state transitions back to hub
                    elif event.key == pygame.K_h:  # H key to return to hub
                        print("DEBUG: Returning to hub from dungeon")
                        common_b_s.in_dungeon = False
                        game_state_manager.set_state(GameState.HUB)
                        add_message("Returning to Novamagus...", MessageCategory.GAME_EVENT)

                    # Save and Load
                    elif event.key == pygame.K_F5:  # Save game
                        if save_game(player, game_dungeon, "dungeon" if common_b_s.in_dungeon else "hub"):
                            add_message("Game saved successfully!", GREEN, MessageCategory.GAME_EVENT)
                        else:
                            add_message("Failed to save game.", RED, MessageCategory.ERROR)
                    
                    elif event.key == pygame.K_F9:  # Load game
                        loaded_data = load_game()
                        if loaded_data:
                            player, game_dungeon, loaded_state, saved_cm_turn = loaded_data
                            condition_manager.current_turn = saved_cm_turn
                            add_message("Game loaded successfully!", GREEN, MessageCategory.GAME_EVENT)
                        else:
                            add_message("Failed to load game.", RED, MessageCategory.ERROR)

                    if action_taken_by_player:
                        process_game_turn(player, game_dungeon)
                        
                        for monster_obj in game_dungeon.monsters:
                            if monster_obj.hit_points > 0 and not getattr(monster_obj, '_was_incapacitated_this_turn', False):
                                handle_monster_turn(monster_obj, player, game_dungeon)

                        for m_obj in list(game_dungeon.monsters):
                            if m_obj.hit_points <= 0 and not getattr(m_obj, 'death_processed_this_turn_final', False):
                                death_messages_loop = util_process_monster_death(m_obj, player, game_dungeon, add_message, items_list)
                                for msg in death_messages_loop: add_message(msg)
                                m_obj.death_processed_this_turn_final = True

                        if getattr(player, 'is_dead', False):
                             game_state_manager.set_state(GameState.GAME_OVER)
                             add_message("You have succumbed to your wounds!", MessageCategory.GAME_EVENT)

                        for m_obj in game_dungeon.monsters:
                            if hasattr(m_obj, 'death_processed_this_turn_final'):
                                delattr(m_obj, 'death_processed_this_turn_final')
                            if hasattr(m_obj, '_was_incapacitated_this_turn'):
                                m_obj._was_incapacitated_this_turn = False

                elif current_loop_state_enum == GameState.PAUSE_MENU:
                    if event.key == pygame.K_p or event.key == pygame.K_ESCAPE: 
                        game_state_manager.set_state(GameState.PLAYING)
                        debug_console.add_message("Game Resumed.", "GAME_EVENT")
                elif current_loop_state_enum == GameState.INVENTORY:
                    if event.key == pygame.K_i: 
                        game_state_manager.set_state(GameState.PLAYING)
                        debug_console.add_message("Inventory Closed.", "GAME_EVENT")
                elif current_loop_state_enum == GameState.CHARACTER_SHEET:
                    if event.key == pygame.K_c: 
                        game_state_manager.set_state(GameState.PLAYING)
                        debug_console.add_message("Character Sheet Closed.", "GAME_EVENT")
                elif current_loop_state_enum == GameState.GAME_OVER:
                    if event.type == pygame.KEYDOWN: 
                        running = False
                        debug_console.add_message("Exiting Game Over.", "GAME_EVENT")

        # Game State Updates (continuous) - only for PLAYING state
        if current_game_state_enum == GameState.PLAYING:
            player_tile_x = player.position[0] // TILE_SIZE
            player_tile_y = player.position[1] // TILE_SIZE
            for drop in game_dungeon.dropped_items[:]:
                if player_tile_x == (drop['position'][0] // TILE_SIZE) and player_tile_y == (drop['position'][1] // TILE_SIZE):
                    if hasattr(player, 'pickup_item'):
                        player.pickup_item(drop['item'])
                    game_dungeon.dropped_items.remove(drop)
            
            chest_coords = (player_tile_x, player_tile_y)
            if chest_coords in game_dungeon.chests:
                chest = game_dungeon.chests[chest_coords]
                if chest.open and (len(chest.contents) > 0 or chest.gold > 0):
                    if chest.gold > 0: 
                        player.gold += chest.gold
                        add_message(f"Found {chest.gold} gold!", MessageCategory.ITEM)
                        chest.gold = 0
                    for item_in_chest in chest.contents[:]: 
                        if hasattr(player, 'pickup_item'):
                            player.pickup_item(item_in_chest)
                    chest.contents = []

        # Drawing Code - only draw if we're not in HUB state (hub handles its own drawing)
        if current_game_state_enum != GameState.HUB:
            screen.fill(BLACK)
            current_draw_state = game_state_manager.get_state()

            if current_draw_state == GameState.PLAYING:
                if hasattr(game_dungeon, 'draw'):
                    game_dungeon.draw(screen)
                if hasattr(player, 'draw'):
                    player.draw(screen, getattr(game_dungeon, 'tile_size', TILE_SIZE), 
                               getattr(game_dungeon, 'camera_offset_x', 0), 
                               getattr(game_dungeon, 'camera_offset_y', 0))
                
                for m_obj in game_dungeon.monsters:
                     if not getattr(m_obj, 'is_dead', False):
                        if hasattr(m_obj, 'draw'):
                            m_obj.draw(screen, getattr(game_dungeon, 'tile_size', TILE_SIZE), 
                                      getattr(game_dungeon, 'camera_offset_x', 0), 
                                      getattr(game_dungeon, 'camera_offset_y', 0))

                draw_right_panel(screen, player, DUNGEON_PLAYABLE_AREA_WIDTH, DUNGEON_PLAYABLE_AREA_HEIGHT, DUNGEON_RIGHT_PANEL_WIDTH)
                draw_bottom_panel(screen, DUNGEON_PLAYABLE_AREA_HEIGHT, DUNGEON_SCREEN_WIDTH, DUNGEON_BOTTOM_PANEL_HEIGHT)

                # Combat prompt logic
                new_combat_prompt_needed = False
                player_tile_x = player.position[0] // TILE_SIZE
                player_tile_y = player.position[1] // TILE_SIZE
                for m_obj in game_dungeon.monsters:
                    if hasattr(m_obj, 'is_alive') and m_obj.is_alive and not getattr(m_obj, 'is_dead', False):
                        monster_tile_x = m_obj.position[0] // TILE_SIZE
                        monster_tile_y = m_obj.position[1] // TILE_SIZE
                        if abs(player_tile_x - monster_tile_x) + abs(player_tile_y - monster_tile_y) == 1:
                            if not combat_occurred_prompt:
                                 draw_attack_prompt(screen, m_obj.name)
                            new_combat_prompt_needed = True
                            break
                combat_occurred_prompt = new_combat_prompt_needed

            elif current_draw_state == GameState.PAUSE_MENU:
                if hasattr(game_dungeon, 'draw'):
                    game_dungeon.draw(screen, player.position[0], player.position[1])
                if hasattr(player, 'draw'):
                    player.draw(screen, getattr(game_dungeon, 'tile_size', TILE_SIZE), 
                               getattr(game_dungeon, 'camera_offset_x', 0), 
                               getattr(game_dungeon, 'camera_offset_y', 0))
                for m_obj in game_dungeon.monsters:
                    if not getattr(m_obj, 'is_dead', False) and hasattr(m_obj, 'draw'):
                        m_obj.draw(screen, getattr(game_dungeon, 'tile_size', TILE_SIZE), 
                                  getattr(game_dungeon, 'camera_offset_x', 0), 
                                  getattr(game_dungeon, 'camera_offset_y', 0))
                draw_bordered_text(screen, "PAUSED", DUNGEON_SCREEN_WIDTH // 2, DUNGEON_SCREEN_HEIGHT // 2, font, RED)

            elif current_draw_state == GameState.INVENTORY:
                if hasattr(game_dungeon, 'draw'):
                    game_dungeon.draw(screen, player.position[0], player.position[1])
                draw_bordered_text(screen, "INVENTORY (I to close)", DUNGEON_SCREEN_WIDTH // 2, DUNGEON_SCREEN_HEIGHT // 2, font, WHITE)

            elif current_draw_state == GameState.CHARACTER_SHEET:
                if hasattr(game_dungeon, 'draw'):
                    game_dungeon.draw(screen, player.position[0], player.position[1])
                draw_bordered_text(screen, "CHARACTER (C to close)", DUNGEON_SCREEN_WIDTH // 2, DUNGEON_SCREEN_HEIGHT // 2, font, WHITE)

            elif current_draw_state == GameState.GAME_OVER:
                draw_bordered_text(screen, "GAME OVER", DUNGEON_SCREEN_WIDTH // 2, DUNGEON_SCREEN_HEIGHT // 2 - 50, font, RED)
                draw_bordered_text(screen, "Press any key to continue", DUNGEON_SCREEN_WIDTH // 2, DUNGEON_SCREEN_HEIGHT // 2 + 50, font, WHITE)

            # Debug info and console
            current_time_ticks = pygame.time.get_ticks()
            if current_time_ticks - last_debug_update > 5000:
                if debug_console.visible:
                    fps_val = clock.get_fps()
                    mem_info = get_memory_usage()
                    add_message(f"FPS: {fps_val:.1f}, {mem_info}", (150,150,255), MessageCategory.DEBUG)
                    if player:
                         add_message(f"Player: HP {player.hit_points}/{player.max_hit_points}, SP {player.spell_points}/{getattr(player, 'max_spell_points', 'N/A')}",
                                      (200,255,200), MessageCategory.DEBUG)
                    if game_dungeon and (current_draw_state == GameState.PLAYING or current_draw_state == GameState.PAUSE_MENU):
                        counts = (len(getattr(game_dungeon, 'monsters', [])), 
                                 len(getattr(game_dungeon, 'dropped_items', [])), 
                                 len(getattr(game_dungeon, 'chests', {})))
                        add_message(f"Entities: {counts[0]} monsters, {counts[1]} items, {counts[2]} chests",
                                  (200,200,255), MessageCategory.DEBUG)
                last_debug_update = current_time_ticks
            
            debug_console.draw(screen)
            pygame.display.flip()

        # Only tick the clock if we're not in hub state (hub handles its own timing)
        if current_game_state_enum != GameState.HUB:
            clock.tick(DUNGEON_FPS)

    pygame.quit()
    sys.exit()