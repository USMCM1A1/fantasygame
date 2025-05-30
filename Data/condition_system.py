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
    def __init__(self, condition_type, duration, source=None, severity=1, effects=None):
        self.condition_type = condition_type
        self.duration = duration
        self.source = source
        self.severity = severity
        self.effects = effects or {}
        self.applied_at_turn = 0
        self.modified_attributes = {}
        self.name = self.condition_type.name.capitalize()
        self.description = self._get_description()

    def _get_description(self):
        descriptions = {
            ConditionType.POISONED: "Taking damage over time",
            ConditionType.PARALYZED: "Cannot move or act",
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
        if not hasattr(target, 'conditions'):
            target.conditions = []
        
        target.conditions.append(self)
        
        target_name_for_log = target.name if hasattr(target, 'name') else 'Unknown Target'
        message = f"{target_name_for_log} is now {self.name}!"

        if self.condition_type == ConditionType.POISONED: message = self._apply_poisoned(target)
        elif self.condition_type == ConditionType.PARALYZED: message = self._apply_paralyzed(target)
        elif self.condition_type == ConditionType.DISEASED: message = self._apply_diseased(target)
        elif self.condition_type == ConditionType.DRAINED: message = self._apply_drained(target)
        elif self.condition_type == ConditionType.CURSED: message = self._apply_cursed(target)
        elif self.condition_type == ConditionType.WEAKENED: message = self._apply_weakened(target)
        elif self.condition_type == ConditionType.STRENGTHENED: message = self._apply_strengthened(target)
        elif self.condition_type == ConditionType.PROTECTED: message = self._apply_protected(target)
        elif self.condition_type == ConditionType.STUNNED: message = self._apply_stunned(target)
        elif self.condition_type == ConditionType.IMMUNE_POISON: message = self._apply_immune_poison(target)
        
        logger.debug(f"Applied {self.name} to {target_name_for_log}")
        return message

    def process_turn(self, target, current_turn):
        if self.is_expired(current_turn):
            return self.remove(target)
        
        message = None
        if self.condition_type == ConditionType.POISONED:
            if not self._is_immune_to_poison(target): message = self._process_poisoned_turn(target)
            else: message = f"{target.name if hasattr(target, 'name') else 'Unknown Target'} is immune to poison and takes no damage."
        elif self.condition_type == ConditionType.BURNING: message = self._process_burning_turn(target)
        elif self.condition_type == ConditionType.REGENERATING: message = self._process_regenerating_turn(target)
        elif self.condition_type == ConditionType.STUNNED: message = self._process_stunned_turn(target)
        return message
        
    def _is_immune_to_poison(self, target):
        if not hasattr(target, 'conditions'): return False
        for c in target.conditions:
            if c.condition_type == ConditionType.IMMUNE_POISON: return True
        if hasattr(target, 'immunities') and 'poison' in target.immunities: return True
        return False

    def remove(self, target):
        target_name_for_log = target.name if hasattr(target, 'name') else 'Unknown Target'
        if hasattr(target, 'conditions') and self in target.conditions:
            target.conditions.remove(self)
        else:
            logger.warning(f"Attempted to remove {self.name} from {target_name_for_log}, but it was not found in their conditions list.")

        for attr, original_value in self.modified_attributes.items():
            if hasattr(target, attr): setattr(target, attr, original_value)
        
        if self.condition_type == ConditionType.PARALYZED: self._remove_paralyzed(target)
        elif self.condition_type == ConditionType.STUNNED: self._remove_stunned(target)
        elif self.condition_type == ConditionType.DRAINED: self._remove_drained(target)
        elif self.condition_type == ConditionType.PROTECTED: self._remove_protected(target)
        elif self.condition_type == ConditionType.STRENGTHENED: self._remove_strengthened(target)
        elif self.condition_type == ConditionType.WEAKENED: self._remove_weakened(target)
        elif self.condition_type == ConditionType.IMMUNE_POISON: self._remove_immune_poison(target)
        
        message = f"{target_name_for_log} is no longer {self.name}."
        logger.debug(f"Removed {self.name} from {target_name_for_log}. Conditions remaining: {[c.name for c in target.conditions] if hasattr(target, 'conditions') else 'None'}")
        return message

    def get_remaining_duration(self, current_turn):
        turns_elapsed = current_turn - self.applied_at_turn
        return max(0, self.duration - turns_elapsed)

    def is_expired(self, current_turn):
        remaining = self.get_remaining_duration(current_turn)
        source_name = self.source.name if self.source and hasattr(self.source, 'name') else 'Unknown Source' # Added check for self.source
        logger.debug(f"Condition {self.name} on target (source: {source_name}) has {remaining} turns remaining (applied at {self.applied_at_turn}, current turn {current_turn}, duration {self.duration})")
        return remaining < 0

    def _apply_poisoned(self, target): return f"{target.name if hasattr(target, 'name') else 'Unknown Target'} is poisoned and will take damage over time!"
    
    def _apply_paralyzed(self, target):
        target_name_for_log = target.name if hasattr(target, 'name') else 'Unknown Target'
        logger.debug(f"Applying PARALYZED to {target_name_for_log}")
        if hasattr(target, 'can_move'):
            if 'can_move' not in self.modified_attributes: self.modified_attributes['can_move'] = target.can_move
            target.can_move = False
            logger.debug(f"{target_name_for_log} can_move set to False")
        if hasattr(target, 'can_act'): 
            if 'can_act' not in self.modified_attributes: self.modified_attributes['can_act'] = target.can_act
            target.can_act = False
            logger.debug(f"{target_name_for_log} can_act set to False")
        return f"{target_name_for_log} is paralyzed and cannot move or act!"

    def _remove_paralyzed(self, target): 
        target_name_for_log = target.name if hasattr(target, 'name') else 'Unknown Target'
        logger.debug(f"Removing PARALYZED from {target_name_for_log}")
        if 'can_move' in self.modified_attributes and hasattr(target, 'can_move'):
            target.can_move = self.modified_attributes['can_move']
            logger.debug(f"{target_name_for_log} can_move restored to {target.can_move}")
        if 'can_act' in self.modified_attributes and hasattr(target, 'can_act'):
            target.can_act = self.modified_attributes['can_act']
            logger.debug(f"{target_name_for_log} can_act restored to {target.can_act}")

    def _apply_diseased(self, target):
        penalty = -2 * self.severity
        if hasattr(target, 'abilities'):
            if 'strength' in target.abilities:
                if 'abilities.strength' not in self.modified_attributes: self.modified_attributes['abilities.strength'] = target.abilities['strength']
                target.abilities['strength'] += penalty
            if 'constitution' in target.abilities:
                if 'abilities.constitution' not in self.modified_attributes: self.modified_attributes['abilities.constitution'] = target.abilities['constitution']
                target.abilities['constitution'] += penalty
        return f"{target.name if hasattr(target, 'name') else 'Unknown Target'} is diseased, reducing strength and constitution by {abs(penalty)}!"

    def _apply_drained(self, target):
        if hasattr(target, 'max_hit_points'):
            drain_amount = min(target.max_hit_points // 4, 5 * self.severity)
            if 'max_hit_points' not in self.modified_attributes: self.modified_attributes['max_hit_points'] = target.max_hit_points
            target.max_hit_points -= drain_amount
            if target.hit_points > target.max_hit_points: target.hit_points = target.max_hit_points
            return f"{target.name if hasattr(target, 'name') else 'Unknown Target'} is drained, reducing maximum hit points by {drain_amount}!"
        return f"{target.name if hasattr(target, 'name') else 'Unknown Target'} is drained!"

    def _apply_cursed(self, target):
        penalty = -1 * self.severity
        if hasattr(target, 'abilities'):
            for ability in target.abilities:
                if f'abilities.{ability}' not in self.modified_attributes: self.modified_attributes[f'abilities.{ability}'] = target.abilities[ability]
                target.abilities[ability] += penalty
            return f"{target.name if hasattr(target, 'name') else 'Unknown Target'} is cursed, reducing all abilities by {abs(penalty)}!"
        return f"{target.name if hasattr(target, 'name') else 'Unknown Target'} is cursed!"

    def _apply_weakened(self, target):
        if hasattr(target, 'damage_modifier'):
            if 'damage_modifier' not in self.modified_attributes: self.modified_attributes['damage_modifier'] = target.damage_modifier
            target.damage_modifier -= self.severity
            return f"{target.name if hasattr(target, 'name') else 'Unknown Target'} is weakened, dealing less damage!"
        return f"{target.name if hasattr(target, 'name') else 'Unknown Target'} is weakened!"

    def _apply_strengthened(self, target):
        if hasattr(target, 'damage_modifier'):
            if 'damage_modifier' not in self.modified_attributes: self.modified_attributes['damage_modifier'] = target.damage_modifier
            target.damage_modifier += self.severity
            return f"{target.name if hasattr(target, 'name') else 'Unknown Target'} is strengthened, dealing more damage!"
        elif hasattr(target, 'abilities') and 'strength' in target.abilities:
            if 'abilities.strength' not in self.modified_attributes: self.modified_attributes['abilities.strength'] = target.abilities['strength']
            target.abilities['strength'] += self.severity
            return f"{target.name if hasattr(target, 'name') else 'Unknown Target'} is strengthened, gaining +{self.severity} strength!"
        return f"{target.name if hasattr(target, 'name') else 'Unknown Target'} is strengthened!"

    def _apply_protected(self, target):
        if hasattr(target, 'ac'):
            if 'ac' not in self.modified_attributes: self.modified_attributes['ac'] = target.ac
            target.ac += self.severity
            return f"{target.name if hasattr(target, 'name') else 'Unknown Target'} is protected, gaining +{self.severity} AC!"
        return f"{target.name if hasattr(target, 'name') else 'Unknown Target'} is protected!"

    def _apply_stunned(self, target):
        target_name_for_log = target.name if hasattr(target, 'name') else 'Unknown Target'
        logger.debug(f"Applying STUNNED to {target_name_for_log}")
        if hasattr(target, 'can_act'): 
            if 'can_act' not in self.modified_attributes: self.modified_attributes['can_act'] = target.can_act
            target.can_act = False; logger.debug(f"{target_name_for_log} can_act set to False")
        if hasattr(target, 'can_move'): 
            if 'can_move' not in self.modified_attributes: self.modified_attributes['can_move'] = target.can_move
            target.can_move = False; logger.debug(f"{target_name_for_log} can_move set to False")
        if hasattr(target, 'can_take_actions'): 
            if 'can_take_actions' not in self.modified_attributes: self.modified_attributes['can_take_actions'] = target.can_take_actions
            target.can_take_actions = False; logger.debug(f"{target_name_for_log} can_take_actions set to False")
        return f"{target_name_for_log} is stunned and cannot act or move!"
        
    def _apply_immune_poison(self, target):
        if hasattr(target, 'immunities'):
            if 'immunities' not in self.modified_attributes: self.modified_attributes['immunities'] = target.immunities.copy() if hasattr(target.immunities, 'copy') else list(target.immunities)
            if 'poison' not in target.immunities: target.immunities.append('poison')
        else:
            target.immunities = ['poison']
            if 'immunities' not in self.modified_attributes: self.modified_attributes['immunities'] = []
        if hasattr(target, 'conditions'):
            removed_poison = False
            for c_obj in list(target.conditions): 
                if c_obj.condition_type == ConditionType.POISONED: target.conditions.remove(c_obj); removed_poison = True
            if removed_poison: return f"{target.name if hasattr(target, 'name') else 'Unknown Target'} is now immune to poison and all poison effects are neutralized!"
        return f"{target.name if hasattr(target, 'name') else 'Unknown Target'} is now immune to poison!"

    def _process_poisoned_turn(self, target):
        target_name_for_log = target.name if hasattr(target, 'name') else 'Unknown Target'
        if hasattr(target, 'hit_points'):
            damage = random.randint(1, 3) * self.severity
            target.hit_points -= damage
            log_message_content = f"{target_name_for_log} takes {damage} poison damage from being poisoned!"
            logger.debug(f"Poison DoT: Generating message: '{log_message_content}' for {target_name_for_log}")
            if target.hit_points <= 0:
                target.hit_points = 0
                # if hasattr(target, 'is_dead'): target.is_dead = True # Deferred to main game loop
                target.pending_death_from_dot = True
                death_message_content = f"{target_name_for_log} takes {damage} poison damage and dies!"
                logger.debug(f"Poison DoT: Generating message: '{death_message_content}' for {target_name_for_log} (death)")
                return death_message_content
            return log_message_content
        return None

    def _process_burning_turn(self, target):
        target_name_for_log = target.name if hasattr(target, 'name') else 'Unknown Target'
        if hasattr(target, 'hit_points'):
            damage = random.randint(2, 5) * self.severity
            target.hit_points -= damage
            if target.hit_points <= 0:
                target.hit_points = 0
                # if hasattr(target, 'is_dead'): target.is_dead = True # Deferred to main game loop
                target.pending_death_from_dot = True
                return f"{target_name_for_log} takes {damage} fire damage and dies!"
            return f"{target_name_for_log} takes {damage} fire damage from burning!"
        return None

    def _process_regenerating_turn(self, target):
        target_name_for_log = target.name if hasattr(target, 'name') else 'Unknown Target'
        if hasattr(target, 'hit_points') and hasattr(target, 'max_hit_points'):
            healing = random.randint(1, 3) * self.severity
            old_hp = target.hit_points
            target.hit_points = min(target.hit_points + healing, target.max_hit_points)
            actual_heal = target.hit_points - old_hp
            if actual_heal > 0: return f"{target_name_for_log} regenerates {actual_heal} hit points!"
        return None
        
    def _process_stunned_turn(self, target): return f"{target.name if hasattr(target, 'name') else 'Unknown Target'} is stunned and skips their turn!"
    
    def _remove_drained(self, target):
        if 'max_hit_points' in self.modified_attributes and hasattr(target, 'max_hit_points'): target.max_hit_points = self.modified_attributes['max_hit_points']
    def _remove_protected(self, target):
        if 'ac' in self.modified_attributes and hasattr(target, 'ac'): target.ac = self.modified_attributes['ac']
    def _remove_strengthened(self, target):
        if 'damage_modifier' in self.modified_attributes and hasattr(target, 'damage_modifier'): target.damage_modifier = self.modified_attributes['damage_modifier']
        elif 'abilities.strength' in self.modified_attributes and hasattr(target, 'abilities'): target.abilities['strength'] = self.modified_attributes['abilities.strength']
    def _remove_weakened(self, target):
        if 'damage_modifier' in self.modified_attributes and hasattr(target, 'damage_modifier'): target.damage_modifier = self.modified_attributes['damage_modifier']
    
    def _remove_stunned(self, target):
        target_name_for_log = target.name if hasattr(target, 'name') else 'Unknown Target'
        logger.debug(f"Removing STUNNED from {target_name_for_log}")
        if 'can_take_actions' in self.modified_attributes and hasattr(target, 'can_take_actions'): target.can_take_actions = self.modified_attributes['can_take_actions']; logger.debug(f"{target_name_for_log} can_take_actions restored")
        if 'can_act' in self.modified_attributes and hasattr(target, 'can_act'): target.can_act = self.modified_attributes['can_act']; logger.debug(f"{target_name_for_log} can_act restored")
        if 'can_move' in self.modified_attributes and hasattr(target, 'can_move'): target.can_move = self.modified_attributes['can_move']; logger.debug(f"{target_name_for_log} can_move restored")
    
    def _remove_immune_poison(self, target):
        if 'immunities' in self.modified_attributes and hasattr(target, 'immunities'): target.immunities = self.modified_attributes['immunities']

class ConditionManager:
    def __init__(self):
        self.current_turn = 0
        self.last_process_time = 0
        # Log instance creation with its ID
        logger.info(f"ConditionManager (id: {id(self)}) initialized. current_turn = {self.current_turn}")

    def apply_condition(self, target, condition):
        target_name_for_log = target.name if hasattr(target, 'name') else 'Unknown Target'
        condition_name_for_log = condition.name if hasattr(condition, 'name') else 'Unknown Condition'
        
        # Log current_turn *before* it's assigned to the condition
        logger.debug(f"ConditionManager (id: {id(self)}) apply_condition: current_turn BEFORE assignment is {self.current_turn} for condition {condition_name_for_log} on {target_name_for_log}")
        condition.applied_at_turn = self.current_turn
        # Log current_turn *after* assignment to see if it changed, and the applied_at_turn value
        logger.debug(f"ConditionManager (id: {id(self)}) apply_condition: current_turn AFTER assignment is {self.current_turn} for {condition_name_for_log}, applied_at_turn = {condition.applied_at_turn}")

        result_message = condition.apply(target) # This adds the condition to target.conditions
        
        # Log the state of conditions on the target *after* applying
        if hasattr(target, 'conditions'):
            target_conditions_info = [(c.name, id(c), c.duration, c.applied_at_turn) for c in target.conditions]
            logger.debug(f"ConditionManager (id: {id(self)}) apply_condition: Conditions on {target_name_for_log} after applying {condition_name_for_log} (id: {id(condition)}): {target_conditions_info}")
        else:
            logger.debug(f"ConditionManager (id: {id(self)}) apply_condition: Target {target_name_for_log} has no conditions list after applying {condition_name_for_log} (id: {id(condition)}).")
        return result_message
    
    def process_turn(self, targets=None):
        import time 
        current_time = time.time()
        # time_since_last_process = current_time - self.last_process_time # Optional: can be verbose
        self.current_turn += 1
        messages = []
        logger.debug(f"===== PROCESSING TURN {self.current_turn} (Manager ID: {id(self)}) =====")
        self.last_process_time = current_time
        if not targets:
            logger.warning(f"No targets provided to process_turn (Manager ID: {id(self)})")
            return messages
        
        for target in targets:
            target_name_for_log = target.name if hasattr(target, 'name') else 'Unknown Target'
            
            # Initialize the flag
            if not hasattr(target, '_was_incapacitated_this_turn'):
                target._was_incapacitated_this_turn = False
            else:
                # Reset if it's a new turn for this target's processing
                target._was_incapacitated_this_turn = False 

            if not hasattr(target, 'conditions') or not target.conditions:
                # If no conditions, ensure flag is False and continue
                target._was_incapacitated_this_turn = False
                continue

            # Check for incapacitating conditions at the START of processing this target's conditions
            # Iterate once to check initial state. We only care if they *start* the turn incapacitated.
            # This flag should persist for the whole turn's logic even if the condition itself expires mid-processing.
            for c_obj_check in target.conditions: 
                if c_obj_check.condition_type == ConditionType.PARALYZED or c_obj_check.condition_type == ConditionType.STUNNED:
                    # If a PARALYZED or STUNNED condition is present in the list at this point,
                    # it means it was active at the end of the last turn or applied this turn.
                    # It should therefore incapacitate for the current turn's actions, even if it expires now.
                    target._was_incapacitated_this_turn = True
                    logger.debug(f"Target {target_name_for_log} was initially incapacitated by {c_obj_check.name} in turn {self.current_turn} because the condition is present at the start of processing. Setting _was_incapacitated_this_turn = True")
                    break # Found one, no need to check further for this initial scan
            
            # Log conditions on target *before* processing them for this turn
            target_conditions_info = [(c.name, id(c), c.duration, c.applied_at_turn) for c in target.conditions]
            logger.debug(f"ConditionManager (id: {id(self)}) process_turn (turn {self.current_turn}): Processing conditions for {target_name_for_log}. Current conditions: {target_conditions_info}, Was Incapacitated Flag: {getattr(target, '_was_incapacitated_this_turn', 'Not set')}")
            
            updated_conditions = []
            for c_obj in list(target.conditions): 
                message = c_obj.process_turn(target, self.current_turn)
                if message: messages.append(message)
                if not c_obj.is_expired(self.current_turn):
                    updated_conditions.append(c_obj)
            target.conditions = updated_conditions
        return messages

    def remove_condition(self, target, condition_type):
        if not hasattr(target, 'conditions'): return False
        removed = False
        for c_obj in list(target.conditions): 
            if c_obj.condition_type == condition_type:
                c_obj.remove(target) 
                removed = True
        return removed

    def has_condition(self, target, condition_type):
        if not hasattr(target, 'conditions'): return False
        for c_obj in target.conditions: 
            if c_obj.condition_type == condition_type: return True
        return False

    def get_conditions(self, target):
        if not hasattr(target, 'conditions'): return []
        return target.conditions

    def clear_conditions(self, target):
        if not hasattr(target, 'conditions'): return 0
        count = len(target.conditions)
        for c_obj in list(target.conditions): c_obj.remove(target)
        return count

# This is THE single global instance that should be used everywhere.
# Other files should `from Data.condition_system import condition_manager`
condition_manager = ConditionManager() 
# Log the ID of the global instance upon creation
logger.info(f"Global condition_manager (id: {id(condition_manager)}) created in Data.condition_system. Initial current_turn: {condition_manager.current_turn}")


# Helper functions using the global condition_manager
def apply_poison(target, duration=3, source=None, severity=1):
    # Log which condition_manager instance is being used by this helper
    logger.debug(f"Helper apply_poison: Using condition_manager (id: {id(condition_manager)}) with current_turn: {condition_manager.current_turn}")
    condition = Condition(ConditionType.POISONED, duration, source, severity)
    return condition_manager.apply_condition(target, condition)

def apply_paralysis(target, duration=2, source=None, severity=1):
    # Log which condition_manager instance is being used by this helper
    logger.debug(f"Helper apply_paralysis: Using condition_manager (id: {id(condition_manager)}) with current_turn: {condition_manager.current_turn}")
    condition = Condition(ConditionType.PARALYZED, duration, source, severity)
    return condition_manager.apply_condition(target, condition)

def apply_curse(target, duration=5, source=None, severity=1):
    logger.debug(f"Helper apply_curse: Using condition_manager (id: {id(condition_manager)}) with current_turn: {condition_manager.current_turn}")
    condition = Condition(ConditionType.CURSED, duration, source, severity)
    return condition_manager.apply_condition(target, condition)

def apply_protection(target, duration=3, source=None, severity=2):
    logger.debug(f"Helper apply_protection: Using condition_manager (id: {id(condition_manager)}) with current_turn: {condition_manager.current_turn}")
    condition = Condition(ConditionType.PROTECTED, duration, source, severity)
    return condition_manager.apply_condition(target, condition)
    
def apply_stun(target, duration=2, source=None, severity=1):
    logger.debug(f"Helper apply_stun: Using condition_manager (id: {id(condition_manager)}) with current_turn: {condition_manager.current_turn}")
    condition = Condition(ConditionType.STUNNED, duration, source, severity)
    return condition_manager.apply_condition(target, condition)
    
def apply_poison_immunity(target, duration=5, source=None, severity=1):
    logger.debug(f"Helper apply_poison_immunity: Using condition_manager (id: {id(condition_manager)}) with current_turn: {condition_manager.current_turn}")
    condition = Condition(ConditionType.IMMUNE_POISON, duration, source, severity)
    return condition_manager.apply_condition(target, condition)

def render_conditions(screen, character, x, y):
    import pygame 
    if not hasattr(character, 'conditions') or not character.conditions: return
    icon_size = 16; spacing = 4
    condition_colors = {
        ConditionType.POISONED: (0, 255, 0), ConditionType.PARALYZED: (100, 100, 255),
        ConditionType.DISEASED: (139, 69, 19), ConditionType.DRAINED: (128, 0, 128),
        ConditionType.CURSED: (75, 0, 130), ConditionType.SLOWED: (0, 191, 255),
        ConditionType.BURNING: (255, 165, 0), ConditionType.PROTECTED: (255, 215, 0),
        ConditionType.STRENGTHENED: (255, 0, 0), ConditionType.REGENERATING: (50, 205, 50),
        ConditionType.STUNNED: (255, 0, 255), ConditionType.IMMUNE_POISON: (0, 128, 0)
    }
    try: font_small = pygame.font.Font(None, 12)
    except pygame.error: font_small = pygame.font.SysFont("monospace", 10)

    for i, cond in enumerate(character.conditions):
        condition_x = x + (icon_size + spacing) * i; condition_y = y
        color = condition_colors.get(cond.condition_type, (200, 200, 200))
        pygame.draw.rect(screen, color, (condition_x, condition_y, icon_size, icon_size))
        # Use global condition_manager to get current_turn for rendering
        remaining = cond.get_remaining_duration(condition_manager.current_turn)
        duration_text = font_small.render(str(remaining), True, (255, 255, 255))
        text_rect = duration_text.get_rect(center=(condition_x + icon_size // 2, condition_y + icon_size // 2))
        screen.blit(duration_text, text_rect)
