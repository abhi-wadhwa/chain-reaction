import math
import time
import numpy as np
from .base import Agent


class MCTSNode:
    __slots__ = ("state", "player", "parent", "move", "children",
                 "untried_moves", "visit_count", "total_value")

    def __init__(self, state, player: int, parent=None, move: int | None = None):
        self.state = state
        self.player = player
        self.parent = parent
        self.move = move
        self.children: list[MCTSNode] = []
        self.untried_moves: list[int] = list(state.get_valid_move_indices())
        self.visit_count = 0
        self.total_value = 0.0

    def ucb1(self, exploration_c: float) -> float:
        if self.visit_count == 0:
            return float("inf")
        exploitation = self.total_value / self.visit_count
        exploration = exploration_c * math.sqrt(
            math.log(self.parent.visit_count) / self.visit_count
        )
        return exploitation + exploration

    def best_child(self, exploration_c: float) -> "MCTSNode":
        return max(self.children, key=lambda c: c.ucb1(exploration_c))

    def is_fully_expanded(self) -> bool:
        return len(self.untried_moves) == 0

    def is_terminal(self) -> bool:
        return self.state.check_winner() != 0


class MCTSAgent(Agent):
    name = "MCTSAgent"

    def __init__(
        self,
        simulations: int = 1000,
        exploration_c: float = 1.41,
        rollout_type: str = "informed",
        time_limit: float = 5.0,
    ):
        self.simulations = simulations
        self.exploration_c = exploration_c
        self.rollout_type = rollout_type
        self.time_limit = time_limit
        self._rng = np.random.RandomState(42)

    def select_move(self, game_state, player: int) -> int:
        valid = game_state.get_valid_move_indices()
        if len(valid) == 1:
            return int(valid[0])

        root = MCTSNode(game_state, player)
        deadline = time.time() + self.time_limit

        for _ in range(self.simulations):
            if time.time() > deadline:
                break
            node = self._select(root)
            node = self._expand(node)
            value = self._rollout(node, player)
            self._backpropagate(node, value)

        if not root.children:
            return int(self._rng.choice(valid))

        best = max(root.children, key=lambda c: c.visit_count)
        return best.move

    def _select(self, node: MCTSNode) -> MCTSNode:
        while not node.is_terminal() and node.is_fully_expanded():
            if not node.children:
                return node
            node = node.best_child(self.exploration_c)
        return node

    def _expand(self, node: MCTSNode) -> MCTSNode:
        if node.is_terminal() or not node.untried_moves:
            return node
        move = node.untried_moves.pop(self._rng.randint(len(node.untried_moves)))
        new_state, _ = node.state.apply_move(move)
        child = MCTSNode(new_state, 3 - node.player, parent=node, move=move)
        node.children.append(child)
        return child

    def _rollout(self, node: MCTSNode, root_player: int) -> float:
        state = node.state.copy()
        current = node.player

        for _ in range(150):
            winner = state.check_winner()
            if winner != 0:
                return 1.0 if winner == root_player else 0.0

            valid = state.get_valid_move_indices()
            if len(valid) == 0:
                return 0.5

            if self.rollout_type == "informed":
                move = self._informed_rollout_move(state, valid, current)
            else:
                move = int(self._rng.choice(valid))

            state, _ = state.apply_move(move)
            current = 3 - current

        return 0.5  # draw on early termination

    def _informed_rollout_move(self, state, valid: np.ndarray, player: int) -> int:
        opponent = 3 - player
        crit = state._crit_mass
        neighbors = state._neighbors
        owners = state.owners
        counts = state.counts

        safe_moves = []
        for cell in valid:
            is_safe = True
            for ni in neighbors[int(cell)]:
                if owners[ni] == opponent and counts[ni] >= crit[ni] - 1:
                    is_safe = False
                    break
            if is_safe:
                safe_moves.append(int(cell))

        if safe_moves:
            return safe_moves[self._rng.randint(len(safe_moves))]
        return int(self._rng.choice(valid))

    def _backpropagate(self, node: MCTSNode, value: float):
        current = node
        while current is not None:
            current.visit_count += 1
            if current.parent is not None:
                # Value is from perspective of root player
                # Node's parent made the move, so if root_player made the move,
                # the value is good; otherwise invert
                if current.parent.player == current.state.current_player:
                    # Parent's opponent just moved (current.player is parent.player's opponent)
                    current.total_value += value
                else:
                    current.total_value += (1.0 - value)
            else:
                current.total_value += value
            current = current.parent

    def get_config(self) -> dict:
        return {
            "name": self.name,
            "params": {
                "simulations": {"value": self.simulations, "min": 100, "max": 50000, "step": 100, "type": "int", "label": "Simulations per move"},
                "exploration_c": {"value": self.exploration_c, "min": 0.1, "max": 5.0, "step": 0.1, "type": "float", "label": "Exploration constant (c)"},
                "rollout_type": {"value": self.rollout_type, "options": ["random", "informed"], "type": "select", "label": "Rollout strategy"},
                "time_limit": {"value": self.time_limit, "min": 0.5, "max": 30.0, "step": 0.5, "type": "float", "label": "Time limit (seconds)"},
            },
        }
