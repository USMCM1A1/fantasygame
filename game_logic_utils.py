import random
# Assuming items_list and add_message might be needed from common_b_s or another shared module.
# For now, to break cycles, these dependencies need to be carefully managed.
# If items_list is global in common_b_s, common_b_s cannot import this module directly if this module needs it.
# Let's assume items_list will be passed or imported from a safe location.
# add_message is also critical.

# To avoid direct import of common_b_s here if common_b_s will import this,
# these functions might need to take `items_list` and `add_message_func` as parameters.

# For now, let's assume common_b_s will be refactored NOT to import this directly,
# or these functions will be called from a higher level module that can provide these.
# If common_b_s needs process_monster_death, then common_b_s cannot import this.

# Option 1: Make them truly independent by passing dependencies.
# Option 2: Move items_list and add_message to a lower-level module than both. (game_config or game_data_loader)

# Let's try to make it so common_b_s does NOT import this file.
# game_loop.py will import this and can pass common_b_s.add_message or common_b_s.items_list if needed.
# However, process_monster_death is called by game_loop.py's combat function, which in turn calls this.
# The original call was common_b_s.process_monster_death.

# For now, to make it runnable, I'll import what it needs.
# This implies common_b_s cannot import game_logic_utils.
# The spell_system also calls process_monster_death.
# If spell_system imports this, and common_b_s imports spell_system (via spell_bridge), then common_b_s cannot import this.

# This is the core of the cycle problem.
# Let's assume `add_message` and `items_list` will be passed if needed, or handled by the caller.
# For now, to get the function out, I'll define it.
# The call from spell_system needs to be refactored.

# Refined approach:
# process_monster_death is called by game_loop.py (via combat) and Data/spell_system.py
# game_loop.py can easily access common_b_s.add_message and common_b_s.items_list.
# Data/spell_system.py cannot easily access common_b_s without a cycle.
#
# Solution idea:
# 1. Define process_monster_death here.
# 2. It needs `add_message` and `items_list`.
# 3. `game_loop.py` can import this and call it, providing `common_b_s.add_message` and `common_b_s.items_list`.
# 4. `Data/spell_system.py` needs to be changed: instead of calling `process_monster_death` directly,
#    it should return information that a monster died, and `game_loop.py` (the caller of `cast_spell`)
#    will then call `process_monster_death` from `game_logic_utils.py`.
# This breaks the need for spell_system to know about monster death processing details.

def process_monster_death(monster, player, dungeon_instance, add_message_func, items_list_ref):
    """
    Handles the logic when a monster dies, including XP and loot.
    Args:
        monster: The Monster object that died.
        player: The Player object.
        dungeon_instance: The current Dungeon instance.
        add_message_func: Function to call for displaying messages (e.g., common_b_s.add_message).
        items_list_ref: Reference to the global list of items for loot drops.
    Returns:
        list: A list of messages related to the monster's death.
    """
    messages = []

    if not hasattr(monster, 'monster_type'): # Should not happen for actual monsters
        messages.append(f"{monster.name} has been defeated!")
        return messages

    monster.hit_points = 0
    monster.set_dead_sprite() # Assumes monster object has this method
    monster.is_dead = True

    if dungeon_instance is not None:
        dungeon_instance.remove_monster(monster) # Assumes dungeon has this method

    messages.append(f"A {monster.name} has died.")

    cr = getattr(monster, 'cr', 1)
    num_items = min(3, max(1, cr))
    drop_chance = min(0.99, 0.7 + (cr * 0.05))

    for _ in range(num_items):
        if random.random() < drop_chance and items_list_ref:
            # We need deepcopy for items if they are mutable and we don't want to alter the master list.
            # Assuming items in items_list_ref are like templates.
            from copy import deepcopy
            dropped_item_template = random.choice(items_list_ref)
            dropped_item = deepcopy(dropped_item_template) # Create a new instance

            if hasattr(dropped_item, "name"):
                drop_position = monster.position[:]
                if dungeon_instance is not None:
                    dungeon_instance.dropped_items.append({'item': dropped_item, 'position': drop_position})
                messages.append(f"The {monster.name} dropped a {dropped_item.name}!")

    xp_gained = cr * 50
    if hasattr(player, 'add_experience'): # Check if Player object has this method
        # add_experience should just add XP, not handle level up messages.
        # Level up checks and messages should be handled by the game loop or player class after XP gain.
        player.add_experience(xp_gained)
        messages.append(f"{player.name} gains {xp_gained} XP from defeating the {monster.name}!")

    return messages

def can_equip_item(player, item_to_equip):
    """
    Checks if the player can equip the given item.
    Args:
        player: The Player object.
        item_to_equip: The Item object to check.
    Returns:
        tuple: (can_equip_bool, reason_string)
    """
    if not item_to_equip:
        return False, "Item does not exist."

    # 1. Check Requirements (level, class, stats)
    if hasattr(item_to_equip, 'meets_requirements'):
        can_meet_reqs, reason = item_to_equip.meets_requirements(player)
        if not can_meet_reqs:
            return False, reason

    # 2. Check Equipment Slot
    slot = getattr(item_to_equip, 'equipment_slot', None)
    if not slot:
        return False, f"{item_to_equip.name} is not equippable."

    if slot == "weapon":
        # Player can always equip a weapon, it will replace the old one.
        # Add specific logic for two-handed weapons if applicable:
        # if item_to_equip.is_two_handed and player.equipment.get("shield"):
        #     return False, "Cannot equip a two-handed weapon while a shield is equipped."
        pass
    elif slot == "shield":
        # if player.equipment.get("weapon") and player.equipment.get("weapon").is_two_handed:
        #     return False, "Cannot equip a shield while a two-handed weapon is equipped."
        pass
    elif slot == "armor":
        pass # Armor just replaces old armor
    elif slot == "jewelry":
        # Example: Limit number of rings or amulets if needed
        # For simplicity, assume any number of jewelry can be equipped for now,
        # or that specific jewelry types (ring, amulet) are handled by Player.equip_item
        # This basic check here is about general equippability.
        # More complex logic (e.g. max 2 rings) should be in Player.equip_item or a more specific check.
        pass
    elif slot == "inventory": # Explicitly non-equippable if slot is "inventory"
        return False, f"{item_to_equip.name} cannot be equipped."
    else: # Unknown slot
        return False, f"Unknown equipment slot: {slot} for {item_to_equip.name}."

    # 3. Class Restrictions (if not covered by item.meets_requirements)
    # Example: if item_to_equip.restricted_to_class and player.char_class not in item_to_equip.restricted_to_class:
    #     return False, f"{item_to_equip.name} cannot be used by {player.char_class}."

    return True, ""

def handle_targeting(caster, target, spell_properties, dungeon_instance):
    """
    Placeholder for the original handle_targeting function.
    The new spell system uses Data.targeting_system.can_target.
    This placeholder allows legacy calls to resolve.
    Args:
        caster: The character casting the spell.
        target: The intended target (can be a character or a position).
        spell_properties: Dictionary of the spell's properties.
        dungeon_instance: The current dungeon object.
    Returns:
        tuple: (is_valid_target_bool, message_string)
    """
    # In a real implementation, this would involve:
    # 1. Checking spell range (e.g., spell_properties.get("max_range"))
    # 2. Checking line of sight if applicable (dungeon_instance.has_line_of_sight)
    # 3. Checking target type (self, enemy, ally, point)
    # For now, assume target is valid if it exists.
    if target is None and spell_properties.get("targets", "single") != "self": # "self" spells might not have a target initially
        return False, "No target selected for non-self spell."

    # This is a very basic placeholder. The original common_b_s.can_target_spell
    # (which handle_targeting likely called or was part of) had more detailed logic.
    # If USING_NEW_SPELL_SYSTEM is True, common_b_s.can_target_spell uses Data.targeting_system.can_target.
    # This placeholder is mainly for calls from modules that haven't been updated to the new system.
    print(f"Warning: Using placeholder game_logic_utils.handle_targeting for {spell_properties.get('name')}.")
    return True, "Targeting assumed valid by placeholder."

def compute_fov(dungeon, player, radius):
    """
    Placeholder for Field of View calculation.
    The original was in common_b_s.py and used bresenham and has_line_of_sight.
    Args:
        dungeon: The current dungeon object.
        player: The player object.
        radius: The radius of the FOV.
    Returns:
        set: A set of (x, y) tuples representing visible cells.
    """
    # For now, return a very simple FOV: just the player's current tile and immediate neighbors.
    # This allows the game to run without crashing. Actual FOV logic is complex.
    visible_cells = set()
    if not player or not hasattr(player, 'position'):
        print("Warning: compute_fov called with invalid player or player position.")
        return visible_cells

    from game_config import TILE_SIZE # TILE_SIZE needed for tile conversion
    player_tile_x = player.position[0] // TILE_SIZE
    player_tile_y = player.position[1] // TILE_SIZE

    visible_cells.add((player_tile_x, player_tile_y))
    for dx in range(-1, 2):
        for dy in range(-1, 2):
            if dx == 0 and dy == 0:
                continue
            check_x, check_y = player_tile_x + dx, player_tile_y + dy
            # Basic bounds check, assuming dungeon has width/height attributes
            if hasattr(dungeon, 'width') and hasattr(dungeon, 'height'):
                if 0 <= check_x < dungeon.width and 0 <= check_y < dungeon.height:
                    visible_cells.add((check_x, check_y))
            else: # If no dungeon dimensions, just add (might include out-of-bounds if not careful)
                 visible_cells.add((check_x, check_y))


    print(f"Warning: Using placeholder game_logic_utils.compute_fov for player at ({player_tile_x},{player_tile_y}).")
    return visible_cells

def get_valid_equipment_slots():
    """
    Returns a list of valid equipment slot names.
    Placeholder function.
    """
    # This should align with how equipment slots are defined and used in Player class
    # and potentially item data.
    slots = [
        "weapon",
        "shield",
        "armor",
        # Assuming a player can have multiple jewelry items,
        # the actual slot might be more dynamic e.g. "jewelry_1", "jewelry_2"
        # or the Player class handles how many of type "jewelry" can be equipped.
        # For now, a generic "jewelry" slot might be too simple if specific ring/amulet slots are needed.
        # Let's assume a few distinct slots for common jewelry types for now.
        "ring1",
        "ring2",
        "amulet",
        "head",
        "hands",
        "feet",
        "belt"
    ]
    print("Warning: Using placeholder game_logic_utils.get_valid_equipment_slots().")
    return slots

def swap_equipment(player, slot1_name, slot2_name):
    """Placeholder for swapping equipment between two slots."""
    print(f"Warning: Placeholder swap_equipment called for {player.name}, {slot1_name}, {slot2_name}.")
    # Actual logic would involve:
    # - Getting items from player.equipment[slot1_name] and player.equipment[slot2_name]
    # - Checking if slots are compatible or if one is inventory
    # - Updating player.equipment
    # - Applying/removing item effects
    return False, "Swap equipment placeholder not implemented."

def unequip_item(player, item_slot_or_object):
    """Placeholder for unequipping an item."""
    # This function might take a slot name or the item object itself.
    # For simplicity, assume it's a slot name for now.
    print(f"Warning: Placeholder unequip_item called for {player.name}, slot/item: {item_slot_or_object}.")
    # Actual logic:
    # - Find item in player.equipment based on slot_or_object
    # - Remove its effects
    # - Move to player.inventory
    # - Clear the slot in player.equipment
    return False, "Unequip item placeholder not implemented."

def get_clicked_equipment_slot(player, mouse_pos, equipment_panel_rect, slot_layout_info):
    """
    Placeholder to determine which equipment slot was clicked.
    This is highly UI-dependent.
    """
    print(f"Warning: Placeholder get_clicked_equipment_slot called at {mouse_pos}.")
    # Actual logic:
    # - Iterate through slot_layout_info (which would contain rects for each slot)
    # - Check if mouse_pos collides with any slot_rect relative to equipment_panel_rect
    # - Return the name of the clicked slot or None.
    return None

def shop_interaction(screen, clock, player):
    """Placeholder for the shop interaction UI and logic."""
    print(f"Warning: Placeholder shop_interaction called for player {player.name}.")
    # This would be a complex function, likely with its own event loop,
    # displaying shop inventory, player inventory, handling buy/sell.
    # For now, just a print and return.
    # It might need access to add_message, specific item lists for the shop, etc.
    if hasattr(player, 'add_message'): # Check if player has add_message (it's usually global)
        player.add_message("The shop is currently closed (placeholder).")
    else: # Fallback if add_message isn't directly on player
        pass # Or find another way to message if necessary
    return # No specific return value defined in original usage pattern.

def manage_inventory(player, screen, clock, font): # Added typical params
    """Placeholder for managing inventory UI and logic."""
    print(f"Warning: Placeholder manage_inventory called for player {player.name}.")
    # This would be a complex UI state, similar to shop_interaction.
    # For now, just a print. It likely needs add_message, and various drawing utils.
    # Might also need item data and player's inventory access.
    # Returning a game state or None if it's a blocking state.
    if hasattr(player, 'add_message'):
        player.add_message("Inventory is currently unavailable (placeholder).")
    return None # Or a new game state if it's a state function

def display_help_screen(screen, font): # Added typical params
    """Placeholder for displaying the help screen."""
    print(f"Warning: Placeholder display_help_screen called.")
    # This would draw a help overlay or screen.
    # Needs access to drawing utilities and potentially text content for help.
    # For now, just a print.
    # Example: screen.fill((0,0,0)); draw_text("Help Screen Placeholder", screen, ...); pygame.display.flip(); wait_for_key()
    if font: # Basic check
        pass # Actual drawing would go here.
    return None

def handle_monster_turn(monster, player, dungeon_tiles, dungeon_instance):
    """
    Placeholder for processing a single monster's turn.
    Args:
        monster: The Monster object whose turn it is.
        player: The Player object.
        dungeon_tiles: The grid of tiles in the dungeon.
        dungeon_instance: The current Dungeon instance.
    """
    # Basic placeholder logic:
    # - Monster might try to move towards the player if not adjacent.
    # - If adjacent, monster might attack the player.
    # - This would involve pathfinding (e.g., A* or simpler) and combat rolls.

    messages = [] # In case this function needs to return messages in the future.

    if not monster or not monster.is_alive:
        return messages

    # Example: Simple "move towards player if not adjacent, else attack"
    # This requires TILE_SIZE for distance calculation and player/monster having x,y attributes.
    # For simplicity, this placeholder won't implement actual movement or attack.

    # Rough distance check (assuming monster and player have x,y attributes in tile coordinates)
    # dx = player.x - monster.x
    # dy = player.y - monster.y

    # if abs(dx) <= 1 and abs(dy) <= 1: # Adjacent (including diagonals)
    #     # Placeholder for attack
    #     if hasattr(monster, 'attack_power'): # A simple check
    #         print(f"{monster.name} attacks {player.name} (placeholder).")
    #         # Actual attack logic would go here.
    #     else:
    #         print(f"{monster.name} is near {player.name} but cannot attack (placeholder).")
    # else:
    #     # Placeholder for movement
    #     print(f"{monster.name} moves (placeholder).")
    #     # Actual pathfinding and move logic would go here.
    #     # monster.move_towards(player, dungeon_tiles, dungeon_instance)

    print(f"Warning: Using placeholder game_logic_utils.handle_monster_turn for {monster.name}.")

    # To integrate with game_loop.py's message handling, this function could return messages.
    # For now, it just prints. If messages are to be displayed in game log,
    # it should append to `messages` list and return it, and game_loop should process them.
    # e.g., messages.append(f"{monster.name} growls menacingly.")
    return messages
