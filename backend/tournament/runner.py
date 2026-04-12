from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Any, Callable

from engine.game_engine import GameEngine
from .elo import EloSystem
from .records import GameRecord, TournamentResult


def _play_single_game(
    agent1_cls: type,
    agent1_kwargs: dict,
    agent2_cls: type,
    agent2_kwargs: dict,
    rows: int,
    cols: int,
    move_time_limit: float,
) -> GameRecord:
    a1 = agent1_cls(**agent1_kwargs)
    a2 = agent2_cls(**agent2_kwargs)
    engine = GameEngine()
    return engine.play_game(a1, a2, rows, cols, move_time_limit)


class TournamentRunner:
    def __init__(
        self,
        agents: list[dict[str, Any]],
        rows: int = 5,
        cols: int = 5,
        games_per_pairing: int = 10,
        parallel_workers: int = 1,
        move_time_limit: float = 5.0,
    ):
        self.agents = agents  # [{name, cls, kwargs}, ...]
        self.rows = rows
        self.cols = cols
        self.games_per_pairing = games_per_pairing
        self.parallel_workers = parallel_workers
        self.move_time_limit = move_time_limit

    def run(
        self, progress_callback: Callable | None = None
    ) -> TournamentResult:
        elo_system = EloSystem()
        n = len(self.agents)
        agent_names = [a["name"] for a in self.agents]

        ratings = {name: elo_system.initial_rating for name in agent_names}
        win_matrix = {
            name: {other: 0 for other in agent_names} for name in agent_names
        }
        per_agent_stats = {
            name: {"wins": 0, "losses": 0, "draws": 0, "games": 0}
            for name in agent_names
        }
        game_records: list[GameRecord] = []

        # Build list of all games to play
        games_to_play = []
        for i in range(n):
            for j in range(i + 1, n):
                for g in range(self.games_per_pairing):
                    if g % 2 == 0:
                        first, second = i, j
                    else:
                        first, second = j, i
                    games_to_play.append((first, second))

        total_games = len(games_to_play)
        completed = 0

        if self.parallel_workers <= 1:
            for first_idx, second_idx in games_to_play:
                a1 = self.agents[first_idx]
                a2 = self.agents[second_idx]
                record = _play_single_game(
                    a1["cls"], a1.get("kwargs", {}),
                    a2["cls"], a2.get("kwargs", {}),
                    self.rows, self.cols, self.move_time_limit,
                )
                game_records.append(record)
                completed += 1

                name1 = a1["name"]
                name2 = a2["name"]
                winner = record.result.get("winner", 0)

                self._update_stats(
                    winner, name1, name2, ratings, win_matrix,
                    per_agent_stats, elo_system,
                )

                if progress_callback:
                    progress_callback({
                        "pairing": f"{name1} vs {name2}",
                        "result": record.result,
                        "elo_ratings": dict(ratings),
                        "progress_pct": completed / total_games * 100,
                    })
        else:
            with ProcessPoolExecutor(max_workers=self.parallel_workers) as executor:
                future_to_info = {}
                for first_idx, second_idx in games_to_play:
                    a1 = self.agents[first_idx]
                    a2 = self.agents[second_idx]
                    future = executor.submit(
                        _play_single_game,
                        a1["cls"], a1.get("kwargs", {}),
                        a2["cls"], a2.get("kwargs", {}),
                        self.rows, self.cols, self.move_time_limit,
                    )
                    future_to_info[future] = (a1["name"], a2["name"])

                for future in as_completed(future_to_info):
                    name1, name2 = future_to_info[future]
                    record = future.result()
                    game_records.append(record)
                    completed += 1

                    winner = record.result.get("winner", 0)
                    self._update_stats(
                        winner, name1, name2, ratings, win_matrix,
                        per_agent_stats, elo_system,
                    )

                    if progress_callback:
                        progress_callback({
                            "pairing": f"{name1} vs {name2}",
                            "result": record.result,
                            "elo_ratings": dict(ratings),
                            "progress_pct": completed / total_games * 100,
                        })

        agent_configs = []
        for a in self.agents:
            inst = a["cls"](**a.get("kwargs", {}))
            agent_configs.append(inst.get_config())

        return TournamentResult(
            agents=agent_configs,
            elo_ratings=ratings,
            win_matrix=win_matrix,
            game_records=game_records,
            per_agent_stats=per_agent_stats,
        )

    def _update_stats(
        self, winner: int, name1: str, name2: str,
        ratings: dict, win_matrix: dict, per_agent_stats: dict,
        elo_system: EloSystem,
    ):
        per_agent_stats[name1]["games"] += 1
        per_agent_stats[name2]["games"] += 1

        if winner == 1:
            win_matrix[name1][name2] += 1
            per_agent_stats[name1]["wins"] += 1
            per_agent_stats[name2]["losses"] += 1
            ratings[name1], ratings[name2] = elo_system.update(
                ratings[name1], ratings[name2]
            )
        elif winner == 2:
            win_matrix[name2][name1] += 1
            per_agent_stats[name2]["wins"] += 1
            per_agent_stats[name1]["losses"] += 1
            ratings[name2], ratings[name1] = elo_system.update(
                ratings[name2], ratings[name1]
            )
        else:
            per_agent_stats[name1]["draws"] += 1
            per_agent_stats[name2]["draws"] += 1
