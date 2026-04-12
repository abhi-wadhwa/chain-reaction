import numpy as np
from .base import Agent


class RandomAgent(Agent):
    name = "RandomAgent"

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = np.random.RandomState(seed)

    def select_move(self, game_state, player: int) -> int:
        valid_indices = game_state.get_valid_move_indices()
        return int(self.rng.choice(valid_indices))

    def get_config(self) -> dict:
        return {
            "name": self.name,
            "params": {
                "seed": {
                    "value": self.seed,
                    "min": 0,
                    "max": 99999,
                    "step": 1,
                    "type": "int",
                    "label": "Random seed",
                },
            },
        }
