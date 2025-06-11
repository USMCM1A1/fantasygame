"""
This module defines the types of saving throws used in the game
and potentially other save-related mechanics in the future.
"""
from enum import Enum

class SaveType(Enum):
    REFLEX = "Dexterity"
    POISON_DISEASE = "Constitution"
    SPELL = "Wisdom"

    @property
    def ability_name(self):
        return self.value
