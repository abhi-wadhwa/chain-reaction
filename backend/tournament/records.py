from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GameRecord:
    board_size: dict
    agent_configs: list[dict]
    moves: list[dict]
    result: dict
    move_times: list[float]
    total_moves: int
    game_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        return {
            "game_id": self.game_id,
            "board_size": self.board_size,
            "agent_configs": self.agent_configs,
            "moves": self.moves,
            "result": self.result,
            "move_times": self.move_times,
            "total_moves": self.total_moves,
        }


@dataclass
class TournamentResult:
    agents: list[dict]
    elo_ratings: dict[str, float]
    win_matrix: dict[str, dict[str, int]]
    game_records: list[GameRecord]
    per_agent_stats: dict[str, dict[str, Any]]
    tournament_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        return {
            "tournament_id": self.tournament_id,
            "agents": self.agents,
            "elo_ratings": self.elo_ratings,
            "win_matrix": self.win_matrix,
            "game_records": [g.to_dict() for g in self.game_records],
            "per_agent_stats": self.per_agent_stats,
        }
