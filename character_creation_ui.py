import pygame
import sys
import random
import os

# Import necessary components from common_b_s.py
from common_b_s import (
    Player, Dungeon, roll_ability_helper, load_sprite, draw_text,
    assets_data, font,
    BLACK, WHITE, LIGHT_GRAY, GREEN, BLUE, RED, DARK_GRAY,
    HUB_SCREEN_WIDTH as SCREEN_WIDTH,
    HUB_SCREEN_HEIGHT as SCREEN_HEIGHT,
    HUB_TILE_SIZE as TILE_SIZE, # Using HUB_TILE_SIZE and aliasing to TILE_SIZE
    # races # common_b_s.races not used for now, keeping local racial_bonuses_text
)

# DEFAULT_FONT_SIZE is used locally for text rendering logic, ensure it's defined if not from common_b_s
# It was a placeholder, if `font` from common_b_s is used directly, this might not be needed
# or should be derived from the imported font's size. For now, let's keep a local definition
# if it's used for calculations independent of the actual imported font object's size.
# common_b_s.font is pygame.font.SysFont('monospace', 15). So DEFAULT_FONT_SIZE should be 15 or related.
# The character_creation_ui used 32. This will cause rendering issues if not handled.
# For now, I'll use the imported font's height for line spacing calculations where DEFAULT_FONT_SIZE was used.
# If a specific size "32" was intended for some text, a new font object would be needed.
# Let's assume for now, all text uses the imported `font`.

# Main character creation function
def character_creation_screen(screen, clock):
    # This function will contain the main loop for the character creation UI
    
    # Load background image
    # Try to load from common_b_s.assets_data, fallback to hardcoded path
    background_path_from_assets = assets_data.get("sprites", {}).get("background", {}).get("character_creation_bg") # Assuming key is "character_creation_bg"
    fallback_background_path = "/Users/williammarcellino/Documents/Fantasy_Game/Fantasy_Game_Art_Assets/Misc/B&S_UI_background.png"
    
    background_image = None
    
    if background_path_from_assets and os.path.exists(background_path_from_assets):
        try:
            background_image = pygame.image.load(background_path_from_assets).convert()
            background_image = pygame.transform.scale(background_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
            print(f"Loaded background from assets_data: {background_path_from_assets}")
        except pygame.error as e:
            print(f"Error loading background from assets_data {background_path_from_assets}: {e}. Trying fallback.")
            background_image = None # Ensure it's None if first try fails
    
    if not background_image and os.path.exists(fallback_background_path): # If assets_data load failed or path was None
        try:
            background_image = pygame.image.load(fallback_background_path).convert()
            background_image = pygame.transform.scale(background_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
            print(f"Loaded background from fallback path: {fallback_background_path}")
        except pygame.error as e:
            print(f"Error loading background from fallback {fallback_background_path}: {e}")
            background_image = None 
    
    if not background_image:
        print(f"Background image path not found or invalid in assets_data and fallback. Will use black background.")


    # Game loop variables
    running = True
    # Core state variables
    character_name = ""
    # Use the imported roll_ability_helper
    current_stats = {name: roll_ability_helper() for name in ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"]}
    stats_rolled = True 
    stats_accepted = False
    selected_race = None
    selected_class = None
    character_finalized = False 

    name_input_active = False
    ability_names = list(current_stats.keys())

    # UI layout variables
    # Use imported font's height for line spacing calculations
    font_height = font.get_height() 
    
    ui_area_y_start = int(SCREEN_HEIGHT * 0.20) 
    column_1_x = 50
    column_2_x = 400 
    input_field_width = 280 
    input_field_height = font_height + 10 # Adjust height based on font
    button_width = 150
    button_height = font_height + 20 # Adjust height based on font
    padding = 20

    name_input_rect = pygame.Rect(column_1_x, ui_area_y_start + padding, input_field_width, input_field_height)

    ability_rects = {} 
    current_y_offset_for_stats = name_input_rect.bottom + padding * 2
    for i, name in enumerate(ability_names):
        label_rect = pygame.Rect(column_1_x, current_y_offset_for_stats + i * (input_field_height + padding // 2), input_field_width // 2, input_field_height)
        value_rect = pygame.Rect(column_1_x + input_field_width // 2 + padding // 2, current_y_offset_for_stats + i * (input_field_height + padding // 2), input_field_width // 2 - padding // 2, input_field_height)
        ability_rects[name] = {"label": label_rect, "value": value_rect}
    
    last_stat_y_bottom = ability_rects[ability_names[-1]]["value"].bottom
    stat_buttons_y_offset = last_stat_y_bottom + padding * 2 
    
    roll_button_rect = pygame.Rect(column_1_x, stat_buttons_y_offset, button_width, button_height)
    accept_button_rect = pygame.Rect(column_1_x + button_width + padding, stat_buttons_y_offset, button_width, button_height)
    help_button_rect = pygame.Rect(column_1_x + 2 * (button_width + padding), stat_buttons_y_offset, button_width, button_height) 

    show_help_text = False
    help_text_content = (
        "Ability Scores:\n\n"
        "Strength: Affects physical power and carrying capacity.\n"
        "Dexterity: Governs agility, reflexes, and accuracy.\n"
        "Constitution: Represents health and endurance.\n"
        "Intelligence: Determines reasoning and problem-solving.\n"
        "Wisdom: Reflects perception, intuition, and willpower.\n"
        "Charisma: Influences social interactions and leadership.\n\n"
        "Scores are rolled by summing 3 six-sided dice (3d6).\n"
        "Higher scores provide bonuses, lower scores penalties."
    )
    help_text_area_rect = pygame.Rect(SCREEN_WIDTH // 4, SCREEN_HEIGHT // 4, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)

    # Use imported assets_data and load_sprite
    dice_sprite_path = assets_data['sprites']['misc']['dice'] # Path from common_b_s assets_data
    dice_image = None
    if dice_sprite_path and os.path.exists(dice_sprite_path):
        try:
            dice_image = load_sprite(dice_sprite_path) # Use imported load_sprite
            if dice_image: # Scale if loaded successfully
                 dice_image = pygame.transform.smoothscale(dice_image, (80,80))
        except Exception as e:
            print(f"Error loading dice sprite {dice_sprite_path}: {e}")
    else:
        print(f"Dice sprite path not found or invalid in assets_data: {dice_sprite_path}")

    race_names = ['High Elf', 'Wood Elf', 'Halfling', 'Dwarf', 'Human']
    racial_bonuses_text = { # Keeping local for now
        'High Elf': 'Bonuses: +1 Intelligence. Keen intellect and magical aptitude.',
        'Wood Elf': 'Bonuses: +1 Dexterity. Agile, masters of bow and stealth.',
        'Halfling': 'Bonuses: +1 Dexterity. Quick, nimble, surprisingly brave.',
        'Dwarf': 'Bonuses: +1 Constitution. Hardy, resilient, strong earth connection.',
        'Human': 'Bonuses: +1 to any one stat. Versatile and adaptable.'
    }
    race_button_y_start = stat_buttons_y_offset + button_height + padding * 2
    race_buttons = {}
    for i, name in enumerate(race_names):
        rect = pygame.Rect(column_1_x, race_button_y_start + i * (button_height // 1.5 + padding // 2), button_width, button_height // 1.5)
        race_buttons[name] = rect
    race_help_text_y_start = race_buttons[race_names[-1]].bottom + padding

    class_names = ['Warrior', 'Spellblade', 'Wizard', 'Priest', 'Thief', 'Archer']
    class_button_y_start = race_help_text_y_start + font_height * 3 + padding 
    class_buttons = {}
    for i, name in enumerate(class_names):
        rect = pygame.Rect(column_1_x, class_button_y_start + i * (button_height // 1.5 + padding // 2), button_width, button_height // 1.5)
        class_buttons[name] = rect

    while running and not character_finalized: 
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False 
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                
                if name_input_active: 
                    if event.key == pygame.K_RETURN:
                        name_input_active = False
                        print(f"Character name set to: {character_name}")
                    elif event.key == pygame.K_BACKSPACE:
                        character_name = character_name[:-1]
                    else:
                        if len(character_name) < 20 and (event.unicode.isalnum() or event.unicode == ' '):
                            character_name += event.unicode
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: 
                    if show_help_text:
                        if help_button_rect.collidepoint(mouse_pos):
                            show_help_text = not show_help_text
                            name_input_active = False 
                        elif not help_text_area_rect.collidepoint(mouse_pos): 
                            show_help_text = False
                    else:
                        if name_input_rect.collidepoint(mouse_pos):
                            name_input_active = True
                        else:
                            name_input_active = False 
                        
                        if roll_button_rect.collidepoint(mouse_pos):
                            current_stats = {name: roll_ability_helper() for name in ability_names}
                            stats_rolled = True
                            stats_accepted = False 
                            print("Rerolled stats:", current_stats) 
                        
                        elif accept_button_rect.collidepoint(mouse_pos) and stats_rolled:
                            stats_accepted = not stats_accepted 
                            if stats_accepted: print("Stats accepted:", current_stats)
                            else: print("Stats un-accepted.")
                        
                        for race_name, rect in race_buttons.items():
                            if rect.collidepoint(mouse_pos):
                                selected_race = race_name
                                print(f"Race selected: {selected_race}")
                                break 
                        
                        for class_name, rect in class_buttons.items():
                            if rect.collidepoint(mouse_pos):
                                selected_class = class_name
                                print(f"Class selected: {selected_class}")
                                break

                        elif help_button_rect.collidepoint(mouse_pos):
                            show_help_text = not show_help_text
                            name_input_active = False 

        screen.fill(BLACK)
        if background_image:
            screen.blit(background_image, (0,0))
        
        # Use imported draw_text and font
        draw_text(screen, "Character Creation", WHITE, SCREEN_WIDTH // 2 - 100, padding, font=font)

        name_label_y = ui_area_y_start + padding - font_height 
        draw_text(screen, "Character Name:", WHITE, name_input_rect.x, name_label_y, font=font)
        pygame.draw.rect(screen, LIGHT_GRAY if name_input_active else WHITE, name_input_rect, 2 if name_input_active else 1)
        draw_text(screen, character_name, BLACK, name_input_rect.x + 5, name_input_rect.y + 5, font=font, background_color=WHITE)

        stats_title_y = ability_rects[ability_names[0]]["label"].y - padding - font_height // 2
        draw_text(screen, "Ability Scores:", WHITE, column_1_x, stats_title_y, font=font)
        
        if stats_rolled: 
            for name in ability_names:
                label_r, value_r = ability_rects[name]["label"], ability_rects[name]["value"]
                draw_text(screen, f"{name}:", WHITE, label_r.x, label_r.y + 5, font=font)
                pygame.draw.rect(screen, WHITE, value_r, 1) 
                value_color = BLUE if stats_accepted else BLACK
                draw_text(screen, str(current_stats[name]), value_color, value_r.x + 5, value_r.y + 5, font=font, background_color=WHITE)
        else: 
            for name in ability_names:
                label_r, value_r = ability_rects[name]["label"], ability_rects[name]["value"]
                draw_text(screen, f"{name}:", WHITE, label_r.x, label_r.y + 5, font=font)
                pygame.draw.rect(screen, WHITE, value_r, 1)
                draw_text(screen, "0", LIGHT_GRAY, value_r.x + 5, value_r.y + 5, font=font, background_color=WHITE)

        roll_text_render = "Re-roll" if stats_accepted else "Roll"
        pygame.draw.rect(screen, GREEN, roll_button_rect)
        draw_text(screen, roll_text_render, BLACK, roll_button_rect.centerx - len(roll_text_render)*font_height//4, roll_button_rect.centery - font_height//2 +2, font=font)
        
        accept_color = LIGHT_GRAY if not stats_rolled else (GREEN if stats_accepted else BLUE)
        accept_text_render = "Accepted" if stats_accepted else "Accept"
        pygame.draw.rect(screen, accept_color, accept_button_rect)
        draw_text(screen, accept_text_render, BLACK, accept_button_rect.centerx - len(accept_text_render)*font_height//4, accept_button_rect.centery - font_height//2+2, font=font)
        
        pygame.draw.rect(screen, LIGHT_GRAY, help_button_rect) 
        draw_text(screen, "Help", BLACK, help_button_rect.centerx - len("Help")*font_height//4, help_button_rect.centery - font_height//2+2, font=font)

        dice_display_actual_rect = pygame.Rect(column_2_x, ui_area_y_start + padding, 80, 80)
        if dice_image:
            screen.blit(dice_image, dice_display_actual_rect.topleft)
        else: 
            pygame.draw.rect(screen, LIGHT_GRAY, dice_display_actual_rect)
            draw_text(screen, "Dice", BLACK, dice_display_actual_rect.centerx - 20, dice_display_actual_rect.centery - 10, font=font)
        
        race_section_y_start = dice_display_actual_rect.bottom + padding * 2
        draw_text(screen, "Select Race:", WHITE, column_2_x, race_section_y_start, font=font)
        current_race_y = race_section_y_start + font_height + padding // 2
        for name in race_names:
            button_rect = pygame.Rect(column_2_x, current_race_y, button_width, button_height // 1.5)
            race_buttons[name] = button_rect 
            highlight = (selected_race == name)
            btn_color = GREEN if highlight else BLUE
            pygame.draw.rect(screen, btn_color, button_rect)
            pygame.draw.rect(screen, WHITE, button_rect, 1 if not highlight else 2) 
            draw_text(screen, name, BLACK, button_rect.centerx - len(name)*font_height//4.5, button_rect.centery - font_height//2.5, font=font)
            current_race_y += button_height // 1.5 + padding // 2
        
        race_help_display_y = current_race_y + padding
        # Create a smaller font for racial bonus text if desired, or use the main font
        small_font = pygame.font.Font(None, int(font_height * 0.9)) # Example: 90% of main font size
        if selected_race and selected_race in racial_bonuses_text:
            lines = racial_bonuses_text[selected_race].split('. ')
            for i, line in enumerate(lines):
                draw_text(screen, line + ('.' if not line.endswith('.') and i < len(lines)-1 else ''), WHITE, column_2_x, race_help_display_y + i * int(font_height*0.8), font=small_font)
        else:
            draw_text(screen, "Select a race to see details.", LIGHT_GRAY, column_2_x, race_help_display_y, font=small_font)

        class_section_y_start = race_help_display_y + (font_height * 0.8 * 2) + padding * 2 
        draw_text(screen, "Select Class:", WHITE, column_2_x, class_section_y_start, font=font)
        current_class_y = class_section_y_start + font_height + padding // 2
        for name in class_names:
            button_rect = pygame.Rect(column_2_x, current_class_y, button_width, button_height // 1.5)
            class_buttons[name] = button_rect 
            highlight = (selected_class == name)
            btn_color = GREEN if highlight else BLUE
            pygame.draw.rect(screen, btn_color, button_rect)
            pygame.draw.rect(screen, WHITE, button_rect, 1 if not highlight else 2) 
            draw_text(screen, name, BLACK, button_rect.centerx - len(name)*font_height//4.5, button_rect.centery - font_height//2.5, font=font)
            current_class_y += button_height // 1.5 + padding // 2

        ready_button_active = bool(character_name.strip() and stats_accepted and selected_race and selected_class)
        ready_button_color = GREEN if ready_button_active else LIGHT_GRAY
        ready_button_rect = pygame.Rect((SCREEN_WIDTH - button_width) // 2, SCREEN_HEIGHT - button_height - padding, button_width, button_height)
        
        pygame.draw.rect(screen, ready_button_color, ready_button_rect)
        ready_text_color = BLACK if ready_button_active else DARK_GRAY 
        draw_text(screen, "Ready", ready_text_color, ready_button_rect.centerx - len("Ready")*font_height//4, ready_button_rect.centery - font_height//2 + 2, font=font)
        
        if ready_button_active and ready_button_rect.collidepoint(mouse_pos) and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not show_help_text:
             character_finalized = True 
             print("Character creation complete! Finalizing...")

        if show_help_text:
            overlay_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay_surface.fill((0, 0, 0, 180)) 
            screen.blit(overlay_surface, (0,0))
            
            pygame.draw.rect(screen, LIGHT_GRAY, help_text_area_rect)
            pygame.draw.rect(screen, WHITE, help_text_area_rect, 2) 

            help_lines = help_text_content.split('\n')
            line_y = help_text_area_rect.y + padding
            for line in help_lines:
                draw_text(screen, line, BLACK, help_text_area_rect.x + padding, line_y, font=font) # Use imported font
                line_y += font_height # Use imported font's height

        pygame.display.flip()
        clock.tick(60)

    if character_finalized: 
        # Use imported Player and Dungeon classes
        created_player = Player(name=character_name.strip(), race=selected_race, char_class=selected_class, abilities=current_stats, start_position=[0,0], sprite=None) # start_pos and sprite are placeholders for common_b_s.Player
        
        created_player.apply_race_bonus() 
        created_player.level = 1
        created_player.hit_points = created_player.roll_hit_points() 
        created_player.max_hit_points = created_player.hit_points
        created_player.spell_points = created_player.calculate_spell_points() 
        created_player.ac = created_player.calculate_ac() 
        created_player.gold = random.randint(20, 50) 

        initial_dungeon = Dungeon(width=20, height=15, level=1) 
        print(f"Player '{created_player.name}' (Level {created_player.level} {created_player.race} {created_player.char_class}) created successfully.")
        print(f"HP: {created_player.hit_points}, SP: {created_player.spell_points}, AC: {created_player.ac}, Gold: {created_player.gold}")
        print(f"Initial Dungeon (Level {initial_dungeon.level}) created.")
        return created_player, initial_dungeon
    
    print("Exiting character creation screen without finalizing.")
    return None, None 

if __name__ == '__main__':
    pygame.init()
    if not pygame.font.get_init(): pygame.font.init()
    
    # Font is now imported from common_b_s, so direct initialization here is not needed unless fallback
    if font is None: # Should not happen if common_b_s.font is valid
        print(f"CRITICAL: Font from common_b_s is None. Exiting.")
        pygame.quit()
        sys.exit()
    
    # DARK_GRAY is also imported from common_b_s

    try:
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Character Creation Test")
        clock = pygame.time.Clock()
        
        created_player, initial_dungeon = character_creation_screen(screen, clock)
        
        if created_player and initial_dungeon:
            print(f"\n--- Character Creation Successful ---")
            print(f"Name: {created_player.name}, Race: {created_player.race}, Class: {created_player.char_class}")
            print(f"Level: {created_player.level}, HP: {created_player.hit_points}/{created_player.max_hit_points}, SP: {created_player.spell_points}, AC: {created_player.ac}")
            print(f"Abilities: {created_player.abilities}")
            print(f"Gold: {created_player.gold}")
            print(f"Initial Dungeon: Level {initial_dungeon.level}, Size: {initial_dungeon.width}x{initial_dungeon.height}, Start: {initial_dungeon.start_position}")
        else:
            print("\n--- Character creation was exited or not completed. ---")

    except pygame.error as e:
        print(f"Pygame Error in __main__: {e}")
    except Exception as e:
        print(f"General Error in __main__: {e}")
    finally:
        pygame.quit()
        sys.exit()
