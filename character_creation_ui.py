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
    actual_screen_width, actual_screen_height = screen.get_size()

    # Load background image (scaled to actual screen size)
    background_path_from_assets = assets_data.get("sprites", {}).get("background", {}).get("character_creation_bg")
    fallback_background_path = "/Users/williammarcellino/Documents/Fantasy_Game/Fantasy_Game_Art_Assets/Misc/B&S_UI_background.png"
    background_image = None
    if background_path_from_assets and os.path.exists(background_path_from_assets):
        try:
            background_image = pygame.image.load(background_path_from_assets).convert()
            background_image = pygame.transform.scale(background_image, (actual_screen_width, actual_screen_height))
            print(f"Loaded background from assets_data: {background_path_from_assets}")
        except pygame.error as e:
            print(f"Error loading background from assets_data: {e}. Trying fallback.")
            background_image = None
    if not background_image and os.path.exists(fallback_background_path):
        try:
            background_image = pygame.image.load(fallback_background_path).convert()
            background_image = pygame.transform.scale(background_image, (actual_screen_width, actual_screen_height))
            print(f"Loaded background from fallback path: {fallback_background_path}")
        except pygame.error as e:
            print(f"Error loading background from fallback: {e}")
            background_image = None
    if not background_image:
        print("Background image not found. Using black background.")

    # Core state variables
    character_name = ""
    current_stats = {name: roll_ability_helper() for name in ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"]}
    stats_rolled = True
    stats_accepted = False
    selected_race = None
    selected_class = None
    character_finalized = False
    name_input_active = False
    ability_names = list(current_stats.keys())
    show_help_text = False

    # UI Layout Constants
    font_height = font.get_height()
    padding = 20
    input_field_height = font_height + 10
    button_width = 180 # Made buttons slightly wider
    button_height = font_height + 20

    # Top banner area (uses aliased SCREEN_HEIGHT from HUB)
    ui_top_banner_height = int(SCREEN_HEIGHT * 0.20)
    vertical_shift_amount = int(actual_screen_height * 0.25) # Main content shift

    # Column X positions (relative to actual_screen_width for responsiveness)
    column_1_x = int(actual_screen_width * 0.05) # Name, Stats
    column_2_x = int(actual_screen_width * 0.40) # Dice, Race
    column_3_x = column_2_x + button_width + padding * 3 # Class (to the right of Race)

    # Name Input (shifted)
    name_label_y = ui_top_banner_height + padding + vertical_shift_amount - font_height
    name_input_rect = pygame.Rect(column_1_x, ui_top_banner_height + padding + vertical_shift_amount, input_field_width, input_field_height)

    # Stats Section (shifted, below Name)
    stats_title_y = name_input_rect.bottom + padding * 2
    ability_rects = {}
    current_y_offset_for_stats = stats_title_y + font_height + padding // 2
    for i, name in enumerate(ability_names):
        label_rect = pygame.Rect(column_1_x, current_y_offset_for_stats + i * (input_field_height + padding // 2), input_field_width // 2, input_field_height)
        value_rect = pygame.Rect(column_1_x + input_field_width // 2 + padding // 2, current_y_offset_for_stats + i * (input_field_height + padding // 2), input_field_width // 2 - padding // 2, input_field_height)
        ability_rects[name] = {"label": label_rect, "value": value_rect}

    last_stat_y_bottom = ability_rects[ability_names[-1]]["value"].bottom
    stat_buttons_y_offset = last_stat_y_bottom + padding * 2
    roll_button_rect = pygame.Rect(column_1_x, stat_buttons_y_offset, button_width, button_height)
    accept_button_rect = pygame.Rect(column_1_x + button_width + padding, stat_buttons_y_offset, button_width, button_height)
    # Adjusted help button X to avoid overlap if column_1_x is small or button_width is large
    help_button_x = accept_button_rect.right + padding
    if help_button_x + button_width > column_2_x - padding: # Check if it overlaps with next column
        help_button_x = column_1_x # Stack it below if no space
        stat_buttons_y_offset += button_height + padding
        roll_button_rect.y = stat_buttons_y_offset
        accept_button_rect.y = stat_buttons_y_offset
    help_button_rect = pygame.Rect(help_button_x, stat_buttons_y_offset, button_width, button_height)

    # Help Text Area (centered on actual screen)
    help_text_content = (
        "Ability Scores:\n\n"
        "Strength: Affects physical power and carrying capacity.\nDexterity: Governs agility, reflexes, and accuracy.\n"
        "Constitution: Represents health and endurance.\nIntelligence: Determines reasoning and problem-solving.\n"
        "Wisdom: Reflects perception, intuition, and willpower.\nCharisma: Influences social interactions and leadership.\n\n"
        "Scores are rolled by summing 3 six-sided dice (3d6).\nHigher scores provide bonuses, lower scores penalties."
    )
    help_text_area_rect = pygame.Rect(actual_screen_width // 4, actual_screen_height // 4, actual_screen_width // 2, actual_screen_height // 2)

    # Dice Sprite (shifted down)
    dice_sprite_path = assets_data['sprites']['misc']['dice']
    dice_image = None
    if dice_sprite_path and os.path.exists(dice_sprite_path):
        try:
            dice_image = load_sprite(dice_sprite_path)
            if dice_image: dice_image = pygame.transform.smoothscale(dice_image, (80, 80))
        except Exception as e: print(f"Error loading dice sprite {dice_sprite_path}: {e}")
    else: print(f"Dice sprite path not found: {dice_sprite_path}")
    dice_display_actual_rect = pygame.Rect(column_2_x, ui_top_banner_height + padding + vertical_shift_amount, 80, 80)

    # Race Selection (shifted down, in column_2_x)
    race_names = ['High Elf', 'Wood Elf', 'Halfling', 'Dwarf', 'Human']
    racial_bonuses_text = {
        'High Elf': 'Bonuses: +1 Intelligence. Keen intellect and magical aptitude.',
        'Wood Elf': 'Bonuses: +1 Dexterity. Agile, masters of bow and stealth.',
        'Halfling': 'Bonuses: +1 Dexterity. Quick, nimble, surprisingly brave.',
        'Dwarf': 'Bonuses: +1 Constitution. Hardy, resilient, strong earth connection.',
        'Human': 'Bonuses: +1 to any one stat. Versatile and adaptable.'
    }
    race_section_y_start = dice_display_actual_rect.bottom + padding * 2
    race_buttons = {}
    current_race_y_for_buttons = race_section_y_start + font_height + padding // 2
    for i, name in enumerate(race_names):
        rect = pygame.Rect(column_2_x, current_race_y_for_buttons + i * (button_height // 1.5 + padding // 2), button_width, button_height // 1.5)
        race_buttons[name] = rect

    # Class Selection (shifted down, in column_3_x, aligned vertically with Race label)
    class_names = ['Warrior', 'Spellblade', 'Wizard', 'Priest', 'Thief', 'Archer']
    class_section_label_y = race_section_y_start # Align Y with "Select Race" label
    class_buttons = {}
    current_class_y_for_buttons = class_section_label_y + font_height + padding // 2
    for i, name in enumerate(class_names):
        rect = pygame.Rect(column_3_x, current_class_y_for_buttons + i * (button_height // 1.5 + padding // 2), button_width, button_height // 1.5)
        class_buttons[name] = rect

    running = True
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
                    else: # This is when show_help_text is False
                        # Determine what was clicked and manage name_input_active state

                        # Default to deactivating name input unless the name input field itself is clicked
                        # This handles clicks on non-interactive areas.
                        # If a button is clicked, it will explicitly set name_input_active = False.

                        clicked_on_name_input = name_input_rect.collidepoint(mouse_pos)

                        if clicked_on_name_input:
                            name_input_active = True
                        # Roll Button
                        elif roll_button_rect.collidepoint(mouse_pos):
                            current_stats = {name: roll_ability_helper() for name in ability_names}
                            stats_rolled = True
                            stats_accepted = False
                            print("Rerolled stats:", current_stats)
                            name_input_active = False
                        # Accept Stats Button
                        elif accept_button_rect.collidepoint(mouse_pos) and stats_rolled:
                            stats_accepted = not stats_accepted
                            if stats_accepted: print("Stats accepted:", current_stats)
                            else: print("Stats un-accepted.")
                            name_input_active = False
                        # Help Button (main help)
                        elif help_button_rect.collidepoint(mouse_pos):
                            show_help_text = not show_help_text # Toggle help
                            name_input_active = False
                        # If none of the main action buttons were clicked, check selection buttons (Race/Class)
                        else:
                            race_button_clicked = False
                            for race_name, rect in race_buttons.items():
                                if rect.collidepoint(mouse_pos):
                                    selected_race = race_name
                                    print(f"Race selected: {selected_race}")
                                    name_input_active = False
                                    race_button_clicked = True
                                    break

                            if not race_button_clicked: # Only check class if a race wasn't clicked
                                class_button_clicked = False
                                for class_name, rect in class_buttons.items():
                                    if rect.collidepoint(mouse_pos):
                                        selected_class = class_name
                                        print(f"Class selected: {selected_class}")
                                        name_input_active = False
                                        class_button_clicked = True
                                        break
                                # If no button was clicked at all (neither main action nor selection)
                                # and it wasn't a click on the name input field itself, then deactivate name input.
                                if not race_button_clicked and not class_button_clicked and not clicked_on_name_input:
                                    name_input_active = False

        screen.fill(BLACK)
        if background_image:
            screen.blit(background_image, (0,0))

        # Draw Title (respects ui_top_banner_height, uses aliased SCREEN_WIDTH from HUB for centering within that banner area)
        title_text_surface = font.render("Character Creation", True, WHITE)
        title_x = (SCREEN_WIDTH - title_text_surface.get_width()) // 2 # Centering based on HUB_SCREEN_WIDTH for banner
        draw_text(screen, "Character Creation", WHITE, title_x, padding)


        # Name Input - uses name_label_y and name_input_rect which are now correctly shifted
        draw_text(screen, "Character Name:", WHITE, name_input_rect.x, name_label_y)
        pygame.draw.rect(screen, DARK_GRAY, name_input_rect)
        pygame.draw.rect(screen, WHITE if name_input_active else LIGHT_GRAY, name_input_rect, 2 if name_input_active else 1)
        draw_text(screen, character_name, WHITE, name_input_rect.x + 5, name_input_rect.y + 5)

        # Stats Section - uses stats_title_y and ability_rects which are now correctly shifted
        draw_text(screen, "Ability Scores:", WHITE, column_1_x, stats_title_y)
        if stats_rolled:
            for name in ability_names:
                label_r, value_r = ability_rects[name]["label"], ability_rects[name]["value"]
                draw_text(screen, f"{name}:", WHITE, label_r.x, label_r.y + 5)
                pygame.draw.rect(screen, DARK_GRAY, value_r)
                pygame.draw.rect(screen, WHITE, value_r, 1)
                draw_text(screen, str(current_stats[name]), WHITE, value_r.x + 5, value_r.y + 5)
        else:
            for name in ability_names:
                label_r, value_r = ability_rects[name]["label"], ability_rects[name]["value"]
                draw_text(screen, f"{name}:", WHITE, label_r.x, label_r.y + 5)
                pygame.draw.rect(screen, DARK_GRAY, value_r)
                pygame.draw.rect(screen, WHITE, value_r, 1)
                draw_text(screen, "0", LIGHT_GRAY, value_r.x + 5, value_r.y + 5)

        # Stat Buttons (Roll, Accept, Help) - use their pre-calculated rects
        roll_text_render = "Re-roll" if stats_accepted else "Roll"
        pygame.draw.rect(screen, GREEN, roll_button_rect)
        draw_text(screen, roll_text_render, BLACK, roll_button_rect.centerx - font.size(roll_text_render)[0]//2, roll_button_rect.centery - font_height//2 +2)

        accept_color = LIGHT_GRAY if not stats_rolled else (GREEN if stats_accepted else BLUE)
        accept_text_render = "Accepted" if stats_accepted else "Accept"
        pygame.draw.rect(screen, accept_color, accept_button_rect)
        draw_text(screen, accept_text_render, BLACK, accept_button_rect.centerx - font.size(accept_text_render)[0]//2, accept_button_rect.centery - font_height//2+2)

        pygame.draw.rect(screen, LIGHT_GRAY, help_button_rect)
        draw_text(screen, "Help", BLACK, help_button_rect.centerx - font.size("Help")[0]//2, help_button_rect.centery - font_height//2+2)

        # Dice Sprite (uses dice_display_actual_rect which is now correctly shifted)
        if dice_image:
            screen.blit(dice_image, dice_display_actual_rect.topleft)
        else:
            pygame.draw.rect(screen, LIGHT_GRAY, dice_display_actual_rect)
            draw_text(screen, "Dice", BLACK, dice_display_actual_rect.centerx - font.size("Dice")[0]//2, dice_display_actual_rect.centery - font_height//2)

        # Race Selection (uses race_section_y_start, current_race_y_for_buttons, column_2_x)
        draw_text(screen, "Select Race:", WHITE, column_2_x, race_section_y_start)
        # current_race_y_for_buttons was initialized before loop, use it directly for button rects
        for name_idx, race_name_val in enumerate(race_names): # Use a different name to avoid conflict
            button_rect = race_buttons[race_name_val] # Get the rect that was defined with Y positions in the init phase
            highlight = (selected_race == race_name_val)
            btn_color = GREEN if highlight else BLUE
            pygame.draw.rect(screen, btn_color, button_rect)
            pygame.draw.rect(screen, WHITE, button_rect, 1 if not highlight else 2)
            draw_text(screen, race_name_val, BLACK, button_rect.centerx - font.size(race_name_val)[0]//2, button_rect.centery - font_height//2.5) # Centered text

        # Race Help Text Display
        # actual_race_help_text_y_start needs to be calculated based on the last race button's bottom
        if race_buttons: # Ensure race_buttons is not empty
            last_race_button_bottom = race_buttons[race_names[-1]].bottom
            actual_race_help_text_y_start = last_race_button_bottom + padding
            if selected_race and selected_race in racial_bonuses_text:
                lines = racial_bonuses_text[selected_race].split('. ')
                for i, line in enumerate(lines):
                    draw_text(screen, line + ('.' if not line.endswith('.') and i < len(lines)-1 else ''), WHITE, column_2_x, actual_race_help_text_y_start + i * int(font_height*0.9)) # Slightly smaller line height
            else:
                draw_text(screen, "Select a race to see details.", LIGHT_GRAY, column_2_x, actual_race_help_text_y_start)

        # Class Selection (uses class_section_label_y, current_class_y_for_buttons, column_3_x)
        draw_text(screen, "Select Class:", WHITE, column_3_x, class_section_label_y)
        # current_class_y_for_buttons was initialized before loop
        for name_idx, class_name_val in enumerate(class_names): # Use a different name
            button_rect = class_buttons[class_name_val] # Get the rect that was defined with Y positions in the init phase
            highlight = (selected_class == class_name_val)
            btn_color = GREEN if highlight else BLUE
            pygame.draw.rect(screen, btn_color, button_rect)
            pygame.draw.rect(screen, WHITE, button_rect, 1 if not highlight else 2)
            draw_text(screen, class_name_val, BLACK, button_rect.centerx - font.size(class_name_val)[0]//2, button_rect.centery - font_height//2.5) # Centered text

        # Ready Button (uses actual_screen_width/height for positioning)
        ready_button_active = bool(character_name.strip() and stats_accepted and selected_race and selected_class)
        ready_button_color = GREEN if ready_button_active else LIGHT_GRAY
        ready_button_rect = pygame.Rect((actual_screen_width - button_width) // 2, actual_screen_height - button_height - padding, button_width, button_height)

        pygame.draw.rect(screen, ready_button_color, ready_button_rect)
        ready_text_color = BLACK if ready_button_active else DARK_GRAY
        draw_text(screen, "Ready", ready_text_color, ready_button_rect.centerx - font.size("Ready")[0]//2, ready_button_rect.centery - font_height//2 + 2)

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
                draw_text(screen, line, BLACK, help_text_area_rect.x + padding, line_y) # Use imported font
                line_y += font_height # Use imported font's height

        pygame.display.flip()
        clock.tick(60)

    if character_finalized:
        # Convert keys in current_stats to lowercase for the Player class
        lowercase_abilities = {key.lower(): value for key, value in current_stats.items()}

        # Use imported Player and Dungeon classes
        created_player = Player(name=character_name.strip(), race=selected_race, char_class=selected_class, abilities=lowercase_abilities, start_position=[0,0], sprite=None) # start_pos and sprite are placeholders for common_b_s.Player

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
