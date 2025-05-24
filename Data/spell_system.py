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

# Add relative path for imports
sys.path.append(os.path.dirname(__file__))
from spell_helpers import *

# Set up logging
logger = logging.getLogger(__name__)

# Status effect handling
class StatusEffect:
    """Represents a temporary status effect applied to a character."""
    
    def __init__(self, name, duration, source=None):
        self.name = name
        self.duration = duration
        self.source = source  # Character who applied the effect
        self.applied_at = 0   # Will be set when effect is applied
    
    def on_apply(self, target):
        """Called when the effect is first applied."""
        pass
    
    def on_turn(self, target):
        """Called at the beginning of the target's turn."""
        pass
    
    def on_remove(self, target):
        """Called when the effect expires or is removed."""
        pass

# Effect type implementations
class DamageEffect(StatusEffect):
    """Effect that deals damage over time (like poison or burning)."""
    
    def __init__(self, name, duration, damage_dice, damage_type, source=None):
        super().__init__(name, duration, source)
        self.damage_dice = damage_dice
        self.damage_type = damage_type
    
    def on_turn(self, target):
        """Apply damage at the beginning of the target's turn."""
        from common_b_s import roll_dice_expression, add_message
        
        damage = roll_dice_expression(self.damage_dice, self.source)
        target.hit_points -= damage
        add_message(f"{target.name} takes {damage} {self.damage_type} damage from {self.name}!")
        
        # Check if target is dead
        if target.hit_points <= 0:
            add_message(f"{target.name} has been defeated by {self.name}!")
            target.hit_points = 0
            if hasattr(target, 'is_dead'):
                target.is_dead = True

class BuffEffect(StatusEffect):
    """Effect that provides temporary stat bonuses."""
    
    def __init__(self, name, duration, stat_bonuses, source=None):
        super().__init__(name, duration, source)
        # stat_bonuses is a dict like {'ac': 2, 'strength': 1}
        self.stat_bonuses = stat_bonuses
        self.applied_bonuses = {}  # Track which bonuses were actually applied
    
    def on_apply(self, target):
        """Apply stat bonuses when the effect starts."""
        for stat, bonus in self.stat_bonuses.items():
            # Handle different types of stats
            if stat == 'ac':
                target.ac += bonus
                self.applied_bonuses[stat] = bonus
            elif stat == 'dam' and hasattr(target, 'wicked_weapon_bonus'):
                target.wicked_weapon_bonus += bonus
                self.applied_bonuses[stat] = bonus
            elif stat in target.abilities:
                target.abilities[stat] += bonus
                self.applied_bonuses[stat] = bonus
    
    def on_remove(self, target):
        """Remove the stat bonuses when the effect ends."""
        for stat, bonus in self.applied_bonuses.items():
            if stat == 'ac':
                target.ac -= bonus
            elif stat == 'dam' and hasattr(target, 'wicked_weapon_bonus'):
                target.wicked_weapon_bonus -= bonus
            elif stat in target.abilities:
                target.abilities[stat] -= bonus

# Spell casting framework
def cast_spell(caster, target, spell_name, dungeon, spells_data):
    """
    Unified spell casting function that handles all types of spells.
    
    Args:
        caster: Character casting the spell
        target: Target character or position
        spell_name: Name of the spell to cast
        dungeon: Dungeon object (for LOS checks and targeting)
        spells_data: Spell data loaded from JSON
        
    Returns:
        List of message strings describing what happened
    """
    messages = []
    
    # Check if spell can be cast
    can_cast, message, spell = can_cast_spell(spell_name, caster, target, dungeon, spells_data)
    if not can_cast:
        messages.append(message)
        return messages
    
    # Get spell type and effect type
    spell_type = spell.get("type", "damage")
    effect_type = get_spell_effect_type(spell)
    target_type = spell.get("targets", "single")
    
    # Log spell casting attempt
    logger.info(f"{caster.name} casting {spell_name} ({spell_type}) at {target}")
    
    # Deduct spell points
    spell_cost = get_spell_cost(spell)
    caster.spell_points -= spell_cost
    
    # Handle self-centered area spells like Frost Nova
    range_type = spell.get("range_type", "ranged")
    if range_type == "self" and target_type == "area":
        # Override target to use caster's position for self-centered area spells
        target = caster.position if hasattr(caster, 'position') else target
        
    # For area spells, need to get all valid targets
    if target_type == "area" and spell_type in ["healing", "buff"]:
        # This is a beneficial area spell - get all valid targets
        from targeting_system import get_area_targets
        
        area_size = spell.get("area_size", 1)
        area_shape = spell.get("area_shape", "circle")
        
        # Get all potential targets
        all_characters = [caster]
        if dungeon and hasattr(dungeon, 'monsters'):
            all_characters.extend(dungeon.monsters)
        
        # For healing/buff, typically only allies are affected
        targets = get_area_targets(
            target, 
            area_size, 
            all_characters, 
            shape=area_shape,
            caster=caster,
            include_allies=True,
            include_enemies=False,  # Don't buff enemies by default
            check_los=True,
            dungeon=dungeon
        )
        
        # Apply the spell to each target
        if targets:
            messages.append(f"{caster.name} casts {spell_name}, affecting {len(targets)} allies!")
            
            for single_target in targets:
                if spell_type == "healing":
                    messages.extend(handle_healing_spell(caster, single_target, spell))
                elif spell_type == "buff":
                    messages.extend(handle_buff_spell(caster, single_target, spell))
        else:
            messages.append(f"{caster.name} casts {spell_name}, but it affects no one!")
    else:
        # Handle regular spell casting
        if spell_type == "damage":
            # Process damage spell
            messages.extend(handle_damage_spell(caster, target, spell, dungeon))
        elif spell_type == "healing":
            # Process healing spell
            if target_type == "area" or target_type == "allies":
                # Area healing spell
                messages.extend(handle_area_healing_spell(caster, target, spell, dungeon))
            else:
                # Single-target healing spell
                messages.extend(handle_healing_spell(caster, target, spell))
        elif spell_type == "buff":
            # Process buff spell
            if target_type == "area" or target_type == "allies":
                # Area buff spell
                messages.extend(handle_area_buff_spell(caster, target, spell, dungeon))
            else:
                # Single-target buff spell
                messages.extend(handle_buff_spell(caster, target, spell))
        elif spell_type == "debuff":
            # Process debuff spell
            messages.extend(handle_debuff_spell(caster, target, spell))
        elif spell_type == "utility":
            # Process utility spell
            messages.extend(handle_utility_spell(caster, target, spell, dungeon))
        else:
            # Unknown spell type
            messages.append(f"Unknown spell type: {spell_type}")
    
    # Play appropriate sound effect based on spell type
    from common_b_s import spell_sound
    
    # Could have different sounds for different spell types
    # if hasattr(caster, 'sound_manager'):
    #     sound_to_play = get_spell_sound(spell)
    #     caster.sound_manager.play_sound(sound_to_play)
    # else:
    spell_sound.play()
    
    # Handle visual effects if specified
    visual_effect_path = spell.get("visual_effect")
    visual_duration = spell.get("visual_duration", 1.0)
    
    if visual_effect_path and hasattr(target, 'position'):
        # Import the visual effect function
        from common_b_s import display_visual_effect, create_fireball_explosion
        
        # Special handling for fireball effects
        if spell.get("name") == "Fireball" and spell.get("type") == "damage" and spell.get("effect_type") == "Fire":
            # If it's a fireball, use the dynamic effect
            area_size = spell.get("area_size", 2)
            create_fireball_explosion(
                target.position, 
                size=area_size,
                duration=visual_duration,
                frames=int(visual_duration * 10),
                dungeon=dungeon,
                caster=caster
            )
        else:
            # Generic handling for other visual effects
            display_visual_effect(
                visual_effect_path,
                target.position,
                duration=visual_duration,
                size_multiplier=spell.get("area_size", 1),
                frames=int(visual_duration * 10),
                dungeon=dungeon,
                caster=caster
            )
    
    return messages

def handle_damage_spell(caster, target, spell, dungeon):
    """
    Handle damage-dealing spells.
    
    Args:
        caster: Character casting the spell
        target: Target character or position
        spell: Spell data dictionary
        dungeon: Dungeon object
        
    Returns:
        List of message strings
    """
    from common_b_s import roll_dice_expression, process_monster_death
    import random
    
    messages = []
    
    # Get basic spell information
    spell_name = spell.get("name", "Unknown Spell")
    damage_dice = get_spell_damage(spell, caster)
    effect_type = get_spell_effect_type(spell)
    target_type = spell.get("targets", "single")
    spell_level = spell.get("level", 1)
    
    # Handle area of effect spells
    if target_type == "area":
        return handle_area_damage_spell(caster, target, spell, dungeon)
    
    # Calculate base damage from dice
    base_damage = roll_dice_expression(damage_dice, caster)
    
    # Add caster's ability modifier to damage if applicable
    ability_mod = 0
    if hasattr(caster, 'abilities') and hasattr(caster, 'char_class'):
        # Determine which ability affects spell power based on class
        ability_key = 'intelligence'  # Default for wizards
        if caster.char_class.lower() == 'priest':
            ability_key = 'wisdom'
        elif caster.char_class.lower() == 'spellblade':
            ability_key = 'charisma'
            
        # Get the modifier if the ability exists
        if ability_key in caster.abilities:
            # Convert ability score to modifier (e.g., 14 -> +2)
            ability_score = caster.abilities[ability_key]
            ability_mod = (ability_score - 10) // 2
    
    # Add ability modifier to damage
    damage = base_damage + ability_mod
    
    # Check for critical hit (5% chance)
    is_critical = random.random() < 0.05
    if is_critical:
        damage = damage * 2
        messages.append(f"CRITICAL SPELL HIT!")
    
    # Apply spell level scaling if enabled
    scaling_enabled = spell.get("scaling_enabled", False)
    if scaling_enabled:
        # Calculate level difference (how many levels above minimum)
        min_level = spell.get("level", 1)
        level_diff = caster.level - min_level
        
        # Add scaling damage per level (with a cap based on spell level)
        max_scaling_levels = 5 * spell_level  # Up to 5 levels of scaling per spell level
        scaling_levels = min(level_diff, max_scaling_levels)
        
        if scaling_levels > 0:
            # Default scaling is 1 point per level
            scaling_per_level = spell.get("scaling_per_level", 1)
            scaling_bonus = scaling_levels * scaling_per_level
            
            damage += scaling_bonus
            messages.append(f"Spell scales with caster level: +{scaling_bonus} damage!")
    
    # Apply custom damage multiplier if present
    damage_multiplier = spell.get("damage_multiplier", 1.0)
    if damage_multiplier != 1.0:
        damage = int(damage * damage_multiplier)
    
    # Guarantee minimum damage of 1 unless target is immune
    if damage < 1:
        damage = 1
    
    # Check for resistances/vulnerabilities/immunities
    from condition_system import condition_manager, ConditionType
    
    is_immune = False
    # Check direct immunities list
    if hasattr(target, 'immunities'):
        # Handle both string and enum types in immunities
        immunities_lower = []
        for immunity in target.immunities:
            if hasattr(immunity, 'lower'):
                immunities_lower.append(immunity.lower())
            elif hasattr(immunity, 'name'):
                immunities_lower.append(immunity.name.lower())
            else:
                # For any other type, convert to string and lowercase
                immunities_lower.append(str(immunity).lower())
        
        if hasattr(effect_type, 'lower'):
            if effect_type.lower() in immunities_lower:
                is_immune = True
        elif hasattr(effect_type, 'name'):
            if effect_type.name.lower() in immunities_lower:
                is_immune = True
        else:
            if str(effect_type).lower() in immunities_lower:
                is_immune = True
    # Check for poison immunity specifically through the condition system
    elif effect_type.lower() == "poison" and condition_manager.has_condition(target, ConditionType.IMMUNE_POISON):
        is_immune = True
        
    if is_immune:
        damage = 0
        messages.append(f"{target.name} is immune to {effect_type} damage!")
    elif hasattr(target, 'resistances') and effect_type in target.resistances:
        original_damage = damage
        damage = damage // 2
        messages.append(f"{target.name} resists {effect_type} damage! ({original_damage} → {damage})")
    elif hasattr(target, 'vulnerabilities') and effect_type in target.vulnerabilities:
        original_damage = damage
        damage = damage * 2
        messages.append(f"{target.name} is vulnerable to {effect_type} damage! ({original_damage} → {damage})")
    
    # Apply damage
    target.hit_points -= damage
    
    # Generate appropriate message
    if is_critical:
        messages.append(f"{caster.name} casts {spell_name} at {target.name} for {damage} {effect_type} damage! (CRITICAL)")
    else:
        messages.append(f"{caster.name} casts {spell_name} at {target.name} for {damage} {effect_type} damage!")
    
    # Apply status effects if any
    effects = get_spell_effects(spell)
    duration = get_spell_duration(spell, caster)
    
    if effects:
        from condition_system import condition_manager, ConditionType, Condition
        
        # Log information about applying effects
        logger.debug(f"Applying effects from {spell_name}: {effects} with duration {duration}")
        
        # Import the bridge module to apply spell conditions correctly
        from condition_bridge import apply_spell_condition
        
        # Apply conditions through the bridge module
        effect_messages = apply_spell_condition(spell, caster, target)
        messages.extend(effect_messages)
        return messages
        
        # Original code (commented out as we're using the bridge instead)
        # for effect_name in effects:
        #    effect_type = None
        #    severity = spell.get("severity", 1)
        #    
        #    if effect_name == "Poisoned":
        #        effect_type = ConditionType.POISONED
        #    elif effect_name == "Burning":
        #        effect_type = ConditionType.BURNING
        #    elif effect_name == "Frozen":
        #        effect_type = ConditionType.FROZEN
        #    
        #    if effect_type:
        #        condition = Condition(effect_type, duration, caster, severity)
        #        result_message = condition_manager.apply_condition(target, condition)
        #        messages.append(result_message)
    
    # Check if target is defeated
    if target.hit_points <= 0:
        death_messages = process_monster_death(target, caster, dungeon)
        messages.extend(death_messages)
    
    return messages

def handle_area_damage_spell(caster, target_pos, spell, dungeon):
    """
    Handle area-of-effect damage spells.
    
    Args:
        caster: Character casting the spell
        target_pos: Target position (center of area)
        spell: Spell data dictionary
        dungeon: Dungeon object
        
    Returns:
        List of message strings
    """
    from common_b_s import roll_dice_expression, process_monster_death
    from targeting_system import get_area_targets
    import random
    
    messages = []
    
    # Get basic spell information
    spell_name = spell.get("name", "Unknown Spell")
    damage_dice = get_spell_damage(spell, caster)
    effect_type = get_spell_effect_type(spell)
    area_size = spell.get("area_size", 1)
    spell_level = spell.get("level", 1)
    
    # Get the area shape and pattern
    area_shape = spell.get("area_shape", "circle")
    # Possible shapes: circle, square, diamond, line, cone
    
    # Special targeting types - check both targeting_type and area_type for backward compatibility
    targeting_type = spell.get("targeting_type", spell.get("area_type", "standard"))
    # Possible types: standard, burst, wall, beam, nova
    
    # Check for targeting settings
    friendly_fire = spell.get("friendly_fire", False)
    affect_caster = spell.get("affect_caster", False)
    
    # Get all potential targets in the area
    all_characters = []
    if dungeon and hasattr(dungeon, 'monsters'):
        all_characters.extend(dungeon.monsters)
        
    # Add player characters (including the caster)
    if dungeon and hasattr(dungeon, 'player'):
        all_characters.append(dungeon.player)
    else:
        # If we can't find the player through dungeon, add the caster directly
        all_characters.append(caster)
    
    # Handle self-targeting spells (always use caster's position)
    range_type = spell.get("range_type", "ranged")
    if range_type == "self":
        target_pos = caster.position if hasattr(caster, 'position') else target_pos
    
    # Handle different targeting types
    if targeting_type == "standard" or targeting_type == "burst":
        # Standard area targeting (centered on target position)
        targets = get_area_targets(
            target_pos, 
            area_size, 
            all_characters, 
            shape=area_shape,
            caster=caster,
            include_allies=friendly_fire,
            include_enemies=True,
            check_los=True,  # Require line of sight to targets
            dungeon=dungeon
        )
    elif targeting_type == "nova":
        # Nova is centered on the caster
        targets = get_area_targets(
            caster.position if hasattr(caster, 'position') else target_pos,
            area_size, 
            all_characters, 
            shape=area_shape,
            caster=caster,
            include_allies=friendly_fire,
            include_enemies=True,
            check_los=True,
            dungeon=dungeon
        )
    elif targeting_type == "beam" or targeting_type == "line":
        # Beam goes in a line from caster to target
        from targeting_system import targeting_system
        
        # Get caster position
        caster_pos = caster.position if hasattr(caster, 'position') else (0, 0)
        
        # Calculate line path from caster to target
        line_width = spell.get("line_width", 1)  # Width of the beam
        
        # Get all tiles in the line
        line_tiles = targeting_system.get_line_of_effect(caster_pos, target_pos, width=line_width)
        
        # Find characters in those tiles
        targets = []
        for character in all_characters:
            if not hasattr(character, 'position'):
                continue
                
            char_tile = targeting_system.pixel_to_tile(character.position)
            
            if char_tile in line_tiles:
                # Filter by ally/enemy status
                is_ally = targeting_system.is_ally(caster, character)
                
                if (is_ally and friendly_fire) or (not is_ally):
                    targets.append(character)
    elif targeting_type == "cone":
        # Cone projecting from the caster in the direction of the target
        from targeting_system import targeting_system
        import math
        
        # Get caster position
        caster_pos = caster.position if hasattr(caster, 'position') else (0, 0)
        
        # Calculate direction vector from caster to target
        dx = target_pos[0] - caster_pos[0]
        dy = target_pos[1] - caster_pos[1]
        
        # Get cone angle (in degrees)
        cone_angle = spell.get("cone_angle", 90)  # Default to 90 degree cone
        
        # Get all tiles in the cone
        cone_tiles = targeting_system.get_cone_of_effect(
            caster_pos, 
            (dx, dy), 
            area_size, 
            cone_angle
        )
        
        # Find characters in those tiles
        targets = []
        for character in all_characters:
            if not hasattr(character, 'position'):
                continue
                
            char_tile = targeting_system.pixel_to_tile(character.position)
            
            if char_tile in cone_tiles:
                # Filter by ally/enemy status
                is_ally = targeting_system.is_ally(caster, character)
                
                if (is_ally and friendly_fire) or (not is_ally):
                    targets.append(character)
    else:
        # Default to standard area targeting
        targets = get_area_targets(
            target_pos, 
            area_size, 
            all_characters, 
            shape=area_shape,
            caster=caster,
            include_allies=friendly_fire,
            include_enemies=True,
            check_los=True,
            dungeon=dungeon
        )
    
    # Filter out caster if they shouldn't be affected
    if not affect_caster:
        targets = [target for target in targets if target != caster]
    
    # Apply effects to all targets in the area
    if not targets:
        messages.append(f"{caster.name} casts {spell_name}, but it hits nothing!")
        return messages
    
    # Add initial message with appropriate description based on targeting type
    if targeting_type == "standard" or targeting_type == "burst":
        if len(targets) == 1:
            messages.append(f"{caster.name} casts {spell_name}, creating a burst of {effect_type} energy that hits 1 target!")
        else:
            messages.append(f"{caster.name} casts {spell_name}, creating a burst of {effect_type} energy that hits {len(targets)} targets!")
        
        # Handle visual effects for area spells
        visual_effect_path = spell.get("visual_effect")
        visual_duration = spell.get("visual_duration", 1.0)
        
        if visual_effect_path:
            # Import the visual effect function
            from common_b_s import display_visual_effect, create_fireball_explosion
            
            # Special handling for fireball effects
            if spell.get("name") == "Fireball" and spell.get("effect_type") == "Fire":
                # If it's a fireball, use the dynamic effect
                area_size = spell.get("area_size", 2)
                create_fireball_explosion(
                    target_pos, 
                    size=area_size,
                    duration=visual_duration,
                    frames=int(visual_duration * 10),
                    dungeon=dungeon,
                    caster=caster
                )
            else:
                # Generic handling for other visual effects
                display_visual_effect(
                    visual_effect_path,
                    target_pos,
                    duration=visual_duration,
                    size_multiplier=spell.get("area_size", 1),
                    frames=int(visual_duration * 10),
                    dungeon=dungeon,
                    caster=caster
                )
    
    elif targeting_type == "nova":
        if len(targets) == 1:
            messages.append(f"{caster.name} casts {spell_name}, releasing a nova of {effect_type} energy that hits 1 target!")
        else:
            messages.append(f"{caster.name} casts {spell_name}, releasing a nova of {effect_type} energy that hits {len(targets)} targets!")
    
    elif targeting_type == "beam" or targeting_type == "line":
        if len(targets) == 1:
            messages.append(f"{caster.name} casts {spell_name}, firing a beam of {effect_type} energy that hits 1 target!")
        else:
            messages.append(f"{caster.name} casts {spell_name}, firing a beam of {effect_type} energy that hits {len(targets)} targets!")
    
    elif targeting_type == "cone":
        if len(targets) == 1:
            messages.append(f"{caster.name} casts {spell_name}, unleashing a cone of {effect_type} energy that hits 1 target!")
        else:
            messages.append(f"{caster.name} casts {spell_name}, unleashing a cone of {effect_type} energy that hits {len(targets)} targets!")
    
    else:
        # Generic message
        if len(targets) == 1:
            messages.append(f"{caster.name} casts {spell_name}, affecting 1 target in the area!")
        else:
            messages.append(f"{caster.name} casts {spell_name}, affecting {len(targets)} targets in the area!")
    
    # Log details about who is affected
    logger.debug(f"Area spell {spell_name} affects: {[t.name for t in targets if hasattr(t, 'name')]}")
    
    # Apply damage to each target
    status_effects = get_spell_effects(spell)
    duration = get_spell_duration(spell, caster)
    
    # Calculate caster's ability modifier (once for all targets)
    ability_mod = 0
    if hasattr(caster, 'abilities') and hasattr(caster, 'char_class'):
        # Determine which ability affects spell power based on class
        ability_key = 'intelligence'  # Default for wizards
        if caster.char_class.lower() == 'priest':
            ability_key = 'wisdom'
        elif caster.char_class.lower() == 'spellblade':
            ability_key = 'charisma'
            
        # Get the modifier if the ability exists
        if ability_key in caster.abilities:
            # Convert ability score to modifier (e.g., 14 -> +2)
            ability_score = caster.abilities[ability_key]
            ability_mod = (ability_score - 10) // 2
    
    for target in targets:
        # Calculate base damage from dice
        base_damage = roll_dice_expression(damage_dice, caster)
        
        # Add ability modifier to damage
        damage = base_damage + ability_mod
        
        # For AOE spells, usually reduced damage compared to single target
        # This can be configured per spell with an area_damage_multiplier
        aoe_multiplier = spell.get("area_damage_multiplier", 0.75)
        damage = int(damage * aoe_multiplier)
        
        # Apply spell level scaling if enabled
        scaling_enabled = spell.get("scaling_enabled", False)
        scaling_bonus = 0
        if scaling_enabled:
            # Calculate level difference (how many levels above minimum)
            min_level = spell.get("level", 1)
            level_diff = caster.level - min_level
            
            # Add scaling damage per level (with a cap based on spell level)
            max_scaling_levels = 3 * spell_level  # Less scaling for AOE spells
            scaling_levels = min(level_diff, max_scaling_levels)
            
            if scaling_levels > 0:
                # Default scaling is 1 point per level
                scaling_per_level = spell.get("scaling_per_level", 1)
                scaling_bonus = scaling_levels * scaling_per_level
                damage += scaling_bonus
        
        # Apply custom damage multiplier if present
        damage_multiplier = spell.get("damage_multiplier", 1.0)
        if damage_multiplier != 1.0:
            damage = int(damage * damage_multiplier)
        
        # Distance from center can reduce damage (optional)
        if spell.get("distance_falloff", False) and hasattr(target, 'position'):
            from targeting_system import targeting_system
            # Calculate distance from target to center
            dist = targeting_system.calculate_euclidean_distance(target_pos, target.position)
            # Each tile away from center reduces damage by 10%
            falloff_per_tile = spell.get("falloff_per_tile", 0.1)
            if dist > 0:
                dist_multiplier = max(0.5, 1.0 - (dist * falloff_per_tile))
                damage = int(damage * dist_multiplier)
        
        # Guarantee minimum damage of 1 unless target is immune
        if damage < 1:
            damage = 1
        
        # Check for resistances/vulnerabilities/immunities
        from condition_system import condition_manager, ConditionType
        
        is_immune = False
        # Check direct immunities list
        if hasattr(target, 'immunities'):
            # Handle both string and enum types in immunities
            immunities_lower = []
            for immunity in target.immunities:
                if hasattr(immunity, 'lower'):
                    immunities_lower.append(immunity.lower())
                elif hasattr(immunity, 'name'):
                    immunities_lower.append(immunity.name.lower())
                else:
                    # For any other type, convert to string and lowercase
                    immunities_lower.append(str(immunity).lower())
            
            if hasattr(effect_type, 'lower'):
                if effect_type.lower() in immunities_lower:
                    is_immune = True
            elif hasattr(effect_type, 'name'):
                if effect_type.name.lower() in immunities_lower:
                    is_immune = True
            else:
                if str(effect_type).lower() in immunities_lower:
                    is_immune = True
        # Check for poison immunity specifically through the condition system
        elif effect_type.lower() == "poison" and condition_manager.has_condition(target, ConditionType.IMMUNE_POISON):
            is_immune = True
            
        if is_immune:
            damage = 0
            messages.append(f"{target.name} is immune to {effect_type} damage!")
        elif hasattr(target, 'resistances') and effect_type in target.resistances:
            original_damage = damage
            damage = damage // 2
            messages.append(f"{target.name} resists {effect_type} damage! ({original_damage} → {damage})")
        elif hasattr(target, 'vulnerabilities') and effect_type in target.vulnerabilities:
            original_damage = damage
            damage = damage * 2
            messages.append(f"{target.name} is vulnerable to {effect_type} damage! ({original_damage} → {damage})")
        
        # Apply damage
        target.hit_points -= damage
        
        # Include scaling info in message if applicable
        if scaling_bonus > 0:
            messages.append(f"{target.name} takes {damage} {effect_type} damage! (including +{scaling_bonus} from caster level)")
        else:
            messages.append(f"{target.name} takes {damage} {effect_type} damage!")
        
        # Apply status effects if any
        if status_effects:
            from condition_system import condition_manager, ConditionType, Condition
            
            for effect_name in status_effects:
                effect_type = None
                severity = spell.get("severity", 1)
                
                if effect_name == "Poisoned":
                    effect_type = ConditionType.POISONED
                elif effect_name == "Burning":
                    effect_type = ConditionType.BURNING
                elif effect_name == "Frozen":
                    effect_type = ConditionType.FROZEN
                elif effect_name == "Stunned":
                    effect_type = ConditionType.STUNNED
                elif effect_name == "Slowed":
                    effect_type = ConditionType.SLOWED
                
                if effect_type:
                    # For AOE spells, effects might have shorter duration
                    aoe_duration_multiplier = spell.get("area_duration_multiplier", 0.75)
                    adjusted_duration = max(1, int(duration * aoe_duration_multiplier))
                    
                    condition = Condition(effect_type, adjusted_duration, caster, severity)
                    result_message = condition_manager.apply_condition(target, condition)
                    messages.append(result_message)
        
        # Check if target is defeated
        if target.hit_points <= 0:
            death_messages = process_monster_death(target, caster, dungeon)
            messages.extend(death_messages)
    
    return messages

def handle_healing_spell(caster, target, spell):
    """
    Handle healing spells.
    
    Args:
        caster: Character casting the spell
        target: Target character
        spell: Spell data dictionary
        
    Returns:
        List of message strings
    """
    from common_b_s import roll_dice_expression
    import random
    
    messages = []
    
    # Get basic spell information
    spell_name = spell.get("name", "Unknown Spell")
    healing_dice = get_spell_healing(spell, caster)
    effect_type = get_spell_effect_type(spell)
    spell_level = spell.get("level", 1)
    target_type = spell.get("targets", "single")
    
    # Handle area healing (like Mass Cure Wounds) separately
    if target_type == "area" or target_type == "allies":
        # This should be handled by the main cast_spell function
        # which will call handle_healing_spell for each target
        pass
    
    # Calculate base healing from dice
    base_healing = roll_dice_expression(healing_dice, caster)
    
    # Add caster's ability modifier to healing
    ability_mod = 0
    if hasattr(caster, 'abilities') and hasattr(caster, 'char_class'):
        # Determine which ability affects healing based on class
        ability_key = 'wisdom'  # Default for priests
        if caster.char_class.lower() == 'wizard':
            ability_key = 'intelligence'
        elif caster.char_class.lower() == 'spellblade':
            ability_key = 'charisma'
            
        # Get the modifier if the ability exists
        if ability_key in caster.abilities:
            # Convert ability score to modifier (e.g., 14 -> +2)
            ability_score = caster.abilities[ability_key]
            ability_mod = (ability_score - 10) // 2
    
    # Add ability modifier to healing
    healing = base_healing + ability_mod
    
    # Check for critical healing (5% chance)
    is_critical = random.random() < 0.05
    if is_critical:
        healing = healing * 2
        messages.append(f"CRITICAL HEALING!")
    
    # Apply spell level scaling if enabled
    scaling_enabled = spell.get("scaling_enabled", False)
    if scaling_enabled:
        # Calculate level difference (how many levels above minimum)
        min_level = spell.get("level", 1)
        level_diff = caster.level - min_level
        
        # Add scaling healing per level (with a cap based on spell level)
        max_scaling_levels = 5 * spell_level  # Up to 5 levels of scaling per spell level
        scaling_levels = min(level_diff, max_scaling_levels)
        
        if scaling_levels > 0:
            # Default scaling is 1 point per level
            scaling_per_level = spell.get("scaling_per_level", 1)
            scaling_bonus = scaling_levels * scaling_per_level
            
            healing += scaling_bonus
            if scaling_bonus > 0:
                messages.append(f"Spell scales with caster level: +{scaling_bonus} healing!")
    
    # Apply custom healing multiplier if present (some classes may have healing bonuses)
    healing_multiplier = spell.get("healing_multiplier", 1.0)
    
    # Check if caster has a healing bonus ability
    if hasattr(caster, 'healing_bonus_multiplier'):
        healing_multiplier *= caster.healing_bonus_multiplier
    
    if healing_multiplier != 1.0:
        healing = int(healing * healing_multiplier)
    
    # Guarantee minimum healing of 1
    if healing < 1:
        healing = 1
    
    # Apply healing
    old_hp = target.hit_points
    max_hp = getattr(target, 'max_hit_points', 100)  # Default to 100 if not defined
    target.hit_points = min(target.hit_points + healing, max_hp)
    actual_healing = target.hit_points - old_hp
    
    # Generate appropriate message
    if actual_healing > 0:
        if is_critical:
            messages.append(f"{caster.name} casts {spell_name} and heals {target.name} for {actual_healing} HP! (CRITICAL)")
        else:
            messages.append(f"{caster.name} casts {spell_name} and heals {target.name} for {actual_healing} HP!")
    else:
        messages.append(f"{caster.name} casts {spell_name}, but {target.name} is already at full health!")
    
    # Remove status effects if specified
    effects_removed = spell.get("effects_removed", [])
    
    if effects_removed:
        from condition_system import condition_manager, ConditionType
        
        for effect_name in effects_removed:
            effect_removed = False
            
            # Map effect name to condition type
            if effect_name == "Poisoned":
                effect_removed = condition_manager.remove_condition(target, ConditionType.POISONED)
                if effect_removed:
                    messages.append(f"{target.name} is no longer poisoned!")
            
            elif effect_name == "Diseased":
                effect_removed = condition_manager.remove_condition(target, ConditionType.DISEASED)
                if effect_removed:
                    messages.append(f"{target.name} is cured of disease!")
            
            elif effect_name == "Cursed":
                effect_removed = condition_manager.remove_condition(target, ConditionType.CURSED)
                if effect_removed:
                    messages.append(f"{target.name} is no longer cursed!")
            
            elif effect_name == "Burning":
                effect_removed = condition_manager.remove_condition(target, ConditionType.BURNING)
                if effect_removed:
                    messages.append(f"The flames engulfing {target.name} are extinguished!")
            
            elif effect_name == "Frozen":
                effect_removed = condition_manager.remove_condition(target, ConditionType.FROZEN)
                if effect_removed:
                    messages.append(f"{target.name} is no longer frozen!")
            
            elif effect_name == "all":
                # Remove all negative effects
                num_removed = condition_manager.clear_conditions(target)
                if num_removed > 0:
                    messages.append(f"All negative effects are removed from {target.name}!")
    
    return messages

def handle_area_healing_spell(caster, target_pos, spell, dungeon):
    """
    Handle area-of-effect healing spells.
    
    Args:
        caster: Character casting the spell
        target_pos: Target position (center of area)
        spell: Spell data dictionary
        dungeon: Dungeon object
        
    Returns:
        List of message strings
    """
    from targeting_system import get_area_targets
    
    messages = []
    
    # Get basic spell information
    spell_name = spell.get("name", "Unknown Spell")
    healing_dice = get_spell_healing(spell, caster)
    effect_type = get_spell_effect_type(spell)
    area_size = spell.get("area_size", 1)
    area_shape = spell.get("area_shape", "circle")
    spell_level = spell.get("level", 1)
    
    # Healing spells typically only target allies
    include_enemies = spell.get("include_enemies", False)
    
    # Get all potential targets in the area
    all_characters = []
    if dungeon and hasattr(dungeon, 'monsters'):
        all_characters.extend(dungeon.monsters)
        
    # Add player characters (including the caster)
    if dungeon and hasattr(dungeon, 'player'):
        all_characters.append(dungeon.player)
    else:
        # If we can't find the player through dungeon, add the caster directly
        all_characters.append(caster)
    
    # Get targets within the area of effect
    targets = get_area_targets(
        target_pos, 
        area_size, 
        all_characters, 
        shape=area_shape,
        caster=caster,
        include_allies=True,      # Always include allies for healing
        include_enemies=include_enemies,  # Usually don't include enemies for healing
        check_los=True,         
        dungeon=dungeon
    )
    
    # Apply effects to all targets in the area
    if not targets:
        messages.append(f"{caster.name} casts {spell_name}, but it affects no one!")
        return messages
    
    # Add initial message with appropriate description
    if len(targets) == 1:
        messages.append(f"{caster.name} casts {spell_name}, channeling healing energy to 1 ally!")
    else:
        messages.append(f"{caster.name} casts {spell_name}, channeling healing energy to {len(targets)} allies!")
    
    # Area healing is typically less powerful per target than single-target healing
    aoe_healing_multiplier = spell.get("area_healing_multiplier", 0.75)
    
    # Calculate caster's ability modifier (once for all targets)
    ability_mod = 0
    if hasattr(caster, 'abilities') and hasattr(caster, 'char_class'):
        # Determine which ability affects healing based on class
        ability_key = 'wisdom'  # Default for priests
        if caster.char_class.lower() == 'wizard':
            ability_key = 'intelligence'
        elif caster.char_class.lower() == 'spellblade':
            ability_key = 'charisma'
            
        # Get the modifier if the ability exists
        if ability_key in caster.abilities:
            # Convert ability score to modifier (e.g., 14 -> +2)
            ability_score = caster.abilities[ability_key]
            ability_mod = (ability_score - 10) // 2
    
    # Apply healing and effect removal to each target
    for target in targets:
        # Call the single-target handler but with reduced healing
        # We'll create a modified spell data with the area multiplier applied
        modified_spell = spell.copy()
        
        # Apply AOE multiplier to healing dice
        # This modifies the dice formula, like "2d8" -> "2d8*0.75"
        if healing_dice and aoe_healing_multiplier != 1.0:
            modified_spell["healing_multiplier"] = aoe_healing_multiplier
        
        # Get healing messages for this target
        target_messages = handle_healing_spell(caster, target, modified_spell)
        
        # Add all non-redundant messages
        for msg in target_messages:
            if msg not in messages:  # Skip duplicated effect removal messages
                messages.append(msg)
    
    return messages

def handle_buff_spell(caster, target, spell):
    """
    Handle buff spells that provide temporary bonuses.
    
    Args:
        caster: Character casting the spell
        target: Target character
        spell: Spell data dictionary
        
    Returns:
        List of message strings
    """
    messages = []
    
    # Get basic spell information
    spell_name = spell.get("name", "Unknown Spell")
    effect_type = get_spell_effect_type(spell)
    spell_level = spell.get("level", 1)
    target_type = spell.get("targets", "single")
    
    # Calculate base duration
    base_duration = get_spell_duration(spell, caster)
    
    # Apply scaling to duration if enabled
    duration_scaling = spell.get("duration_scaling", False)
    if duration_scaling and hasattr(caster, 'level'):
        # Each level above minimum adds 1 turn duration
        min_level = spell.get("level", 1)
        level_diff = caster.level - min_level
        
        # Cap the scaling based on spell level
        max_scaling_levels = 3 * spell_level
        scaling_levels = min(level_diff, max_scaling_levels)
        
        if scaling_levels > 0:
            scaling_per_level = spell.get("duration_per_level", 1)
            duration_bonus = scaling_levels * scaling_per_level
            base_duration += duration_bonus
    
    # Final duration
    duration = base_duration
    
    # Create stat bonuses dictionary
    stat_bonuses = {}
    
    # Add AC bonus if present
    ac_bonus = get_spell_ac_bonus(spell)
    if ac_bonus > 0:
        stat_bonuses["ac"] = ac_bonus
    
    # Add damage bonus if present
    dam_bonus = get_spell_damage_bonus(spell)
    if dam_bonus > 0:
        stat_bonuses["dam"] = dam_bonus
    
    # Add attack bonus if present
    if "to_hit_bonus" in spell:
        try:
            stat_bonuses["attack_bonus"] = int(spell.get("to_hit_bonus"))
        except (ValueError, TypeError):
            pass
    
    # Add saving throw bonuses if present
    if "save_bonus" in spell:
        try:
            save_bonus = int(spell.get("save_bonus"))
            stat_bonuses["save_bonus"] = save_bonus
        except (ValueError, TypeError):
            pass
    
    # Add ability score bonuses if present
    for ability in ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]:
        ability_key = f"{ability}_bonus"
        if ability_key in spell:
            try:
                bonus = int(spell.get(ability_key))
                stat_bonuses[ability] = bonus
            except (ValueError, TypeError):
                pass
    
    # Add movement speed bonus if present
    if "speed_bonus" in spell:
        try:
            stat_bonuses["speed"] = int(spell.get("speed_bonus"))
        except (ValueError, TypeError):
            pass
    
    # Add spell resistance if present
    if "spell_resistance" in spell:
        try:
            stat_bonuses["spell_resistance"] = int(spell.get("spell_resistance"))
        except (ValueError, TypeError):
            pass
    
    # Add temporary hit points if present
    if "temp_hp" in spell:
        try:
            temp_hp = int(spell.get("temp_hp"))
            # Scale temp HP with caster level if enabled
            if spell.get("temp_hp_scaling", False) and hasattr(caster, 'level'):
                min_level = spell.get("level", 1)
                level_diff = caster.level - min_level
                
                if level_diff > 0:
                    temp_hp_per_level = spell.get("temp_hp_per_level", 1)
                    temp_hp += level_diff * temp_hp_per_level
            
            stat_bonuses["temp_hp"] = temp_hp
        except (ValueError, TypeError):
            pass
    
    # Check for special abilities granted by the spell
    special_abilities = spell.get("grant_abilities", [])
    if special_abilities:
        stat_bonuses["special_abilities"] = special_abilities
    
    # Apply the buff effect through the effect manager
    from effect_manager import effect_manager
    from condition_system import ConditionType, Condition
    
    # Create appropriate condition based on buff type
    condition_type = None
    condition_name = spell_name
    
    # Map effects to condition types
    effects = get_spell_effects(spell)
    for effect in effects:
        if effect == "Strengthened":
            condition_type = ConditionType.STRENGTHENED
        elif effect == "Protected":
            condition_type = ConditionType.PROTECTED
        elif effect == "Hasted":
            condition_type = ConditionType.HASTED
        elif effect == "Blessed":
            condition_type = ConditionType.BLESSED
        elif effect == "Regenerating":
            condition_type = ConditionType.REGENERATING
        elif effect == "Invisible":
            condition_type = ConditionType.INVISIBLE
    
    # If no specific condition type matched, use PROTECTED as default
    if not condition_type and len(stat_bonuses) > 0:
        condition_type = ConditionType.PROTECTED
    
    buff_applied = False
    
    # Apply the buff effect
    if condition_type and stat_bonuses:
        # Create condition with appropriate severity based on spell level
        severity = max(1, spell_level)
        condition = Condition(condition_type, duration, caster, severity, stat_bonuses)
        
        # Apply condition to target
        from condition_system import condition_manager
        result_message = condition_manager.apply_condition(target, condition)
        messages.append(result_message)
        buff_applied = True
        
        # Build message about applied buffs
        buff_description = []
        for stat, bonus in stat_bonuses.items():
            if stat == "ac":
                buff_description.append(f"+{bonus} AC")
            elif stat == "dam":
                buff_description.append(f"+{bonus} damage")
            elif stat == "attack_bonus":
                buff_description.append(f"+{bonus} to hit")
            elif stat == "save_bonus":
                buff_description.append(f"+{bonus} to saves")
            elif stat == "temp_hp":
                buff_description.append(f"{bonus} temporary HP")
            elif stat == "speed":
                buff_description.append(f"+{bonus} movement speed")
            elif stat == "spell_resistance":
                buff_description.append(f"{bonus}% spell resistance")
            elif stat == "special_abilities":
                for ability in bonus:
                    buff_description.append(ability)
            elif stat in ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]:
                buff_description.append(f"+{bonus} {stat.capitalize()}")
            else:
                buff_description.append(f"+{bonus} {stat}")
        
        buff_text = ", ".join(buff_description)
        
        # Generate custom message based on the spell effect
        if "Invisible" in effects:
            messages.append(f"{caster.name} casts {spell_name}, making {target.name} invisible for {duration} turns!")
        elif "Regenerating" in effects:
            messages.append(f"{caster.name} casts {spell_name}, granting {target.name} regeneration for {duration} turns!")
        else:
            messages.append(f"{caster.name} casts {spell_name} on {target.name}, granting {buff_text} for {duration} turns!")
    
    # If no buffs were applied, show a failure message
    if not buff_applied:
        messages.append(f"{caster.name} casts {spell_name} on {target.name}, but it has no effect!")
    
    return messages

def handle_area_buff_spell(caster, target_pos, spell, dungeon):
    """
    Handle area-of-effect buff spells.
    
    Args:
        caster: Character casting the spell
        target_pos: Target position (center of area)
        spell: Spell data dictionary
        dungeon: Dungeon object
        
    Returns:
        List of message strings
    """
    from targeting_system import get_area_targets
    
    messages = []
    
    # Get basic spell information
    spell_name = spell.get("name", "Unknown Spell")
    effect_type = get_spell_effect_type(spell)
    area_size = spell.get("area_size", 1)
    area_shape = spell.get("area_shape", "circle")
    spell_level = spell.get("level", 1)
    
    # Buff spells typically only target allies
    include_enemies = spell.get("include_enemies", False)
    
    # Get all potential targets in the area
    all_characters = []
    if dungeon and hasattr(dungeon, 'monsters'):
        all_characters.extend(dungeon.monsters)
        
    # Add player characters (including the caster)
    if dungeon and hasattr(dungeon, 'player'):
        all_characters.append(dungeon.player)
    else:
        # If we can't find the player through dungeon, add the caster directly
        all_characters.append(caster)
    
    # Get targets within the area of effect
    targets = get_area_targets(
        target_pos, 
        area_size, 
        all_characters, 
        shape=area_shape,
        caster=caster,
        include_allies=True,      # Always include allies for buffs
        include_enemies=include_enemies,  # Usually don't include enemies for buffs
        check_los=True,         
        dungeon=dungeon
    )
    
    # Apply effects to all targets in the area
    if not targets:
        messages.append(f"{caster.name} casts {spell_name}, but it affects no one!")
        return messages
    
    # Add initial message with appropriate description
    if len(targets) == 1:
        messages.append(f"{caster.name} casts {spell_name}, empowering 1 ally!")
    else:
        messages.append(f"{caster.name} casts {spell_name}, empowering {len(targets)} allies!")
    
    # For area buffs, we might reduce the bonus or duration slightly
    area_bonus_multiplier = spell.get("area_bonus_multiplier", 1.0)  # Usually full strength
    area_duration_multiplier = spell.get("area_duration_multiplier", 0.8)  # Slightly reduced duration
    
    # Apply buff to each target
    for target in targets:
        # Create a modified version of the spell for each target
        modified_spell = spell.copy()
        
        # Apply area multipliers
        if area_bonus_multiplier != 1.0:
            # Modify all numerical bonuses
            for key in ["ac", "dam", "to_hit_bonus", "save_bonus", "strength_bonus", 
                       "dexterity_bonus", "constitution_bonus", "intelligence_bonus", 
                       "wisdom_bonus", "charisma_bonus", "speed_bonus", "spell_resistance"]:
                if key in modified_spell:
                    try:
                        modified_spell[key] = int(modified_spell[key] * area_bonus_multiplier)
                    except (ValueError, TypeError):
                        pass
                        
        # Modify duration
        if area_duration_multiplier != 1.0:
            base_duration = get_spell_duration(spell, caster)
            modified_spell["duration"] = max(1, int(base_duration * area_duration_multiplier))
        
        # Get buff messages for this target
        target_messages = handle_buff_spell(caster, target, modified_spell)
        
        # Add non-redundant messages
        for msg in target_messages:
            if msg not in messages:
                messages.append(msg)
    
    return messages

def handle_utility_spell(caster, target, spell, dungeon):
    """
    Handle utility spells like Light, Invisibility, Dispel, Detect, etc.
    
    Args:
        caster: Character casting the spell
        target: Target character or position
        spell: Spell data dictionary
        dungeon: Dungeon object
        
    Returns:
        List of message strings
    """
    import random
    messages = []
    
    # Get basic spell information
    spell_name = spell.get("name", "Unknown Spell")
    spell_level = spell.get("level", 1)
    utility_type = spell.get("utility_type", "general")
    duration = get_spell_duration(spell, caster)
    
    # Get caster's relevant ability score modifier
    ability_mod = 0
    if hasattr(caster, 'abilities') and hasattr(caster, 'char_class'):
        # Determine which ability affects utility spells based on class
        ability_key = 'intelligence'  # Default for wizards
        if caster.char_class.lower() == 'priest':
            ability_key = 'wisdom'
        elif caster.char_class.lower() == 'spellblade':
            ability_key = 'charisma'
            
        # Get the modifier if the ability exists
        if ability_key in caster.abilities:
            ability_score = caster.abilities[ability_key]
            ability_mod = (ability_score - 10) // 2
    
    # Handle specific utility types
    
    #--------------------------------------------------------------------------
    # LIGHT SPELLS
    #--------------------------------------------------------------------------
    if utility_type == "light" or spell_name == "Light" or spell_name == "Dancing Lights":
        # Set the light radius on the caster or target
        light_radius = get_spell_light_radius(spell)
        # Apply scaling if enabled
        if spell.get("scaling_enabled", True) and hasattr(caster, 'level'):
            # Each level above minimum can increase light radius
            min_level = spell.get("level", 1)
            level_diff = caster.level - min_level
            
            if level_diff > 0:
                radius_per_level = spell.get("radius_per_level", 1)
                light_radius += level_diff * radius_per_level
                
        # Apply ability modifier bonus if applicable
        if spell.get("apply_ability_mod", False):
            light_radius += ability_mod
        
        # Determine light target
        light_target = caster
        if spell.get("target_object", False) and isinstance(target, tuple):
            # Light can target an object at a location
            messages.append(f"{caster.name} casts {spell_name}, illuminating that location with a radius of {light_radius} tiles!")
            
            # If the game has a way to create a light source at a position
            if hasattr(dungeon, 'add_light_source'):
                dungeon.add_light_source(target, light_radius, duration)
        else:
            # Apply to a character
            if target != caster and hasattr(target, 'light_radius'):
                light_target = target
                messages.append(f"{caster.name} casts {spell_name} on {target.name}, giving them a light radius of {light_radius} tiles!")
            else:
                messages.append(f"{caster.name} casts {spell_name}, creating a light radius of {light_radius} tiles!")
            
            # Apply the light effect
            light_target.light_radius = light_radius
            
            # Track the spell duration for the light if applicable
            if duration > 0 and hasattr(light_target, 'timed_effects'):
                light_effect = {
                    'type': 'light',
                    'duration': duration,
                    'value': light_radius,
                    'original_value': getattr(light_target, 'original_light_radius', 0)
                }
                light_target.timed_effects.append(light_effect)
    
    #--------------------------------------------------------------------------
    # DISPEL EFFECTS
    #--------------------------------------------------------------------------
    elif utility_type == "dispel" or spell_name == "Dispel Magic" or spell_name == "Remove Curse":
        # Remove magical effects from the target
        from effect_manager import effect_manager
        
        effect_types_removed = spell.get("effect_types_removed", ["all"])
        
        if "all" in effect_types_removed:
            # Clear all magical effects from the target
            num_effects = effect_manager.clear_all_effects(target)
            if num_effects > 0:
                messages.append(f"{caster.name} casts {spell_name}, removing {num_effects} magical effects from {target.name}!")
            else:
                messages.append(f"{caster.name} casts {spell_name}, but {target.name} has no magical effects to remove!")
        else:
            # Remove specific effect types
            from condition_system import ConditionType
            
            effects_removed = 0
            for effect_type in effect_types_removed:
                condition_type = None
                
                # Map string to condition type
                if effect_type == "curse":
                    condition_type = ConditionType.CURSED
                elif effect_type == "poison":
                    condition_type = ConditionType.POISONED
                elif effect_type == "disease":
                    condition_type = ConditionType.DISEASED
                # Add other mappings as needed
                
                if condition_type:
                    removed = effect_manager.remove_condition(target, condition_type)
                    if removed:
                        effects_removed += 1
                        messages.append(f"{target.name} is no longer affected by {effect_type}!")
            
            if effects_removed == 0:
                messages.append(f"{caster.name} casts {spell_name}, but {target.name} has no relevant effects to remove!")
    
    #--------------------------------------------------------------------------
    # INVISIBILITY
    #--------------------------------------------------------------------------
    elif utility_type == "invisibility" or spell_name == "Invisibility":
        # Apply invisibility effect to the target
        from condition_system import condition_manager, ConditionType, Condition
        
        # Check if target already has invisibility
        if hasattr(target, 'conditions') and any(c.condition_type == ConditionType.INVISIBLE for c in target.conditions):
            messages.append(f"{caster.name} casts {spell_name}, but {target.name} is already invisible!")
            return messages
        
        # Create an invisibility effect
        severity = spell.get("severity", spell_level)  # Higher level spells have stronger invisibility
        invisibility = Condition(ConditionType.INVISIBLE, duration, caster, severity)
        condition_manager.apply_condition(target, invisibility)
        
        messages.append(f"{caster.name} casts {spell_name} on {target.name}, making them invisible for {duration} turns!")
    
    #--------------------------------------------------------------------------
    # DETECTION SPELLS
    #--------------------------------------------------------------------------
    elif utility_type == "detection" or spell_name.startswith("Detect"):
        # Figure out what we're detecting
        detect_type = spell.get("detect_type", "")
        if not detect_type and spell_name.startswith("Detect "):
            # Extract from spell name (e.g., "Detect Magic" → "magic")
            detect_type = spell_name[7:].lower()
        
        # Detection radius
        detect_radius = spell.get("detect_radius", 5 + ability_mod)
        
        # Scale with level if enabled
        if spell.get("scaling_enabled", True) and hasattr(caster, 'level'):
            min_level = spell.get("level", 1)
            level_diff = caster.level - min_level
            
            if level_diff > 0:
                radius_per_level = spell.get("radius_per_level", 1)
                detect_radius += level_diff * radius_per_level
        
        # Handle different detection types
        if detect_type == "magic":
            # Detect magic items and effects
            magic_found = []
            
            # Check for magic items in the area
            if hasattr(dungeon, 'items'):
                for item_pos, item in dungeon.items.items():
                    # Check if item is within range
                    if isinstance(item_pos, tuple) and isinstance(caster.position, tuple):
                        import math
                        dx = item_pos[0] - caster.position[0]
                        dy = item_pos[1] - caster.position[1]
                        distance = math.sqrt(dx*dx + dy*dy)
                        
                        if distance <= detect_radius and hasattr(item, 'magical') and item.magical:
                            magic_found.append(f"a magical {item.name} at {item_pos}")
            
            # Check for magical effects on creatures
            if hasattr(dungeon, 'monsters'):
                for monster in dungeon.monsters:
                    # Check if monster is within range
                    if hasattr(monster, 'position') and isinstance(caster.position, tuple):
                        import math
                        dx = monster.position[0] - caster.position[0]
                        dy = monster.position[1] - caster.position[1]
                        distance = math.sqrt(dx*dx + dy*dy)
                        
                        if distance <= detect_radius:
                            # Check for magical effects on monster
                            has_magic = False
                            if hasattr(monster, 'conditions') and monster.conditions:
                                has_magic = True
                            
                            if has_magic:
                                magic_found.append(f"magical effects on {monster.name}")
            
            # Report findings
            if magic_found:
                messages.append(f"{caster.name} casts {spell_name} and detects: {', '.join(magic_found)}")
            else:
                messages.append(f"{caster.name} casts {spell_name} but detects no magical auras within {detect_radius} tiles.")
        
        elif detect_type == "traps":
            # Detect traps in the area
            traps_found = []
            
            # Check for traps in the dungeon
            if hasattr(dungeon, 'traps'):
                for trap_pos, trap in dungeon.traps.items():
                    # Check if trap is within range
                    if isinstance(trap_pos, tuple) and isinstance(caster.position, tuple):
                        import math
                        dx = trap_pos[0] - caster.position[0]
                        dy = trap_pos[1] - caster.position[1]
                        distance = math.sqrt(dx*dx + dy*dy)
                        
                        if distance <= detect_radius:
                            # Make a detection roll if the spell requires it
                            if spell.get("requires_check", False):
                                detection_dc = trap.get("detection_dc", 15)
                                detection_roll = random.randint(1, 20) + ability_mod + spell_level
                                
                                if detection_roll >= detection_dc:
                                    traps_found.append(f"a {trap.get('name', 'trap')} at {trap_pos}")
                                    # Mark the trap as detected if the game supports it
                                    if hasattr(trap, 'detected'):
                                        trap.detected = True
                            else:
                                # Automatically detect all traps in range
                                traps_found.append(f"a {trap.get('name', 'trap')} at {trap_pos}")
                                # Mark the trap as detected if the game supports it
                                if hasattr(trap, 'detected'):
                                    trap.detected = True
            
            # Report findings
            if traps_found:
                messages.append(f"{caster.name} casts {spell_name} and detects: {', '.join(traps_found)}")
            else:
                messages.append(f"{caster.name} casts {spell_name} but detects no traps within {detect_radius} tiles.")
        
        else:
            # Generic detection spell
            messages.append(f"{caster.name} casts {spell_name}, searching for {detect_type} within {detect_radius} tiles.")
    
    #--------------------------------------------------------------------------
    # UNLOCKING SPELLS
    #--------------------------------------------------------------------------
    elif utility_type == "unlock" or spell_name == "Knock" or spell_name == "Unlock":
        # Determine what we're unlocking
        unlock_target = None
        unlock_success = False
        
        # Target can be a door or chest or lock position
        if isinstance(target, tuple) and dungeon:
            # Check if target position has a door
            if hasattr(dungeon, 'doors') and target in dungeon.doors:
                unlock_target = dungeon.doors[target]
                target_desc = "door"
            
            # Check if target position has a chest or container
            elif hasattr(dungeon, 'containers') and target in dungeon.containers:
                unlock_target = dungeon.containers[target]
                target_desc = "container"
            
            # Check if target position has a special lock
            elif hasattr(dungeon, 'locks') and target in dungeon.locks:
                unlock_target = dungeon.locks[target]
                target_desc = "lock"
        
        # Process the unlocking
        if unlock_target:
            if hasattr(unlock_target, 'locked') and unlock_target.locked:
                # Calculate unlock power based on spell level and caster's ability
                unlock_power = spell_level * 5 + ability_mod
                
                # Check against lock difficulty
                lock_dc = getattr(unlock_target, 'lock_dc', 15)
                
                # Magic unlock spells are very powerful
                if unlock_power >= lock_dc or random.randint(1, 20) + unlock_power >= lock_dc + 5:
                    unlock_target.locked = False
                    if hasattr(unlock_target, 'open') and callable(unlock_target.open):
                        unlock_target.open()
                    
                    messages.append(f"{caster.name} casts {spell_name}, and the {target_desc} unlocks with a click!")
                    unlock_success = True
                else:
                    messages.append(f"{caster.name} casts {spell_name}, but the {target_desc} remains locked! The lock seems too complex.")
            elif hasattr(unlock_target, 'locked') and not unlock_target.locked:
                messages.append(f"{caster.name} casts {spell_name}, but the {target_desc} is already unlocked.")
            else:
                messages.append(f"{caster.name} casts {spell_name}, but the {target_desc} has no lock to affect.")
        else:
            messages.append(f"{caster.name} casts {spell_name}, but there's nothing to unlock at the target location.")
    
    #--------------------------------------------------------------------------
    # TELEPORTATION
    #--------------------------------------------------------------------------
    elif utility_type == "teleport" or spell_name == "Teleport" or spell_name == "Dimension Door":
        # Get teleport distance
        teleport_range = spell.get("teleport_range", spell_level * 5)
        
        # Source and destination positions
        source_pos = None
        dest_pos = None
        
        if hasattr(target, 'position') and isinstance(target.position, tuple):
            # Teleporting a character
            source_pos = target.position
            
            # The destination can be specified as a parameter or calculated based on direction
            dest_pos = spell.get("destination", None)
            
            if not dest_pos and isinstance(target, tuple):
                # Target position is the destination
                dest_pos = target
            
            # Validate the destination
            if dest_pos:
                # Check if destination is in range
                if source_pos and isinstance(source_pos, tuple):
                    import math
                    dx = dest_pos[0] - source_pos[0]
                    dy = dest_pos[1] - source_pos[1]
                    distance = math.sqrt(dx*dx + dy*dy)
                    
                    if distance > teleport_range:
                        messages.append(f"{caster.name} casts {spell_name}, but the destination is too far away ({distance:.1f} tiles vs {teleport_range} range).")
                        return messages
                
                # Check if destination is valid (not a wall, etc.)
                if dungeon and hasattr(dungeon, 'is_position_walkable'):
                    if not dungeon.is_position_walkable(dest_pos):
                        messages.append(f"{caster.name} casts {spell_name}, but the destination is not a valid location.")
                        return messages
                
                # Teleport the target
                target.position = dest_pos
                messages.append(f"{caster.name} casts {spell_name}, and {target.name} vanishes and reappears at the destination!")
            else:
                messages.append(f"{caster.name} casts {spell_name}, but no valid destination was provided.")
        else:
            messages.append(f"{caster.name} casts {spell_name}, but the target cannot be teleported.")
    
    #--------------------------------------------------------------------------
    # SCRYING / CLAIRVOYANCE
    #--------------------------------------------------------------------------
    elif utility_type == "scrying" or spell_name == "Clairvoyance" or spell_name == "Scrying":
        # Get scrying range
        scry_range = spell.get("scry_range", spell_level * 10)
        
        # Target position
        scry_pos = None
        
        if isinstance(target, tuple):
            # Target position is the scrying location
            scry_pos = target
        
        # Check if position is in range
        if scry_pos and isinstance(caster.position, tuple):
            import math
            dx = scry_pos[0] - caster.position[0]
            dy = scry_pos[1] - caster.position[1]
            distance = math.sqrt(dx*dx + dy*dy)
            
            if distance > scry_range:
                messages.append(f"{caster.name} casts {spell_name}, but the location is too far away ({distance:.1f} tiles vs {scry_range} range).")
                return messages
        
        # Reveal the area around the target position
        if scry_pos and dungeon and hasattr(dungeon, 'reveal_area'):
            # Determine reveal radius
            reveal_radius = spell.get("reveal_radius", 3)
            dungeon.reveal_area(scry_pos, reveal_radius)
            
            # Report what was seen
            messages.append(f"{caster.name} casts {spell_name}, gaining magical vision of the area around {scry_pos}.")
            
            # Report entities in the revealed area
            entities = []
            
            # Check for monsters in the revealed area
            if hasattr(dungeon, 'monsters'):
                for monster in dungeon.monsters:
                    if hasattr(monster, 'position') and isinstance(monster.position, tuple):
                        import math
                        dx = monster.position[0] - scry_pos[0]
                        dy = monster.position[1] - scry_pos[1]
                        distance = math.sqrt(dx*dx + dy*dy)
                        
                        if distance <= reveal_radius:
                            entities.append(f"{monster.name} at {monster.position}")
            
            if entities:
                messages.append(f"Through the {spell_name} spell, {caster.name} sees: {', '.join(entities)}")
        else:
            messages.append(f"{caster.name} casts {spell_name}, but cannot establish magical vision at the target location.")
    
    #--------------------------------------------------------------------------
    # OTHER UTILITY SPELLS
    #--------------------------------------------------------------------------
    else:
        # Generic handling for other utility spells
        messages.append(f"{caster.name} casts {spell_name}.")
    
    return messages

def handle_debuff_spell(caster, target, spell):
    """
    Handle debuff spells that apply negative effects to enemies.
    
    Args:
        caster: Character casting the spell
        target: Target character
        spell: Spell data dictionary
        
    Returns:
        List of message strings
    """
    messages = []
    
    # Get basic spell information
    spell_name = spell.get("name", "Unknown Spell")
    duration = get_spell_duration(spell, caster)
    
    # Get effect information
    effects = get_spell_effects(spell)
    
    # Apply effects
    from condition_system import condition_manager, ConditionType, Condition
    
    effects_applied = []
    for effect_name in effects:
        # Map effect name to ConditionType
        effect_type = None
        severity = spell.get("severity", 1)
        
        if effect_name == "Cursed":
            effect_type = ConditionType.CURSED
        elif effect_name == "Poisoned":
            effect_type = ConditionType.POISONED
        elif effect_name == "Paralyzed":
            effect_type = ConditionType.PARALYZED
        elif effect_name == "Slowed":
            effect_type = ConditionType.SLOWED
        elif effect_name == "Weakened":
            effect_type = ConditionType.WEAKENED
        elif effect_name == "Blinded":
            effect_type = ConditionType.BLINDED
        elif effect_name == "Stunned":
            effect_type = ConditionType.STUNNED
        elif effect_name == "Confused":
            effect_type = ConditionType.CONFUSED
        elif effect_name == "Burning":
            effect_type = ConditionType.BURNING
        elif effect_name == "Frozen":
            effect_type = ConditionType.FROZEN
        elif effect_name == "Immune" or effect_name == "Immune_Poison":
            effect_type = ConditionType.IMMUNE_POISON
        
        if effect_type:
            condition = Condition(effect_type, duration, caster, severity)
            result_message = condition_manager.apply_condition(target, condition)
            messages.append(result_message)
            effects_applied.append(effect_name.lower())
    
    if not effects_applied:
        messages.append(f"{caster.name} casts {spell_name} on {target.name}, but it has no effect!")
    else:
        effect_text = ", ".join(effects_applied)
        messages.append(f"{caster.name} casts {spell_name} on {target.name}, applying {effect_text}!")
    
    return messages