#!/usr/bin/env python
# coding: utf-8

"""
Condition Bridge for Blade & Sigil
This module connects the spell system with the condition system,
allowing spells to apply and remove status conditions.
"""

import logging
from .condition_system import (
    ConditionType, Condition, condition_manager,
    apply_poison, apply_paralysis, apply_curse, apply_protection,
    apply_stun, apply_poison_immunity
)

# Set up logging
logger = logging.getLogger(__name__)

def apply_spell_condition(spell, caster, target):
    """
    Apply any conditions associated with a spell to the target.
    
    Args:
        spell: Spell data dictionary
        caster: Character casting the spell
        target: Character being affected by the spell
        
    Returns:
        list: Messages describing applied conditions
    """
    messages = []
    
    # Check if the spell applies conditions
    effects = spell.get("effects", [])
    if not effects:
        return messages
    
    # Get spell parameters
    duration = spell.get("duration", 3)  # Default 3 turns
    severity = max(1, spell.get("level", 1))  # Use spell level as default severity
    
    # Debug log the duration to track where it might be getting lost
    logger.debug(f"Applying condition(s) from spell {spell.get('name', 'unknown')} with duration {duration} and severity {severity}")
    
    # Apply each effect
    for effect in effects:
        if isinstance(effect, str):
            effect_name = effect
        elif isinstance(effect, dict):
            effect_name = effect.get("name", "")
            # Override defaults with specific values if provided
            if "duration" in effect:
                duration = effect["duration"]
            if "severity" in effect:
                severity = effect["severity"]
        else:
            continue
        
        # Apply the appropriate condition based on effect name
        message = None
        
        # Add more debug logging to track what's happening with conditions
        logger.debug(f"Applying condition '{effect_name}' with duration {duration}")
        
        if effect_name.lower() == "poisoned":
            # For debugging - ensure durations are working correctly
            logger.debug(f"Applying POISON with explicit duration {duration}")
            message = apply_poison(target, duration, caster, severity)
        elif effect_name.lower() == "paralyzed":
            message = apply_paralysis(target, duration, caster, severity)
        elif effect_name.lower() == "cursed":
            message = apply_curse(target, duration, caster, severity)
        elif effect_name.lower() == "protected":
            # For debugging - ensure durations are working correctly
            logger.debug(f"Applying PROTECTED with explicit duration {duration}")
            message = apply_protection(target, duration, caster, severity)
        elif effect_name.lower() == "stunned":
            message = apply_stun(target, duration, caster, severity)
        elif effect_name.lower() == "immune" or effect_name.lower() == "immune_poison":
            message = apply_poison_immunity(target, duration, caster, severity)
        elif effect_name.lower() == "diseased":
            condition = Condition(ConditionType.DISEASED, duration, caster, severity)
            message = condition_manager.apply_condition(target, condition)
        elif effect_name.lower() == "drained":
            condition = Condition(ConditionType.DRAINED, duration, caster, severity)
            message = condition_manager.apply_condition(target, condition)
        elif effect_name.lower() == "slowed":
            condition = Condition(ConditionType.SLOWED, duration, caster, severity)
            message = condition_manager.apply_condition(target, condition)
        elif effect_name.lower() == "blinded":
            condition = Condition(ConditionType.BLINDED, duration, caster, severity)
            message = condition_manager.apply_condition(target, condition)
        elif effect_name.lower() == "silenced":
            condition = Condition(ConditionType.SILENCED, duration, caster, severity)
            message = condition_manager.apply_condition(target, condition)
        elif effect_name.lower() == "strengthened":
            condition = Condition(ConditionType.STRENGTHENED, duration, caster, severity)
            message = condition_manager.apply_condition(target, condition)
        elif effect_name.lower() == "regenerating":
            condition = Condition(ConditionType.REGENERATING, duration, caster, severity)
            message = condition_manager.apply_condition(target, condition)
        elif effect_name.lower() == "burning":
            condition = Condition(ConditionType.BURNING, duration, caster, severity)
            message = condition_manager.apply_condition(target, condition)
        
        if message:
            messages.append(message)
    
    return messages

def remove_spell_conditions(spell, target):
    """
    Remove any conditions specified in a spell's effects_removed field.
    
    Args:
        spell: Spell data dictionary
        target: Character to remove conditions from
        
    Returns:
        list: Messages describing removed conditions
    """
    messages = []
    
    # Check if the spell removes conditions
    effects_removed = spell.get("effects_removed", [])
    if not effects_removed:
        return messages
    
    # If "all" is specified, remove all conditions
    if "all" in effects_removed:
        count = condition_manager.clear_conditions(target)
        if count > 0:
            messages.append(f"All conditions removed from {target.name}!")
        return messages
    
    # Otherwise remove specific conditions
    for effect_name in effects_removed:
        # Map effect name to condition type
        condition_type = None
        
        if effect_name.lower() == "poisoned":
            condition_type = ConditionType.POISONED
        elif effect_name.lower() == "paralyzed":
            condition_type = ConditionType.PARALYZED
        elif effect_name.lower() == "cursed":
            condition_type = ConditionType.CURSED
        elif effect_name.lower() == "diseased":
            condition_type = ConditionType.DISEASED
        elif effect_name.lower() == "drained":
            condition_type = ConditionType.DRAINED
        elif effect_name.lower() == "slowed":
            condition_type = ConditionType.SLOWED
        elif effect_name.lower() == "blinded":
            condition_type = ConditionType.BLINDED
        elif effect_name.lower() == "silenced":
            condition_type = ConditionType.SILENCED
        elif effect_name.lower() == "burning":
            condition_type = ConditionType.BURNING
        elif effect_name.lower() == "stunned":
            condition_type = ConditionType.STUNNED
        elif effect_name.lower() == "immune" or effect_name.lower() == "immune_poison":
            condition_type = ConditionType.IMMUNE_POISON
        
        # Remove the condition if found
        if condition_type and condition_manager.remove_condition(target, condition_type):
            messages.append(f"{effect_name.capitalize()} removed from {target.name}!")
    
    return messages

def check_condition_restrictions(caster, spell):
    """
    Check if a character is restricted from casting a spell due to conditions.
    
    Args:
        caster: Character attempting to cast the spell
        spell: Spell data dictionary
        
    Returns:
        tuple: (can_cast, message) where can_cast is a boolean and 
               message explains why not if applicable
    """
    # Check for silence condition which prevents spell casting
    if condition_manager.has_condition(caster, ConditionType.SILENCED):
        return False, f"{caster.name} cannot cast spells while silenced!"
    
    # Check for paralysis which prevents most actions
    if condition_manager.has_condition(caster, ConditionType.PARALYZED):
        return False, f"{caster.name} cannot cast spells while paralyzed!"
    
    # Check for stunned which prevents most actions
    if condition_manager.has_condition(caster, ConditionType.STUNNED):
        return False, f"{caster.name} cannot cast spells while stunned!"
    
    return True, ""

def integrate_spell_system_with_conditions(spell_system_module):
    """
    Enhance the spell system module to handle conditions.
    
    This function modifies the spell_system module's handle_damage_spell, 
    handle_healing_spell, etc. functions to integrate with the condition system.
    
    Args:
        spell_system_module: The module containing the spell system
    """
    # Store original functions
    original_handle_damage = spell_system_module.handle_damage_spell
    original_handle_healing = spell_system_module.handle_healing_spell
    original_can_cast_spell = spell_system_module.can_cast_spell
    
    # Define enhanced functions
    def enhanced_handle_damage(caster, target, spell, dungeon):
        # Check for immunities before handling damage
        effect_type = spell.get("effect_type", "Physical").lower()
        
        # Check if target is immune to this damage type through monster properties or conditions
        target_is_immune = False
        
        # Check direct immunities list
        if hasattr(target, 'immunities') and effect_type.lower() in [immunity.lower() for immunity in target.immunities]:
            target_is_immune = True
            messages = [f"{caster.name} casts {spell.get('name', 'Unknown Spell')}, but {target.name} is immune to {effect_type} damage!"]
        # Check for poison immunity specifically through the condition system
        elif effect_type.lower() == "poison" and condition_manager.has_condition(target, ConditionType.IMMUNE_POISON):
            target_is_immune = True
            messages = [f"{caster.name} casts {spell.get('name', 'Unknown Spell')}, but {target.name} is immune to poison damage!"]
        else:
            # Call original function if target is not immune
            messages = original_handle_damage(caster, target, spell, dungeon)
        
        # Apply conditions if the target is not immune to the primary effect type
        if not target_is_immune:
            condition_messages = apply_spell_condition(spell, caster, target)
            messages.extend(condition_messages)
        
        return messages
    
    def enhanced_handle_healing(caster, target, spell):
        # Call original function
        messages = original_handle_healing(caster, target, spell)
        
        # Remove conditions if specified
        condition_messages = remove_spell_conditions(spell, target)
        messages.extend(condition_messages)
        
        return messages
    
    def enhanced_can_cast_spell(spell_name, caster, target=None, dungeon=None, spells_data=None):
        # Check condition restrictions first
        if hasattr(caster, 'conditions') and caster.conditions:
            spell = None
            for s in spells_data.get("spells", []):
                if s.get("name") == spell_name:
                    spell = s
                    break
                    
            if spell:
                can_cast, message = check_condition_restrictions(caster, spell)
                if not can_cast:
                    return False, message, None
        
        # Call original function
        return original_can_cast_spell(spell_name, caster, target, dungeon, spells_data)
    
    # Replace the original functions with enhanced versions
    spell_system_module.handle_damage_spell = enhanced_handle_damage
    spell_system_module.handle_healing_spell = enhanced_handle_healing
    spell_system_module.can_cast_spell = enhanced_can_cast_spell
    
    # Add condition handling to spell types that don't handle them yet
    original_handle_buff = spell_system_module.handle_buff_spell
    
    def enhanced_handle_buff(caster, target, spell):
        # Call original function
        messages = original_handle_buff(caster, target, spell)
        
        # Apply conditions
        condition_messages = apply_spell_condition(spell, caster, target)
        messages.extend(condition_messages)
        
        return messages
    
    spell_system_module.handle_buff_spell = enhanced_handle_buff
    
    # Add function to process conditions in main game loop
    def process_conditions(all_characters):
        """
        Process conditions for all characters at the start of a turn.
        
        Args:
            all_characters: List of all characters (player + monsters)
            
        Returns:
            list: Messages describing condition effects
        """
        return condition_manager.process_turn(all_characters)
    
    # Add the new function to the module
    spell_system_module.process_conditions = process_conditions
