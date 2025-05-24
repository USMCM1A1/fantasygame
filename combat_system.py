#!/usr/bin/env python
# coding: utf-8

# =============================================================================
# === Unified Combat System ===
# =============================================================================
import random
import pygame

# Import necessary components from common_b_s
from common_b_s import (
    roll_dice_expression, 
    has_line_of_sight, 
    process_monster_death,
    TILE_SIZE,
    melee_sound,
    arrow_sound,
    spell_sound
)

def perform_attack(attacker, target, attack_type, dungeon):
    """
    Unified attack function that routes to appropriate handler based on attack type.
    
    Parameters:
    - attacker: Character object making the attack
    - target: Character object being attacked
    - attack_type: String identifying the attack type (spell_X, ranged_X, melee_X)
    - dungeon: Dungeon instance for line of sight checks and other interactions
    
    Returns:
    - List of message strings describing the attack result
    """
    if attack_type.startswith("spell_"):
        # Handle magical spells
        return perform_spell_attack(attacker, target, attack_type[6:], dungeon)
    elif attack_type.startswith("ranged_"):
        # Handle ranged physical attacks
        return perform_ranged_attack(attacker, target, attack_type[7:], dungeon)
    elif attack_type.startswith("melee_"):
        # Handle melee attacks
        return perform_melee_attack(attacker, target, attack_type[6:], dungeon)
    else:
        return [f"Unknown attack type: {attack_type}"]

def perform_melee_attack(attacker, target, attack_subtype, dungeon):
    """
    Handle standard melee attacks.
    
    Parameters:
    - attacker: Character object making the attack
    - target: Character object being attacked
    - attack_subtype: Specific melee attack type (e.g., 'basic', 'power')
    - dungeon: Dungeon instance
    
    Returns:
    - List of message strings describing the result
    """
    messages = []
    
    # Calculate attack rolls based on attacker type
    if hasattr(attacker, 'calculate_modifier'):
        # Player character
        attack_mod = attacker.calculate_modifier(attacker.get_effective_ability("strength"))
        attack_roll = roll_dice_expression("1d20") + attack_mod + attacker.attack_bonus
    else:
        # Monster
        attack_roll = roll_dice_expression("1d20") + attacker.to_hit
        
    # Determine target's AC
    target_ac = target.get_effective_ac()
    
    # Check if attack hits
    if attack_roll >= target_ac:
        # Calculate damage
        if hasattr(attacker, 'get_effective_damage'):
            # Player character
            damage = attacker.get_effective_damage()
        else:
            # Monster
            damage = roll_dice_expression(attacker.dam)
            
        # Apply damage with type handling
        if hasattr(target, 'apply_damage'):
            # Use monster's apply_damage method which handles vulnerabilities/resistances/immunities
            actual_damage = target.apply_damage(damage, "physical")
            if actual_damage < damage:
                messages.append(f"{attacker.name} hits {target.name} for {actual_damage} damage (reduced)!")
            elif actual_damage > damage:
                messages.append(f"{attacker.name} hits {target.name} for {actual_damage} damage (vulnerability)!")
            elif actual_damage == 0:
                messages.append(f"{attacker.name} hits {target.name} but it has no effect!")
            else:
                messages.append(f"{attacker.name} hits {target.name} for {actual_damage} damage!")
        else:
            # Standard damage application for entities without type handling
            target.hit_points -= damage
            messages.append(f"{attacker.name} hits {target.name} for {damage} damage!")
        
        # Play appropriate sound effect
        melee_sound.play()
        
        # Check for target death
        if target.hit_points <= 0:
            if hasattr(target, 'hit_points') and not hasattr(target, 'character_type'):
                # Monster death
                death_messages = process_monster_death(target, attacker, dungeon) or []
                for msg in death_messages:
                    messages.append(msg)
            else:
                # Player death
                messages.append(f"{target.name} has been defeated!")
    else:
        messages.append(f"{attacker.name} misses {target.name}!")
        
    return messages

def perform_ranged_attack(attacker, target, attack_subtype, dungeon):
    """
    Handle ranged attacks like bow shots, thrown weapons, etc.
    
    Parameters:
    - attacker: Character object making the attack
    - target: Character object being attacked
    - attack_subtype: Specific ranged attack type (e.g., 'arrow', 'throw')
    - dungeon: Dungeon instance for line of sight checks
    
    Returns:
    - List of message strings describing the result
    """
    messages = []
    
    # Check if attacker has a bow equipped (required for ranged attacks)
    if hasattr(attacker, 'equipment') and not (
            attacker.equipment.get('weapon') and 
            hasattr(attacker.equipment['weapon'], 'item_type') and 
            attacker.equipment['weapon'].item_type == "weapon_bow"
        ):
        messages.append(f"{attacker.name} needs a bow equipped to perform a ranged attack.")
        return messages
    
    # Get positions
    ax, ay = attacker.position[0] // TILE_SIZE, attacker.position[1] // TILE_SIZE
    tx, ty = target.position[0] // TILE_SIZE, target.position[1] // TILE_SIZE
    manhattan_distance = abs(ax - tx) + abs(ay - ty)
    
    # Get range from the equipped bow
    max_range = attacker.equipment['weapon'].range
        
    if manhattan_distance > max_range:
        messages.append(f"{attacker.name} is too far away for a {attack_subtype} attack.")
        return messages
        
    # Check line of sight
    if not has_line_of_sight(attacker, target, dungeon, required_clear=1):
        messages.append(f"{attacker.name} does not have a clear shot at {target.name}.")
        return messages
        
    # Calculate attack roll based on Dexterity for ranged attacks
    if hasattr(attacker, 'calculate_modifier'):
        # Player character
        attack_mod = attacker.calculate_modifier(attacker.abilities.get('dexterity', 10))
        attack_roll = roll_dice_expression("1d20") + attack_mod + attacker.attack_bonus
    else:
        # Monster
        attack_roll = roll_dice_expression("1d20") + attacker.to_hit
        
    # Determine target's AC
    target_ac = target.get_effective_ac()
    
    # Check if attack hits
    if attack_roll >= target_ac:
        # Calculate damage using the equipped bow
        weapon = attacker.equipment['weapon']
        damage = weapon.roll_damage(attacker)
        
        # Add dexterity modifier for bow attacks
        if hasattr(attacker, 'calculate_modifier'):
            damage += attacker.calculate_modifier(attacker.abilities.get('dexterity', 10))
            
        # Get weapon name for display
        bow_name = weapon.name.split(" ")[0] + " " + weapon.name.split(" ")[1]  # Extract "Basic Shortbow" from "Basic Shortbow (1d6)"
        
        # Apply damage with type handling
        if hasattr(target, 'apply_damage'):
            # Use monster's apply_damage method which handles vulnerabilities/resistances/immunities
            actual_damage = target.apply_damage(damage, "physical")
            if actual_damage < damage:
                messages.append(f"{attacker.name} fires an arrow from their {bow_name} at {target.name} for {actual_damage} damage (reduced)!")
            elif actual_damage > damage:
                messages.append(f"{attacker.name} fires an arrow from their {bow_name} at {target.name} for {actual_damage} damage (vulnerability)!")
            elif actual_damage == 0:
                messages.append(f"{attacker.name} fires an arrow from their {bow_name} at {target.name} but it has no effect!")
            else:
                messages.append(f"{attacker.name} fires an arrow from their {bow_name} at {target.name} for {actual_damage} damage!")
        else:
            # Standard damage application for entities without type handling
            target.hit_points -= damage
            messages.append(f"{attacker.name} fires an arrow from their {bow_name} at {target.name} for {damage} damage!")
        
        # Play appropriate sound effect
        arrow_sound.play()
        
        # Check for target death
        if target.hit_points <= 0:
            if hasattr(target, 'hit_points') and not hasattr(target, 'character_type'):
                # Monster death
                death_messages = process_monster_death(target, attacker, dungeon) or []
                for msg in death_messages:
                    messages.append(msg)
            else:
                # Player death
                messages.append(f"{target.name} has been defeated!")
    else:
        bow_name = weapon.name.split(" ")[0] + " " + weapon.name.split(" ")[1]
        messages.append(f"{attacker.name} fires an arrow from their {bow_name} at {target.name} but misses!")
        
    return messages

def perform_spell_attack(attacker, target, spell_name, dungeon):
    """
    Handle spell casting by delegating to the existing cast_spell function.
    This is a wrapper around cast_spell to maintain a consistent interface.
    
    Parameters:
    - attacker: Character object casting the spell
    - target: Character object being targeted by the spell
    - spell_name: Name of the spell to cast
    - dungeon: Dungeon instance for line of sight checks and other interactions
    
    Returns:
    - List of message strings describing the result
    """
    # Import cast_spell here to avoid circular imports
    from common_b_s import cast_spell
    
    # Just pass through to the existing cast_spell function
    return cast_spell(attacker, target, spell_name, dungeon)

def combat_round(attacker, defender, dungeon):
    """
    Execute a full round of combat between two characters.
    Determines initiative, executes attacks for each character, and handles results.
    
    Parameters:
    - attacker: First character in the combat
    - defender: Second character in the combat
    - dungeon: Dungeon instance
    
    Returns:
    - List of message strings describing the combat
    """
    combat_messages = []
    
    # Determine initiative
    if hasattr(attacker, 'calculate_modifier'):
        # Player character
        attacker_init = roll_dice_expression("1d10") + attacker.calculate_modifier(attacker.get_effective_ability("dexterity"))
    else:
        # Monster
        attacker_init = roll_dice_expression("1d10") + attacker.to_hit
        
    if hasattr(defender, 'calculate_modifier'):
        # Player character
        defender_init = roll_dice_expression("1d10") + defender.calculate_modifier(defender.get_effective_ability("dexterity"))
    else:
        # Monster
        defender_init = roll_dice_expression("1d10") + defender.to_hit
    
    # Determine who goes first
    if attacker_init >= defender_init:
        first = attacker
        second = defender
        combat_messages.append(f"{attacker.name} goes first!")
    else:
        first = defender
        second = attacker
        combat_messages.append(f"{defender.name} goes first!")
    
    # Execute attacks in initiative order
    # First character attacks
    if first.hit_points > 0:
        attack_messages = perform_attack(first, second, "melee_basic", dungeon)
        combat_messages.extend(attack_messages)
        
    # Second character counter-attacks if still alive
    if second.hit_points > 0:
        attack_messages = perform_attack(second, first, "melee_basic", dungeon)
        combat_messages.extend(attack_messages)
    
    return combat_messages

def combat(player, monster, dungeon_instance):
    """
    Legacy combat function for backward compatibility.
    
    Parameters:
    - player: Player character
    - monster: Monster character
    - dungeon_instance: Dungeon instance
    
    Returns:
    - List of message strings describing the combat
    """
    return combat_round(player, monster, dungeon_instance)