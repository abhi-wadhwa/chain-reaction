from __future__ import annotations

import numpy as np
from collections import deque
from .utils import precompute_neighbors, precompute_critical_mass


class GameState:
    __slots__ = (
        "rows", "cols", "owners", "counts", "current_player",
        "move_count", "_neighbors", "_crit_mass",
    )

    def __init__(
        self,
        rows: int,
        cols: int,
        owners: np.ndarray | None = None,
        counts: np.ndarray | None = None,
        current_player: int = 1,
        move_count: int = 0,
    ):
        self.rows = rows
        self.cols = cols
        size = rows * cols
        self.owners = owners if owners is not None else np.zeros(size, dtype=np.int8)
        self.counts = counts if counts is not None else np.zeros(size, dtype=np.int8)
        self.current_player = current_player
        self.move_count = move_count
        self._neighbors = precompute_neighbors(rows, cols)
        self._crit_mass = precompute_critical_mass(rows, cols)

    def get_valid_moves(self) -> np.ndarray:
        return (self.owners == 0) | (self.owners == self.current_player)

    def get_valid_move_indices(self) -> np.ndarray:
        return np.where(self.get_valid_moves())[0]

    def apply_move(self, cell_index: int) -> tuple[GameState, list[dict]]:
        owner = self.owners[cell_index]
        if owner != 0 and owner != self.current_player:
            raise ValueError(
                f"Cell {cell_index} owned by player {owner}, "
                f"current player is {self.current_player}"
            )

        new_owners = self.owners.copy()
        new_counts = self.counts.copy()
        player = self.current_player

        new_owners[cell_index] = player
        new_counts[cell_index] += 1

        explosion_steps: list[dict] = []

        queue = deque()
        if new_counts[cell_index] >= self._crit_mass[cell_index]:
            queue.append(cell_index)

        max_iterations = self.rows * self.cols * 50  # safety limit
        iterations = 0
        while queue and iterations < max_iterations:
            iterations += 1
            ci = queue.popleft()
            cm = self._crit_mass[ci]
            if new_counts[ci] < cm:
                continue

            own = new_owners[ci]
            remaining = new_counts[ci] - cm

            step = {
                "cell": int(ci),
                "sends_to": list(self._neighbors[ci]),
                "new_owners": {},
                "new_counts": {},
            }

            if remaining > 0:
                new_counts[ci] = remaining
                new_owners[ci] = own
            else:
                new_counts[ci] = 0
                new_owners[ci] = 0

            step["new_counts"][int(ci)] = int(new_counts[ci])
            step["new_owners"][int(ci)] = int(new_owners[ci])

            for ni in self._neighbors[ci]:
                new_owners[ni] = own
                new_counts[ni] += 1
                step["new_owners"][int(ni)] = int(own)
                step["new_counts"][int(ni)] = int(new_counts[ni])
                if new_counts[ni] >= self._crit_mass[ni]:
                    queue.append(ni)

            if new_owners[ci] != 0 and new_counts[ci] >= self._crit_mass[ci]:
                queue.append(ci)

            explosion_steps.append(step)

            # Check if one player captured everything (chain reaction complete)
            active_owners = new_owners[new_counts > 0]
            if len(active_owners) > 0 and np.all(active_owners == active_owners[0]):
                unique = np.unique(active_owners)
                if len(unique) == 1:
                    break

        next_player = 3 - self.current_player
        new_state = GameState(
            rows=self.rows,
            cols=self.cols,
            owners=new_owners,
            counts=new_counts,
            current_player=next_player,
            move_count=self.move_count + 1,
        )
        return new_state, explosion_steps

    def check_winner(self) -> int:
        if self.move_count < 2:
            return 0
        has1 = bool(np.any((self.owners == 1) & (self.counts > 0)))
        has2 = bool(np.any((self.owners == 2) & (self.counts > 0)))
        if has1 and not has2:
            return 1
        if has2 and not has1:
            return 2
        return 0

    def to_dict(self) -> dict:
        return {
            "rows": self.rows,
            "cols": self.cols,
            "owners": self.owners.tolist(),
            "counts": self.counts.tolist(),
            "current_player": self.current_player,
            "move_count": self.move_count,
        }

    def to_tensor(self) -> np.ndarray:
        """Return shape (6, rows, cols) float32 array for neural network input.
        Channels:
          0: current player orb counts
          1: opponent orb counts
          2: current player distance-to-explosion (crit_mass - count, 0 for empty/opponent)
          3: opponent distance-to-explosion
          4: critical mass map
          5: turn indicator (all 1s if P1, all 0s if P2)
        """
        size = self.rows * self.cols
        tensor = np.zeros((6, self.rows, self.cols), dtype=np.float32)
        opponent = 3 - self.current_player

        owners_2d = self.owners.reshape(self.rows, self.cols)
        counts_2d = self.counts.reshape(self.rows, self.cols)
        crit_2d = self._crit_mass.reshape(self.rows, self.cols).astype(np.float32)

        cur_mask = owners_2d == self.current_player
        opp_mask = owners_2d == opponent

        # Channel 0: current player orb counts
        tensor[0] = np.where(cur_mask, counts_2d, 0).astype(np.float32)
        # Channel 1: opponent orb counts
        tensor[1] = np.where(opp_mask, counts_2d, 0).astype(np.float32)
        # Channel 2: current player distance to explosion
        tensor[2] = np.where(cur_mask, crit_2d - counts_2d, 0).astype(np.float32)
        # Channel 3: opponent distance to explosion
        tensor[3] = np.where(opp_mask, crit_2d - counts_2d, 0).astype(np.float32)
        # Channel 4: critical mass map
        tensor[4] = crit_2d
        # Channel 5: turn indicator
        tensor[5] = 1.0 if self.current_player == 1 else 0.0

        return tensor

    def copy(self) -> GameState:
        return GameState(
            rows=self.rows,
            cols=self.cols,
            owners=self.owners.copy(),
            counts=self.counts.copy(),
            current_player=self.current_player,
            move_count=self.move_count,
        )
