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
# If common_b_s needs process_monster_death, then common_b_s cannot be imported here.

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
