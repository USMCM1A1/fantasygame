# Blade & Sigil Condition System

## Overview

The Condition System provides a framework for implementing and managing status effects (buffs, debuffs, and other temporary effects) that can be applied to characters and monsters. This system is integrated with the Spell System but can also be used independently.

## Components

### 1. `condition_system.py` - Core System

The core of the condition system featuring:

- `ConditionType` enum defining all possible conditions (Poisoned, Paralyzed, etc.)
- `Condition` class representing an individual status effect
- `ConditionManager` class to track and process all active conditions
- Helper functions for applying common conditions
- Rendering function for visual display of conditions

### 2. `condition_bridge.py` - Integration with Spell System

Connects the condition system with the spell casting system:

- `apply_spell_condition()` - Applies conditions from spells
- `remove_spell_conditions()` - Removes conditions as specified by healing spells
- `check_condition_restrictions()` - Prevents casting when under restrictive conditions
- `integrate_spell_system_with_conditions()` - Enhances spell handler functions

### 3. Character Class Integration

The Character class has been extended with condition tracking abilities:

- `conditions` list - Stores active conditions
- `damage_modifier` attribute - For condition effects that modify damage
- `can_move` flag - Used by paralysis effects
- Methods for adding, removing, checking, and processing conditions

## Implemented Conditions

The system supports various condition types with different effects:

1. **Poisoned** - Deals damage over time (1-3 per turn)
2. **Paralyzed** - Prevents movement
3. **Diseased** - Reduces strength and constitution
4. **Drained** - Reduces maximum hit points
5. **Cursed** - Reduces all ability scores
6. **Slowed** - Reduces movement speed
7. **Blinded** - Reduces accuracy 
8. **Silenced** - Prevents spell casting
9. **Weakened** - Reduces damage output
10. **Strengthened** - Increases damage output
11. **Protected** - Increases AC
12. **Regenerating** - Heals hit points each turn
13. **Burning** - Deals fire damage over time (2-5 per turn)

## Using the Condition System

### Applying Conditions

```python
from Data.condition_system import ConditionType, Condition, condition_manager

# Using the ConditionManager directly
poison_condition = Condition(ConditionType.POISONED, duration=3, source=player, severity=1)
message = condition_manager.apply_condition(monster, poison_condition)
add_message(message)  # Display the effect message

# Or use helper functions for common conditions
from Data.condition_system import apply_poison
message = apply_poison(monster, duration=3, source=player, severity=1)
add_message(message)

# Using Character class methods
poison_condition = Condition(ConditionType.POISONED, duration=3, severity=1)
message = character.add_condition(poison_condition)
add_message(message)
```

### Processing Conditions Each Turn

```python
# Using condition manager across multiple characters
all_characters = [player] + dungeon.monsters
messages = condition_manager.process_turn(all_characters)
for msg in messages:
    add_message(msg)

# Using Character's process method directly
messages = character.process_condition_effects(current_turn)
for msg in messages:
    add_message(msg)
```

### Checking for Conditions

```python
# Using ConditionManager
if condition_manager.has_condition(character, ConditionType.PARALYZED):
    # Character can't move this turn
    add_message(f"{character.name} is paralyzed and cannot move!")
    return

# Using Character class method
if character.has_condition(ConditionType.PARALYZED):
    add_message(f"{character.name} is paralyzed and cannot move!")
    return
    
# Check if character can take actions
if not character.can_take_actions():
    add_message(f"{character.name} is immobilized and cannot act!")
    return
```

### Removing Conditions

```python
# Using ConditionManager
if condition_manager.remove_condition(character, ConditionType.POISONED):
    add_message(f"{character.name} is no longer poisoned!")
    
# Using Character class method
if character.remove_condition(ConditionType.POISONED):
    add_message(f"{character.name} is no longer poisoned!")
    
# Remove all conditions through ConditionManager
count = condition_manager.clear_conditions(character)
if count > 0:
    add_message(f"All {count} conditions have been removed from {character.name}!")
    
# Remove all conditions through Character class
count = character.clear_conditions()
if count > 0:
    add_message(f"All {count} conditions have been removed from {character.name}!")
```

## Integration with Spells

The condition system integrates with the spell system through the spell definition in `spells.json`. To add conditions to spells:

```json
{
  "name": "Poison Dart",
  "type": "damage",
  "effect_type": "Poison",
  "level": 1,
  "classes": ["Wizard", "Thief"],
  "sp_cost": 1,
  "damage_dice": "1d3",
  "range_type": "ranged",
  "max_range": 5,
  "targets": "single",
  "effects": ["Poisoned"],
  "duration": 3,
  "description": "Fires a poisoned dart that deals initial damage and poisons the target"
}
```

For healing spells that remove conditions:

```json
{
  "name": "Cure Disease",
  "type": "healing",
  "effect_type": "Holy",
  "level": 2,
  "classes": ["Priest"],
  "sp_cost": 2,
  "healing_dice": "1d4",
  "range_type": "touch",
  "targets": "single",
  "effects_removed": ["Diseased", "Poisoned", "Cursed"],
  "description": "Cures diseases, poison, and curses while providing minor healing"
}
```

## Visual Rendering

The condition system includes a `render_conditions()` function that can be called during the rendering loop to display active conditions as colored icons above characters. Each condition type has a unique color, and displays the remaining duration in turns.

```python
from condition_system import render_conditions

# In your rendering code:
render_conditions(screen, player, player.position[0], player.position[1] - 20)

# For monsters
for monster in dungeon.monsters:
    if not monster.is_dead:
        render_conditions(screen, monster, monster.position[0], monster.position[1] - 20)
```

## Extension Points

To add a new condition type:

1. Add a new value to the `ConditionType` enum
2. Add a description to `_get_description()` in the `Condition` class
3. Add application logic in a new `_apply_X()` method
4. Add turn processing logic in a new `_process_X_turn()` method if needed
5. Add removal logic in a new `_remove_X()` method if needed
6. Add a color mapping in `render_conditions()`
7. Add the condition to the mapping in `apply_spell_condition()` for spell integration