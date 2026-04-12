from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents import AGENT_REGISTRY
from engine.game_engine import GameEngine
from engine.game_state import GameState

router = APIRouter(prefix="/api/game", tags=["game"])

# In-memory store for interactive games
_interactive_games: dict[str, dict[str, Any]] = {}


class AgentSpec(BaseModel):
    type: str
    params: dict = {}


class PlayRequest(BaseModel):
    agent1: AgentSpec
    agent2: AgentSpec
    rows: int = 5
    cols: int = 5
    move_time_limit: float = 5.0


class InteractivePlayRequest(BaseModel):
    agent: AgentSpec
    rows: int = 5
    cols: int = 5
    human_player: int = 1  # 1 or 2


class HumanMoveRequest(BaseModel):
    cell: int


def _create_agent(spec: AgentSpec):
    if spec.type not in AGENT_REGISTRY:
        raise HTTPException(400, f"Unknown agent type: {spec.type}")
    cls = AGENT_REGISTRY[spec.type]
    return cls(**spec.params)


@router.post("/play")
def play_game(req: PlayRequest):
    """Run a full AI vs AI game, return GameRecord."""
    agent1 = _create_agent(req.agent1)
    agent2 = _create_agent(req.agent2)
    engine = GameEngine()
    record = engine.play_game(agent1, agent2, req.rows, req.cols, req.move_time_limit)
    return record.to_dict()


@router.post("/play-interactive")
def play_interactive(req: InteractivePlayRequest):
    """Start a human-vs-AI interactive game."""
    ai_agent = _create_agent(req.agent)
    game_id = str(uuid.uuid4())
    state = GameState(req.rows, req.cols)

    game = {
        "game_id": game_id,
        "state": state,
        "ai_agent": ai_agent,
        "human_player": req.human_player,
        "ai_player": 3 - req.human_player,
        "moves": [],
        "move_count": 0,
        "finished": False,
        "result": None,
    }

    # If AI goes first, make its move
    if state.current_player == game["ai_player"]:
        _ai_move(game)

    _interactive_games[game_id] = game
    return {
        "game_id": game_id,
        "state": game["state"].to_dict(),
        "moves": game["moves"],
        "finished": game["finished"],
        "result": game["result"],
    }


@router.post("/{game_id}/move")
def human_move(game_id: str, req: HumanMoveRequest):
    """Human makes a move in an interactive game."""
    if game_id not in _interactive_games:
        raise HTTPException(404, "Game not found")

    game = _interactive_games[game_id]
    if game["finished"]:
        raise HTTPException(400, "Game is already finished")

    state: GameState = game["state"]
    if state.current_player != game["human_player"]:
        raise HTTPException(400, "Not your turn")

    valid = state.get_valid_moves()
    if not valid[req.cell]:
        raise HTTPException(400, f"Invalid move: cell {req.cell}")

    new_state, explosion_steps = state.apply_move(req.cell)
    game["moves"].append({
        "player": game["human_player"],
        "cell": req.cell,
        "explosion_steps": explosion_steps,
        "board_after": new_state.to_dict(),
    })
    game["state"] = new_state
    game["move_count"] += 1

    winner = new_state.check_winner()
    if winner != 0:
        game["finished"] = True
        game["result"] = {"winner": winner, "reason": "elimination"}
    elif new_state.current_player == game["ai_player"]:
        _ai_move(game)

    return {
        "game_id": game_id,
        "state": game["state"].to_dict(),
        "moves": game["moves"][-2:],  # last human + AI moves
        "finished": game["finished"],
        "result": game["result"],
    }


def _ai_move(game: dict):
    """Have the AI agent make a move."""
    state: GameState = game["state"]
    ai = game["ai_agent"]
    ai_player = game["ai_player"]

    cell = ai.select_move(state, ai_player)
    new_state, explosion_steps = state.apply_move(cell)
    game["moves"].append({
        "player": ai_player,
        "cell": int(cell),
        "explosion_steps": explosion_steps,
        "board_after": new_state.to_dict(),
    })
    game["state"] = new_state
    game["move_count"] += 1

    winner = new_state.check_winner()
    if winner != 0:
        game["finished"] = True
        game["result"] = {"winner": winner, "reason": "elimination"}
