from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

# Subscriber stores
_tournament_subscribers: dict[str, list[asyncio.Queue]] = {}
_game_subscribers: dict[str, list[asyncio.Queue]] = {}
_training_subscribers: dict[str, list[asyncio.Queue]] = {}


def notify_tournament(tournament_id: str, message: dict):
    """Called from tournament runner thread to push updates."""
    queues = _tournament_subscribers.get(tournament_id, [])
    for q in queues:
        try:
            q.put_nowait(message)
        except asyncio.QueueFull:
            pass


def notify_game(game_id: str, message: dict):
    """Called to push game updates."""
    queues = _game_subscribers.get(game_id, [])
    for q in queues:
        try:
            q.put_nowait(message)
        except asyncio.QueueFull:
            pass


def notify_training(training_id: str, message: dict):
    """Called from training thread to push updates."""
    queues = _training_subscribers.get(training_id, [])
    for q in queues:
        try:
            q.put_nowait(message)
        except asyncio.QueueFull:
            pass


@router.websocket("/ws/tournament/{tournament_id}")
async def ws_tournament(websocket: WebSocket, tournament_id: str):
    await websocket.accept()
    queue: asyncio.Queue = asyncio.Queue(maxsize=1000)

    if tournament_id not in _tournament_subscribers:
        _tournament_subscribers[tournament_id] = []
    _tournament_subscribers[tournament_id].append(queue)

    try:
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=1.0)
                await websocket.send_json(msg)
                if msg.get("type") == "tournament_complete":
                    break
            except asyncio.TimeoutError:
                # Send ping to keep alive
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    finally:
        _tournament_subscribers[tournament_id].remove(queue)
        if not _tournament_subscribers[tournament_id]:
            del _tournament_subscribers[tournament_id]


@router.websocket("/ws/game/{game_id}")
async def ws_game(websocket: WebSocket, game_id: str):
    await websocket.accept()
    queue: asyncio.Queue = asyncio.Queue(maxsize=1000)

    if game_id not in _game_subscribers:
        _game_subscribers[game_id] = []
    _game_subscribers[game_id].append(queue)

    try:
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=1.0)
                await websocket.send_json(msg)
                if msg.get("type") == "end":
                    break
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    finally:
        _game_subscribers[game_id].remove(queue)
        if not _game_subscribers[game_id]:
            del _game_subscribers[game_id]


@router.websocket("/ws/training/{training_id}")
async def ws_training(websocket: WebSocket, training_id: str):
    await websocket.accept()
    queue: asyncio.Queue = asyncio.Queue(maxsize=2000)

    if training_id not in _training_subscribers:
        _training_subscribers[training_id] = []
    _training_subscribers[training_id].append(queue)

    try:
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=2.0)
                await websocket.send_json(msg)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    finally:
        _training_subscribers[training_id].remove(queue)
        if not _training_subscribers[training_id]:
            del _training_subscribers[training_id]
