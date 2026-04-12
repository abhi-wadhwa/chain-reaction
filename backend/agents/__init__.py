from .base import Agent
from .random_agent import RandomAgent
from .greedy_agent import GreedyAgent
from .minimax_agent import MinimaxAgent
from .mcts_agent import MCTSAgent
from .neural_mcts_agent import NeuralMCTSAgent

AGENT_REGISTRY: dict[str, type[Agent]] = {
    "random": RandomAgent,
    "greedy": GreedyAgent,
    "minimax": MinimaxAgent,
    "mcts": MCTSAgent,
    "neural_mcts": NeuralMCTSAgent,
}

__all__ = [
    "Agent", "RandomAgent", "GreedyAgent", "MinimaxAgent", "MCTSAgent",
    "NeuralMCTSAgent", "AGENT_REGISTRY",
]
