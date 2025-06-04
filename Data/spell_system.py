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
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(DATA_DIR)

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
# --- End Path Setup ---

from . import spell_helpers
from .condition_system import condition_manager, Condition, ConditionType
from . import targeting_system
from . import condition_bridge

# New imports for utilities and config
from game_config import SPELLS_FILE_CONFIG_PATH, DATA_DIR_CONFIG_PATH, RED, WHITE, YELLOW # Import colors
from game_utils import roll_dice_expression
from game_effects import spell_sound, arrow_sound, frost_sound, display_visual_effect, create_fireball_explosion_effect # Direct import of sounds and effects

# Set up logging
logger = logging.getLogger(__name__)

# Load spells_data using spell_helpers
SPELLS_FILE = os.path.join(DATA_DIR_CONFIG_PATH, SPELLS_FILE_CONFIG_PATH)
spells_data_loaded = spell_helpers.load_spells_data(SPELLS_FILE)


def cast_spell(caster, target, spell_name, dungeon, spells_data_param=None):
    current_spells_data = spells_data_param if spells_data_param is not None else spells_data_loaded
    messages = []

    can_cast, message, spell = spell_helpers.can_cast_spell(spell_name, caster, target, dungeon, current_spells_data)
    if not can_cast:
        messages.append(message)
        return messages
    
    spell_type = spell.get("type", "damage")
    target_type = spell.get("targets", "single")
    target_name_for_log = target.name if hasattr(target, 'name') else str(target)
    logger.info(f"{caster.name} casting {spell_name} ({spell_type}) at {target_name_for_log}")
    
    spell_cost = spell_helpers.get_spell_cost(spell)
    caster.spell_points -= spell_cost
    
    range_type = spell.get("range_type", "ranged")
    actual_target_pos = target
    if range_type == "self" and target_type == "area":
        actual_target_pos = caster.position if hasattr(caster, 'position') else target

    if target_type == "area" and spell_type in ["healing", "buff"]:
        area_size = spell.get("area_size", 1)
        area_shape = spell.get("area_shape", "circle")
        
        all_characters_in_dungeon = [caster]
        if hasattr(dungeon, 'player') and dungeon.player not in all_characters_in_dungeon:
             all_characters_in_dungeon.append(dungeon.player)
        if dungeon and hasattr(dungeon, 'monsters'):
            all_characters_in_dungeon.extend(dungeon.monsters)
        
        center_pos_for_aoe = actual_target_pos
        if hasattr(actual_target_pos, 'position'):
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
        if spell_type == "damage": messages.extend(handle_damage_spell(caster, target, spell, dungeon))
        elif spell_type == "healing": messages.extend(handle_healing_spell(caster, target, spell))
        elif spell_type == "buff": messages.extend(handle_buff_spell(caster, target, spell))
        elif spell_type == "debuff": messages.extend(handle_debuff_spell(caster, target, spell))
        elif spell_type == "utility": messages.extend(handle_utility_spell(caster, target, spell, dungeon))
        else: messages.append(f"Unknown spell type: {spell_type}")
    
    spell_sound.play() # Use directly imported sound
    
    visual_effect_path = spell.get("visual_effect")
    visual_duration = spell.get("visual_duration", 1.0)
    
    effect_display_position = None
    if hasattr(target, 'position'): 
        effect_display_position = target.position
    elif isinstance(target, tuple):
        effect_display_position = target
    elif range_type == "self":
        effect_display_position = caster.position
        
    if visual_effect_path and effect_display_position:
        if spell.get("name") == "Fireball" and spell.get("type") == "damage" and spell.get("effect_type") == "Fire":
            create_fireball_explosion_effect( # Use directly imported function
                effect_display_position, size=spell.get("area_size", 2), duration=visual_duration,
                frames=int(visual_duration * 10), dungeon=dungeon, caster=caster
            )
        else:
            display_visual_effect( # Use directly imported function
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
        return handle_area_damage_spell(caster, target, spell, dungeon) 

    if not hasattr(target, 'hit_points'): 
        messages.append(f"Invalid target {target.name if hasattr(target,'name') else 'object'} for damage spell {spell_name}.")
        return messages

    base_damage = roll_dice_expression(damage_dice, caster)
    
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
    damage = max(1, damage)

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

    condition_messages = condition_bridge.apply_spell_condition(spell, caster, target)
    messages.extend(condition_messages)
            
    if target.hit_points <= 0:
        target.is_dead = True
        messages.append(f"{target_name_log} was slain by {spell_name}!")
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
    
    center_of_aoe = target_pos
    if hasattr(target_pos, 'position'):
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

        base_damage = roll_dice_expression(damage_dice, caster)
        damage_to_target = base_damage
        
        actual_damage_to_target = damage_to_target
        if hasattr(individual_target, 'immunities') and effect_type_str.lower() in [str(imm).lower() for imm in individual_target.immunities]:
            actual_damage_to_target = 0
            messages.append(f"{target_name_log} is immune!")
        elif hasattr(individual_target, 'resistances') and effect_type_str.lower() in [str(res).lower() for res in individual_target.resistances]:
            actual_damage_to_target = damage_to_target // 2
            messages.append(f"{target_name_log} resists {effect_type_str} damage! ({damage_to_target} -> {actual_damage_to_target})")
        elif hasattr(individual_target, 'vulnerabilities') and effect_type_str.lower() in [str(vul).lower() for vul in individual_target.vulnerabilities]:
            actual_damage_to_target = damage_to_target * 2
            messages.append(f"{target_name_log} is vulnerable to {effect_type_str} damage! ({damage_to_target} -> {actual_damage_to_target})")


        individual_target.hit_points -= actual_damage_to_target
        messages.append(f"{target_name_log} takes {actual_damage_to_target} {effect_type_str} damage!")

        condition_messages = condition_bridge.apply_spell_condition(spell, caster, individual_target)
        messages.extend(condition_messages)

        if individual_target.hit_points <= 0:
            individual_target.is_dead = True
            messages.append(f"{target_name_log} was slain by {spell_name}!")
    return messages

def handle_healing_spell(caster, target, spell):
    messages = []
    spell_name = spell.get("name", "Unknown Spell")
    healing_dice = spell_helpers.get_spell_healing(spell, caster)
    target_name_log = target.name if hasattr(target, 'name') else 'Unknown Target'

    if not hasattr(target, 'hit_points') or not hasattr(target, 'max_hit_points'):
        messages.append(f"Cannot heal {target_name_log}.")
        return messages

    base_healing = roll_dice_expression(healing_dice, caster)
    healing_amount = max(1, base_healing)

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
    
    if not condition_messages and spell.get("effects"):
         messages.append(f"{caster.name} casts {spell_name} on {target_name_log}, but specific effects defined in spell were not applied by bridge.")
    elif not spell.get("effects") and not condition_messages :
         messages.append(f"{caster.name} casts {spell_name} on {target_name_log}.")
    return messages

def handle_area_buff_spell(caster, target_pos, spell, dungeon):
    messages = []
    spell_name = spell.get("name", "Unknown Spell")
    messages.append(f"{caster.name} casts {spell_name} affecting an area (details omitted for brevity).")
    # In a full version, this would iterate targets from get_area_targets and call handle_buff_spell for each.
    return messages

def handle_debuff_spell(caster, target, spell):
    messages = []
    spell_name = spell.get("name", "Unknown Spell")
    target_name_log = target.name if hasattr(target, 'name') else 'Unknown Target'

    condition_messages = condition_bridge.apply_spell_condition(spell, caster, target)
    messages.extend(condition_messages)

    if not condition_messages and spell.get("effects"):
         messages.append(f"{caster.name} casts {spell_name} on {target_name_log}, but specific effects were not applied by bridge.")
    elif not spell.get("effects") and not condition_messages:
         messages.append(f"{caster.name} casts {spell_name} on {target_name_log}.")
    return messages

def handle_utility_spell(caster, target, spell, dungeon):
    messages = []
    spell_name = spell.get("name", "Unknown Spell")
    utility_type = spell.get("utility_type", "general")

    condition_messages = condition_bridge.apply_spell_condition(spell, caster, target)
    messages.extend(condition_messages)

    if utility_type == "light":
        light_radius = spell_helpers.get_spell_light_radius(spell)
        if hasattr(caster, 'light_radius'):
             caster.light_radius = max(getattr(caster, 'light_radius', 0), light_radius)
        messages.append(f"{caster.name} casts {spell_name}, and the area brightens!")
    
    if not condition_messages and utility_type not in ["light"]:
        messages.append(f"{caster.name} casts {spell_name}.")
    return messages
