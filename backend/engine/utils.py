import numpy as np

_neighbors_cache: dict[tuple[int, int], list[list[int]]] = {}
_crit_mass_cache: dict[tuple[int, int], np.ndarray] = {}


def precompute_neighbors(rows: int, cols: int) -> list[list[int]]:
    key = (rows, cols)
    if key in _neighbors_cache:
        return _neighbors_cache[key]
    neighbors = []
    for r in range(rows):
        for c in range(cols):
            nbrs = []
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    nbrs.append(nr * cols + nc)
            neighbors.append(nbrs)
    _neighbors_cache[key] = neighbors
    return neighbors


def precompute_critical_mass(rows: int, cols: int) -> np.ndarray:
    key = (rows, cols)
    if key in _crit_mass_cache:
        return _crit_mass_cache[key]
    crit = np.zeros(rows * cols, dtype=np.int8)
    for r in range(rows):
        for c in range(cols):
            n = 0
            if r > 0:
                n += 1
            if r < rows - 1:
                n += 1
            if c > 0:
                n += 1
            if c < cols - 1:
                n += 1
            crit[r * cols + c] = n
    _crit_mass_cache[key] = crit
    return crit
