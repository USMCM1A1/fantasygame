# Blade & Sigil Magic System

## Overview

The refactored magic system replaces the hardcoded approach with a data-driven, modular design that:

1. Loads spell definitions from a JSON file
2. Provides a unified spell casting framework
3. Supports conditions, targeting, and various effect types
4. Makes adding new spells easier without modifying core code

## Implementation Components

### 1. `spells.json` - Data Structure

The `spells.json` file contains all spell definitions with standardized fields:

```json
{
  "name": "Magic Missile",
  "type": "damage",
  "effect_type": "Magic",
  "level": 1,
  "classes": ["Wizard"],
  "sp_cost": 1,
  "damage_dice": "1d4+1",
  "range_type": "ranged",
  "max_range": 4,
  "targets": "single",
  "description": "A bolt of magical energy that never misses its target"
}
```

Important fields include:
- `type`: damage, healing, buff, utility
- `effect_type`: Magic, Physical, Holy, Fire, etc.
- `range_type`: self, touch, ranged
- `targets`: single, area, self, allies

### 2. `spell_helpers.py` - Helper Functions

Contains utility functions for accessing spell properties:

- `get_spell_by_name()`
- `get_spell_cost()`
- `get_spell_damage()`
- `get_spell_effects()`
- `check_spell_requirements()`

These functions handle type conversion, error checking, and provide consistent default values.

### 3. `spell_system.py` - Spell Casting Framework

The core spell casting system with type-specific handlers:

- `cast_spell()` - Main entry point for all spell casting
- `handle_damage_spell()`
- `handle_healing_spell()`
- `handle_buff_spell()`
- `handle_utility_spell()`

### 4. `effect_manager.py` - Status Effect Handling

Tracks and manages temporary spell effects:

- `StatusEffectManager` class
- Effect types (DamageEffect, BuffEffect)
- Visual rendering of active effects

## Integration Steps

1. **Import the modules in common_b_s.py**:
   ```python
   from Data.spell_helpers import *
   from Data.spell_system import cast_spell
   from Data.effect_manager import effect_manager
   ```

2. **Replace the existing cast_spell function**:
   ```python
   def cast_spell(caster, target, spell_name, dungeon):
       # Use the new unified system
       from Data.spell_system import cast_spell as new_cast_spell
       return new_cast_spell(caster, target, spell_name, dungeon, spells_data)
   ```

3. **Update the spells_dialogue function** to use the new system.

4. **Update UI to display status effects** by adding a call to `render_status_effects()` in the character drawing code.

5. **Process status effects each turn** by calling `effect_manager.process_turn()` at the start of each game turn.

## Adding New Spells

To add a new spell:

1. Add a new entry to `spells.json` with all required fields
2. No code changes needed for standard spell types (damage, healing, buff, utility)
3. For special effects, add custom handling logic to the appropriate handler function

Example new spell:
```json
{
  "name": "Fireball",
  "type": "damage",
  "effect_type": "Fire",
  "level": 3,
  "classes": ["Wizard"],
  "sp_cost": 3,
  "damage_dice": "3d6",
  "range_type": "ranged",
  "max_range": 6,
  "targets": "area",
  "area_size": 2,
  "description": "A ball of fire that explodes on impact"
}
```

## Testing

Test the system with different character classes and spell types:

1. Wizard casting damage spells (Magic Missile)
2. Priest casting healing spells (Cure Light Wounds)
3. Spellblade casting buff spells (Wicked Weapon)
4. Test area of effect spells
5. Test status effects application and removal
6. Verify spell requirements (class, level, spell points)