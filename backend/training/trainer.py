from __future__ import annotations

import os
import time
import math
import numpy as np
from dataclasses import dataclass, field
from typing import Callable, Any

import torch
import torch.nn as nn
import torch.optim as optim

from training.network import ChainReactionNet
from training.self_play import SelfPlayWorker, augment_examples
from training.replay_buffer import ReplayBuffer
from training.evaluator import ModelEvaluator
from training.checkpoints import checkpoint_path, save_training_state
from engine.game_engine import GameEngine
from agents.random_agent import RandomAgent
from agents.greedy_agent import GreedyAgent
from agents.minimax_agent import MinimaxAgent
from agents.neural_mcts_agent import NeuralMCTSAgent


@dataclass
class TrainingConfig:
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
    temperature_moves: int = 0  # 0 = auto (rows*cols//2)
    replay_window: int = 5
    eval_games: int = 100
    eval_threshold: float = 0.55
    checkpoint_dir: str = "checkpoints"
    num_residual_blocks: int = 4
    device: str = "auto"
    resign_threshold: float = -0.9
    benchmark_games: int = 20

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


class AlphaZeroTrainer:
    def __init__(self, config: TrainingConfig):
        self.config = config
        self._device = self._resolve_device(config.device)
        self._running = False
        self._paused = False
        self._stopped = False

        # Metrics history
        self.value_loss_history: list[float] = []
        self.policy_loss_history: list[float] = []
        self.total_loss_history: list[float] = []
        self.win_rate_history: list[dict] = []
        self.elo_history: list[float] = []
        self.self_play_stats_history: list[dict] = []
        self.accepted_iterations: list[int] = []
        self.best_iteration: int = 0
        self.current_iteration: int = 0
        self.current_phase: str = "idle"

    def _resolve_device(self, device: str) -> torch.device:
        if device == "auto":
            return torch.device("cuda" if torch.cuda.is_available() else "cpu")
        return torch.device(device)

    def train(self, status_callback: Callable | None = None):
        cfg = self.config
        self._running = True
        self._stopped = False

        temp_moves = cfg.temperature_moves if cfg.temperature_moves > 0 else cfg.board_rows * cfg.board_cols // 2

        # Initialize network
        network = ChainReactionNet(
            cfg.board_rows, cfg.board_cols,
            num_residual_blocks=cfg.num_residual_blocks,
        ).to(self._device)

        optimizer = optim.AdamW(
            network.parameters(),
            lr=cfg.learning_rate,
            weight_decay=cfg.weight_decay,
        )

        # LR scheduler
        total_steps = cfg.num_iterations * cfg.training_epochs
        if cfg.lr_schedule == "cosine":
            scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=total_steps)
        elif cfg.lr_schedule == "step":
            scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=max(1, total_steps // 3), gamma=0.1)
        else:
            scheduler = None

        replay_buffer = ReplayBuffer(window_size=cfg.replay_window)

        # Save initial checkpoint
        os.makedirs(cfg.checkpoint_dir, exist_ok=True)
        best_path = checkpoint_path(cfg.checkpoint_dir, 0, cfg.board_rows, cfg.board_cols)
        network.save_checkpoint(best_path, optimizer, {
            "iteration": 0,
            "board_rows": cfg.board_rows,
            "board_cols": cfg.board_cols,
            "num_residual_blocks": cfg.num_residual_blocks,
        })

        for iteration in range(1, cfg.num_iterations + 1):
            if self._stopped:
                break

            while self._paused:
                time.sleep(0.5)
                if self._stopped:
                    break
            if self._stopped:
                break

            self.current_iteration = iteration

            # ── Phase 1: Self-play ──────────────────────────────────
            self.current_phase = "self_play"
            network.eval()
            worker = SelfPlayWorker(
                network, self._device,
                cfg.board_rows, cfg.board_cols,
                mcts_simulations=cfg.mcts_simulations,
                c_puct=cfg.c_puct,
                temperature_moves=temp_moves,
                resign_threshold=cfg.resign_threshold,
            )

            all_examples = []
            sp_game_lengths = []
            sp_p1_wins = 0
            sp_total = 0

            for g in range(cfg.games_per_iteration):
                if self._stopped:
                    break
                disable_resign = (g % 10 == 0)  # 10% no resignation
                examples = worker.play_game(disable_resignation=disable_resign)
                all_examples.extend(examples)

                game_len = len(examples)
                sp_game_lengths.append(game_len)
                if examples and examples[-1].value_target == 1.0:
                    sp_p1_wins += 1
                sp_total += 1

                if status_callback:
                    status_callback({
                        "phase": "self_play",
                        "iteration": iteration,
                        "game": g + 1,
                        "total_games": cfg.games_per_iteration,
                    })

            if self._stopped:
                break

            # Data augmentation
            augmented = augment_examples(all_examples, cfg.board_rows, cfg.board_cols)

            # ── Phase 2: Buffer update ──────────────────────────────
            self.current_phase = "buffer_update"
            replay_buffer.add_iteration(augmented, iteration)
            if status_callback:
                status_callback({
                    "phase": "buffer_update",
                    "buffer_size": replay_buffer.size(),
                    "new_examples": len(augmented),
                })

            # ── Phase 3: Network training ───────────────────────────
            self.current_phase = "training"
            network.train()
            epoch_losses = []

            for epoch in range(cfg.training_epochs):
                if self._stopped:
                    break

                tensors, policies, values = replay_buffer.sample(cfg.batch_size)
                t_tensors = torch.from_numpy(tensors).to(self._device)
                t_policies = torch.from_numpy(policies).to(self._device)
                t_values = torch.from_numpy(values).to(self._device)

                optimizer.zero_grad()
                log_policy_pred, value_pred = network(t_tensors)

                value_loss = nn.functional.mse_loss(value_pred, t_values)
                policy_loss = -torch.mean(torch.sum(t_policies * log_policy_pred, dim=1))
                total_loss = value_loss + policy_loss

                if torch.isnan(total_loss):
                    if status_callback:
                        status_callback({"phase": "error", "message": "NaN loss detected"})
                    break

                total_loss.backward()
                torch.nn.utils.clip_grad_norm_(network.parameters(), 1.0)
                optimizer.step()
                if scheduler:
                    scheduler.step()

                vl = value_loss.item()
                pl = policy_loss.item()
                tl = total_loss.item()
                epoch_losses.append(tl)
                self.value_loss_history.append(vl)
                self.policy_loss_history.append(pl)
                self.total_loss_history.append(tl)

                if status_callback:
                    status_callback({
                        "phase": "training",
                        "iteration": iteration,
                        "epoch": epoch + 1,
                        "total_epochs": cfg.training_epochs,
                        "value_loss": vl,
                        "policy_loss": pl,
                        "total_loss": tl,
                    })

            if self._stopped:
                break

            # Save candidate checkpoint
            candidate_path = checkpoint_path(cfg.checkpoint_dir, iteration, cfg.board_rows, cfg.board_cols)
            avg_vl = np.mean([self.value_loss_history[-1]]) if self.value_loss_history else 0
            avg_pl = np.mean([self.policy_loss_history[-1]]) if self.policy_loss_history else 0
            network.save_checkpoint(candidate_path, optimizer, {
                "iteration": iteration,
                "board_rows": cfg.board_rows,
                "board_cols": cfg.board_cols,
                "num_residual_blocks": cfg.num_residual_blocks,
                "value_loss": avg_vl,
                "policy_loss": avg_pl,
            })

            # ── Phase 4: Evaluation ─────────────────────────────────
            self.current_phase = "evaluation"
            evaluator = ModelEvaluator(
                cfg.board_rows, cfg.board_cols,
                simulations=min(cfg.mcts_simulations, 100),
                c_puct=cfg.c_puct,
                max_games=cfg.eval_games,
            )

            eval_result = evaluator.evaluate(
                candidate_path, best_path,
                threshold=cfg.eval_threshold,
                callback=status_callback,
            )

            # ── Phase 5: Model decision ─────────────────────────────
            self.current_phase = "model_decision"
            if eval_result["accepted"]:
                best_path = candidate_path
                self.best_iteration = iteration
                self.accepted_iterations.append(iteration)
                if status_callback:
                    status_callback({
                        "phase": "model_accepted",
                        "iteration": iteration,
                        "win_rate": eval_result["win_rate"],
                    })
                # Reload best model
                network_state = torch.load(best_path, map_location=self._device, weights_only=False)
                network.load_state_dict(network_state["model_state_dict"])
            else:
                if status_callback:
                    status_callback({
                        "phase": "model_rejected",
                        "iteration": iteration,
                        "win_rate": eval_result["win_rate"],
                    })
                # Revert to best model
                network_state = torch.load(best_path, map_location=self._device, weights_only=False)
                network.load_state_dict(network_state["model_state_dict"])

            # ── Phase 6: Benchmark ──────────────────────────────────
            self.current_phase = "benchmark"
            win_rates = self._run_benchmarks(best_path, status_callback)
            self.win_rate_history.append(win_rates)

            # Self-play stats
            sp_stats = {
                "avg_game_length": float(np.mean(sp_game_lengths)) if sp_game_lengths else 0,
                "p1_win_rate": sp_p1_wins / sp_total if sp_total > 0 else 0.5,
            }
            self.self_play_stats_history.append(sp_stats)

            # Update checkpoint metadata with win rates
            meta = {
                "iteration": iteration,
                "board_rows": cfg.board_rows,
                "board_cols": cfg.board_cols,
                "num_residual_blocks": cfg.num_residual_blocks,
                "value_loss": avg_vl,
                "policy_loss": avg_pl,
                "win_rates": win_rates,
            }
            network.save_checkpoint(candidate_path, optimizer, meta)

            # ── Iteration complete ──────────────────────────────────
            self.current_phase = "iteration_complete"
            if status_callback:
                status_callback({
                    "phase": "iteration_complete",
                    "iteration": iteration,
                    "total_iterations": cfg.num_iterations,
                    "best_model_iteration": self.best_iteration,
                    "value_loss_history": self.value_loss_history[-cfg.training_epochs:],
                    "policy_loss_history": self.policy_loss_history[-cfg.training_epochs:],
                    "win_rates": win_rates,
                    "self_play_stats": sp_stats,
                })

            # Save training state
            save_training_state(cfg.checkpoint_dir, {
                "current_iteration": iteration,
                "best_iteration": self.best_iteration,
                "config": cfg.to_dict(),
                "value_loss_history": self.value_loss_history,
                "policy_loss_history": self.policy_loss_history,
                "win_rate_history": self.win_rate_history,
                "self_play_stats_history": self.self_play_stats_history,
            })

        self._running = False
        self.current_phase = "completed"

    def _run_benchmarks(self, model_path: str, callback) -> dict:
        """Play the trained model against baseline agents."""
        engine = GameEngine()
        benchmarks = {
            "random": RandomAgent(seed=0),
            "greedy": GreedyAgent(),
            "minimax_d3": MinimaxAgent(max_depth=3, time_limit=2.0),
        }
        win_rates = {}

        for name, opponent in benchmarks.items():
            wins = 0
            for g in range(self.config.benchmark_games):
                if self._stopped:
                    break
                neural = NeuralMCTSAgent(
                    simulations=min(self.config.mcts_simulations, 100),
                    c_puct=self.config.c_puct,
                    temperature=0.1,
                    model_path=model_path,
                    time_limit=10.0,
                )
                if g % 2 == 0:
                    record = engine.play_game(neural, opponent, self.config.board_rows, self.config.board_cols, move_time_limit=10.0)
                    if record.result.get("winner") == 1:
                        wins += 1
                else:
                    record = engine.play_game(opponent, neural, self.config.board_rows, self.config.board_cols, move_time_limit=10.0)
                    if record.result.get("winner") == 2:
                        wins += 1

            wr = wins / self.config.benchmark_games if self.config.benchmark_games > 0 else 0
            win_rates[name] = wr

            if callback:
                callback({
                    "phase": "benchmark",
                    "opponent": name,
                    "wins": wins,
                    "losses": self.config.benchmark_games - wins,
                    "win_rate": wr,
                })

        return win_rates

    def pause(self):
        self._paused = True
        self.current_phase = "paused"

    def resume(self):
        self._paused = False

    def stop(self):
        self._stopped = True
        self._paused = False
        self._running = False
        self.current_phase = "stopped"

    def get_status(self) -> dict:
        return {
            "running": self._running,
            "paused": self._paused,
            "phase": self.current_phase,
            "iteration": self.current_iteration,
            "total_iterations": self.config.num_iterations,
            "best_iteration": self.best_iteration,
            "value_loss_history": self.value_loss_history,
            "policy_loss_history": self.policy_loss_history,
            "win_rate_history": self.win_rate_history,
            "self_play_stats_history": self.self_play_stats_history,
        }
