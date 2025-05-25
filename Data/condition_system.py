#!/usr/bin/env python
# coding: utf-8

"""
Condition System for Blade & Sigil
This module defines status conditions like Poisoned, Paralyzed, etc.
and provides functionality to apply and process these conditions.
"""

import logging
import random
from enum import Enum, auto

# Set up logging
logger = logging.getLogger(__name__)

class ConditionType(Enum):
    """Enumeration of condition types."""
    POISONED = auto()
    PARALYZED = auto()
    DISEASED = auto()
    DRAINED = auto()
    CURSED = auto()
    SLOWED = auto()
    BLINDED = auto()
    SILENCED = auto()
    WEAKENED = auto()
    STRENGTHENED = auto()
    HASTED = auto()
    INVISIBLE = auto()
    BLESSED = auto()
    PROTECTED = auto()
    REGENERATING = auto()
    BURNING = auto()
    FROZEN = auto()
    CONFUSED = auto()
    STUNNED = auto()
    IMMUNE_POISON = auto()

class Condition:
    """
    Represents a status condition affecting a character.
    
    Conditions can modify attributes, apply damage over time,
    or prevent certain actions from being taken.
    """
    
    def __init__(self, condition_type, duration, source=None, severity=1, effects=None):
        """
        Initialize a new condition.
        
        Args:
            condition_type: ConditionType enum value
            duration: Number of turns the condition will last
            source: Character who applied the condition (optional)
            severity: Intensity level of the condition (default 1)
            effects: Dictionary of specific effect parameters (optional)
        """
        self.condition_type = condition_type
        self.duration = duration
        self.source = source
        self.severity = severity
        self.effects = effects or {}
        self.applied_at_turn = 0
        self.modified_attributes = {}  # Track which attributes were modified
        
        # Set the name based on condition type
        self.name = self.condition_type.name.capitalize()
        
        # Set the description based on condition type
        self.description = self._get_description()
    
    def _get_description(self):
        """Get the description for this condition type."""
        descriptions = {
            ConditionType.POISONED: "Taking damage over time",
            ConditionType.PARALYZED: "Cannot move",
            ConditionType.DISEASED: "Reduced strength and constitution",
            ConditionType.DRAINED: "Reduced maximum hit points",
            ConditionType.CURSED: "Reduced ability scores",
            ConditionType.SLOWED: "Reduced movement speed",
            ConditionType.BLINDED: "Cannot see, reduced accuracy",
            ConditionType.SILENCED: "Cannot cast spells",
            ConditionType.WEAKENED: "Reduced damage",
            ConditionType.STRENGTHENED: "Increased damage",
            ConditionType.HASTED: "Increased movement speed",
            ConditionType.INVISIBLE: "Cannot be seen",
            ConditionType.BLESSED: "Increased saving throws",
            ConditionType.PROTECTED: "Increased AC",
            ConditionType.REGENERATING: "Regenerating hit points",
            ConditionType.BURNING: "Taking fire damage over time",
            ConditionType.FROZEN: "Reduced speed and dexterity",
            ConditionType.CONFUSED: "Random movement",
            ConditionType.STUNNED: "Skip turns and cannot take actions",
            ConditionType.IMMUNE_POISON: "Immunity to poison damage and effects"
        }
        return descriptions.get(self.condition_type, "Unknown condition")
    
    def apply(self, target):
        """
        Apply this condition to a target character.
        
        Args:
            target: The character to apply the condition to
            
        Returns:
            str: Message describing the effect
        """
        # Set condition tracking on target if not already present
        if not hasattr(target, 'conditions'):
            target.conditions = []
        
        # Add to target's conditions list
        target.conditions.append(self)
        
        # Apply specific effects based on condition type
        message = f"{target.name} is now {self.name}!"
        
        # Apply condition-specific effects
        if self.condition_type == ConditionType.POISONED:
            message = self._apply_poisoned(target)
        elif self.condition_type == ConditionType.PARALYZED:
            message = self._apply_paralyzed(target)
        elif self.condition_type == ConditionType.DISEASED:
            message = self._apply_diseased(target)
        elif self.condition_type == ConditionType.DRAINED:
            message = self._apply_drained(target)
        elif self.condition_type == ConditionType.CURSED:
            message = self._apply_cursed(target)
        elif self.condition_type == ConditionType.WEAKENED:
            message = self._apply_weakened(target)
        elif self.condition_type == ConditionType.STRENGTHENED:
            message = self._apply_strengthened(target)
        elif self.condition_type == ConditionType.PROTECTED:
            message = self._apply_protected(target)
        elif self.condition_type == ConditionType.STUNNED:
            message = self._apply_stunned(target)
        elif self.condition_type == ConditionType.IMMUNE_POISON:
            message = self._apply_immune_poison(target)
        
        logger.debug(f"Applied {self.name} to {target.name}")
        return message
    
    def process_turn(self, target, current_turn):
        """
        Process the condition's effect at the start of a turn.
        
        Args:
            target: The character with the condition
            current_turn: The current game turn number
            
        Returns:
            str or None: Message describing any effects, or None
        """
        # Calculate how many turns this condition has been active
        turns_active = current_turn - self.applied_at_turn
        
        # Check for expiry
        if turns_active >= self.duration:
            return self.remove(target)
        
        message = None
        
        # Apply turn effects based on condition type
        if self.condition_type == ConditionType.POISONED:
            # Check if target is immune to poison
            if not self._is_immune_to_poison(target):
                message = self._process_poisoned_turn(target)
            else:
                message = f"{target.name} is immune to poison and takes no damage."
        elif self.condition_type == ConditionType.BURNING:
            message = self._process_burning_turn(target)
        elif self.condition_type == ConditionType.REGENERATING:
            message = self._process_regenerating_turn(target)
        elif self.condition_type == ConditionType.STUNNED:
            message = self._process_stunned_turn(target)
        
        return message
        
    def _is_immune_to_poison(self, target):
        """Check if target is immune to poison."""
        if not hasattr(target, 'conditions'):
            return False
            
        for condition in target.conditions:
            if condition.condition_type == ConditionType.IMMUNE_POISON:
                return True
                
        # Also check for innate immunity in monster types
        if hasattr(target, 'immunities') and 'poison' in target.immunities:
            return True
            
        return False
    
    def remove(self, target):
        """
        Remove this condition from a target character.
        
        Args:
            target: The character to remove the condition from
            
        Returns:
            str: Message describing the effect
        """
        # Remove from target's conditions list
        if hasattr(target, 'conditions'):
            if self in target.conditions:
                target.conditions.remove(self)
        
        # Restore modified attributes
        for attr, original_value in self.modified_attributes.items():
            if hasattr(target, attr):
                setattr(target, attr, original_value)
        
        # Apply condition-specific cleanup
        if self.condition_type == ConditionType.DRAINED:
            self._remove_drained(target)
        elif self.condition_type == ConditionType.PROTECTED:
            self._remove_protected(target)
        elif self.condition_type == ConditionType.STRENGTHENED:
            self._remove_strengthened(target)
        elif self.condition_type == ConditionType.WEAKENED:
            self._remove_weakened(target)
        elif self.condition_type == ConditionType.STUNNED:
            self._remove_stunned(target)
        elif self.condition_type == ConditionType.IMMUNE_POISON:
            self._remove_immune_poison(target)
        
        message = f"{target.name} is no longer {self.name}."
        logger.debug(f"Removed {self.name} from {target.name}")
        return message
    
    def get_remaining_duration(self, current_turn):
        """
        Get the number of turns remaining for this condition.
        
        Args:
            current_turn: The current game turn number
            
        Returns:
            int: Turns remaining
        """
        turns_elapsed = current_turn - self.applied_at_turn
        return max(0, self.duration - turns_elapsed)
    
    def is_expired(self, current_turn):
        """
        Check if this condition has expired.
        
        Args:
            current_turn: The current game turn number
            
        Returns:
            bool: True if expired
        """
        # For debugging, print the remaining duration
        remaining = self.get_remaining_duration(current_turn)
        logger.debug(f"Condition {self.name} has {remaining} turns remaining (applied at {self.applied_at_turn}, current turn {current_turn}, duration {self.duration})")
        return remaining <= 0
    
    # === Condition-specific application methods ===
    
    def _apply_poisoned(self, target):
        """Apply poison effects."""
        # Poison just deals damage over time, no immediate effect
        return f"{target.name} is poisoned and will take damage over time!"
    
    def _apply_paralyzed(self, target):
        """Apply paralysis effects."""
        # Store and modify movement ability
        if hasattr(target, 'can_move'):
            self.modified_attributes['can_move'] = target.can_move
            target.can_move = False
        return f"{target.name} is paralyzed and cannot move!"
    
    def _apply_diseased(self, target):
        """Apply disease effects."""
        # Reduce strength and constitution
        penalty = -2 * self.severity
        
        if hasattr(target, 'abilities'):
            # Store original values
            if 'strength' in target.abilities:
                self.modified_attributes['abilities.strength'] = target.abilities['strength']
                target.abilities['strength'] += penalty
            
            if 'constitution' in target.abilities:
                self.modified_attributes['abilities.constitution'] = target.abilities['constitution']
                target.abilities['constitution'] += penalty
        
        return f"{target.name} is diseased, reducing strength and constitution by {abs(penalty)}!"
    
    def _apply_drained(self, target):
        """Apply energy drain effects."""
        # Reduce maximum hit points
        if hasattr(target, 'max_hit_points'):
            drain_amount = min(target.max_hit_points // 4, 5 * self.severity)
            self.modified_attributes['max_hit_points'] = target.max_hit_points
            target.max_hit_points -= drain_amount
            
            # Ensure current hit points don't exceed new maximum
            if target.hit_points > target.max_hit_points:
                target.hit_points = target.max_hit_points
            
            return f"{target.name} is drained, reducing maximum hit points by {drain_amount}!"
        
        return f"{target.name} is drained!"
    
    def _apply_cursed(self, target):
        """Apply curse effects."""
        # Reduce all ability scores
        penalty = -1 * self.severity
        
        if hasattr(target, 'abilities'):
            for ability in target.abilities:
                self.modified_attributes[f'abilities.{ability}'] = target.abilities[ability]
                target.abilities[ability] += penalty
            
            return f"{target.name} is cursed, reducing all abilities by {abs(penalty)}!"
        
        return f"{target.name} is cursed!"
    
    def _apply_weakened(self, target):
        """Apply weakness effects."""
        # Reduce damage output
        if hasattr(target, 'damage_modifier'):
            self.modified_attributes['damage_modifier'] = target.damage_modifier
            target.damage_modifier -= self.severity
            return f"{target.name} is weakened, dealing less damage!"
        
        return f"{target.name} is weakened!"
    
    def _apply_strengthened(self, target):
        """Apply strength effects."""
        # Increase damage output
        if hasattr(target, 'damage_modifier'):
            self.modified_attributes['damage_modifier'] = target.damage_modifier
            target.damage_modifier += self.severity
            return f"{target.name} is strengthened, dealing more damage!"
        
        # Alternative: directly modify strength ability
        elif hasattr(target, 'abilities') and 'strength' in target.abilities:
            self.modified_attributes['abilities.strength'] = target.abilities['strength']
            target.abilities['strength'] += self.severity
            return f"{target.name} is strengthened, gaining +{self.severity} strength!"
        
        return f"{target.name} is strengthened!"
    
    def _apply_protected(self, target):
        """Apply protection effects."""
        # Increase AC
        if hasattr(target, 'ac'):
            self.modified_attributes['ac'] = target.ac
            target.ac += self.severity
            return f"{target.name} is protected, gaining +{self.severity} AC!"
        
        return f"{target.name} is protected!"
        
    def _apply_stunned(self, target):
        """Apply stunned effects."""
        # Store and modify ability to take actions
        if hasattr(target, 'can_act'):
            self.modified_attributes['can_act'] = target.can_act
            target.can_act = False
        
        # Store and modify movement ability
        if hasattr(target, 'can_move'):
            self.modified_attributes['can_move'] = target.can_move
            target.can_move = False
            
        # Store and modify can_take_actions if it exists
        if hasattr(target, 'can_take_actions'):
            self.modified_attributes['can_take_actions'] = target.can_take_actions
            target.can_take_actions = False
            
        return f"{target.name} is stunned and cannot act or move!"
        
    def _apply_immune_poison(self, target):
        """Apply poison immunity."""
        # Add poison to target's immunities list
        if hasattr(target, 'immunities'):
            # Save original immunities for restoration later
            self.modified_attributes['immunities'] = target.immunities.copy() if hasattr(target.immunities, 'copy') else list(target.immunities)
            
            # Add poison to immunities if not already present
            if 'poison' not in target.immunities:
                target.immunities.append('poison')
        else:
            # Create immunities list if it doesn't exist
            target.immunities = ['poison']
            self.modified_attributes['immunities'] = []
            
        # Check if target already has any poison conditions and remove them
        if hasattr(target, 'conditions'):
            removed_poison = False
            for condition in list(target.conditions):
                if condition.condition_type == ConditionType.POISONED:
                    target.conditions.remove(condition)
                    removed_poison = True
            
            if removed_poison:
                return f"{target.name} is now immune to poison and all poison effects are neutralized!"
        
        return f"{target.name} is now immune to poison!"
    
    # === Condition-specific turn processing methods ===
    
    def _process_poisoned_turn(self, target):
        """Process poison damage per turn."""
        if hasattr(target, 'hit_points'):
            damage = random.randint(1, 3) * self.severity
            target.hit_points -= damage
            
            # Check for death
            if target.hit_points <= 0:
                target.hit_points = 0
                if hasattr(target, 'is_dead'):
                    target.is_dead = True
                return f"{target.name} takes {damage} poison damage and dies!"
            
            return f"{target.name} takes {damage} poison damage from being poisoned!"
        
        return None
    
    def _process_burning_turn(self, target):
        """Process burn damage per turn."""
        if hasattr(target, 'hit_points'):
            damage = random.randint(2, 5) * self.severity
            target.hit_points -= damage
            
            # Check for death
            if target.hit_points <= 0:
                target.hit_points = 0
                if hasattr(target, 'is_dead'):
                    target.is_dead = True
                return f"{target.name} takes {damage} fire damage and dies!"
            
            return f"{target.name} takes {damage} fire damage from burning!"
        
        return None
    
    def _process_regenerating_turn(self, target):
        """Process healing per turn from regeneration."""
        if hasattr(target, 'hit_points') and hasattr(target, 'max_hit_points'):
            healing = random.randint(1, 3) * self.severity
            old_hp = target.hit_points
            target.hit_points = min(target.hit_points + healing, target.max_hit_points)
            actual_heal = target.hit_points - old_hp
            
            if actual_heal > 0:
                return f"{target.name} regenerates {actual_heal} hit points!"
        
        return None
        
    def _process_stunned_turn(self, target):
        """Process stunned effects per turn."""
        # This is primarily a reminder message
        return f"{target.name} is stunned and skips their turn!"
    
    # === Condition-specific removal methods ===
    
    def _remove_drained(self, target):
        """Restore maximum hit points after drain effect ends."""
        if 'max_hit_points' in self.modified_attributes and hasattr(target, 'max_hit_points'):
            target.max_hit_points = self.modified_attributes['max_hit_points']
    
    def _remove_protected(self, target):
        """Restore AC after protection effect ends."""
        if 'ac' in self.modified_attributes and hasattr(target, 'ac'):
            target.ac = self.modified_attributes['ac']
    
    def _remove_strengthened(self, target):
        """Restore strength after strengthening effect ends."""
        if 'damage_modifier' in self.modified_attributes and hasattr(target, 'damage_modifier'):
            target.damage_modifier = self.modified_attributes['damage_modifier']
        elif 'abilities.strength' in self.modified_attributes and hasattr(target, 'abilities'):
            target.abilities['strength'] = self.modified_attributes['abilities.strength']
    
    def _remove_weakened(self, target):
        """Restore damage output after weakness effect ends."""
        if 'damage_modifier' in self.modified_attributes and hasattr(target, 'damage_modifier'):
            target.damage_modifier = self.modified_attributes['damage_modifier']
            
    def _remove_stunned(self, target):
        """Restore ability to act and move after stun effect ends."""
        # Restore can_take_actions if it exists and was modified
        if 'can_take_actions' in self.modified_attributes and hasattr(target, 'can_take_actions'):
            target.can_take_actions = self.modified_attributes['can_take_actions']
            
        # can_act and can_move should be restored by the general attribute restoration
        # This method handles any additional cleanup needed
        pass
        
    def _remove_immune_poison(self, target):
        """Remove poison immunity when the effect ends."""
        # Restore original immunities if they were modified
        if 'immunities' in self.modified_attributes and hasattr(target, 'immunities'):
            target.immunities = self.modified_attributes['immunities']

class ConditionManager:
    """
    Manages conditions across all characters in the game.
    
    This class tracks all active conditions, processes their effects
    each turn, and handles condition removal.
    """
    
    def __init__(self):
        """Initialize the condition manager."""
        self.current_turn = 0
        self.last_process_time = 0  # Used to debug if we're processing too frequently
    
    def apply_condition(self, target, condition):
        """
        Apply a condition to a target.
        
        Args:
            target: Character to apply the condition to
            condition: Condition object
            
        Returns:
            str: Message describing the effect
        """
        # --- Add this log line ---
        logger.debug(f"ConditionManager (id: {id(self)}) apply_condition: current_turn before assignment is {self.current_turn} for condition {condition.name} on {target.name if hasattr(target, 'name') else 'Unknown Target'}")
        # --- End of added log line ---
        
        # Set the application turn
        condition.applied_at_turn = self.current_turn
        
        result_message = condition.apply(target) # Store result of apply

        # --- Add this log line ---
        if hasattr(target, 'conditions'):
            target_conditions_info = [(c.name, id(c), c.duration, c.applied_at_turn) for c in target.conditions]
            logger.debug(f"ConditionManager (id: {id(self)}) apply_condition: Conditions on {target.name if hasattr(target, 'name') else 'Unknown Target'} after applying {condition.name} (id: {id(condition)}): {target_conditions_info}")
        else:
            logger.debug(f"ConditionManager (id: {id(self)}) apply_condition: Target {target.name if hasattr(target, 'name') else 'Unknown Target'} has no conditions list after applying {condition.name} (id: {id(condition)}).")
        # --- End of added log line ---
            
        return result_message
    
    def process_turn(self, targets=None):
        """
        Process all conditions for the start of a new turn.
        
        Args:
            targets: Optional list of characters to process. If None,
                    processes all characters with conditions.
            
        Returns:
            list: Messages generated during processing
        """
        # Get current timestamp for debugging
        import time
        current_time = time.time()
        time_since_last_process = current_time - self.last_process_time
        
        # Increment the game turn counter
        self.current_turn += 1
        messages = []
        
        # Debug print the current turn
        logger.debug(f"===== PROCESSING TURN {self.current_turn} =====")
        logger.debug(f"Processing {len(targets) if targets else 0} targets")
        logger.debug(f"Time since last process_turn: {time_since_last_process:.2f} seconds")
        
        # Update last process time
        self.last_process_time = current_time
        
        # If no targets specified, we need to use our own tracking
        # But for simplicity in this implementation, we'll require targets
        if not targets:
            logger.warning("No targets provided to process_turn")
            return messages
        
        # Process each target's conditions
        for target in targets:
            if not hasattr(target, 'conditions'):
                # logger.debug(f"Target {target.name if hasattr(target, 'name') else 'Unknown Target'} has no conditions list to process.")
                continue
                
            # --- Add this log line ---
            target_conditions_info = [(c.name, id(c), c.duration, c.applied_at_turn) for c in target.conditions]
            logger.debug(f"ConditionManager (id: {id(self)}) process_turn (turn {self.current_turn}): Processing conditions for {target.name if hasattr(target, 'name') else 'Unknown Target'}. Current conditions: {target_conditions_info}")
            # --- End of added log line ---

            updated_conditions = []
            for condition in target.conditions: # Iterate on a copy if modifying
                # Process turn effects
                message = condition.process_turn(target, self.current_turn)
                if message:
                    messages.append(message)
                
                # Keep conditions that haven't expired
                if not condition.is_expired(self.current_turn):
                    updated_conditions.append(condition)
            
            # Update the target's conditions list
            target.conditions = updated_conditions
        
        return messages
    
    def remove_condition(self, target, condition_type):
        """
        Remove a specific type of condition from a target.
        
        Args:
            target: Character to remove the condition from
            condition_type: ConditionType enum value
            
        Returns:
            bool: True if a condition was removed
        """
        if not hasattr(target, 'conditions'):
            return False
        
        removed = False
        for condition in list(target.conditions):
            if condition.condition_type == condition_type:
                message = condition.remove(target)
                target.conditions.remove(condition)
                removed = True
        
        return removed
    
    def has_condition(self, target, condition_type):
        """
        Check if a target has a specific condition.
        
        Args:
            target: Character to check
            condition_type: ConditionType enum value
            
        Returns:
            bool: True if the target has the condition
        """
        if not hasattr(target, 'conditions'):
            return False
        
        for condition in target.conditions:
            if condition.condition_type == condition_type:
                return True
        
        return False
    
    def get_conditions(self, target):
        """
        Get all conditions affecting a target.
        
        Args:
            target: Character to get conditions for
            
        Returns:
            list: Condition objects
        """
        if not hasattr(target, 'conditions'):
            return []
        
        return target.conditions
    
    def clear_conditions(self, target):
        """
        Remove all conditions from a target.
        
        Args:
            target: Character to clear conditions from
            
        Returns:
            int: Number of conditions removed
        """
        if not hasattr(target, 'conditions'):
            return 0
        
        count = len(target.conditions)
        
        # Remove each condition properly
        for condition in list(target.conditions):
            condition.remove(target)
        
        # Clear the list
        target.conditions = []
        
        return count

# Create a global instance of the condition manager
condition_manager = ConditionManager()

# Helper functions for common condition applications
def apply_poison(target, duration=3, source=None, severity=1):
    """Helper to apply poison condition."""
    condition = Condition(ConditionType.POISONED, duration, source, severity)
    return condition_manager.apply_condition(target, condition)

def apply_paralysis(target, duration=2, source=None, severity=1):
    """Helper to apply paralysis condition."""
    condition = Condition(ConditionType.PARALYZED, duration, source, severity)
    return condition_manager.apply_condition(target, condition)

def apply_curse(target, duration=5, source=None, severity=1):
    """Helper to apply curse condition."""
    condition = Condition(ConditionType.CURSED, duration, source, severity)
    return condition_manager.apply_condition(target, condition)

def apply_protection(target, duration=3, source=None, severity=2):
    """Helper to apply protection condition."""
    condition = Condition(ConditionType.PROTECTED, duration, source, severity)
    return condition_manager.apply_condition(target, condition)
    
def apply_stun(target, duration=2, source=None, severity=1):
    """Helper to apply stunned condition."""
    condition = Condition(ConditionType.STUNNED, duration, source, severity)
    return condition_manager.apply_condition(target, condition)
    
def apply_poison_immunity(target, duration=5, source=None, severity=1):
    """Helper to apply poison immunity condition."""
    condition = Condition(ConditionType.IMMUNE_POISON, duration, source, severity)
    return condition_manager.apply_condition(target, condition)

def render_conditions(screen, character, x, y):
    """
    Render visual indicators of active conditions for a character.
    
    Args:
        screen: Pygame surface to render on
        character: Character to render conditions for
        x, y: Base position for rendering condition icons
    """
    import pygame
    
    if not hasattr(character, 'conditions') or not character.conditions:
        return
    
    # Icon size and spacing
    icon_size = 16
    spacing = 4
    
    # Define colors for different condition types
    condition_colors = {
        ConditionType.POISONED: (0, 255, 0),      # Green for poison
        ConditionType.PARALYZED: (100, 100, 255), # Blue for paralysis
        ConditionType.DISEASED: (139, 69, 19),    # Brown for disease
        ConditionType.DRAINED: (128, 0, 128),     # Purple for drain
        ConditionType.CURSED: (75, 0, 130),       # Indigo for curse
        ConditionType.SLOWED: (0, 191, 255),      # Light blue for slow
        ConditionType.BURNING: (255, 165, 0),     # Orange for burning
        ConditionType.PROTECTED: (255, 215, 0),   # Gold for protection
        ConditionType.STRENGTHENED: (255, 0, 0),  # Red for strengthened
        ConditionType.REGENERATING: (50, 205, 50), # Lime for regeneration
        ConditionType.STUNNED: (255, 0, 255),     # Magenta for stunned
        ConditionType.IMMUNE_POISON: (0, 128, 0)  # Dark green for poison immunity
    }
    
    # Render each condition
    for i, condition in enumerate(character.conditions):
        # Calculate position
        condition_x = x + (icon_size + spacing) * i
        condition_y = y
        
        # Determine condition color
        color = condition_colors.get(condition.condition_type, (200, 200, 200))
        
        # Draw condition icon
        pygame.draw.rect(screen, color, (condition_x, condition_y, icon_size, icon_size))
        
        # Create a small font for condition duration
        font = pygame.font.Font(None, 12)
        
        # Render duration text
        remaining = condition.get_remaining_duration(condition_manager.current_turn)
        duration_text = font.render(str(remaining), True, (255, 255, 255))
        text_rect = duration_text.get_rect(center=(condition_x + icon_size // 2, condition_y + icon_size // 2))
        screen.blit(duration_text, text_rect)
