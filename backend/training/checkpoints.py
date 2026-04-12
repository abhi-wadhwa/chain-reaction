from __future__ import annotations

import os
import json
from pathlib import Path


def get_checkpoint_dir(base_dir: str = "checkpoints") -> Path:
    path = Path(base_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def checkpoint_path(base_dir: str, iteration: int, rows: int, cols: int) -> str:
    d = get_checkpoint_dir(base_dir)
    return str(d / f"checkpoint_iter_{iteration}_board_{rows}x{cols}.pt")


def list_checkpoints(base_dir: str = "checkpoints") -> list[dict]:
    """List all checkpoints with metadata."""
    d = get_checkpoint_dir(base_dir)
    results = []

    try:
        import torch
    except ImportError:
        return results

    for f in sorted(d.glob("checkpoint_iter_*_board_*.pt")):
        try:
            checkpoint = torch.load(f, map_location="cpu", weights_only=False)
            meta = checkpoint.get("metadata", {})
            results.append({
                "path": str(f),
                "filename": f.name,
                "iteration": meta.get("iteration", 0),
                "board_rows": meta.get("board_rows", 0),
                "board_cols": meta.get("board_cols", 0),
                "value_loss": meta.get("value_loss", None),
                "policy_loss": meta.get("policy_loss", None),
                "win_rates": meta.get("win_rates", {}),
                "elo": meta.get("elo", None),
            })
        except Exception:
            continue

    return sorted(results, key=lambda x: x["iteration"])


def save_training_state(base_dir: str, state: dict):
    """Save full training state (metrics history, config, etc.)."""
    d = get_checkpoint_dir(base_dir)
    path = d / "training_state.json"
    with open(path, "w") as f:
        json.dump(state, f, indent=2, default=str)


def load_training_state(base_dir: str) -> dict | None:
    d = get_checkpoint_dir(base_dir)
    path = d / "training_state.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)
