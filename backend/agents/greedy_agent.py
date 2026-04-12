import numpy as np
from .base import Agent


def evaluate_state(state, player: int, weights: dict) -> float:
    opponent = 3 - player
    owners = state.owners
    counts = state.counts
    crit = state._crit_mass
    neighbors = state._neighbors
    rows, cols = state.rows, state.cols
    size = rows * cols

    p_mask = owners == player
    o_mask = owners == opponent

    p_orbs = float(np.sum(counts[p_mask]))
    o_orbs = float(np.sum(counts[o_mask]))

    p_cells = float(np.sum(p_mask))
    o_cells = float(np.sum(o_mask))

    p_loaded = float(np.sum(p_mask & (counts == crit - 1)))
    o_loaded = float(np.sum(o_mask & (counts == crit - 1)))

    # Corner and edge cells
    corner_indices = []
    edge_indices = []
    for r in range(rows):
        for c in range(cols):
            idx = r * cols + c
            if (r == 0 or r == rows - 1) and (c == 0 or c == cols - 1):
                corner_indices.append(idx)
            elif r == 0 or r == rows - 1 or c == 0 or c == cols - 1:
                edge_indices.append(idx)
    corner_indices = np.array(corner_indices)
    edge_indices = np.array(edge_indices)

    p_corners = float(np.sum(owners[corner_indices] == player))
    o_corners = float(np.sum(owners[corner_indices] == opponent))
    p_edges = float(np.sum(owners[edge_indices] == player))
    o_edges = float(np.sum(owners[edge_indices] == opponent))

    # Threats: opponent cells adjacent to own loaded cells
    threats = 0.0
    vulnerability = 0.0
    loaded_p = np.where(p_mask & (counts == crit - 1))[0]
    loaded_o = np.where(o_mask & (counts == crit - 1))[0]

    for ci in loaded_p:
        for ni in neighbors[ci]:
            if owners[ni] == opponent:
                threats += 1.0

    for ci in loaded_o:
        for ni in neighbors[ci]:
            if owners[ni] == player:
                vulnerability += 1.0

    score = (
        weights["w_orbs"] * (p_orbs - o_orbs)
        + weights["w_cells"] * (p_cells - o_cells)
        + weights["w_loaded"] * (p_loaded - o_loaded)
        + weights["w_corners"] * (p_corners - o_corners)
        + weights["w_edges"] * (p_edges - o_edges)
        + weights["w_threats"] * threats
        + weights["w_vulnerability"] * vulnerability
    )
    return score


class GreedyAgent(Agent):
    name = "GreedyAgent"

    DEFAULT_WEIGHTS = {
        "w_orbs": 1.0,
        "w_cells": 0.5,
        "w_loaded": 3.0,
        "w_corners": 2.0,
        "w_edges": 1.0,
        "w_threats": 2.5,
        "w_vulnerability": -2.0,
    }

    def __init__(self, **weights):
        self.weights = {**self.DEFAULT_WEIGHTS, **weights}

    def select_move(self, game_state, player: int) -> int:
        valid_indices = game_state.get_valid_move_indices()
        best_score = -float("inf")
        best_move = valid_indices[0]

        for cell in valid_indices:
            new_state, _ = game_state.apply_move(int(cell))
            winner = new_state.check_winner()
            if winner == player:
                return int(cell)
            if winner == 3 - player:
                continue
            score = evaluate_state(new_state, player, self.weights)
            if score > best_score:
                best_score = score
                best_move = int(cell)

        return best_move

    def get_config(self) -> dict:
        return {
            "name": self.name,
            "params": {
                "w_orbs": {"value": self.weights["w_orbs"], "min": -10.0, "max": 10.0, "step": 0.1, "type": "float", "label": "Orb count weight"},
                "w_cells": {"value": self.weights["w_cells"], "min": -10.0, "max": 10.0, "step": 0.1, "type": "float", "label": "Cell count weight"},
                "w_loaded": {"value": self.weights["w_loaded"], "min": -10.0, "max": 10.0, "step": 0.1, "type": "float", "label": "Loaded cells weight"},
                "w_corners": {"value": self.weights["w_corners"], "min": -10.0, "max": 10.0, "step": 0.1, "type": "float", "label": "Corner ownership weight"},
                "w_edges": {"value": self.weights["w_edges"], "min": -10.0, "max": 10.0, "step": 0.1, "type": "float", "label": "Edge ownership weight"},
                "w_threats": {"value": self.weights["w_threats"], "min": -10.0, "max": 10.0, "step": 0.1, "type": "float", "label": "Threat weight"},
                "w_vulnerability": {"value": self.weights["w_vulnerability"], "min": -10.0, "max": 10.0, "step": 0.1, "type": "float", "label": "Vulnerability weight"},
            },
        }
