import time
import numpy as np
from .base import Agent
from .greedy_agent import evaluate_state


class MinimaxAgent(Agent):
    name = "MinimaxAgent"

    DEFAULT_WEIGHTS = {
        "w_orbs": 1.0,
        "w_cells": 0.5,
        "w_loaded": 3.0,
        "w_corners": 2.0,
        "w_edges": 1.0,
        "w_threats": 2.5,
        "w_vulnerability": -2.0,
    }

    def __init__(self, max_depth: int = 4, time_limit: float = 5.0, **weights):
        self.max_depth = max_depth
        self.time_limit = time_limit
        self.weights = {**self.DEFAULT_WEIGHTS, **weights}
        self.tt: dict = {}
        self._deadline: float = 0.0
        self._timed_out: bool = False

    def select_move(self, game_state, player: int) -> int:
        self.tt.clear()
        self._deadline = time.time() + self.time_limit
        self._timed_out = False

        valid_indices = game_state.get_valid_move_indices()
        if len(valid_indices) == 1:
            return int(valid_indices[0])

        best_move = int(valid_indices[0])

        for depth in range(1, self.max_depth + 1):
            if self._timed_out:
                break
            move = self._search_at_depth(game_state, player, depth)
            if not self._timed_out:
                best_move = move
            else:
                break

        return best_move

    def _search_at_depth(self, state, player: int, max_depth: int) -> int:
        valid_indices = state.get_valid_move_indices()
        best_val = -float("inf")
        best_move = int(valid_indices[0])
        alpha = -float("inf")
        beta = float("inf")

        ordered = self._order_moves(state, valid_indices, player)

        for cell in ordered:
            if time.time() > self._deadline:
                self._timed_out = True
                break
            new_state, _ = state.apply_move(int(cell))
            winner = new_state.check_winner()
            if winner == player:
                return int(cell)
            if winner == 3 - player:
                val = -1000.0
            else:
                val = -self._negamax(new_state, 3 - player, max_depth - 1, -beta, -alpha)

            if val > best_val:
                best_val = val
                best_move = int(cell)
            alpha = max(alpha, val)

        return best_move

    def _negamax(self, state, player: int, depth: int, alpha: float, beta: float) -> float:
        if time.time() > self._deadline:
            self._timed_out = True
            return 0.0

        winner = state.check_winner()
        if winner == player:
            return 1000.0
        if winner == 3 - player:
            return -1000.0

        if depth <= 0:
            return evaluate_state(state, player, self.weights)

        tt_key = (state.owners.tobytes(), state.counts.tobytes(), player)
        if tt_key in self.tt:
            stored_val, stored_depth = self.tt[tt_key]
            if stored_depth >= depth:
                return stored_val

        valid_indices = state.get_valid_move_indices()
        if len(valid_indices) == 0:
            return 0.0

        ordered = self._order_moves(state, valid_indices, player)
        best_val = -float("inf")

        for cell in ordered:
            if time.time() > self._deadline:
                self._timed_out = True
                break
            new_state, _ = state.apply_move(int(cell))
            val = -self._negamax(new_state, 3 - player, depth - 1, -beta, -alpha)
            best_val = max(best_val, val)
            alpha = max(alpha, val)
            if alpha >= beta:
                break

        if not self._timed_out:
            self.tt[tt_key] = (best_val, depth)

        return best_val

    def _order_moves(self, state, valid_indices: np.ndarray, player: int) -> list[int]:
        scores = []
        for cell in valid_indices:
            new_state, _ = state.apply_move(int(cell))
            winner = new_state.check_winner()
            if winner == player:
                return [int(cell)]
            score = evaluate_state(new_state, player, self.weights)
            scores.append((score, int(cell)))
        scores.sort(reverse=True)
        return [cell for _, cell in scores]

    def get_config(self) -> dict:
        return {
            "name": self.name,
            "params": {
                "max_depth": {"value": self.max_depth, "min": 1, "max": 10, "step": 1, "type": "int", "label": "Max search depth"},
                "time_limit": {"value": self.time_limit, "min": 0.5, "max": 30.0, "step": 0.5, "type": "float", "label": "Time limit (seconds)"},
                "w_orbs": {"value": self.weights["w_orbs"], "min": -10.0, "max": 10.0, "step": 0.1, "type": "float", "label": "Orb count weight"},
                "w_cells": {"value": self.weights["w_cells"], "min": -10.0, "max": 10.0, "step": 0.1, "type": "float", "label": "Cell count weight"},
                "w_loaded": {"value": self.weights["w_loaded"], "min": -10.0, "max": 10.0, "step": 0.1, "type": "float", "label": "Loaded cells weight"},
                "w_corners": {"value": self.weights["w_corners"], "min": -10.0, "max": 10.0, "step": 0.1, "type": "float", "label": "Corner ownership weight"},
                "w_edges": {"value": self.weights["w_edges"], "min": -10.0, "max": 10.0, "step": 0.1, "type": "float", "label": "Edge ownership weight"},
                "w_threats": {"value": self.weights["w_threats"], "min": -10.0, "max": 10.0, "step": 0.1, "type": "float", "label": "Threat weight"},
                "w_vulnerability": {"value": self.weights["w_vulnerability"], "min": -10.0, "max": 10.0, "step": 0.1, "type": "float", "label": "Vulnerability weight"},
            },
        }
