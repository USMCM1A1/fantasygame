#!/usr/bin/env python
# coding: utf-8

"""
Spell Helper Functions for Blade & Sigil
This module provides utility functions for accessing and manipulating spell data
loaded from the spells.json configuration file.
"""

import json
import os
import logging

# Set up logging
logger = logging.getLogger(__name__)

def load_spells_data(spells_file):
    """
    Load spells data from JSON file.
    
    Args:
        spells_file: Path to the spells.json file
        
    Returns:
        Dictionary containing spell data
    """
    try:
        with open(spells_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading spells file: {e}")
        return {"spells": []}

def get_spell_by_name(spells_data, spell_name, class_name=None):
    """
    Find a spell by name, optionally filtering by class.
    
    Args:
        spells_data: Dictionary containing spell data
        spell_name: Name of the spell to find
        class_name: Optional class name to filter by
        
    Returns:
        Spell dictionary or None if not found
    """
    # Normalize class name for comparison
    if class_name:
        class_name = class_name.title()
    
    # Search for matching spell
    for spell in spells_data.get("spells", []):
        if spell.get("name") == spell_name:
            # If class_name is specified, check if this class can use the spell
            if class_name:
                if not any(cls.title() == class_name for cls in spell.get("classes", [])):
                    continue
            return spell
    
    return None

def get_spell_cost(spell):
    """
    Get the spell point cost of a spell.
    
    Args:
        spell: Spell dictionary
        
    Returns:
        Integer spell point cost (default: 1)
    """
    try:
        return int(spell.get("sp_cost", 1))
    except (ValueError, TypeError):
        logger.warning(f"Invalid sp_cost value for spell {spell.get('name')}, defaulting to 1")
        return 1

def get_spell_effect_type(spell):
    """
    Get the effect type of a spell (Magic, Physical, Holy, etc.).
    
    Args:
        spell: Spell dictionary
        
    Returns:
        String effect type (default: "Magic")
    """
    return spell.get("effect_type", "Magic")

def get_spell_damage(spell, caster=None):
    """
    Get the damage dice expression for a spell.
    
    Args:
        spell: Spell dictionary
        caster: Optional caster character for attribute-based calculations
        
    Returns:
        String damage dice expression or None if spell doesn't deal damage
    """
    return spell.get("damage_dice", None)

def get_spell_healing(spell, caster=None):
    """
    Get the healing dice expression for a spell.
    
    Args:
        spell: Spell dictionary
        caster: Optional caster character for attribute-based calculations
        
    Returns:
        String healing dice expression or None if spell doesn't heal
    """
    return spell.get("healing_dice", None)

def get_spell_duration(spell, caster=None):
    """
    Get the duration of a spell effect in turns.
    
    Args:
        spell: Spell dictionary
        caster: Optional caster character for attribute-based calculations
        
    Returns:
        Integer duration (default: 0 for instant effects)
    """
    try:
        base_duration = int(spell.get("duration", 0))
        
        # Handle caster attribute modifiers if needed
        # Example: duration could be increased by caster's intelligence
        if caster and hasattr(caster, 'abilities') and spell.get('duration_scales_with_ability', False):
            ability_key = 'intelligence'  # Default for wizards
            if hasattr(caster, 'char_class'):
                if caster.char_class.lower() == 'priest':
                    ability_key = 'wisdom'
                elif caster.char_class.lower() == 'spellblade':
                    ability_key = 'charisma'
            
            if ability_key in caster.abilities:
                ability_score = caster.abilities[ability_key]
                ability_mod = (ability_score - 10) // 2
                base_duration += ability_mod
        
        # Log the duration for debugging
        logger.debug(f"Spell {spell.get('name')} duration: {base_duration} turns")
        
        return max(1, base_duration)  # Ensure duration is at least 1 turn
    except (ValueError, TypeError):
        logger.warning(f"Invalid duration value for spell {spell.get('name')}, defaulting to 1")
        return 1  # Changed default to 1 to ensure effects last at least one turn

def get_spell_range(spell):
    """
    Get the maximum range of a spell in tiles.
    
    Args:
        spell: Spell dictionary
        
    Returns:
        Integer range (default based on range_type)
    """
    range_type = spell.get("range_type", "self")
    
    # If max_range is specified, use that
    if "max_range" in spell:
        try:
            return int(spell.get("max_range"))
        except (ValueError, TypeError):
            pass
    
    # Default ranges based on range_type
    if range_type == "self" or range_type == "touch":
        return 0
    elif range_type == "ranged":
        return 4  # Default ranged spell range
    else:
        return 1  # Default for other types

def get_spell_targets(spell):
    """
    Get the targeting style of a spell.
    
    Args:
        spell: Spell dictionary
        
    Returns:
        String target type (single, area, self, allies, etc.)
    """
    return spell.get("targets", "single")

def get_spell_area_size(spell):
    """
    Get the area of effect size for area spells.
    
    Args:
        spell: Spell dictionary
        
    Returns:
        Integer area size in tiles (default: 1)
    """
    try:
        return int(spell.get("area_size", 1))
    except (ValueError, TypeError):
        return 1

def get_spell_effects(spell):
    """
    Get the status effects this spell can apply.
    
    Args:
        spell: Spell dictionary
        
    Returns:
        List of status effect strings or empty list
    """
    effects = spell.get("effects", [])
    if isinstance(effects, str):
        return [effects]  # Convert single string to list
    return effects

def get_spell_ac_bonus(spell):
    """
    Get the AC bonus provided by a buff spell.
    
    Args:
        spell: Spell dictionary
        
    Returns:
        Integer AC bonus (default: 0)
    """
    try:
        return int(spell.get("ac", 0))
    except (ValueError, TypeError):
        return 0

def get_spell_damage_bonus(spell):
    """
    Get the damage bonus provided by a buff spell.
    
    Args:
        spell: Spell dictionary
        
    Returns:
        Integer damage bonus (default: 0)
    """
    try:
        return int(spell.get("dam", 0))
    except (ValueError, TypeError):
        return 0

def get_spell_light_radius(spell):
    """
    Get the light radius for light-producing spells.
    
    Args:
        spell: Spell dictionary
        
    Returns:
        Integer light radius in tiles (default: 0)
    """
    try:
        return int(spell.get("light_radius", 0))
    except (ValueError, TypeError):
        return 0

def check_spell_requirements(spell, caster, target=None, dungeon=None):
    """
    Check if a spell meets all requirements to be cast.
    
    Args:
        spell: Spell dictionary
        caster: Character trying to cast the spell
        target: Optional target character or position
        dungeon: Optional dungeon object for line-of-sight checks
        
    Returns:
        Tuple (meets_requirements, message) where meets_requirements is a boolean
        and message explains why requirements aren't met (if applicable)
    """
    # Check if caster has enough spell points
    spell_cost = get_spell_cost(spell)
    if caster.spell_points < spell_cost:
        return False, f"Not enough spell points ({caster.spell_points}/{spell_cost})"
    
    # Check class requirements
    class_key = caster.char_class.title()
    if not any(cls.title() == class_key for cls in spell.get("classes", [])):
        return False, f"{caster.char_class}s cannot cast {spell.get('name')}"
    
    # Check level requirements
    if caster.level < spell.get("level", 1):
        return False, f"Requires level {spell.get('level')} or higher"
    
    # Check range and targeting requirements if target is provided
    if target and dungeon:
        try:
            import os
            import sys
            sys.path.append(os.path.dirname(__file__))
            from targeting_system import can_target
            
            can_target_result, target_message = can_target(caster, target, spell, dungeon)
            if not can_target_result:
                return False, target_message
        except ImportError as e:
            # If targeting_system is not available, assume targeting is valid
            print(f"WARNING: targeting_system not available for target validation: {e}")
            pass
    
    return True, ""

def can_cast_spell(spell_name, caster, target=None, dungeon=None, spells_data=None):
    """
    High-level function to check if a specific spell can be cast.
    
    Args:
        spell_name: Name of the spell to check
        caster: Character trying to cast the spell
        target: Optional target character or position
        dungeon: Optional dungeon object for line-of-sight checks
        spells_data: Optional spells data dictionary (loaded from elsewhere)
        
    Returns:
        Tuple (can_cast, message, spell) where can_cast is a boolean,
        message explains why if can_cast is False, and spell is the spell data or None
    """
    if not spells_data:
        # This should be loaded from wherever your game keeps the spell data
        # The implementation will depend on your game's architecture
        return False, "Spell data not available", None
    
    spell = get_spell_by_name(spells_data, spell_name, caster.char_class)
    if not spell:
        return False, f"Spell {spell_name} not found", None
    
    meets_req, message = check_spell_requirements(spell, caster, target, dungeon)
    return meets_req, message, spell