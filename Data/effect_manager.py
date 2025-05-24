#!/usr/bin/env python
# coding: utf-8

"""
Status Effect Manager for Blade & Sigil
This module provides functionality to track and manage temporary status
effects on characters, such as buffs, debuffs, and damage over time.
"""

import logging
import pygame

# Set up logging
logger = logging.getLogger(__name__)

class StatusEffectManager:
    """Manages status effects across all characters in the game."""
    
    def __init__(self):
        # Dictionary mapping character to their active effects
        # Format: {character_id: [effect1, effect2, ...]}
        self.active_effects = {}
        # Game turn counter
        self.current_turn = 0
    
    def add_effect(self, target, effect):
        """
        Apply a status effect to a target.
        
        Args:
            target: Character receiving the effect
            effect: StatusEffect object to apply
        
        Returns:
            bool: True if effect was successfully applied
        """
        # Generate a unique ID for the target if we don't have one
        target_id = id(target)
        
        # Initialize effects list for this target if needed
        if target_id not in self.active_effects:
            self.active_effects[target_id] = []
        
        # Set the application time for the effect
        effect.applied_at = self.current_turn
        
        # Call the effect's apply method
        effect.on_apply(target)
        
        # Add to active effects
        self.active_effects[target_id].append((effect, target))
        
        logger.debug(f"Applied effect {effect.name} to {target.name}")
        return True
    
    def process_turn(self):
        """
        Process the effects for all characters at the start of a new turn.
        
        Returns:
            List of messages generated during processing
        """
        self.current_turn += 1
        messages = []
        
        # For each character, process their active effects
        for target_id, effects_list in list(self.active_effects.items()):
            updated_effects = []
            
            for effect, target in effects_list:
                # Calculate how many turns this effect has been active
                turns_active = self.current_turn - effect.applied_at
                
                # Check if effect has expired
                if turns_active >= effect.duration:
                    # Effect has expired, call on_remove
                    effect.on_remove(target)
                    messages.append(f"{target.name} is no longer affected by {effect.name}")
                else:
                    # Effect is still active, call on_turn
                    effect.on_turn(target)
                    updated_effects.append((effect, target))
            
            # Update the list of active effects for this target
            if updated_effects:
                self.active_effects[target_id] = updated_effects
            else:
                # Remove the target from active_effects if they have no more effects
                del self.active_effects[target_id]
        
        return messages
    
    def remove_effect(self, target, effect_name):
        """
        Remove a named effect from a target.
        
        Args:
            target: Character to remove effect from
            effect_name: Name of the effect to remove
        
        Returns:
            bool: True if effect was found and removed
        """
        target_id = id(target)
        
        if target_id not in self.active_effects:
            return False
        
        updated_effects = []
        effect_removed = False
        
        for effect, effect_target in self.active_effects[target_id]:
            if effect.name == effect_name:
                # Call on_remove for the effect being removed
                effect.on_remove(target)
                effect_removed = True
            else:
                updated_effects.append((effect, effect_target))
        
        if updated_effects:
            self.active_effects[target_id] = updated_effects
        else:
            del self.active_effects[target_id]
        
        return effect_removed
    
    def has_effect(self, target, effect_name):
        """
        Check if a target has a specific effect active.
        
        Args:
            target: Character to check
            effect_name: Name of the effect to check for
        
        Returns:
            bool: True if target has the effect active
        """
        target_id = id(target)
        
        if target_id not in self.active_effects:
            return False
        
        for effect, _ in self.active_effects[target_id]:
            if effect.name == effect_name:
                return True
        
        return False
    
    def get_active_effects(self, target):
        """
        Get all active effects for a target.
        
        Args:
            target: Character to get effects for
        
        Returns:
            List of (effect, turns_remaining) tuples
        """
        target_id = id(target)
        
        if target_id not in self.active_effects:
            return []
        
        result = []
        for effect, _ in self.active_effects[target_id]:
            turns_elapsed = self.current_turn - effect.applied_at
            turns_remaining = max(0, effect.duration - turns_elapsed)
            result.append((effect, turns_remaining))
        
        return result
    
    def clear_all_effects(self, target):
        """
        Remove all effects from a target.
        
        Args:
            target: Character to clear effects from
        
        Returns:
            int: Number of effects removed
        """
        target_id = id(target)
        
        if target_id not in self.active_effects:
            return 0
        
        count = len(self.active_effects[target_id])
        
        # Call on_remove for each effect
        for effect, _ in self.active_effects[target_id]:
            effect.on_remove(target)
        
        # Remove the target from active_effects
        del self.active_effects[target_id]
        
        return count
    
    def clear_effects_by_type(self, target, effect_type):
        """
        Remove all effects of a specific type from a target.
        
        Args:
            target: Character to remove effects from
            effect_type: Type of effects to remove (e.g., "poison", "buff")
        
        Returns:
            int: Number of effects removed
        """
        target_id = id(target)
        
        if target_id not in self.active_effects:
            return 0
        
        count = 0
        updated_effects = []
        
        for effect, effect_target in self.active_effects[target_id]:
            if hasattr(effect, 'effect_type') and effect.effect_type == effect_type:
                # Call on_remove for the effect being removed
                effect.on_remove(target)
                count += 1
            else:
                updated_effects.append((effect, effect_target))
        
        if updated_effects:
            self.active_effects[target_id] = updated_effects
        else:
            del self.active_effects[target_id]
        
        return count

# Create a global instance of the effect manager
effect_manager = StatusEffectManager()

# Function to render active effects as visual indicators
def render_status_effects(screen, character, x, y):
    """
    Render visual indicators of active status effects for a character.
    
    Args:
        screen: Pygame surface to render on
        character: Character to render effects for
        x, y: Base position for rendering effect icons
    """
    active_effects = effect_manager.get_active_effects(character)
    
    if not active_effects:
        return
    
    # Icon size and spacing
    icon_size = 16
    spacing = 4
    
    # Define colors for different effect types
    effect_colors = {
        "buff": (0, 255, 0),       # Green for buffs
        "debuff": (255, 0, 0),     # Red for debuffs
        "poison": (0, 255, 0),     # Green for poison
        "burning": (255, 165, 0),  # Orange for burning
        "frozen": (0, 191, 255),   # Light blue for frozen
        "invisible": (200, 200, 200)  # Light gray for invisibility
    }
    
    # Render each effect
    for i, (effect, turns_remaining) in enumerate(active_effects):
        # Calculate position
        effect_x = x + (icon_size + spacing) * i
        effect_y = y
        
        # Determine effect color
        if hasattr(effect, 'effect_type') and effect.effect_type in effect_colors:
            color = effect_colors[effect.effect_type]
        else:
            color = (255, 255, 0)  # Default to yellow
        
        # Draw effect icon
        pygame.draw.rect(screen, color, (effect_x, effect_y, icon_size, icon_size))
        
        # Create a small font for effect duration
        font = pygame.font.Font(None, 12)
        
        # Render duration text
        duration_text = font.render(str(turns_remaining), True, (255, 255, 255))
        text_rect = duration_text.get_rect(center=(effect_x + icon_size // 2, effect_y + icon_size // 2))
        screen.blit(duration_text, text_rect)