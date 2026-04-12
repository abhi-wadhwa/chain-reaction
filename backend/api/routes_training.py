from __future__ import annotations

import threading
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from training.trainer import AlphaZeroTrainer, TrainingConfig
from training.checkpoints import list_checkpoints

router = APIRouter(prefix="/api/training", tags=["training"])

# In-memory store for training sessions
_training_sessions: dict[str, dict[str, Any]] = {}


class TrainingStartRequest(BaseModel):
    board_rows: int = 5
    board_cols: int = 5
    num_iterations: int = 50
    games_per_iteration: int = 100
    mcts_simulations: int = 200
    training_epochs: int = 10
    batch_size: int = 64
    learning_rate: float = 0.001
    lr_schedule: str = "cosine"
    weight_decay: float = 1e-4
    c_puct: float = 1.5
    temperature_moves: int = 0
    replay_window: int = 5
    eval_games: int = 100
    eval_threshold: float = 0.55
    num_residual_blocks: int = 4
    device: str = "auto"
    resign_threshold: float = -0.9
    benchmark_games: int = 20


@router.post("/start")
def start_training(req: TrainingStartRequest):
    """Start a new training session."""
    training_id = str(uuid.uuid4())

    config = TrainingConfig(
        board_rows=req.board_rows,
        board_cols=req.board_cols,
        num_iterations=req.num_iterations,
        games_per_iteration=req.games_per_iteration,
        mcts_simulations=req.mcts_simulations,
        training_epochs=req.training_epochs,
        batch_size=req.batch_size,
        learning_rate=req.learning_rate,
        lr_schedule=req.lr_schedule,
        weight_decay=req.weight_decay,
        c_puct=req.c_puct,
        temperature_moves=req.temperature_moves,
        replay_window=req.replay_window,
        eval_games=req.eval_games,
        eval_threshold=req.eval_threshold,
        checkpoint_dir=f"checkpoints/{training_id}",
        num_residual_blocks=req.num_residual_blocks,
        device=req.device,
        resign_threshold=req.resign_threshold,
        benchmark_games=req.benchmark_games,
    )

    trainer = AlphaZeroTrainer(config)
    session = {
        "id": training_id,
        "trainer": trainer,
        "config": config.to_dict(),
        "status": "running",
        "updates": [],
    }
    _training_sessions[training_id] = session

    def run():
        def on_status(update):
            session["updates"].append(update)
            # Keep only last 500 updates in memory
            if len(session["updates"]) > 500:
                session["updates"] = session["updates"][-500:]
            # Notify WebSocket subscribers
            from api.ws_live import notify_training
            notify_training(training_id, update)

        try:
            trainer.train(status_callback=on_status)
            session["status"] = "completed"
        except Exception as e:
            session["status"] = "error"
            session["error"] = str(e)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    return {"training_id": training_id, "status": "started"}


@router.post("/{training_id}/pause")
def pause_training(training_id: str):
    if training_id not in _training_sessions:
        raise HTTPException(404, "Training session not found")
    _training_sessions[training_id]["trainer"].pause()
    _training_sessions[training_id]["status"] = "paused"
    return {"status": "paused"}


@router.post("/{training_id}/resume")
def resume_training(training_id: str):
    if training_id not in _training_sessions:
        raise HTTPException(404, "Training session not found")
    _training_sessions[training_id]["trainer"].resume()
    _training_sessions[training_id]["status"] = "running"
    return {"status": "running"}


@router.post("/{training_id}/stop")
def stop_training(training_id: str):
    if training_id not in _training_sessions:
        raise HTTPException(404, "Training session not found")
    _training_sessions[training_id]["trainer"].stop()
    _training_sessions[training_id]["status"] = "stopped"
    return {"status": "stopped"}


@router.get("/{training_id}/status")
def get_status(training_id: str):
    if training_id not in _training_sessions:
        raise HTTPException(404, "Training session not found")
    session = _training_sessions[training_id]
    trainer_status = session["trainer"].get_status()
    return {
        "id": training_id,
        "status": session["status"],
        **trainer_status,
    }


@router.get("/{training_id}/checkpoints")
def get_checkpoints(training_id: str):
    if training_id not in _training_sessions:
        raise HTTPException(404, "Training session not found")
    config = _training_sessions[training_id]["config"]
    checkpoint_dir = config.get("checkpoint_dir", f"checkpoints/{training_id}")
    return list_checkpoints(checkpoint_dir)


@router.get("/{training_id}/metrics")
def get_metrics(training_id: str):
    if training_id not in _training_sessions:
        raise HTTPException(404, "Training session not found")
    trainer = _training_sessions[training_id]["trainer"]
    return {
        "value_loss_history": trainer.value_loss_history,
        "policy_loss_history": trainer.policy_loss_history,
        "total_loss_history": trainer.total_loss_history,
        "win_rate_history": trainer.win_rate_history,
        "self_play_stats_history": trainer.self_play_stats_history,
        "accepted_iterations": trainer.accepted_iterations,
    }


@router.post("/{training_id}/export-agent")
def export_agent(training_id: str, body: dict):
    """Make a trained checkpoint available as an agent."""
    if training_id not in _training_sessions:
        raise HTTPException(404, "Training session not found")
    checkpoint = body.get("checkpoint", "")
    agent_name = body.get("agent_name", "TrainedBot")

    if not checkpoint:
        raise HTTPException(400, "checkpoint path required")

    return {
        "status": "exported",
        "agent_name": agent_name,
        "checkpoint": checkpoint,
        "agent_type": "neural_mcts",
        "params": {"model_path": checkpoint},
    }


@router.get("/sessions")
def list_sessions():
    """List all training sessions."""
    return [
        {
            "id": sid,
            "status": s["status"],
            "config": s["config"],
        }
        for sid, s in _training_sessions.items()
    ]
