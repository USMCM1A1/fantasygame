import pygame
import sys
import os
import random # Added for handle_dungeon_map_transition

# It's good practice to only import what's necessary.
# However, to exactly replicate the dependencies of show_title_screen
# as it was in blade_sigil_v5_5.py, we might need more from common_b_s.
# For now, starting with the essentials.
import json
import datetime
from copy import deepcopy

from common_b_s import (
    DUNGEON_SCREEN_WIDTH, DUNGEON_SCREEN_HEIGHT, WHITE, font, # for show_title_screen
    Character, Dungeon, Tile, Door, Chest, Monster, Item, # Basic game object classes
    Weapon, Armor, Shield, Jewelry, Consumable, # Item subclasses
    create_item, load_sprite, assets_data, condition_manager, # Utilities and data
    roll_dice_expression, # for Player gold initialization within load_game if new player created
    # Added for state transitions and messaging:
    add_message, GREEN, RED, YELLOW, levelup_sound # Player removed
)
from player import Player # Player imported from player.py
# Player class from blade_sigil_v5_5.py is needed for save/load
# Player class is now imported from common_b_s to resolve circular dependency.
# from common_b_s import Player # Already added to the block above
from character_creation_ui import character_creation_screen
import novamagus_hub # For hub transitions and its transition_to_dungeon flag
import common_b_s # To access and modify common_b_s.in_dungeon -> This line is now uncommented.


class GameStateManager:
    def __init__(self):
        self.states = {}
        self.current_state = None

    def add_state(self, state_name, state_object):
        self.states[state_name] = state_object

    def set_state(self, state_name):
        if state_name in self.states:
            self.current_state = state_name
        else:
            print(f"Error: State '{state_name}' not found.")

    def get_state(self):
        if self.current_state and self.current_state in self.states:
            return self.states[self.current_state]
        else:
            return None

    def update(self, dt):
        state = self.get_state()
        if state:
            state.update(dt)

    def handle_events(self, events):
        state = self.get_state()
        if state:
            state.handle_events(events)

    def draw(self, screen):
        state = self.get_state()
        if state:
            state.draw(screen)

# === Save/Load Game System ===
def save_game(player, dungeon, game_state="dungeon"):
    """
    Save the current game state to a JSON file.

    Args:
        player: The Player object to save
        dungeon: The Dungeon object to save
        game_state: Current game state (hub or dungeon)

    Returns:
        bool: True if save was successful, False otherwise
    """
    # Create save directory if it doesn't exist
    # Using absolute path as it was in common_b_s.py
    save_dir = "/Users/williammarcellino/Documents/Fantasy_Game/B&S_savegame"
    os.makedirs(save_dir, exist_ok=True)

    save_file = os.path.join(save_dir, "savefile.json")

    try:
        # Create player data dictionary
        player_data = {
            "name": player.name,
            "race": player.race,
            "char_class": player.char_class,
            "position": player.position,
            "abilities": player.abilities,
            "level": player.level,
            "hit_points": player.hit_points,
            "max_hit_points": player.max_hit_points,
            "spell_points": player.spell_points,
            "gold": player.gold,
            "inventory": [],
            "equipment": {
                "weapon": None,
                "armor": None,
                "shield": None,
                "jewelry": []
            }
        }

        # Save inventory items
        for item_obj in player.inventory: # renamed item to item_obj to avoid conflict
            item_data = {
                "name": item_obj.name,
                "item_type": item_obj.item_type,
                "value": item_obj.value,
                "description": item_obj.description
            }

            if hasattr(item_obj, "damage"):
                item_data["damage"] = item_obj.damage
            if hasattr(item_obj, "ac_bonus"):
                item_data["ac"] = item_obj.ac_bonus
            if hasattr(item_obj, "bonus_stat") and hasattr(item_obj, "bonus_value"):
                if item_obj.bonus_stat == "intelligence": item_data["intelligence"] = item_obj.bonus_value
                elif item_obj.bonus_stat == "strength": item_data["strength"] = item_obj.bonus_value
                # ... (add other stats as needed) ...
                else: item_data[item_obj.bonus_stat] = item_obj.bonus_value # Generic case
                item_data["effect"] = {"type": "stat_bonus", "stat": item_obj.bonus_stat, "value": item_obj.bonus_value}
            elif hasattr(item_obj, "stat_bonus") and hasattr(item_obj, "bonus_value"): # Legacy
                 item_data["effect"] = {"type": "stat_bonus", "stat": item_obj.stat_bonus, "value": item_obj.bonus_value}

            player_data["inventory"].append(item_data)

        # Save equipment
        for slot, item_obj in player.equipment.items():
            if item_obj:
                if slot == "jewelry": # Jewelry is a list
                    player_data["equipment"]["jewelry"] = []
                    for jewel in item_obj:
                        jewel_data = {"name": jewel.name, "item_type": jewel.item_type, "value": jewel.value, "description": jewel.description}
                        if hasattr(jewel, "bonus_stat") and hasattr(jewel, "bonus_value"):
                            if jewel.bonus_stat == "intelligence": jewel_data["intelligence"] = jewel.bonus_value
                            # ... (add other stats) ...
                            else: jewel_data[jewel.bonus_stat] = jewel.bonus_value
                            jewel_data["effect"] = {"type": "stat_bonus", "stat": jewel.bonus_stat, "value": jewel.bonus_value}
                        elif hasattr(jewel, "stat_bonus") and hasattr(jewel, "bonus_value"): # Legacy
                             jewel_data["effect"] = {"type": "stat_bonus", "stat": jewel.stat_bonus, "value": jewel.bonus_value}
                        player_data["equipment"]["jewelry"].append(jewel_data)
                else:
                    item_data = {"name": item_obj.name, "item_type": item_obj.item_type, "value": item_obj.value, "description": item_obj.description}
                    if hasattr(item_obj, "damage"): item_data["damage"] = item_obj.damage
                    if hasattr(item_obj, "ac_bonus"): item_data["ac"] = item_obj.ac_bonus
                    player_data["equipment"][slot] = item_data

        dungeon_data = {
            "width": dungeon.width,
            "height": dungeon.height,
            "tiles": [],
            "doors": [],
            "chests": [],
            "monsters": [],
            "dropped_items": []
        }

        for x in range(dungeon.width):
            row = []
            for y in range(dungeon.height):
                tile = dungeon.tiles[x][y]
                row.append({"x": x, "y": y, "type": tile.type, "discovered": getattr(tile, 'discovered', False)}) # Added discovered
            dungeon_data["tiles"].append(row)

        for coords, door_obj in dungeon.doors.items():
            door_data = {"x": door_obj.x, "y": door_obj.y, "locked": door_obj.locked, "open": door_obj.open, "door_type": door_obj.door_type}
            if hasattr(door_obj, 'destination_map'): door_data['destination_map'] = door_obj.destination_map
            dungeon_data["doors"].append(door_data)

        for coords, chest_obj in dungeon.chests.items():
            chest_data = {"x": chest_obj.x, "y": chest_obj.y, "locked": chest_obj.locked, "open": chest_obj.open, "gold": chest_obj.gold, "contents": []}
            for item_obj_in_chest in chest_obj.contents:
                item_data = {"name": item_obj_in_chest.name, "item_type": item_obj_in_chest.item_type, "value": item_obj_in_chest.value, "description": item_obj_in_chest.description}
                if hasattr(item_obj_in_chest, "damage"): item_data["damage"] = item_obj_in_chest.damage
                if hasattr(item_obj_in_chest, "ac_bonus"): item_data["ac"] = item_obj_in_chest.ac_bonus
                chest_data["contents"].append(item_data)
            dungeon_data["chests"].append(chest_data)

        for monster_obj in dungeon.monsters:
            if monster_obj.is_dead: continue
            monster_data = {
                "name": monster_obj.name, "hit_points": monster_obj.hit_points, "max_hit_points": monster_obj.max_hit_points,
                "to_hit": monster_obj.to_hit, "ac": monster_obj.ac, "move": monster_obj.move, "dam": monster_obj.dam,
                "position": monster_obj.position, "monster_type": monster_obj.monster_type, "level": monster_obj.level, "cr": monster_obj.cr,
                "vulnerabilities": monster_obj.vulnerabilities, "resistances": monster_obj.resistances, "immunities": monster_obj.immunities
            }
            dungeon_data["monsters"].append(monster_data)

        for dropped in dungeon.dropped_items:
            item_obj_drop = dropped["item"]
            item_data = {"name": item_obj_drop.name, "item_type": item_obj_drop.item_type, "value": item_obj_drop.value, "description": item_obj_drop.description, "position": dropped["position"]}
            if hasattr(item_obj_drop, "damage"): item_data["damage"] = item_obj_drop.damage
            if hasattr(item_obj_drop, "ac_bonus"): item_data["ac"] = item_obj_drop.ac_bonus
            dungeon_data["dropped_items"].append(item_data)

        save_data = {
            "player": player_data,
            "dungeon": dungeon_data,
            "game_state": game_state,
            "condition_manager_turn": condition_manager.current_turn,
            "timestamp": datetime.datetime.now().isoformat(),
            "version": "1.0" # Or a dynamic version variable
        }

        with open(save_file, 'w') as f:
            json.dump(save_data, f, indent=4)

        print(f"Game saved successfully to {save_file}")
        return True

    except Exception as e:
        print(f"Error saving game: {e}")
        # Consider logging the full traceback here
        import traceback
        traceback.print_exc()
        return False

def load_game():
    """
    Load a game from the save file.
    """
    save_file = "/Users/williammarcellino/Documents/Fantasy_Game/B&S_savegame/savefile.json"

    if not os.path.exists(save_file):
        print("No save file found.")
        return None

    try:
        with open(save_file, 'r') as f:
            save_data = json.load(f)

        saved_cm_turn = save_data.get("condition_manager_turn", 0)
        player_data = save_data.get("player", {})
        dungeon_data_dict = save_data.get("dungeon", {}) # Renamed to avoid conflict with Dungeon class
        game_state = save_data.get("game_state", "dungeon")

        # Player object creation:
        # Using blade_sigil_v5_5.Player which inherits common_b_s.Character
        player_sprite_path_key = player_data.get("char_class", "Warrior").lower()
        sprite_path = assets_data["sprites"]["heroes"][player_sprite_path_key]["live"]
        player_sprite = load_sprite(sprite_path) # load_sprite is from common_b_s

        # Abilities might need deepcopy if they are complex objects, but here they are dicts of primitives
        abilities = deepcopy(player_data.get("abilities", {}))

        # Instantiate Player from blade_sigil_v5_5
        player = Player(
            name=player_data.get("name", "Hero"),
            race=player_data.get("race", "Human"),
            char_class=player_data.get("char_class", "Warrior"),
            start_position=player_data.get("position", [0,0]), # Provide a default
            sprite=player_sprite,
            abilities=abilities
        )

        player.level = player_data.get("level", 1)
        player.hit_points = player_data.get("hit_points", 10)
        player.max_hit_points = player_data.get("max_hit_points", 10)
        player.spell_points = player_data.get("spell_points", 0)
        player.gold = player_data.get("gold", 0)
        player.inventory = []
        player.equipment = {"weapon": None, "armor": None, "shield": None, "jewelry": []}

        for item_data in player_data.get("inventory", []):
            item_obj = create_item(item_data) # create_item from common_b_s
            if item_obj: player.inventory.append(item_obj)

        equipment_saved_data = player_data.get("equipment", {})
        for slot, item_data in equipment_saved_data.items():
            if item_data:
                if slot == "jewelry": # list of items
                    player.equipment["jewelry"] = []
                    for jewel_data in item_data: # item_data is a list here
                        jewel_obj = create_item(jewel_data)
                        if jewel_obj: player.equipment["jewelry"].append(jewel_obj)
                else: # single item
                    item_obj = create_item(item_data)
                    if item_obj: player.equipment[slot] = item_obj

        # Dungeon reconstruction:
        # game_dungeon will be a common_b_s.Dungeon instance
        game_dungeon = Dungeon(dungeon_data_dict.get("width", 20), dungeon_data_dict.get("height", 15))
        game_dungeon.tiles = [[Tile(x, y, 'wall') for y in range(game_dungeon.height)] for x in range(game_dungeon.width)] # Re-init tiles

        for x, row_data in enumerate(dungeon_data_dict.get("tiles", [])):
            if x < game_dungeon.width:
                for y, tile_data in enumerate(row_data):
                    if y < game_dungeon.height:
                        tile_type = tile_data.get("type", "wall")
                        game_dungeon.tiles[x][y].type = tile_type
                        game_dungeon.tiles[x][y].discovered = tile_data.get("discovered", False)
                        # Sprites for tiles are typically set by Tile constructor or Dungeon methods
                        if tile_type in ('floor', 'corridor'):
                            game_dungeon.tiles[x][y].sprite = load_sprite(assets_data["sprites"]["tiles"]["floor"])
                        elif tile_type == 'stair_up':
                            game_dungeon.tiles[x][y].sprite = load_sprite(assets_data["sprites"]["tiles"]["stair_up"])
                        elif tile_type == 'stair_down':
                            game_dungeon.tiles[x][y].sprite = load_sprite(assets_data["sprites"]["tiles"]["stair_down"])
                        # Door sprites are handled by Door class or when placing doors

        game_dungeon.doors = {}
        for door_data in dungeon_data_dict.get("doors", []):
            door_obj = Door(door_data.get("x"), door_data.get("y"), door_data.get("locked", False), door_data.get("door_type", "normal"))
            door_obj.open = door_data.get("open", False)
            if 'destination_map' in door_data: door_obj.destination_map = door_data['destination_map']
            game_dungeon.doors[(door_obj.x, door_obj.y)] = door_obj
            # Also update the tile where the door is
            if 0 <= door_obj.x < game_dungeon.width and 0 <= door_obj.y < game_dungeon.height:
                 game_dungeon.tiles[door_obj.x][door_obj.y].type = 'locked_door' if door_obj.locked else 'door'
                 game_dungeon.tiles[door_obj.x][door_obj.y].sprite = door_obj.sprite


        game_dungeon.chests = {}
        for chest_data in dungeon_data_dict.get("chests", []):
            chest_obj = Chest(chest_data.get("x"), chest_data.get("y"))
            chest_obj.locked = chest_data.get("locked", True)
            chest_obj.open = chest_data.get("open", False)
            chest_obj.gold = chest_data.get("gold", 0)
            chest_obj.contents = []
            for item_data_in_chest in chest_data.get("contents", []):
                item_obj = create_item(item_data_in_chest)
                if item_obj: chest_obj.contents.append(item_obj)
            game_dungeon.chests[(chest_obj.x, chest_obj.y)] = chest_obj
            # Update tile for chest sprite
            if 0 <= chest_obj.x < game_dungeon.width and 0 <= chest_obj.y < game_dungeon.height:
                game_dungeon.tiles[chest_obj.x][chest_obj.y].sprite = chest_obj.sprite


        game_dungeon.monsters = []
        for monster_data in dungeon_data_dict.get("monsters", []):
            # Create monster using common_b_s.Monster
            monster_obj = Monster(
                name=monster_data.get("name"), hit_points=monster_data.get("hit_points"),
                to_hit=monster_data.get("to_hit"), ac=monster_data.get("ac"),
                move=monster_data.get("move"), dam=monster_data.get("dam"),
                sprites=assets_data["monsters"].get(monster_data.get("name"), {}).get("sprites", {}), # Get sprites from assets_data
                monster_type=monster_data.get("monster_type"), level=monster_data.get("level"), cr=monster_data.get("cr")
            )
            monster_obj.position = monster_data.get("position")
            # Restore other attributes like vulnerabilities, resistances, immunities if needed
            game_dungeon.monsters.append(monster_obj)

        game_dungeon.dropped_items = []
        for item_drop_data in dungeon_data_dict.get("dropped_items", []):
            item_obj = create_item(item_drop_data) # create_item handles name, type, etc.
            if item_obj:
                game_dungeon.dropped_items.append({"item": item_obj, "position": item_drop_data.get("position")})

        # It's crucial that load_game returns the *reconstructed Dungeon object*, not the dict
        print(f"Game loaded successfully from {save_file}")
        return (player, game_dungeon, game_state, saved_cm_turn)

    except Exception as e:
        print(f"Error loading game: {e}")
        import traceback
        traceback.print_exc()
        return None

# === State Transition Functions ===

def set_game_state(new_state_str, player_obj=None, dungeon_obj=None):
    """
    Central function to set the game state and update in_dungeon.
    Returns the new_state_str.
    """
    # common_b_s.in_dungeon is now directly imported as in_dungeon
    # This global modification is tricky. Ideally, GameStateManager instance would hold this.
    # For now, this change makes the linter pass if common_b_s module itself is not imported.
    # However, modifying imported variables directly is generally discouraged.
    # This will likely cause issues if not handled carefully.
    # A better approach would be to pass a game context object or have GameStateManager manage this state.

    if new_state_str == "dungeon":
        # This modification might not work as expected if `in_dungeon` is a primitive.
        # Python passes primitives by value. If `common_b_s.in_dungeon` is to be modified,
        # it must be done as `common_b_s.in_dungeon = True`.
        # For now, assuming this is a placeholder for a more robust state management.
        # To actually modify the global in common_b_s, we'd still need to use common_b_s.in_dungeon
        # Making this a local variable `in_dungeon` won't affect the global one.
        # This highlights a deeper issue with current global state management.
        # Let's revert this part of the thought for now and keep common_b_s.in_dungeon
        # and remove the `import common_b_s` later if all members are explicitly imported.

        # Re-evaluating: The goal is to remove `import common_b_s`.
        # If `in_dungeon` is imported `from common_b_s import in_dungeon`,
        # assigning to `in_dungeon` locally in this function will NOT change the global value in common_b_s.
        # This means the current way `set_game_state` tries to modify `common_b_s.in_dungeon`
        # is fundamentally incompatible with removing `import common_b_s` and just importing the variable.
        #
        # For now, I will proceed with adding specific imports and removing `import common_b_s`,
        # but I'll leave the modification as `common_b_s.in_dungeon = ...`
        # This means I *must* keep `import common_b_s` for this to work.
        # This contradicts the goal of removing it.
        #
        # Alternative: `set_game_state` could return the new boolean value for `in_dungeon`
        # and the caller in `blade_sigil_v5_5.py` would update `common_b_s.in_dungeon`.
        # Or, `GameStateManager` class instance should manage this.
        #
        # Let's stick to the explicit imports for now, and keep `import common_b_s` solely for
        # modifying `common_b_s.in_dungeon`. This is an intermediate step.
        # The `from common_b_s import in_dungeon` will be removed from the import list for now.
        common_b_s.in_dungeon = True
    elif new_state_str == "hub":
        common_b_s.in_dungeon = False
    else:
        common_b_s.in_dungeon = False

    # Potentially, this function could also update a GameStateManager instance
    # if we decide to make these methods of the class.
    # For now, it directly modifies common_b_s.in_dungeon and returns the state string.
    return new_state_str

def initialize_game_after_title(title_choice, screen, clock):
    """
    Handles game initialization after the title screen.
    This can lead to character creation or loading a game.
    Returns: (player, game_dungeon, current_game_state_str)
    """
    player = None
    game_dungeon = None
    current_game_state_str = "title_screen" # Default, should be updated

    if title_choice == "load_game":
        print("Loading saved game...")
        loaded_data = load_game() # load_game is now in this module
        if loaded_data:
            player, game_dungeon_data, loaded_state_str, saved_cm_turn = loaded_data
            current_game_state_str = set_game_state(loaded_state_str)
            condition_manager.current_turn = saved_cm_turn

            # Reconstruct Dungeon object if data is a dict (new save format)
            if isinstance(game_dungeon_data, dict):
                # This is a simplified reconstruction. The main game file has more detailed logic.
                # For a full load, that logic should be centralized here or in load_game.
                game_dungeon = Dungeon(game_dungeon_data.get("width", 20), game_dungeon_data.get("height", 15))
                # TODO: Add full tile, door, chest, monster reconstruction from game_dungeon_data
                # This is a significant piece of logic from blade_sigil_v5_5.py
                print("Warning: Simplified dungeon reconstruction in initialize_game_after_title.")
            else:
                game_dungeon = game_dungeon_data # Assumed to be a Dungeon object (old save format)

            add_message(f"Welcome back, {player.name}! Game loaded.", GREEN)
            return player, game_dungeon, current_game_state_str
        else:
            # Load failed, proceed to new game/character creation
            add_message("Failed to load game. Starting new character creation.", RED)
            title_choice = "new_game" # Force new game path

    if title_choice == "new_game":
        print("Starting new game / character creation...")
        # Call character_creation_screen which returns (Player object from common_b_s, Dungeon object from common_b_s)
        # Note: character_creation_screen is imported from character_creation_ui
        created_player_common, created_dungeon_common = character_creation_screen(screen, clock)
        if created_player_common is None or created_dungeon_common is None:
            pygame.quit()
            sys.exit("Character creation cancelled. Exiting.")

        # Convert/wrap common_b_s.Player to blade_sigil_v5_5.Player if necessary,
        # or ensure character_creation_screen returns the right Player type.
        # The current setup: blade_sigil_v5_5.Player inherits common_b_s.Character.
        # character_creation_screen likely returns common_b_s.Player.
        # We need an instance of blade_sigil_v5_5.Player for the main game.

        char_class_lower = created_player_common.char_class.lower()
        sprite_path_key = assets_data["sprites"]["heroes"].get(char_class_lower, assets_data["sprites"]["heroes"]["warrior"]) # Fallback
        player_sprite = load_sprite(sprite_path_key["live"])

        player = Player( # Instantiating blade_sigil_v5_5.Player
            name=created_player_common.name,
            race=created_player_common.race,
            char_class=created_player_common.char_class,
            start_position=created_dungeon_common.start_position, # Position from char creation dungeon
            sprite=player_sprite,
            abilities=deepcopy(created_player_common.abilities) # Ensure abilities are copied
        )
        player.gold = getattr(created_player_common, 'gold', player.gold) # Preserve gold if set

        game_dungeon = created_dungeon_common # Use dungeon from char creation for now.
                                            # It might be immediately replaced if starting in hub.
        current_game_state_str = set_game_state("hub") # New games start in the hub
        add_message(f"Welcome, {player.name}! Your journey begins.", GREEN)
        return player, game_dungeon, current_game_state_str

    # Should not be reached if title_choice is valid
    return None, None, "title_screen"


def transition_to_hub(player_obj):
    """Transitions the game state to the hub."""
    # common_b_s.add_message(f"{player_obj.name} arrives at Novamagus.", common_b_s.WHITE)
    return set_game_state("hub")

def transition_from_hub_to_dungeon(player_obj, screen_ref, clock_ref):
    """
    Handles the transition from the hub to the first dungeon level.
    This function assumes the transition is triggered from within the hub's logic.
    Returns the new game_dungeon instance.
    """
    print("DEBUG: GSM: Transitioning from hub to dungeon...")
    # Create a new dungeon for level 1
    new_dungeon = Dungeon(20, 15, level=1) # Dungeon class from common_b_s
    player_obj.position = deepcopy(new_dungeon.start_position) # Ensure player starts at the new dungeon's start

    # TEST ONLY: Give player 1000 HP for testing purposes (from original code)
    # player_obj.hit_points = 1000
    # player_obj.max_hit_points = 1000
    # add_message("TEST MODE: Player has 1000 HP for indestructible testing!")

    set_game_state("dungeon") # This will set common_b_s.in_dungeon = True
    novamagus_hub.transition_to_dungeon = False # Reset the flag in the hub module
    add_message("You venture into the dark depths...", WHITE)
    return new_dungeon


def handle_dungeon_level_transition(player_obj, current_dungeon_obj):
    """
    Handles transition to a new dungeon level.
    Returns the new_dungeon instance.
    """
    new_level_num = current_dungeon_obj.level + 1
    # Logic for difficulty, maps on next level etc. from blade_sigil_v5_5.py
    # This is a simplified version for now.
    # Ideally, the detailed logic from blade_sigil_v5_5 for level transitions
    # (difficulty_roll, maps_on_next_level, player level up) should be moved here or called.

    # For now, basic transition:
    new_dungeon = Dungeon(current_dungeon_obj.width, current_dungeon_obj.height, level=new_level_num)
    player_obj.position = deepcopy(new_dungeon.start_position)

    # Player level up logic (simplified from blade_sigil_v5_5.py)
    if player_obj.level < new_level_num : # Player levels up if their level is less than the new dungeon level
        player_obj.level_up() # Assumes Player class has level_up method
        levelup_sound.play()
        add_message(f"The challenge empowers you! You advance to character level {player_obj.level}!", GREEN)

    add_message(f"You descend to level {new_level_num} of the dungeon.", WHITE)
    set_game_state("dungeon") # Ensures in_dungeon is True
    return new_dungeon

def handle_dungeon_map_transition(player_obj, current_dungeon_obj, destination_map_number):
    """
    Handles transition to a new map within the same dungeon level.
    Returns the new_dungeon instance.
    """
    maps_on_level = getattr(current_dungeon_obj, 'max_maps', random.randint(1,5)) # Get max_maps or default
    new_dungeon = Dungeon(
        current_dungeon_obj.width,
        current_dungeon_obj.height,
        level=current_dungeon_obj.level,
        map_number=destination_map_number,
        max_maps=maps_on_level
    )
    player_obj.position = deepcopy(new_dungeon.start_position)
    add_message(f"You enter a new area: Map {destination_map_number} of Level {new_dungeon.level}.", WHITE)
    set_game_state("dungeon") # Ensures in_dungeon is True
    return new_dungeon

def handle_test_arena_teleport(player_obj, screen_ref, new_arena_dungeon_obj, new_state_str, new_in_dungeon_val):
    """
    Handles transitions specifically for test arena (teleporting).
    Updates player position to the start of the new arena.
    Returns (new_arena_dungeon_obj, new_game_state_str)
    """
    player_obj.position = deepcopy(new_arena_dungeon_obj.start_position)
    final_state_str = set_game_state(new_state_str) # This also sets common_b_s.in_dungeon
    # in_dungeon = new_in_dungeon_val # Explicitly set if set_game_state doesn't cover it
    add_message(f"Teleported to {new_state_str}.", YELLOW)
    return new_arena_dungeon_obj, final_state_str


def show_title_screen():
    """Display the title screen with options to start a new game or load a saved game."""
    # Initialize screen for title
    title_screen = pygame.display.set_mode((DUNGEON_SCREEN_WIDTH, DUNGEON_SCREEN_HEIGHT))
    pygame.display.set_caption("Blade & Sigil")

    # Load the title screen image
    try:
        # Corrected path to be more generic if possible, or ensure it's an absolute path
        # For now, using the original path from blade_sigil_v5_5.py
        # Consider making this path configurable or relative to an assets directory
        title_image_path = "/Users/williammarcellino/Documents/Fantasy_Game/Fantasy_Game_Art_Assets/Misc/b&s_loading_screen.jpg"
        if not os.path.exists(title_image_path):
            # Attempt a relative path as a fallback, assuming 'Fantasy_Game_Art_Assets' is in a known location
            # This is a guess and might need adjustment based on actual project structure
            # For example, if 'game_state_manager.py' is in the root of 'Fantasy_Game'
            script_dir = os.path.dirname(__file__) # directory of game_state_manager.py
            # This relative path is an example, it might not be correct.
            # title_image_path = os.path.join(script_dir, "Fantasy_Game_Art_Assets", "Misc", "b&s_loading_screen.jpg")


            # If the above relative path doesn't work, we must rely on the absolute path or a known structure.
            # For this exercise, I'll stick to the original absolute path if the first attempt fails.
            # A more robust solution would involve an asset management system or configuration.
            if not os.path.exists(title_image_path):
                 title_image_path = "/Users/williammarcellino/Documents/Fantasy_Game/Fantasy_Game_Art_Assets/Misc/b&s_loading_screen.jpg"


        title_image = pygame.image.load(title_image_path)
        title_image = pygame.transform.scale(title_image, (DUNGEON_SCREEN_WIDTH, DUNGEON_SCREEN_HEIGHT))
    except pygame.error as e:
        print(f"Error loading title image: {e}. Using fallback.")
        # Fallback if image can't be loaded
        title_image = pygame.Surface((DUNGEON_SCREEN_WIDTH, DUNGEON_SCREEN_HEIGHT))
        title_image.fill((0, 0, 0))  # Black background
        title_text = font.render("BLADE & SIGIL", True, WHITE)
        title_rect = title_text.get_rect(center=(DUNGEON_SCREEN_WIDTH//2, DUNGEON_SCREEN_HEIGHT//3))
        title_image.blit(title_text, title_rect)

    # Create buttons
    button_width = 200
    button_height = 50
    button_margin = 20

    # Button positions
    new_game_rect = pygame.Rect(
        (DUNGEON_SCREEN_WIDTH - button_width) // 2,
        DUNGEON_SCREEN_HEIGHT * 2 // 3,
        button_width,
        button_height
    )

    load_game_rect = pygame.Rect(
        (DUNGEON_SCREEN_WIDTH - button_width) // 2,
        DUNGEON_SCREEN_HEIGHT * 2 // 3 + button_height + button_margin,
        button_width,
        button_height
    )

    # Colors
    button_color = (100, 100, 100)
    hover_color = (150, 150, 150)
    text_color = WHITE

    # Check if a save game exists
    # Corrected path for savegame
    save_dir = "/Users/williammarcellino/Documents/Fantasy_Game/B&S_savegame"
    save_file_path = os.path.join(save_dir, "savefile.json")
    has_save = os.path.exists(save_file_path)

    running = True
    while running:
        # Reset screen and draw title image
        title_screen.blit(title_image, (0, 0))

        # Get mouse position
        mouse_pos = pygame.mouse.get_pos()

        # Draw new game button
        new_game_color = hover_color if new_game_rect.collidepoint(mouse_pos) else button_color
        pygame.draw.rect(title_screen, new_game_color, new_game_rect)
        new_game_text = font.render("New Game", True, text_color)
        new_game_text_rect = new_game_text.get_rect(center=new_game_rect.center)
        title_screen.blit(new_game_text, new_game_text_rect)

        # Draw load game button (grayed out if no save exists)
        load_game_color = (50, 50, 50) if not has_save else (hover_color if load_game_rect.collidepoint(mouse_pos) else button_color)
        pygame.draw.rect(title_screen, load_game_color, load_game_rect)
        load_game_text = font.render("Load Game", True, (100, 100, 100) if not has_save else text_color)
        load_game_text_rect = load_game_text.get_rect(center=load_game_rect.center)
        title_screen.blit(load_game_text, load_game_text_rect)

        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if new_game_rect.collidepoint(mouse_pos):
                    return "new_game"
                elif load_game_rect.collidepoint(mouse_pos) and has_save:
                    return "load_game"
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_n:
                    return "new_game"
                elif event.key == pygame.K_l and has_save:
                    return "load_game"
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

        # Display version and instructions
        version_text = font.render("v0.5.5", True, WHITE) # Assuming version is static for now
        title_screen.blit(version_text, (20, DUNGEON_SCREEN_HEIGHT - 30))

        help_text = font.render("Press N for New Game, L to Load Game, ESC to Quit", True, WHITE)
        help_rect = help_text.get_rect(center=(DUNGEON_SCREEN_WIDTH//2, DUNGEON_SCREEN_HEIGHT - 30))
        title_screen.blit(help_text, help_rect)

        pygame.display.flip()
