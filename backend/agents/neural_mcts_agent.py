from __future__ import annotations

import math
import time
import numpy as np
from .base import Agent

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class NeuralMCTSNode:
    __slots__ = (
        "state", "player", "parent", "move", "children",
        "untried_moves", "visit_count", "total_value", "prior",
    )

    def __init__(self, state, player: int, parent=None, move: int | None = None, prior: float = 0.0):
        self.state = state
        self.player = player
        self.parent = parent
        self.move = move
        self.children: list[NeuralMCTSNode] = []
        self.untried_moves: list[int] = list(state.get_valid_move_indices())
        self.visit_count = 0
        self.total_value = 0.0
        self.prior = prior

    def puct_score(self, c_puct: float) -> float:
        if self.visit_count == 0:
            return float("inf")
        q = self.total_value / self.visit_count
        u = c_puct * self.prior * math.sqrt(self.parent.visit_count) / (1 + self.visit_count)
        return q + u

    def best_child(self, c_puct: float) -> NeuralMCTSNode:
        return max(self.children, key=lambda c: c.puct_score(c_puct))

    def is_fully_expanded(self) -> bool:
        return len(self.untried_moves) == 0

    def is_terminal(self) -> bool:
        return self.state.check_winner() != 0


class NeuralMCTSAgent(Agent):
    name = "NeuralMCTSAgent"

    def __init__(
        self,
        simulations: int = 800,
        c_puct: float = 1.5,
        temperature: float = 0.0,
        model_path: str = "",
        time_limit: float = 10.0,
    ):
        self.simulations = simulations
        self.c_puct = c_puct
        self.temperature = temperature
        self.model_path = model_path
        self.time_limit = time_limit
        self._rng = np.random.RandomState(42)
        self._network = None
        self._device = None
        self._fallback_mode = True

        if model_path and TORCH_AVAILABLE:
            self._load_model(model_path)

    def _load_model(self, path: str):
        try:
            from training.network import ChainReactionNet
            checkpoint = torch.load(path, map_location="cpu", weights_only=False)
            meta = checkpoint.get("metadata", {})
            rows = meta.get("board_rows", 5)
            cols = meta.get("board_cols", 5)
            num_blocks = meta.get("num_residual_blocks", 4)
            self._network = ChainReactionNet(rows, cols, num_residual_blocks=num_blocks)
            self._network.load_state_dict(checkpoint["model_state_dict"])
            self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self._network.to(self._device)
            self._network.eval()
            self._fallback_mode = False
        except Exception as e:
            print(f"NeuralMCTSAgent: Failed to load model from {path}: {e}")
            self._fallback_mode = True

    def select_move(self, game_state, player: int) -> int:
        valid = game_state.get_valid_move_indices()
        if len(valid) == 1:
            return int(valid[0])

        root = NeuralMCTSNode(game_state, player)
        deadline = time.time() + self.time_limit

        # Expand root with network priors
        if not self._fallback_mode:
            policy, value = self._evaluate(game_state, player)
            self._expand_with_priors(root, policy)
        else:
            # Uniform priors in fallback mode
            n_valid = len(root.untried_moves)
            for move in list(root.untried_moves):
                new_state, _ = game_state.apply_move(move)
                child = NeuralMCTSNode(
                    new_state, 3 - player, parent=root, move=move,
                    prior=1.0 / n_valid,
                )
                root.children.append(child)
            root.untried_moves.clear()

        for _ in range(self.simulations):
            if time.time() > deadline:
                break
            node = self._select(root)
            value = self._simulate(node, player)
            self._backpropagate(node, value)

        if not root.children:
            return int(self._rng.choice(valid))

        # Temperature-controlled selection
        return self._select_action(root)

    def _evaluate(self, state, root_player: int):
        """Run neural network on state, return (policy, value) from root_player perspective."""
        tensor = state.to_tensor()
        with torch.no_grad():
            t = torch.from_numpy(tensor).unsqueeze(0).to(self._device)
            log_policy, value = self._network(t)
            policy = torch.exp(log_policy).squeeze(0).cpu().numpy()
            v = value.item()

        # Mask invalid moves and renormalize
        valid_mask = state.get_valid_moves()
        policy = policy[:len(valid_mask)] * valid_mask
        policy_sum = policy.sum()
        if policy_sum > 0:
            policy /= policy_sum
        else:
            policy = valid_mask.astype(np.float32)
            policy /= policy.sum()

        # Value is from current player perspective; flip if needed
        if state.current_player != root_player:
            v = -v

        return policy, v

    def _expand_with_priors(self, node: NeuralMCTSNode, policy: np.ndarray):
        """Expand all valid children with network policy priors."""
        for move in list(node.untried_moves):
            new_state, _ = node.state.apply_move(move)
            child = NeuralMCTSNode(
                new_state, 3 - node.player, parent=node, move=move,
                prior=float(policy[move]),
            )
            node.children.append(child)
        node.untried_moves.clear()

    def _select(self, node: NeuralMCTSNode) -> NeuralMCTSNode:
        while not node.is_terminal() and node.is_fully_expanded():
            if not node.children:
                return node
            node = node.best_child(self.c_puct)
        return node

    def _simulate(self, node: NeuralMCTSNode, root_player: int) -> float:
        """Evaluate leaf node: use network if available, else random rollout."""
        winner = node.state.check_winner()
        if winner != 0:
            return 1.0 if winner == root_player else 0.0

        if not self._fallback_mode:
            # Neural evaluation
            policy, value = self._evaluate(node.state, root_player)
            # Expand this node with priors
            if not node.is_fully_expanded():
                self._expand_with_priors(node, policy)
            # Map value from [-1,1] to [0,1]
            return (value + 1.0) / 2.0
        else:
            # Random rollout fallback
            return self._random_rollout(node, root_player)

    def _random_rollout(self, node: NeuralMCTSNode, root_player: int) -> float:
        state = node.state.copy()
        current = node.player
        for _ in range(150):
            winner = state.check_winner()
            if winner != 0:
                return 1.0 if winner == root_player else 0.0
            valid = state.get_valid_move_indices()
            if len(valid) == 0:
                return 0.5
            move = int(self._rng.choice(valid))
            state, _ = state.apply_move(move)
            current = 3 - current
        return 0.5

    def _backpropagate(self, node: NeuralMCTSNode, value: float):
        current = node
        while current is not None:
            current.visit_count += 1
            if current.parent is not None:
                if current.parent.player == current.state.current_player:
                    current.total_value += value
                else:
                    current.total_value += (1.0 - value)
            else:
                current.total_value += value
            current = current.parent

    def _select_action(self, root: NeuralMCTSNode) -> int:
        if self.temperature <= 0.01:
            best = max(root.children, key=lambda c: c.visit_count)
            return best.move

        visits = np.array([c.visit_count for c in root.children], dtype=np.float64)
        visits = visits ** (1.0 / self.temperature)
        probs = visits / visits.sum()
        idx = self._rng.choice(len(root.children), p=probs)
        return root.children[idx].move

    def get_policy_info(self, game_state, player: int) -> dict | None:
        """Return network's policy and value for display in the UI."""
        if self._fallback_mode:
            return None
        policy, value = self._evaluate(game_state, player)
        valid_indices = game_state.get_valid_move_indices()
        top_moves = sorted(
            [(int(m), float(policy[m])) for m in valid_indices],
            key=lambda x: -x[1],
        )[:5]
        return {
            "value": float(value),
            "top_moves": [
                {"cell": m, "prob": p, "row": m // game_state.cols, "col": m % game_state.cols}
                for m, p in top_moves
            ],
        }

    def get_config(self) -> dict:
        return {
            "name": self.name,
            "params": {
                "simulations": {"value": self.simulations, "min": 100, "max": 5000, "step": 100, "type": "int", "label": "Simulations per move"},
                "c_puct": {"value": self.c_puct, "min": 0.5, "max": 5.0, "step": 0.1, "type": "float", "label": "PUCT exploration constant"},
                "temperature": {"value": self.temperature, "min": 0.0, "max": 2.0, "step": 0.1, "type": "float", "label": "Move temperature"},
                "model_path": {"value": self.model_path, "type": "string", "label": "Model checkpoint path"},
                "time_limit": {"value": self.time_limit, "min": 1.0, "max": 60.0, "step": 1.0, "type": "float", "label": "Time limit (seconds)"},
            },
        }
