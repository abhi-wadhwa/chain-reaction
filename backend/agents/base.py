from abc import ABC, abstractmethod


class Agent(ABC):
    name: str = "BaseAgent"

    @abstractmethod
    def select_move(self, game_state, player: int) -> int:
        """Return cell index for the move."""
        pass

    def get_config(self) -> dict:
        """Return agent name and configurable parameters with their current values."""
        return {"name": self.name, "params": {}}
