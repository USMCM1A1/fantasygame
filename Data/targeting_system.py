#!/usr/bin/env python
# coding: utf-8

"""
Targeting System for Blade & Sigil
This module provides a framework for determining valid targets for spells and abilities,
calculating line of sight, and handling area of effect targeting.
"""

import logging
import math

# Set up logging
logger = logging.getLogger(__name__)

# Target selection modes
class TargetMode:
    SINGLE = "single"       # Target a single character/monster
    AREA = "area"           # Target an area (radius around a point)
    LINE = "line"           # Target a line from caster
    CONE = "cone"           # Target a cone-shaped area
    SELF = "self"           # Target the caster only
    ALLIES = "allies"       # Target all allies in range
    ENEMIES = "enemies"     # Target all enemies in range
    ALL = "all"             # Target all characters in range

class TargetingSystem:
    """
    Handles all targeting-related functionality for spells and abilities.
    """
    
    def __init__(self, dungeon=None):
        """
        Initialize the targeting system.
        
        Args:
            dungeon: Optional dungeon object to use for line of sight calculations
        """
        self.dungeon = dungeon
    
    def set_dungeon(self, dungeon):
        """
        Set the dungeon object for line of sight calculations.
        
        Args:
            dungeon: Dungeon object
        """
        self.dungeon = dungeon
    
    def get_valid_targets(self, caster, spell_data, all_characters=None):
        """
        Get all valid targets for a spell based on its targeting rules.
        
        Args:
            caster: Character casting the spell
            spell_data: Spell definition dictionary
            all_characters: Optional list of all characters to consider
            
        Returns:
            list: Valid target characters or positions
        """
        if all_characters is None:
            # If dungeon is available, get monsters from it
            if self.dungeon and hasattr(self.dungeon, 'monsters'):
                all_characters = [caster] + self.dungeon.monsters
            else:
                # Otherwise, we can only target the caster
                all_characters = [caster]
        
        # Get targeting parameters from the spell
        target_type = spell_data.get("targets", TargetMode.SINGLE)
        range_type = spell_data.get("range_type", "self")
        max_range = int(spell_data.get("max_range", 0))
        
        # Self-targeting spells can only target the caster
        if target_type == TargetMode.SELF or range_type == "self":
            return [caster]
        
        valid_targets = []
        
        # Filter potential targets based on range and line of sight
        for character in all_characters:
            # Skip dead characters
            if hasattr(character, 'is_dead') and character.is_dead:
                continue
                
            # Skip the caster for single-target spells (unless explicitly allowed)
            if character == caster and target_type == TargetMode.SINGLE:
                continue
            
            # Only include self for self-targeting spells
            if target_type == TargetMode.SELF and character != caster:
                continue
            
            # Check if target is in range and has line of sight
            if self.is_in_range(caster, character, max_range) and self.has_line_of_sight(caster, character):
                # For ally/enemy targeting, check if target is of the right type
                if target_type == TargetMode.ALLIES and not self.is_ally(caster, character):
                    continue
                if target_type == TargetMode.ENEMIES and not self.is_enemy(caster, character):
                    continue
                
                valid_targets.append(character)
        
        return valid_targets
    
    def is_in_range(self, source, target, max_range, range_type="manhattan"):
        """
        Check if a target is within range of a source using the specified distance metric.
        
        Args:
            source: Source character or position
            target: Target character or position
            max_range: Maximum range in tiles
            range_type: Type of distance calculation to use:
                        "manhattan" - Manhattan distance (default, good for 4-way movement)
                        "chebyshev" - Chebyshev distance (good for 8-way movement)
                        "euclidean" - Euclidean distance (true geometric distance)
            
        Returns:
            bool: True if in range
        """
        # Unlimited range or source is target
        if max_range <= 0 or source == target:
            return True
        
        # Get positions
        source_pos = self.get_position(source)
        target_pos = self.get_position(target)
        
        # Convert to tile coordinates if needed
        source_tile = self.pixel_to_tile(source_pos)
        target_tile = self.pixel_to_tile(target_pos)
        
        # Calculate distance based on specified range type
        if range_type == "manhattan":
            # Manhattan distance (sum of horizontal and vertical distances)
            # Good for movement that can only go orthogonally (no diagonals)
            distance = abs(source_tile[0] - target_tile[0]) + abs(source_tile[1] - target_tile[1])
        elif range_type == "chebyshev":
            # Chebyshev distance (maximum of horizontal and vertical distances)
            # Good for movement that allows diagonals at the same cost as orthogonal
            distance = max(abs(source_tile[0] - target_tile[0]), abs(source_tile[1] - target_tile[1]))
        elif range_type == "euclidean":
            # Euclidean distance (straight-line distance)
            # Good for realistic distance but more complex
            distance = self.calculate_euclidean_distance(source_pos, target_pos)
        else:
            # Default to Manhattan if invalid type provided
            distance = abs(source_tile[0] - target_tile[0]) + abs(source_tile[1] - target_tile[1])
        
        # Compare calculated distance to max_range
        return distance <= max_range
    
    def has_line_of_sight(self, source, target):
        """
        Check if there's a clear line of sight between source and target.
        
        Args:
            source: Source character or position
            target: Target character or position
            
        Returns:
            bool: True if line of sight exists
        """
        # Always have line of sight to self
        if source == target:
            return True
        
        # Need dungeon for line of sight checks
        if not self.dungeon:
            return True  # Default to true if no dungeon
        
        # Get positions
        source_pos = self.get_position(source)
        target_pos = self.get_position(target)
        
        # Get tile positions
        source_tile = self.pixel_to_tile(source_pos)
        target_tile = self.pixel_to_tile(target_pos)
        
        # Handle adjacent targets - always have line of sight to adjacent targets
        if self.are_adjacent(source_tile, target_tile):
            return True
        
        # Use Bresenham's algorithm to trace line of sight
        cells = self.bresenham_line(source_tile[0], source_tile[1], target_tile[0], target_tile[1])
        
        # Check if the cells list is empty or has only source/target
        if len(cells) <= 2:
            return True
        
        # Skip the first cell (source) and check all intermediate cells
        for x, y in cells[1:-1]:  # Skip source and target
            # Check if cell is out of bounds
            if x < 0 or y < 0 or x >= self.dungeon.width or y >= self.dungeon.height:
                return False  # Out of bounds
            
            # Check if the tile exists in the dungeon
            if x >= len(self.dungeon.tiles) or y >= len(self.dungeon.tiles[x]):
                return False
            
            tile = self.dungeon.tiles[x][y]
            
            # Check if tile is a wall (always blocks LOS)
            if hasattr(tile, 'type') and tile.type == 'wall':
                return False
            
            # Check if tile is a door
            if hasattr(tile, 'type') and tile.type == 'door':
                # Check all doors to find if this one is open
                door_is_open = False
                for coord, door in self.dungeon.doors.items():
                    if coord == (x, y):
                        door_is_open = door.open
                        break
                
                # Closed doors block line of sight
                if not door_is_open:
                    return False
        
        return True
        
    def are_adjacent(self, tile1, tile2):
        """
        Check if two tiles are adjacent (including diagonals).
        
        Args:
            tile1: First tile coordinates (x, y)
            tile2: Second tile coordinates (x, y)
            
        Returns:
            bool: True if tiles are adjacent
        """
        dx = abs(tile1[0] - tile2[0])
        dy = abs(tile1[1] - tile2[1])
        
        # Adjacent if the sum of differences is 1 (orthogonal) 
        # or if both differences are 1 (diagonal)
        return (dx + dy == 1) or (dx == 1 and dy == 1)
    
    def calculate_manhattan_distance(self, pos1, pos2):
        """
        Calculate Manhattan distance between two positions.
        
        Args:
            pos1: First position (x, y)
            pos2: Second position (x, y)
            
        Returns:
            int: Manhattan distance in tiles
        """
        # Convert to tile coordinates if needed
        tile1 = self.pixel_to_tile(pos1)
        tile2 = self.pixel_to_tile(pos2)
        
        return abs(tile1[0] - tile2[0]) + abs(tile1[1] - tile2[1])
    
    def calculate_euclidean_distance(self, pos1, pos2):
        """
        Calculate Euclidean distance between two positions.
        
        Args:
            pos1: First position (x, y)
            pos2: Second position (x, y)
            
        Returns:
            float: Euclidean distance in tiles
        """
        # Convert to tile coordinates if needed
        tile1 = self.pixel_to_tile(pos1)
        tile2 = self.pixel_to_tile(pos2)
        
        return math.sqrt((tile1[0] - tile2[0])**2 + (tile1[1] - tile2[1])**2)
    
    def pixel_to_tile(self, pos):
        """
        Convert pixel coordinates to tile coordinates.
        
        Args:
            pos: Position in pixels (x, y)
            
        Returns:
            tuple: Position in tiles (x, y)
        """
        # If the position is already a character, get its position
        if not isinstance(pos, (list, tuple)):
            if hasattr(pos, 'position'):
                pos = pos.position
            else:
                return (0, 0)  # Default if no position available
        
        # Import tile size from common module
        from common_b_s import TILE_SIZE
        
        return (pos[0] // TILE_SIZE, pos[1] // TILE_SIZE)
    
    def get_position(self, entity):
        """
        Get the position of an entity.
        
        Args:
            entity: Either a character object with position attribute, or a position tuple
            
        Returns:
            tuple/list: Position as (x, y)
        """
        if isinstance(entity, (list, tuple)):
            return entity  # Entity is already a position
        elif hasattr(entity, 'position'):
            return entity.position  # Entity is a character with position
        else:
            return (0, 0)  # Default if no position found
    
    def is_ally(self, character1, character2):
        """
        Check if two characters are allies.
        
        Args:
            character1: First character
            character2: Second character
            
        Returns:
            bool: True if characters are allies
        """
        # Consider player characters to be allies with each other
        if hasattr(character1, 'is_player') and hasattr(character2, 'is_player'):
            return character1.is_player and character2.is_player
        
        # Otherwise, characters are allies if they're the same type (monster/player)
        is_monster1 = hasattr(character1, 'monster_type')
        is_monster2 = hasattr(character2, 'monster_type')
        
        return is_monster1 == is_monster2
    
    def is_enemy(self, character1, character2):
        """
        Check if two characters are enemies.
        
        Args:
            character1: First character
            character2: Second character
            
        Returns:
            bool: True if characters are enemies
        """
        # Opposite of is_ally
        return not self.is_ally(character1, character2)
    
    def bresenham_line(self, x0, y0, x1, y1):
        """
        Generate a list of cells that a line from (x0, y0) to (x1, y1) passes through.
        
        Args:
            x0, y0: Starting position
            x1, y1: Ending position
            
        Returns:
            list: Cells the line passes through as [(x, y), ...]
        """
        cells = []
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        
        while True:
            cells.append((x0, y0))
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy
        
        return cells
    
    def get_area_of_effect(self, center, area_size, shape="circle", check_bounds=True, check_los=False, source=None):
        """
        Get all tiles within an area of effect.
        
        Args:
            center: Center position of the area
            area_size: Size of the area (radius for circle, width for square)
            shape: Shape of the area ("circle", "square", "diamond")
            check_bounds: Whether to check if tiles are within dungeon bounds
            check_los: Whether to check line of sight from source to each tile
            source: Source character or position for line of sight checks
            
        Returns:
            list: Tiles within the area as [(x, y), ...]
        """
        center_tile = self.pixel_to_tile(center)
        result = []
        
        # Get dungeon dimensions if available
        max_x, max_y = float('inf'), float('inf')
        if check_bounds and self.dungeon:
            max_x, max_y = self.dungeon.width, self.dungeon.height
        
        # Get all tiles within the area based on shape
        if shape == "circle":
            # For a circle, get tiles within radius using Euclidean distance
            for dx in range(-area_size, area_size + 1):
                for dy in range(-area_size, area_size + 1):
                    x, y = center_tile[0] + dx, center_tile[1] + dy
                    
                    # Check if within radius using Euclidean distance
                    distance = math.sqrt(dx*dx + dy*dy)
                    if distance <= area_size:
                        # Check bounds if requested
                        if not check_bounds or (0 <= x < max_x and 0 <= y < max_y):
                            # Check line of sight if requested
                            if not check_los or source is None or self.has_los_to_tile(source, (x, y)):
                                result.append((x, y))
                                
        elif shape == "diamond":
            # For a diamond (Manhattan distance), get tiles within radius
            for dx in range(-area_size, area_size + 1):
                for dy in range(-area_size, area_size + 1):
                    x, y = center_tile[0] + dx, center_tile[1] + dy
                    
                    # Check if within radius using Manhattan distance
                    distance = abs(dx) + abs(dy)
                    if distance <= area_size:
                        # Check bounds if requested
                        if not check_bounds or (0 <= x < max_x and 0 <= y < max_y):
                            # Check line of sight if requested
                            if not check_los or source is None or self.has_los_to_tile(source, (x, y)):
                                result.append((x, y))
                                
        elif shape == "square":
            # For a square (Chebyshev distance), get all tiles within the square
            for dx in range(-area_size, area_size + 1):
                for dy in range(-area_size, area_size + 1):
                    x, y = center_tile[0] + dx, center_tile[1] + dy
                    
                    # Check bounds if requested
                    if not check_bounds or (0 <= x < max_x and 0 <= y < max_y):
                        # Check line of sight if requested
                        if not check_los or source is None or self.has_los_to_tile(source, (x, y)):
                            result.append((x, y))
        
        return result
        
    def has_los_to_tile(self, source, target_tile):
        """
        Check if there's a clear line of sight from a source to a specific tile.
        
        Args:
            source: Source character or position
            target_tile: Target tile coordinates (x, y)
            
        Returns:
            bool: True if line of sight exists
        """
        # Create a dummy target positioned at the center of the target tile
        from common_b_s import TILE_SIZE
        
        # Convert target tile to pixel position (center of tile)
        target_pos = [
            target_tile[0] * TILE_SIZE + TILE_SIZE // 2,
            target_tile[1] * TILE_SIZE + TILE_SIZE // 2
        ]
        
        # Create a dummy target object
        class DummyTarget:
            def __init__(self, pos):
                self.position = pos
        
        dummy_target = DummyTarget(target_pos)
        
        # Use the existing line of sight function
        return self.has_line_of_sight(source, dummy_target)
    
    def get_line_of_effect(self, start, end, width=1):
        """
        Get all tiles in a line from start to end with a given width.
        
        Args:
            start: Starting position
            end: Ending position
            width: Width of the line in tiles
            
        Returns:
            list: Tiles within the line as [(x, y), ...]
        """
        start_tile = self.pixel_to_tile(start)
        end_tile = self.pixel_to_tile(end)
        
        # Get the base line
        line = self.bresenham_line(start_tile[0], start_tile[1], end_tile[0], end_tile[1])
        
        # If width is 1, return the line as is
        if width <= 1:
            return line
        
        # For wider lines, add additional tiles perpendicular to the line
        result = line.copy()
        
        # Get the direction vector
        if len(line) < 2:
            return line  # Can't determine direction with just one point
        
        # Calculate perpendicular direction
        dx = line[1][0] - line[0][0]
        dy = line[1][1] - line[0][1]
        
        # Normalize
        length = math.sqrt(dx*dx + dy*dy)
        if length > 0:
            dx, dy = dx/length, dy/length
        
        # Perpendicular vector
        px, py = -dy, dx
        
        # Add tiles on both sides
        half_width = width // 2
        for i in range(1, half_width + 1):
            for x, y in line:
                # Add tiles perpendicular to the line
                result.append((int(x + i*px), int(y + i*py)))
                result.append((int(x - i*px), int(y - i*py)))
        
        return result
    
    def get_cone_of_effect(self, source, direction, range_tiles, angle_degrees):
        """
        Get all tiles in a cone starting from source in the given direction.
        
        Args:
            source: Source position
            direction: Direction vector (dx, dy)
            range_tiles: Range of the cone in tiles
            angle_degrees: Angle of the cone in degrees
            
        Returns:
            list: Tiles within the cone as [(x, y), ...]
        """
        source_tile = self.pixel_to_tile(source)
        result = []
        
        # Convert angle to radians
        angle_radians = math.radians(angle_degrees)
        half_angle = angle_radians / 2
        
        # Normalize direction vector
        dx, dy = direction
        length = math.sqrt(dx*dx + dy*dy)
        if length > 0:
            dx, dy = dx/length, dy/length
        
        # Get all tiles in range
        for x in range(source_tile[0] - range_tiles, source_tile[0] + range_tiles + 1):
            for y in range(source_tile[1] - range_tiles, source_tile[1] + range_tiles + 1):
                # Skip source
                if x == source_tile[0] and y == source_tile[1]:
                    continue
                
                # Check if within range
                distance = math.sqrt((x - source_tile[0])**2 + (y - source_tile[1])**2)
                if distance > range_tiles:
                    continue
                
                # Check if within cone angle
                # Vector from source to tile
                vx, vy = x - source_tile[0], y - source_tile[1]
                
                # Normalize
                v_length = math.sqrt(vx*vx + vy*vy)
                if v_length > 0:
                    vx, vy = vx/v_length, vy/v_length
                
                # Dot product gives cosine of angle between vectors
                dot_product = dx*vx + dy*vy
                
                # Convert to angle
                angle = math.acos(max(-1, min(1, dot_product)))
                
                # Check if within half angle
                if angle <= half_angle:
                    result.append((x, y))
        
        return result

# Create a global instance of the targeting system
targeting_system = TargetingSystem()

# Helper function to check if a spell can target a specific character
def can_target(caster, target, spell_data, dungeon=None):
    """
    Check if a spell can target a specific character.
    
    Args:
        caster: Character casting the spell
        target: Target character
        spell_data: Spell definition dictionary
        dungeon: Optional dungeon object
        
    Returns:
        tuple: (can_target, message) where can_target is a boolean and
               message explains why not if applicable
    """
    # Set dungeon if provided
    if dungeon:
        targeting_system.set_dungeon(dungeon)
    
    # Get targeting parameters from the spell
    target_type = spell_data.get("targets", TargetMode.SINGLE)
    range_type = spell_data.get("range_type", "self")
    max_range = int(spell_data.get("max_range", 0))
    distance_metric = spell_data.get("distance_metric", "manhattan")
    
    # Special case for area spells centered on caster
    if range_type == "self" and target_type == TargetMode.AREA:
        # Allow targeting anywhere (but will be centered on caster)
        return True, ""
    
    # Self-targeting spells that aren't area effects can only target the caster
    if target_type == TargetMode.SELF or range_type == "self":
        if target != caster:
            return False, "This spell can only target the caster."
        return True, ""
    
    # Touch range requires adjacency
    if range_type == "touch":
        source_tile = targeting_system.pixel_to_tile(targeting_system.get_position(caster))
        target_tile = targeting_system.pixel_to_tile(targeting_system.get_position(target))
        
        if not targeting_system.are_adjacent(source_tile, target_tile):
            return False, "Target must be adjacent for touch spells."
        return True, ""  # No need for further checks if touch is valid
    
    # Check if target is in range using the appropriate distance metric
    if not targeting_system.is_in_range(caster, target, max_range, distance_metric):
        if distance_metric == "manhattan":
            return False, f"Target is out of range ({max_range} tiles walking distance)."
        elif distance_metric == "chebyshev":
            return False, f"Target is out of range ({max_range} tiles in any direction)."
        else:
            return False, f"Target is out of range ({max_range} tiles)."
    
    # For ranged spells, check line of sight
    if range_type == "ranged" and not targeting_system.has_line_of_sight(caster, target):
        return False, "No clear line of sight to target."
    
    # Check if target is valid for ally/enemy targeting
    if target_type == TargetMode.ALLIES and not targeting_system.is_ally(caster, target):
        return False, "This spell can only target allies."
    if target_type == TargetMode.ENEMIES and not targeting_system.is_enemy(caster, target):
        return False, "This spell can only target enemies."
    
    return True, ""

# Helper function to get all targets within an area of effect
def get_area_targets(center, area_size, all_characters=None, shape="circle", caster=None, 
                   include_allies=True, include_enemies=True, check_los=False, dungeon=None):
    """
    Get all characters within an area of effect with filtering options.
    
    Args:
        center: Center position or character
        area_size: Size of the area
        all_characters: List of all potential target characters
        shape: Shape of the area ("circle", "square", or "diamond")
        caster: Character casting the spell (for ally/enemy determination)
        include_allies: Whether to include allies in results
        include_enemies: Whether to include enemies in results
        check_los: Whether to check line of sight from center to each character
        dungeon: Optional dungeon object for bounds checking
        
    Returns:
        list: Characters within the area of effect that match the criteria
    """
    if all_characters is None:
        return []
    
    # Set dungeon if provided
    if dungeon:
        targeting_system.set_dungeon(dungeon)
    
    # Get the area tiles with requested filters
    source = caster if check_los else None
    tiles = targeting_system.get_area_of_effect(
        targeting_system.get_position(center), 
        area_size, 
        shape=shape,
        check_bounds=True,
        check_los=check_los,
        source=source
    )
    
    # Find all characters within those tiles
    result = []
    for character in all_characters:
        # Skip dead characters
        if hasattr(character, 'is_dead') and character.is_dead:
            continue
            
        # Get character position
        pos = targeting_system.get_position(character)
        tile = targeting_system.pixel_to_tile(pos)
        
        # Check if character is in the area
        if tile in tiles:
            # Check ally/enemy status if caster is provided
            if caster is not None:
                is_ally = targeting_system.is_ally(caster, character)
                
                # Skip allies if we're not including them
                if is_ally and not include_allies:
                    continue
                    
                # Skip enemies if we're not including them
                if not is_ally and not include_enemies:
                    continue
            
            # Character passes all filters, add to result
            result.append(character)
    
    return result