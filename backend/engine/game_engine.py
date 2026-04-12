from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING

from .game_state import GameState

if TYPE_CHECKING:
    from agents.base import Agent
    from tournament.records import GameRecord


class GameEngine:
    def play_game(
        self,
        agent1: Agent,
        agent2: Agent,
        rows: int = 5,
        cols: int = 5,
        move_time_limit: float = 5.0,
        max_moves: int = 500,
    ) -> GameRecord:
        from tournament.records import GameRecord

        state = GameState(rows, cols)
        agents = {1: agent1, 2: agent2}
        moves: list[dict] = []
        move_times: list[float] = []
        result = {"winner": 0, "reason": "ongoing"}

        for move_num in range(max_moves):
            player = state.current_player
            agent = agents[player]

            move_result: dict = {"move": None, "error": None}
            t0 = time.time()

            def run_agent():
                try:
                    move_result["move"] = agent.select_move(state, player)
                except Exception as e:
                    move_result["error"] = str(e)

            thread = threading.Thread(target=run_agent)
            thread.start()
            thread.join(timeout=move_time_limit)
            elapsed = time.time() - t0

            if thread.is_alive():
                result = {"winner": 3 - player, "reason": f"Player {player} timed out"}
                move_times.append(elapsed)
                break

            if move_result["error"] is not None:
                result = {
                    "winner": 3 - player,
                    "reason": f"Player {player} error: {move_result['error']}",
                }
                move_times.append(elapsed)
                break

            cell = move_result["move"]
            valid = state.get_valid_moves()
            if not valid[cell]:
                result = {
                    "winner": 3 - player,
                    "reason": f"Player {player} made invalid move {cell}",
                }
                move_times.append(elapsed)
                break

            new_state, explosion_steps = state.apply_move(cell)
            move_times.append(elapsed)

            moves.append({
                "player": player,
                "cell": int(cell),
                "explosion_steps": explosion_steps,
                "board_after": new_state.to_dict(),
            })

            state = new_state
            winner = state.check_winner()
            if winner != 0:
                result = {"winner": winner, "reason": "elimination"}
                break
        else:
            result = {"winner": 0, "reason": "max_moves_reached"}

        return GameRecord(
            board_size={"rows": rows, "cols": cols},
            agent_configs=[agent1.get_config(), agent2.get_config()],
            moves=moves,
            result=result,
            move_times=move_times,
            total_moves=len(moves),
        )
