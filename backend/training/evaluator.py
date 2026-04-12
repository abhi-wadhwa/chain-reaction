from __future__ import annotations

import math
import numpy as np
from engine.game_state import GameState
from engine.game_engine import GameEngine
from agents.neural_mcts_agent import NeuralMCTSAgent

try:
    import torch
except ImportError:
    torch = None


class ModelEvaluator:
    """Compare two neural network models by playing games between them."""

    def __init__(self, rows: int, cols: int, simulations: int = 100,
                 c_puct: float = 1.5, max_games: int = 400):
        self.rows = rows
        self.cols = cols
        self.simulations = simulations
        self.c_puct = c_puct
        self.max_games = max_games

    def evaluate(
        self,
        new_model_path: str,
        old_model_path: str,
        threshold: float = 0.55,
        callback=None,
    ) -> dict:
        """Play games between new and old model, return evaluation result."""
        engine = GameEngine()
        wins, losses, draws = 0, 0, 0

        for g in range(self.max_games):
            # Alternate who plays first
            if g % 2 == 0:
                agent1 = NeuralMCTSAgent(
                    simulations=self.simulations, c_puct=self.c_puct,
                    temperature=0.1, model_path=new_model_path, time_limit=30.0,
                )
                agent2 = NeuralMCTSAgent(
                    simulations=self.simulations, c_puct=self.c_puct,
                    temperature=0.1, model_path=old_model_path, time_limit=30.0,
                )
                new_is_p1 = True
            else:
                agent1 = NeuralMCTSAgent(
                    simulations=self.simulations, c_puct=self.c_puct,
                    temperature=0.1, model_path=old_model_path, time_limit=30.0,
                )
                agent2 = NeuralMCTSAgent(
                    simulations=self.simulations, c_puct=self.c_puct,
                    temperature=0.1, model_path=new_model_path, time_limit=30.0,
                )
                new_is_p1 = False

            record = engine.play_game(agent1, agent2, self.rows, self.cols, move_time_limit=30.0)
            winner = record.result.get("winner", 0)

            if winner == 0:
                draws += 1
            elif (winner == 1 and new_is_p1) or (winner == 2 and not new_is_p1):
                wins += 1
            else:
                losses += 1

            total = wins + losses + draws
            if callback:
                callback({
                    "phase": "evaluation",
                    "game": g + 1,
                    "wins": wins,
                    "losses": losses,
                    "draws": draws,
                })

            # SPRT early stopping
            if total >= 20:
                win_rate = (wins + draws * 0.5) / total
                if self._sprt_decision(wins, losses, draws, threshold):
                    break

        total = wins + losses + draws
        win_rate = (wins + draws * 0.5) / total if total > 0 else 0.5
        accepted = win_rate >= threshold

        return {
            "accepted": accepted,
            "games_played": total,
            "win_rate": win_rate,
            "wins": wins,
            "losses": losses,
            "draws": draws,
        }

    def _sprt_decision(self, wins, losses, draws, threshold) -> bool:
        """Simple SPRT approximation for early stopping."""
        total = wins + losses + draws
        if total < 20:
            return False
        win_rate = (wins + draws * 0.5) / total
        # If the result is clearly decisive, stop early
        se = math.sqrt(win_rate * (1 - win_rate) / total) if total > 0 else 1.0
        if se < 0.001:
            return True
        # 95% confidence interval doesn't include 0.5
        lower = win_rate - 1.96 * se
        upper = win_rate + 1.96 * se
        if lower > 0.5 or upper < 0.5:
            return True
        return total >= self.max_games
