#!/usr/bin/env python
# coding: utf-8

"""
Spell System Bridge for Blade & Sigil
This module provides compatibility functions to bridge the old spell casting
system with the new data-driven system.
"""

import logging
import os
import sys

# Add relative path for imports
sys.path.append(os.path.dirname(__file__))
from spell_helpers import *
from spell_system import cast_spell as new_cast_spell
from effect_manager import effect_manager

# Set up logging
logger = logging.getLogger(__name__)

# Global variables
SPELLS_FILE = os.path.join(os.path.dirname(__file__), "spells.json")
loaded_spells_data = None

def load_spells():
    """Load spells data from the spells.json file."""
    global loaded_spells_data
    if loaded_spells_data is None:
        try:
            loaded_spells_data = load_spells_data(SPELLS_FILE)
            logger.info(f"Loaded {len(loaded_spells_data.get('spells', []))} spells from {SPELLS_FILE}")
        except Exception as e:
            logger.error(f"Failed to load spells: {e}")
            loaded_spells_data = {"spells": []}
    return loaded_spells_data

def cast_spell_bridge(caster, target, spell_name, dungeon):
    """
    Bridge function to replace the old cast_spell function with minimal code changes.
    
    Args:
        caster: Character casting the spell
        target: Target character or position
        spell_name: Name of the spell to cast
        dungeon: Dungeon object
        
    Returns:
        List of message strings
    """
    # Ensure spells are loaded
    spells_data = load_spells()
    
    # Call the new cast_spell function
    return new_cast_spell(caster, target, spell_name, dungeon, spells_data)

def update_spells_dialogue(screen, player, clock):
    """
    Enhanced version of the spells_dialogue function that works with the new spell system.
    
    Args:
        screen: Pygame screen
        player: Player character
        clock: Pygame clock
        
    Returns:
        Selected spell data dictionary or None if cancelled
    """
    print("DEBUG: Inside update_spells_dialogue function!")
    import pygame
    
    # Ensure spells are loaded
    spells_data = load_spells()
    
    # Use the title version of the player's class
    class_key = player.char_class.title()
    
    # Group spells by level
    spells_by_level = {}
    for spell in spells_data.get("spells", []):
        if any(cls.title() == class_key for cls in spell.get("classes", [])) and player.level >= spell.get("level", 1):
            level = spell.get("level", 1)
            if level not in spells_by_level:
                spells_by_level[level] = []
            spells_by_level[level].append(spell)
    
    # Create a flattened list of available spells grouped by level
    available_spells = []
    for level in sorted(spells_by_level.keys()):
        available_spells.extend(spells_by_level[level])
    
    # Define dialogue panel properties
    dialogue_rect = pygame.Rect(50, 50, 600, 500)  # Larger panel for descriptions and scrolling
    panel_color = (30, 30, 30)
    border_color = (200, 200, 200)
    title_font = pygame.font.Font(None, 28)
    font = pygame.font.Font(None, 24)
    small_font = pygame.font.Font(None, 20)
    
    selected_spell = None
    waiting = True
    
    # Scrolling parameters
    highlighted_index = 0
    scroll_position = 0
    visible_spells = 10  # Number of spells visible at once
    
    # Calculate max scroll position
    max_scroll = max(0, len(available_spells) - visible_spells)
    
    while waiting:
        # Process events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                import sys
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                # Check if a number key 1-9 is pressed
                if pygame.K_1 <= event.key <= pygame.K_9:
                    index = event.key - pygame.K_1 + scroll_position
                    if index < len(available_spells):
                        selected_spell = available_spells[index]
                        waiting = False
                # Allow navigation with arrow keys
                elif event.key == pygame.K_UP:
                    highlighted_index = max(0, highlighted_index - 1)
                    # Scroll up if needed
                    if highlighted_index < scroll_position:
                        scroll_position = highlighted_index
                elif event.key == pygame.K_DOWN:
                    highlighted_index = min(len(available_spells) - 1, highlighted_index + 1)
                    # Scroll down if needed
                    if highlighted_index >= scroll_position + visible_spells:
                        scroll_position = highlighted_index - visible_spells + 1
                elif event.key == pygame.K_PAGEUP:
                    scroll_position = max(0, scroll_position - visible_spells)
                    highlighted_index = scroll_position
                elif event.key == pygame.K_PAGEDOWN:
                    scroll_position = min(max_scroll, scroll_position + visible_spells)
                    highlighted_index = scroll_position
                elif event.key == pygame.K_RETURN:
                    if 0 <= highlighted_index < len(available_spells):
                        selected_spell = available_spells[highlighted_index]
                        waiting = False
                # Cancel with Escape
                elif event.key == pygame.K_ESCAPE:
                    waiting = False
        
        # Draw the dialogue panel
        pygame.draw.rect(screen, panel_color, dialogue_rect)
        pygame.draw.rect(screen, border_color, dialogue_rect, 2)
        
        # Header text
        header = title_font.render(f"Available Spells ({player.spell_points}/{player.calculate_spell_points()} SP)", True, (255, 255, 255))
        screen.blit(header, (dialogue_rect.x + 10, dialogue_rect.y + 10))
        
        # Draw level separators and spells
        y_offset = dialogue_rect.y + 50
        current_level = None
        
        # Show only the visible portion based on scroll position
        visible_range = range(scroll_position, min(scroll_position + visible_spells, len(available_spells)))
        
        for i in visible_range:
            spell = available_spells[i]
            spell_level = spell.get("level", 1)
            
            # Add level header if this is a new level
            if spell_level != current_level:
                current_level = spell_level
                level_text = f"--- Level {current_level} Spells ---"
                level_surface = font.render(level_text, True, (200, 200, 100))
                screen.blit(level_surface, (dialogue_rect.x + (dialogue_rect.width - level_surface.get_width()) // 2, y_offset))
                y_offset += 25
            
            # Determine if this spell is highlighted
            is_highlighted = (i == highlighted_index)
            
            # Background for highlighted spell
            if is_highlighted:
                highlight_rect = pygame.Rect(dialogue_rect.x + 5, y_offset - 2, 
                                          dialogue_rect.width - 10, 26)
                pygame.draw.rect(screen, (60, 60, 100), highlight_rect)
            
            # Get spell details
            spell_name = spell.get("name", "Unknown")
            spell_type = spell.get("type", "unknown").capitalize()
            spell_cost = get_spell_cost(spell)
            
            # Format the spell entry with display index (1-9)
            display_index = i - scroll_position + 1
            if display_index <= 9:
                spell_text = f"{display_index}. {spell_name} ({spell_cost} SP)"
            else:
                spell_text = f"   {spell_name} ({spell_cost} SP)"
                
            color = (255, 255, 255) if player.spell_points >= spell_cost else (150, 150, 150)
            
            text_surface = font.render(spell_text, True, color)
            screen.blit(text_surface, (dialogue_rect.x + 20, y_offset))
            
            # Add spell type indicator
            type_colors = {
                "Damage": (255, 100, 100),    # Red for damage
                "Healing": (100, 255, 100),   # Green for healing
                "Buff": (100, 100, 255),      # Blue for buffs
                "Utility": (255, 255, 100)    # Yellow for utility
            }
            type_color = type_colors.get(spell_type, (200, 200, 200))
            type_text = small_font.render(spell_type, True, type_color)
            screen.blit(type_text, (dialogue_rect.x + dialogue_rect.width - 120, y_offset))
            
            y_offset += 30
        
        # Draw scroll indicators if needed
        if scroll_position > 0:
            pygame.draw.polygon(screen, (200, 200, 200), 
                             [(dialogue_rect.x + dialogue_rect.width - 30, dialogue_rect.y + 40),
                              (dialogue_rect.x + dialogue_rect.width - 20, dialogue_rect.y + 30),
                              (dialogue_rect.x + dialogue_rect.width - 10, dialogue_rect.y + 40)])
        
        if scroll_position < max_scroll:
            pygame.draw.polygon(screen, (200, 200, 200), 
                             [(dialogue_rect.x + dialogue_rect.width - 30, y_offset + 10),
                              (dialogue_rect.x + dialogue_rect.width - 20, y_offset + 20),
                              (dialogue_rect.x + dialogue_rect.width - 10, y_offset + 10)])
        
        # Display description of highlighted spell
        if 0 <= highlighted_index < len(available_spells):
            spell = available_spells[highlighted_index]
            
            # Draw separator line
            separator_y = dialogue_rect.y + dialogue_rect.height - 120
            pygame.draw.line(screen, border_color, 
                          (dialogue_rect.x + 20, separator_y),
                          (dialogue_rect.x + dialogue_rect.width - 20, separator_y))
            
            # Description panel background
            desc_panel = pygame.Rect(dialogue_rect.x + 10, separator_y + 5, 
                                   dialogue_rect.width - 20, 80)
            pygame.draw.rect(screen, (40, 40, 50), desc_panel)
            
            # Spell details
            detail_y = separator_y + 10
            
            # Description - handle word wrapping for long descriptions
            description = spell.get("description", "No description available.")
            max_width = dialogue_rect.width - 40
            words = description.split()
            lines = []
            current_line = ""
            
            for word in words:
                test_line = current_line + " " + word if current_line else word
                if small_font.size(test_line)[0] <= max_width:
                    current_line = test_line
                else:
                    lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)
            
            # Draw description with simple word wrap
            for i, line in enumerate(lines[:2]):  # Show max 2 lines
                desc_text = small_font.render(line, True, (200, 200, 200))
                screen.blit(desc_text, (dialogue_rect.x + 20, detail_y + i * 20))
            
            detail_y += max(1, len(lines)) * 20 + 5
            
            # Effect type and targeting info
            effect_type = spell.get("effect_type", "Unknown")
            range_type = spell.get("range_type", "Unknown")
            targets = spell.get("targets", "Unknown")
            
            targeting_text = f"Type: {effect_type} | Range: {range_type} | Targets: {targets}"
            target_surface = small_font.render(targeting_text, True, (180, 180, 180))
            screen.blit(target_surface, (dialogue_rect.x + 20, detail_y))
            detail_y += 20
            
            # Damage/healing info if applicable
            if "damage_dice" in spell:
                damage_text = f"Damage: {spell.get('damage_dice')}"
                damage_surface = small_font.render(damage_text, True, (255, 150, 150))
                screen.blit(damage_surface, (dialogue_rect.x + 20, detail_y))
            elif "healing_dice" in spell:
                healing_text = f"Healing: {spell.get('healing_dice')}"
                healing_surface = small_font.render(healing_text, True, (150, 255, 150))
                screen.blit(healing_surface, (dialogue_rect.x + 20, detail_y))
        
        # Draw instructions
        instructions = small_font.render("↑↓: Navigate | Enter: Select | PgUp/PgDn: Scroll | Esc: Cancel", 
                                      True, (180, 180, 180))
        screen.blit(instructions, (dialogue_rect.x + 20, dialogue_rect.y + dialogue_rect.height - 25))
        
        pygame.display.flip()
        clock.tick(30)
    
    return selected_spell

def process_status_effects():
    """
    Process all active status effects at the start of a new turn.
    Call this function at the beginning of each game turn.
    
    Returns:
        List of messages generated during processing
    """
    return effect_manager.process_turn()

def apply_status_effect(target, effect):
    """
    Apply a status effect to a target.
    
    Args:
        target: Character to apply effect to
        effect: StatusEffect object
    
    Returns:
        bool: True if effect was successfully applied
    """
    return effect_manager.add_effect(target, effect)

def get_character_effects(character):
    """
    Get all active effects for a character.
    
    Args:
        character: Character to get effects for
        
    Returns:
        List of (effect, turns_remaining) tuples
    """
    return effect_manager.get_active_effects(character)

def add_effect_rendering_to_ui(draw_playable_area_function):
    """
    Modifies the draw_playable_area function to include status effect rendering.
    This is an example of how you might integrate effect rendering with the UI.
    
    This function is not meant to be called directly, but illustrates how
    the integration might be done.
    """
    from effect_manager import render_status_effects
    
    def enhanced_draw_playable_area(screen, game_dungeon, player):
        # Call the original function first
        draw_playable_area_function(screen, game_dungeon, player)
        
        # Render player status effects
        player_pos = (player.position[0], player.position[1] - 20)  # Above player
        render_status_effects(screen, player, player_pos[0], player_pos[1])
        
        # Render monster status effects
        for monster in game_dungeon.monsters:
            if monster.position and not getattr(monster, 'is_dead', False):
                monster_pos = (monster.position[0], monster.position[1] - 20)  # Above monster
                render_status_effects(screen, monster, monster_pos[0], monster_pos[1])
    
    return enhanced_draw_playable_area