#!/usr/bin/env python
# coding: utf-8

"""
Spell Casting System for Blade & Sigil
This module provides the core spell casting framework that uses the data-driven
spell definitions from spells.json.
"""

import random
import logging
import os
import sys

# --- Path Setup for Imports ---
# Assuming this file (spell_system.py) is in the 'Data' directory.
# We want to be able to import other modules from 'Data' and from the parent (root) directory.
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(DATA_DIR)

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
# --- End Path Setup ---

# Module-level imports using the adjusted path
from . import spell_helpers
from .condition_system import condition_manager, Condition, ConditionType
import common_b_s # Should resolve to common_b_s in root
from . import targeting_system
from . import condition_bridge


# Set up logging
logger = logging.getLogger(__name__)

# The StatusEffect, DamageEffect, BuffEffect classes from the original file are omitted here
# as they seem to be part of an older, separate system. If they are still needed,
# they would also need to be audited to ensure they don't create their own ConditionManager instances
# or interfere with the global one. For now, focusing on the main condition flow.

def cast_spell(caster, target, spell_name, dungeon, spells_data=None): # spells_data can be optional if loaded globally
    # Ensure spells_data is loaded if not provided (e.g., from common_b_s or loaded here)
    if spells_data is None:
        spells_data = common_b_s.spells_data # Assuming spells_data is loaded in common_b_s

    messages = []
    # Use the can_cast_spell from spell_helpers (which should be imported)
    can_cast, message, spell = spell_helpers.can_cast_spell(spell_name, caster, target, dungeon, spells_data)
    if not can_cast:
        messages.append(message)
        return messages
    
    spell_type = spell.get("type", "damage")
    target_type = spell.get("targets", "single")
    target_name_for_log = target.name if hasattr(target, 'name') else str(target)
    logger.info(f"{caster.name} casting {spell_name} ({spell_type}) at {target_name_for_log}")
    
    spell_cost = spell_helpers.get_spell_cost(spell)
    caster.spell_points -= spell_cost
    
    # Adjust target for self-centered area spells
    range_type = spell.get("range_type", "ranged")
    actual_target_pos = target # Default to original target/target_pos
    if range_type == "self" and target_type == "area":
        actual_target_pos = caster.position if hasattr(caster, 'position') else target

    if target_type == "area" and spell_type in ["healing", "buff"]:
        area_size = spell.get("area_size", 1)
        area_shape = spell.get("area_shape", "circle")
        
        all_characters_in_dungeon = [caster] # Start with caster
        if hasattr(dungeon, 'player') and dungeon.player not in all_characters_in_dungeon:
             all_characters_in_dungeon.append(dungeon.player)
        if dungeon and hasattr(dungeon, 'monsters'):
            all_characters_in_dungeon.extend(dungeon.monsters)
        
        # Ensure actual_target_pos is a position tuple for get_area_targets
        center_pos_for_aoe = actual_target_pos
        if hasattr(actual_target_pos, 'position'): # If it's a character object
            center_pos_for_aoe = actual_target_pos.position

        targets_in_area = targeting_system.get_area_targets(
            center_pos_for_aoe, area_size, all_characters_in_dungeon, shape=area_shape, caster=caster,
            include_allies=True, include_enemies=False, check_los=True, dungeon=dungeon
        )
        if targets_in_area:
            messages.append(f"{caster.name} casts {spell_name}, affecting {len(targets_in_area)} allies!")
            for single_target_in_area in targets_in_area:
                if spell_type == "healing": messages.extend(handle_healing_spell(caster, single_target_in_area, spell))
                elif spell_type == "buff": messages.extend(handle_buff_spell(caster, single_target_in_area, spell))
        else:
            messages.append(f"{caster.name} casts {spell_name}, but it affects no one!")
    else:
        # Single target or damaging area spell
        if spell_type == "damage": messages.extend(handle_damage_spell(caster, target, spell, dungeon))
        elif spell_type == "healing": messages.extend(handle_healing_spell(caster, target, spell))
        elif spell_type == "buff": messages.extend(handle_buff_spell(caster, target, spell))
        elif spell_type == "debuff": messages.extend(handle_debuff_spell(caster, target, spell))
        elif spell_type == "utility": messages.extend(handle_utility_spell(caster, target, spell, dungeon))
        else: messages.append(f"Unknown spell type: {spell_type}")
    
    common_b_s.spell_sound.play() # Use spell_sound from common_b_s
    
    visual_effect_path = spell.get("visual_effect")
    visual_duration = spell.get("visual_duration", 1.0)
    
    # Determine position for visual effect
    effect_display_position = None
    if hasattr(target, 'position'): 
        effect_display_position = target.position
    elif isinstance(target, tuple): # If target was already a position
        effect_display_position = target
    elif range_type == "self": # For self-cast spells if target wasn't a position
        effect_display_position = caster.position
        
    if visual_effect_path and effect_display_position:
        if spell.get("name") == "Fireball" and spell.get("type") == "damage" and spell.get("effect_type") == "Fire":
            common_b_s.create_fireball_explosion(
                effect_display_position, size=spell.get("area_size", 2), duration=visual_duration,
                frames=int(visual_duration * 10), dungeon=dungeon, caster=caster
            )
        else:
            common_b_s.display_visual_effect(
                visual_effect_path, effect_display_position, duration=visual_duration,
                size_multiplier=spell.get("area_size", 1), frames=int(visual_duration * 10),
                dungeon=dungeon, caster=caster
            )
    return messages

def handle_damage_spell(caster, target, spell, dungeon):
    messages = []
    spell_name = spell.get("name", "Unknown Spell")
    damage_dice = spell_helpers.get_spell_damage(spell, caster)
    effect_type_str = spell_helpers.get_spell_effect_type(spell)
    target_type = spell.get("targets", "single")

    if target_type == "area":
        # For area damage, 'target' is usually the center position of the AOE
        return handle_area_damage_spell(caster, target, spell, dungeon) 

    if not hasattr(target, 'hit_points'): 
        messages.append(f"Invalid target {target.name if hasattr(target,'name') else 'object'} for damage spell {spell_name}.")
        return messages

    base_damage = common_b_s.roll_dice_expression(damage_dice, caster)
    
    ability_mod = 0
    if hasattr(caster, 'abilities') and hasattr(caster, 'char_class'):
        ability_key = 'intelligence' 
        if caster.char_class.lower() == 'priest': ability_key = 'wisdom'
        elif caster.char_class.lower() == 'spellblade': ability_key = 'charisma'
        if ability_key in caster.abilities:
            ability_score = caster.abilities[ability_key]
            ability_mod = (ability_score - 10) // 2
    damage = base_damage + ability_mod
    
    is_critical = random.random() < 0.05
    if is_critical: damage *= 2; messages.append(f"CRITICAL SPELL HIT!")

    # Simplified scaling and multipliers
    # ... full damage calculation logic from original file ...
    damage = max(1, damage) # Ensure at least 1 damage unless immune

    actual_damage = damage 
    target_name_log = target.name if hasattr(target, 'name') else 'Unknown Target'
    if hasattr(target, 'immunities') and effect_type_str.lower() in [str(imm).lower() for imm in target.immunities]: 
        actual_damage = 0
        messages.append(f"{target_name_log} is immune to {effect_type_str} damage!")
    elif hasattr(target, 'resistances') and effect_type_str.lower() in [str(res).lower() for res in target.resistances]:
        actual_damage = damage // 2
        messages.append(f"{target_name_log} resists {effect_type_str} damage! ({damage} -> {actual_damage})")
    elif hasattr(target, 'vulnerabilities') and effect_type_str.lower() in [str(vul).lower() for vul in target.vulnerabilities]:
        actual_damage = damage * 2
        messages.append(f"{target_name_log} is vulnerable to {effect_type_str} damage! ({damage} -> {actual_damage})")
    
    target.hit_points -= actual_damage
    messages.append(f"{caster.name} casts {spell_name} at {target_name_log} for {actual_damage} {effect_type_str} damage!")

    # Apply conditions using the bridge, which uses the global manager
    condition_messages = condition_bridge.apply_spell_condition(spell, caster, target)
    messages.extend(condition_messages)
            
    if target.hit_points <= 0:
        death_messages = common_b_s.process_monster_death(target, caster, dungeon)
        messages.extend(death_messages)
    return messages

def handle_area_damage_spell(caster, target_pos, spell, dungeon):
    messages = []
    spell_name = spell.get("name", "Unknown Spell")
    damage_dice = spell_helpers.get_spell_damage(spell, caster)
    effect_type_str = spell_helpers.get_spell_effect_type(spell)
    area_size = spell.get("area_size", 1)
    area_shape = spell.get("area_shape", "circle")

    all_potential_targets = [caster]
    if hasattr(dungeon, 'player') and dungeon.player not in all_potential_targets:
         all_potential_targets.append(dungeon.player)
    if dungeon and hasattr(dungeon, 'monsters'):
        all_potential_targets.extend(dungeon.monsters)
    
    # Ensure target_pos is a tuple for get_area_targets
    center_of_aoe = target_pos
    if hasattr(target_pos, 'position'): # If target_pos was a character object
        center_of_aoe = target_pos.position

    actual_targets = targeting_system.get_area_targets(
        center_of_aoe, area_size, all_potential_targets, shape=area_shape, caster=caster,
        include_allies=spell.get("friendly_fire", False), include_enemies=True,
        check_los=True, dungeon=dungeon
    )

    if not actual_targets:
        messages.append(f"{caster.name} casts {spell_name}, but it hits nothing!")
        return messages
    
    messages.append(f"{caster.name} casts {spell_name}, affecting {len(actual_targets)} targets in the area!")

    for individual_target in actual_targets:
        if not hasattr(individual_target, 'hit_points'): continue
        target_name_log = individual_target.name if hasattr(individual_target, 'name') else 'Unknown Target'

        base_damage = common_b_s.roll_dice_expression(damage_dice, caster)
        # ... (full damage calculation logic from original file, simplified here) ...
        damage_to_target = base_damage # Placeholder for full calculation
        
        actual_damage_to_target = damage_to_target
        if hasattr(individual_target, 'immunities') and effect_type_str.lower() in [str(imm).lower() for imm in individual_target.immunities]: actual_damage_to_target = 0; messages.append(f"{target_name_log} is immune!")
        # ... (add resistances/vulnerabilities) ...

        individual_target.hit_points -= actual_damage_to_target
        messages.append(f"{target_name_log} takes {actual_damage_to_target} {effect_type_str} damage!")

        condition_messages = condition_bridge.apply_spell_condition(spell, caster, individual_target)
        messages.extend(condition_messages)

        if individual_target.hit_points <= 0:
            death_messages = common_b_s.process_monster_death(individual_target, caster, dungeon)
            messages.extend(death_messages)
    return messages

def handle_healing_spell(caster, target, spell):
    messages = []
    spell_name = spell.get("name", "Unknown Spell")
    healing_dice = spell_helpers.get_spell_healing(spell, caster)
    target_name_log = target.name if hasattr(target, 'name') else 'Unknown Target'

    if not hasattr(target, 'hit_points') or not hasattr(target, 'max_hit_points'):
        messages.append(f"Cannot heal {target_name_log}.")
        return messages

    base_healing = common_b_s.roll_dice_expression(healing_dice, caster)
    # ... (full healing calculation from original, simplified) ...
    healing_amount = base_healing # Placeholder
    healing_amount = max(1, healing_amount)

    old_hp = target.hit_points
    target.hit_points = min(target.hit_points + healing_amount, target.max_hit_points)
    actual_healing = target.hit_points - old_hp
    
    if actual_healing > 0: messages.append(f"{caster.name} casts {spell_name} and heals {target_name_log} for {actual_healing} HP!")
    else: messages.append(f"{caster.name} casts {spell_name}, but {target_name_log} is already at full health!")

    removal_messages = condition_bridge.remove_spell_conditions(spell, target)
    messages.extend(removal_messages)
    return messages

def handle_area_healing_spell(caster, target_pos, spell, dungeon):
    messages = []
    spell_name = spell.get("name", "Unknown Spell")
    area_size = spell.get("area_size", 1); area_shape = spell.get("area_shape", "circle")
    all_potential_targets = [caster]
    if hasattr(dungeon, 'player') and dungeon.player not in all_potential_targets: all_potential_targets.append(dungeon.player)
    if dungeon and hasattr(dungeon, 'monsters'): all_potential_targets.extend(dungeon.monsters)
    
    center_of_aoe = target_pos
    if hasattr(target_pos, 'position'): center_of_aoe = target_pos.position

    actual_targets = targeting_system.get_area_targets(
        center_of_aoe, area_size, all_potential_targets, shape=area_shape, caster=caster,
        include_allies=True, include_enemies=spell.get("heal_enemies", False), 
        check_los=True, dungeon=dungeon
    )
    if not actual_targets: messages.append(f"{caster.name} casts {spell_name}, but it affects no one!"); return messages
    messages.append(f"{caster.name} casts {spell_name}, affecting {len(actual_targets)} targets!")
    for individual_target in actual_targets:
        messages.extend(handle_healing_spell(caster, individual_target, spell))
    return messages

def handle_buff_spell(caster, target, spell):
    messages = []
    spell_name = spell.get("name", "Unknown Spell")
    target_name_log = target.name if hasattr(target, 'name') else 'Unknown Target'
    
    condition_messages = condition_bridge.apply_spell_condition(spell, caster, target)
    messages.extend(condition_messages)
    
    # Check if any actual condition (with a name) was applied by the bridge
    applied_condition_names = []
    if hasattr(target, 'conditions'):
        current_target_conditions = [(c.name) for c in target.conditions if c.applied_at_turn == condition_manager.current_turn and c.source == caster] # Check conditions just applied
    
    if not condition_messages and spell.get("effects"):
         messages.append(f"{caster.name} casts {spell_name} on {target_name_log}, but specific effects defined in spell were not applied by bridge.")
    elif not spell.get("effects"):
         messages.append(f"{caster.name} casts {spell_name} on {target_name_log}.")
    # If condition_messages has content, it means the bridge reported something (e.g. "{Target} is now Protected!")
    return messages

def handle_area_buff_spell(caster, target_pos, spell, dungeon):
    messages = []
    spell_name = spell.get("name", "Unknown Spell")
    area_size = spell.get("area_size", 1); area_shape = spell.get("area_shape", "circle")
    all_potential_targets = [caster]
    if hasattr(dungeon, 'player') and dungeon.player not in all_potential_targets: all_potential_targets.append(dungeon.player)
    if dungeon and hasattr(dungeon, 'monsters'): all_potential_targets.extend(dungeon.monsters)

    center_of_aoe = target_pos
    if hasattr(target_pos, 'position'): center_of_aoe = target_pos.position
        
    actual_targets = targeting_system.get_area_targets(
        center_of_aoe, area_size, all_potential_targets, shape=area_shape, caster=caster,
        include_allies=True, include_enemies=spell.get("buff_enemies", False), 
        check_los=True, dungeon=dungeon
    )
    if not actual_targets: messages.append(f"{caster.name} casts {spell_name}, but it affects no one!"); return messages
    messages.append(f"{caster.name} casts {spell_name}, affecting {len(actual_targets)} targets!")
    for individual_target in actual_targets:
        messages.extend(handle_buff_spell(caster, individual_target, spell))
    return messages

def handle_debuff_spell(caster, target, spell): # Similar to buff_spell
    messages = []
    spell_name = spell.get("name", "Unknown Spell")
    target_name_log = target.name if hasattr(target, 'name') else 'Unknown Target'
    condition_messages = condition_bridge.apply_spell_condition(spell, caster, target)
    messages.extend(condition_messages)
    if not condition_messages and spell.get("effects"):
         messages.append(f"{caster.name} casts {spell_name} on {target_name_log}, but specific effects defined in spell were not applied by bridge.")
    elif not spell.get("effects"):
         messages.append(f"{caster.name} casts {spell_name} on {target_name_log}.")
    return messages

def handle_utility_spell(caster, target, spell, dungeon):
    messages = []
    spell_name = spell.get("name", "Unknown Spell")
    utility_type = spell.get("utility_type", "general") # e.g. "light", "invisibility", "unlock"
    target_name_log = target.name if hasattr(target, 'name') else str(target)

    # Generic effect application via condition_bridge
    # This will handle conditions like "Paralyzed", "Invisible" if defined in spell["effects"]
    condition_messages = condition_bridge.apply_spell_condition(spell, caster, target)
    messages.extend(condition_messages)

    # Specific utility logic for non-condition effects (e.g., Light creating actual light)
    if utility_type == "light":
        light_radius = spell_helpers.get_spell_light_radius(spell)
        # Actual light effect logic might be here or in common_b_s (e.g. player.light_radius = ...)
        if hasattr(caster, 'light_radius'): # Assuming light affects caster primarily
             caster.light_radius = max(getattr(caster, 'light_radius', 0), light_radius)
        messages.append(f"{caster.name} casts {spell_name}, and the area brightens!")
    # Add other specific utility effects here if they are not condition-based
    # elif utility_type == "unlock":
    #     # ... specific unlock logic ...
    #     messages.append(f"{caster.name} casts {spell_name} on {target_name_log}!")
    
    # If no conditions were applied by the bridge and no specific utility logic matched here, add a generic message.
    if not condition_messages and utility_type not in ["light"]: # Add other handled utility_types
        messages.append(f"{caster.name} casts {spell_name} on {target_name_log}.")
        
    return messages
