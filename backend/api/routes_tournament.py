from __future__ import annotations

import threading
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents import AGENT_REGISTRY
from tournament.runner import TournamentRunner

router = APIRouter(prefix="/api/tournament", tags=["tournament"])

# In-memory store for tournaments
_tournaments: dict[str, dict[str, Any]] = {}


class TournamentAgentSpec(BaseModel):
    type: str
    params: dict = {}
    name: str = ""


class TournamentStartRequest(BaseModel):
    agents: list[TournamentAgentSpec]
    rows: int = 5
    cols: int = 5
    games_per_pairing: int = 10
    parallel_workers: int = 1
    move_time_limit: float = 5.0


@router.post("/start")
def start_tournament(req: TournamentStartRequest):
    """Start a tournament in the background."""
    if len(req.agents) < 2:
        raise HTTPException(400, "Need at least 2 agents")

    tournament_id = str(uuid.uuid4())
    agent_list = []
    for i, spec in enumerate(req.agents):
        if spec.type not in AGENT_REGISTRY:
            raise HTTPException(400, f"Unknown agent type: {spec.type}")
        name = spec.name or f"{spec.type}_{i}"
        agent_list.append({
            "name": name,
            "cls": AGENT_REGISTRY[spec.type],
            "kwargs": spec.params,
        })

    tournament = {
        "id": tournament_id,
        "status": "running",
        "progress_pct": 0.0,
        "elo_history": [],
        "game_results": [],
        "final_result": None,
        "cancelled": False,
    }
    _tournaments[tournament_id] = tournament

    def run():
        runner = TournamentRunner(
            agents=agent_list,
            rows=req.rows,
            cols=req.cols,
            games_per_pairing=req.games_per_pairing,
            parallel_workers=req.parallel_workers,
            move_time_limit=req.move_time_limit,
        )

        def on_progress(info):
            if tournament["cancelled"]:
                return
            tournament["progress_pct"] = info["progress_pct"]
            tournament["elo_history"].append(dict(info["elo_ratings"]))
            tournament["game_results"].append({
                "pairing": info["pairing"],
                "result": info["result"],
            })
            # Notify WebSocket subscribers
            from api.ws_live import notify_tournament
            notify_tournament(tournament_id, {
                "type": "game_complete",
                "data": {
                    "pairing": info["pairing"],
                    "result": info["result"],
                    "elo_ratings": info["elo_ratings"],
                    "progress_pct": info["progress_pct"],
                },
            })

        try:
            result = runner.run(progress_callback=on_progress)
            tournament["final_result"] = result.to_dict()
            tournament["status"] = "completed"
            from api.ws_live import notify_tournament
            notify_tournament(tournament_id, {
                "type": "tournament_complete",
                "data": result.to_dict(),
            })
        except Exception as e:
            tournament["status"] = "error"
            tournament["error"] = str(e)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    return {"tournament_id": tournament_id, "status": "running"}


@router.get("/{tournament_id}/status")
def get_status(tournament_id: str):
    """Get current tournament progress."""
    if tournament_id not in _tournaments:
        raise HTTPException(404, "Tournament not found")
    t = _tournaments[tournament_id]
    return {
        "id": t["id"],
        "status": t["status"],
        "progress_pct": t["progress_pct"],
        "games_completed": len(t["game_results"]),
        "elo_ratings": t["elo_history"][-1] if t["elo_history"] else {},
    }


@router.get("/{tournament_id}/results")
def get_results(tournament_id: str):
    """Get full tournament results."""
    if tournament_id not in _tournaments:
        raise HTTPException(404, "Tournament not found")
    t = _tournaments[tournament_id]
    if t["status"] != "completed":
        raise HTTPException(400, f"Tournament status: {t['status']}")
    return t["final_result"]


@router.post("/{tournament_id}/cancel")
def cancel_tournament(tournament_id: str):
    """Cancel a running tournament."""
    if tournament_id not in _tournaments:
        raise HTTPException(404, "Tournament not found")
    t = _tournaments[tournament_id]
    t["cancelled"] = True
    t["status"] = "cancelled"
    return {"status": "cancelled"}
