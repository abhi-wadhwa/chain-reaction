from __future__ import annotations

import numpy as np
import math
from dataclasses import dataclass
from engine.game_state import GameState

try:
    import torch
except ImportError:
    torch = None


@dataclass
class TrainingExample:
    board_tensor: np.ndarray  # (6, rows, cols)
    policy_target: np.ndarray  # (rows*cols,)
    value_target: float  # +1 or -1


class NeuralMCTSNodeSP:
    """MCTS node for self-play (simplified, no agent wrapper)."""
    __slots__ = ("state", "player", "parent", "move", "children",
                 "visit_count", "total_value", "prior")

    def __init__(self, state, player, parent=None, move=None, prior=0.0):
        self.state = state
        self.player = player
        self.parent = parent
        self.move = move
        self.children: list[NeuralMCTSNodeSP] = []
        self.visit_count = 0
        self.total_value = 0.0
        self.prior = prior

    def puct_score(self, c_puct):
        if self.visit_count == 0:
            return float("inf")
        q = self.total_value / self.visit_count
        u = c_puct * self.prior * math.sqrt(self.parent.visit_count) / (1 + self.visit_count)
        return q + u

    def is_terminal(self):
        return self.state.check_winner() != 0


class SelfPlayWorker:
    def __init__(self, network, device, rows, cols, mcts_simulations=200,
                 c_puct=1.5, temperature_moves=None, resign_threshold=-0.9):
        self.network = network
        self.device = device
        self.rows = rows
        self.cols = cols
        self.mcts_simulations = mcts_simulations
        self.c_puct = c_puct
        self.temperature_moves = temperature_moves or (rows * cols // 2)
        self.resign_threshold = resign_threshold
        self.board_size = rows * cols

    def play_game(self, disable_resignation=False) -> list[TrainingExample]:
        state = GameState(self.rows, self.cols)
        history = []  # (tensor, policy, current_player)
        resign_count = 0

        move_num = 0
        while True:
            winner = state.check_winner()
            if winner != 0:
                break

            valid = state.get_valid_move_indices()
            if len(valid) == 0:
                break

            # Run MCTS
            policy, root_value = self._mcts_search(state)

            # Record training data
            tensor = state.to_tensor()
            history.append((tensor, policy.copy(), state.current_player))

            # Temperature-controlled move selection
            if move_num < self.temperature_moves:
                # Sample from visit distribution (temperature = 1.0)
                probs = policy.copy()
                prob_sum = probs.sum()
                if prob_sum > 0:
                    probs /= prob_sum
                else:
                    probs[valid] = 1.0 / len(valid)
                move = np.random.choice(self.board_size, p=probs)
            else:
                # Argmax (temperature -> 0)
                move = int(np.argmax(policy))

            # Resignation check
            if not disable_resignation and root_value < self.resign_threshold:
                resign_count += 1
                if resign_count >= 5:
                    winner = 3 - state.current_player
                    break
            else:
                resign_count = 0

            state, _ = state.apply_move(move)
            move_num += 1

            if move_num > self.board_size * 10:
                break  # safety

        # Label examples with game outcome
        examples = []
        for tensor, policy, player in history:
            if winner == 0:
                value_target = 0.0
            elif winner == player:
                value_target = 1.0
            else:
                value_target = -1.0
            examples.append(TrainingExample(tensor, policy, value_target))

        return examples

    def _mcts_search(self, state) -> tuple[np.ndarray, float]:
        """Run MCTS from state, return (visit distribution, root value estimate)."""
        root = NeuralMCTSNodeSP(state, state.current_player)

        # Expand root
        policy, root_val = self._evaluate_network(state)
        self._expand_node(root, policy)

        for _ in range(self.mcts_simulations):
            node = self._select(root)
            value = self._evaluate_leaf(node)
            self._backprop(node, value, state.current_player)

        # Build visit distribution
        visit_dist = np.zeros(self.board_size, dtype=np.float32)
        total_visits = 0
        for child in root.children:
            visit_dist[child.move] = child.visit_count
            total_visits += child.visit_count

        if total_visits > 0:
            visit_dist /= total_visits

        # Root value = average Q of children weighted by visits
        root_value = 0.0
        if total_visits > 0:
            for child in root.children:
                if child.visit_count > 0:
                    q = child.total_value / child.visit_count
                    root_value += q * child.visit_count / total_visits

        return visit_dist, root_value

    def _evaluate_network(self, state):
        """Get (policy, value) from network."""
        tensor = state.to_tensor()
        with torch.no_grad():
            t = torch.from_numpy(tensor).unsqueeze(0).to(self.device)
            log_policy, value = self.network(t)
            policy = torch.exp(log_policy).squeeze(0).cpu().numpy()
            v = value.item()

        # Mask to valid moves
        valid_mask = state.get_valid_moves()
        policy = policy[:self.board_size] * valid_mask
        policy_sum = policy.sum()
        if policy_sum > 0:
            policy /= policy_sum
        else:
            policy = valid_mask.astype(np.float32)
            policy /= policy.sum()

        return policy, v

    def _expand_node(self, node, policy):
        valid = node.state.get_valid_move_indices()
        for move in valid:
            new_state, _ = node.state.apply_move(int(move))
            child = NeuralMCTSNodeSP(
                new_state, 3 - node.player, parent=node,
                move=int(move), prior=float(policy[move]),
            )
            node.children.append(child)

    def _select(self, node):
        while node.children and not node.is_terminal():
            node = max(node.children, key=lambda c: c.puct_score(self.c_puct))
        return node

    def _evaluate_leaf(self, node) -> float:
        winner = node.state.check_winner()
        if winner != 0:
            return 1.0 if winner == node.player else -1.0

        if not node.children:
            policy, value = self._evaluate_network(node.state)
            self._expand_node(node, policy)
            return value

        return 0.0

    def _backprop(self, node, value, root_player):
        current = node
        while current is not None:
            current.visit_count += 1
            # Value from root player perspective
            if current.player == root_player:
                current.total_value += (value + 1.0) / 2.0
            else:
                current.total_value += (1.0 - (value + 1.0) / 2.0)
            current = current.parent


def augment_examples(examples: list[TrainingExample], rows: int, cols: int) -> list[TrainingExample]:
    """Apply board symmetries for data augmentation."""
    augmented = []
    is_square = rows == cols

    for ex in examples:
        tensor = ex.board_tensor  # (6, rows, cols)
        policy_2d = ex.policy_target.reshape(rows, cols)

        # Identity
        augmented.append(ex)

        # Horizontal flip
        t_hflip = tensor[:, :, ::-1].copy()
        p_hflip = policy_2d[:, ::-1].flatten().copy()
        augmented.append(TrainingExample(t_hflip, p_hflip, ex.value_target))

        # Vertical flip
        t_vflip = tensor[:, ::-1, :].copy()
        p_vflip = policy_2d[::-1, :].flatten().copy()
        augmented.append(TrainingExample(t_vflip, p_vflip, ex.value_target))

        # Both flips
        t_both = tensor[:, ::-1, ::-1].copy()
        p_both = policy_2d[::-1, ::-1].flatten().copy()
        augmented.append(TrainingExample(t_both, p_both, ex.value_target))

        if is_square:
            # 90-degree rotation
            t_90 = np.rot90(tensor, k=1, axes=(1, 2)).copy()
            p_90 = np.rot90(policy_2d, k=1).flatten().copy()
            augmented.append(TrainingExample(t_90, p_90, ex.value_target))

            # 180
            t_180 = np.rot90(tensor, k=2, axes=(1, 2)).copy()
            p_180 = np.rot90(policy_2d, k=2).flatten().copy()
            augmented.append(TrainingExample(t_180, p_180, ex.value_target))

            # 270
            t_270 = np.rot90(tensor, k=3, axes=(1, 2)).copy()
            p_270 = np.rot90(policy_2d, k=3).flatten().copy()
            augmented.append(TrainingExample(t_270, p_270, ex.value_target))

            # Transpose + flip (reflection across diagonal)
            t_tr = np.transpose(tensor, (0, 2, 1)).copy()
            p_tr = policy_2d.T.flatten().copy()
            augmented.append(TrainingExample(t_tr, p_tr, ex.value_target))

    return augmented
