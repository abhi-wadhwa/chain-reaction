from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class ResidualBlock(nn.Module):
    def __init__(self, channels: int):
        super().__init__()
        self.conv1 = nn.Conv2d(channels, channels, 3, padding=1)
        self.bn1 = nn.BatchNorm2d(channels)
        self.conv2 = nn.Conv2d(channels, channels, 3, padding=1)
        self.bn2 = nn.BatchNorm2d(channels)

    def forward(self, x):
        residual = x
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out = out + residual
        return F.relu(out)


class ChainReactionNet(nn.Module):
    def __init__(self, rows: int, cols: int, num_residual_blocks: int = 4, channels: int = 64):
        super().__init__()
        self.rows = rows
        self.cols = cols
        self.board_size = rows * cols
        self.num_residual_blocks = num_residual_blocks

        # Input: 6 channels
        self.input_conv = nn.Sequential(
            nn.Conv2d(6, channels, 3, padding=1),
            nn.BatchNorm2d(channels),
            nn.ReLU(),
        )

        # Residual tower
        self.res_tower = nn.Sequential(
            *[ResidualBlock(channels) for _ in range(num_residual_blocks)]
        )

        # Value head
        self.value_head = nn.Sequential(
            nn.Conv2d(channels, 1, 1),
            nn.BatchNorm2d(1),
            nn.ReLU(),
            nn.Flatten(),
            nn.Linear(self.board_size, 128),
            nn.ReLU(),
            nn.Linear(128, 1),
            nn.Tanh(),
        )

        # Policy head
        self.policy_head = nn.Sequential(
            nn.Conv2d(channels, 2, 1),
            nn.BatchNorm2d(2),
            nn.ReLU(),
            nn.Flatten(),
            nn.Linear(2 * self.board_size, self.board_size),
            nn.LogSoftmax(dim=1),
        )

    def forward(self, x):
        """Input: (batch, 6, rows, cols). Returns: (log_policy, value)."""
        features = self.input_conv(x)
        features = self.res_tower(features)
        log_policy = self.policy_head(features)
        value = self.value_head(features)
        return log_policy, value.squeeze(-1)

    def save_checkpoint(self, path: str, optimizer=None, metadata: dict | None = None):
        checkpoint = {
            "model_state_dict": self.state_dict(),
            "metadata": {
                "board_rows": self.rows,
                "board_cols": self.cols,
                "num_residual_blocks": self.num_residual_blocks,
                **(metadata or {}),
            },
        }
        if optimizer is not None:
            checkpoint["optimizer_state_dict"] = optimizer.state_dict()
        torch.save(checkpoint, path)

    @classmethod
    def load_checkpoint(cls, path: str, device: str = "cpu"):
        checkpoint = torch.load(path, map_location=device, weights_only=False)
        meta = checkpoint.get("metadata", {})
        rows = meta.get("board_rows", 5)
        cols = meta.get("board_cols", 5)
        num_blocks = meta.get("num_residual_blocks", 4)
        net = cls(rows, cols, num_residual_blocks=num_blocks)
        net.load_state_dict(checkpoint["model_state_dict"])
        net.to(device)
        return net, checkpoint
