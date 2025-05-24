# Blade & Sigil Targeting System

## Overview

The Targeting System provides a framework for determining valid targets for spells and abilities, calculating line of sight, and handling area of effect targeting. This system works with the Spell System to provide robust targeting capabilities for magic and ranged attacks.

## Components

### `targeting_system.py` - Core Targeting Engine

The core targeting module features:

- `TargetMode` class defining different targeting modes (single, area, line, etc.)
- `TargetingSystem` class providing the main targeting functionality
- Helper functions for common targeting operations

## Key Features

### Target Selection

The system supports various targeting modes:

1. **Single** - Target a single character/monster
2. **Area** - Target an area (radius around a point)
3. **Line** - Target a line from caster
4. **Cone** - Target a cone-shaped area
5. **Self** - Target the caster only
6. **Allies** - Target all allies in range
7. **Enemies** - Target all enemies in range
8. **All** - Target all characters in range

### Range Calculation

The system supports multiple distance metrics for different spell behaviors:

- **Manhattan Distance** (default): Sum of horizontal and vertical distances - best for spells that follow grid lines
- **Chebyshev Distance**: Maximum of horizontal and vertical distances - best for spells that can travel diagonally at same cost
- **Euclidean Distance**: True geometric distance - best for realistic straight-line spells

Each spell can specify which distance metric to use via the `distance_metric` property.

### Line of Sight

The system provides robust line of sight calculations using Bresenham's line algorithm with enhanced handling for:

- **Adjacent targets**: Characters always have line of sight to adjacent tiles
- **Doors**: Open doors allow line of sight, closed doors block it
- **Walls**: Always block line of sight
- **Edge cases**: Proper bounds checking and handling of short paths
- **Self-targeting**: Characters always have line of sight to themselves

### Area of Effect

For spells that affect multiple targets, the system supports:

- **Circular** AoE - Targets within a radius of the center point
- **Square** AoE - Targets within a square around the center point
- **Line** AoE - Targets along a line with configurable width
- **Cone** AoE - Targets within a cone projecting from the caster

## Using the Targeting System

### Checking Valid Targets

```python
from targeting_system import targeting_system

# Set the current dungeon for proper LOS calculations
targeting_system.set_dungeon(current_dungeon)

# Get all valid targets for a spell
valid_targets = targeting_system.get_valid_targets(
    caster=player,
    spell_data=spell,
    all_characters=[player] + current_dungeon.monsters
)

# Use the helper function for a quick check
from targeting_system import can_target

# Check if a specific character can be targeted
can_cast, message = can_target(
    caster=player,
    target=monster,
    spell_data=spell,
    dungeon=current_dungeon
)

if not can_cast:
    add_message(message)  # Display targeting error
```

### Selecting Targets for UI

When creating a targeting interface, you can use the system to highlight valid targets:

```python
# When player is selecting a spell target
def draw_targeting_overlay(screen, player, spell_data, all_characters):
    # Set up targeting system
    targeting_system.set_dungeon(current_dungeon)
    
    # Get valid targets
    valid_targets = targeting_system.get_valid_targets(
        player, spell_data, all_characters
    )
    
    # Draw targeting indicators for each valid target
    for target in valid_targets:
        # Draw a highlight or indicator at target position
        draw_targeting_indicator(screen, target.position)
    
    # For area spells, show the area of effect
    if spell_data.get("targets") == "area":
        area_size = int(spell_data.get("area_size", 1))
        area_tiles = targeting_system.get_area_of_effect(
            mouse_position, area_size, "circle"
        )
        
        # Draw area indicators
        for tile_x, tile_y in area_tiles:
            draw_area_indicator(screen, tile_x, tile_y)
```

### Finding Area of Effect Targets

For area spells, get all characters within the affected area with filtering options:

```python
from Data.targeting_system import get_area_targets

# Fireball spell that affects a 3-tile radius around target point
# Hurts both allies and enemies that have line of sight
affected_characters = get_area_targets(
    center=target_position,
    area_size=3,
    all_characters=[player] + current_dungeon.monsters,
    shape="circle",
    caster=player,
    include_allies=True,  # Friendly fire!
    include_enemies=True,
    check_los=True,      # Only hits targets with line of sight
    dungeon=current_dungeon
)

# Healing aura that only affects allies in a 2-tile radius
affected_allies = get_area_targets(
    center=player,
    area_size=2,
    all_characters=[player] + current_dungeon.monsters,
    shape="diamond",    # Diamond shape (Manhattan distance)
    caster=player,
    include_allies=True,
    include_enemies=False  # Don't heal enemies
)

# Process effects for all affected characters
for character in affected_characters:
    # Apply damage/effects to each character
    apply_fire_damage(character, "2d6")
```

The system supports three area shapes:
- **Circle**: Uses Euclidean distance for realistic radial effects (explosions)
- **Diamond**: Uses Manhattan distance (good for spreading auras)
- **Square**: Uses Chebyshev distance (good for wide-area blasts)

### Line of Sight Checking

Use line of sight checking for visibility and targeting:

```python
# Check if monster is visible to player
if targeting_system.has_line_of_sight(player, monster):
    # Monster is visible, draw it
    draw_monster(screen, monster)
```

## Integration with Spell System

The targeting system integrates with the spell system through the spell definition in `spells.json`. To specify targeting for spells:

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

## Extension Points

To add a new targeting mode:

1. Add a new value to the `TargetMode` class
2. Add handling logic in `get_valid_targets()` to handle the new mode
3. Optionally add helper methods for common operations with the new mode