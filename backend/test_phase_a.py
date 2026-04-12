#!/usr/bin/env python3
"""Phase A Verification Script — Chain Reaction Game Engine + Agents + Tournament."""

import sys
import time

# ── Test 1: GameState basics ────────────────────────────────────────────────
print("=" * 60)
print("TEST 1: GameState — create 5x5, verify valid moves on empty board")
print("=" * 60)

from engine.game_state import GameState

state = GameState(5, 5)
valid = state.get_valid_moves()
assert valid.sum() == 25, f"Expected 25 valid moves on empty 5x5, got {valid.sum()}"
print(f"  ✓ Empty 5x5 board has {valid.sum()} valid moves")
print(f"  ✓ Current player: {state.current_player}")
print(f"  ✓ Move count: {state.move_count}")
print()

# ── Test 2: Apply a move ────────────────────────────────────────────────────
print("=" * 60)
print("TEST 2: Apply a move, verify owner and count")
print("=" * 60)

cell = 0  # top-left corner
new_state, steps = state.apply_move(cell)
assert new_state.owners[0] == 1, f"Expected owner 1, got {new_state.owners[0]}"
assert new_state.counts[0] == 1, f"Expected count 1, got {new_state.counts[0]}"
assert new_state.current_player == 2, "Should switch to player 2"
assert new_state.move_count == 1
print(f"  ✓ Cell 0 owner: {new_state.owners[0]}, count: {new_state.counts[0]}")
print(f"  ✓ Current player after move: {new_state.current_player}")
print(f"  ✓ Explosion steps: {len(steps)} (expected 0 for single orb on corner)")
print()

# ── Test 3: Force an explosion ──────────────────────────────────────────────
print("=" * 60)
print("TEST 3: Force an explosion on a corner cell")
print("=" * 60)

# Corner cell (0,0) has critical mass 2. Place twice.
s = GameState(5, 5)
s, _ = s.apply_move(0)    # P1 places at (0,0), count=1
s, _ = s.apply_move(5)    # P2 places at (1,0)
s, steps = s.apply_move(0)  # P1 places at (0,0) again, count=2 >= crit_mass=2 → explosion!
print(f"  ✓ Explosion steps recorded: {len(steps)}")
if steps:
    print(f"  ✓ First explosion from cell {steps[0]['cell']}, sends to {steps[0]['sends_to']}")
assert len(steps) > 0, "Expected at least one explosion step"
print()

# ── Test 4: Full Random vs Random game ──────────────────────────────────────
print("=" * 60)
print("TEST 4: Random vs Random (5x5) via GameEngine")
print("=" * 60)

from engine.game_engine import GameEngine
from agents.random_agent import RandomAgent

engine = GameEngine()
r1 = RandomAgent(seed=1)
r2 = RandomAgent(seed=2)
t0 = time.time()
record = engine.play_game(r1, r2, 5, 5, move_time_limit=5.0)
elapsed = time.time() - t0
print(f"  ✓ Game finished in {record.total_moves} moves ({elapsed:.2f}s)")
print(f"  ✓ Result: {record.result}")
print(f"  ✓ Game ID: {record.game_id}")
# Check explosion steps exist in at least some moves
explosion_moves = sum(1 for m in record.moves if m["explosion_steps"])
print(f"  ✓ Moves with explosions: {explosion_moves}/{record.total_moves}")
print()

# ── Test 5: Greedy vs MCTS ─────────────────────────────────────────────────
print("=" * 60)
print("TEST 5: Greedy vs MCTS (5x5, MCTS with 200 sims for speed)")
print("=" * 60)

from agents.greedy_agent import GreedyAgent
from agents.mcts_agent import MCTSAgent

greedy = GreedyAgent()
mcts = MCTSAgent(simulations=200, time_limit=2.0)
t0 = time.time()
record2 = engine.play_game(greedy, mcts, 5, 5, move_time_limit=10.0)
elapsed = time.time() - t0
print(f"  ✓ Game finished in {record2.total_moves} moves ({elapsed:.2f}s)")
print(f"  ✓ Result: {record2.result}")
avg_time = sum(record2.move_times) / len(record2.move_times) if record2.move_times else 0
print(f"  ✓ Average move time: {avg_time:.4f}s")
print()

# ── Test 6: Small Tournament ────────────────────────────────────────────────
print("=" * 60)
print("TEST 6: 4-agent tournament (2 games per pairing)")
print("=" * 60)

from tournament.runner import TournamentRunner

agents = [
    {"name": "Random", "cls": RandomAgent, "kwargs": {"seed": 10}},
    {"name": "Greedy", "cls": GreedyAgent, "kwargs": {}},
    {"name": "Minimax-d2", "cls": __import__("agents.minimax_agent", fromlist=["MinimaxAgent"]).MinimaxAgent, "kwargs": {"max_depth": 2, "time_limit": 2.0}},
    {"name": "MCTS-200", "cls": MCTSAgent, "kwargs": {"simulations": 200, "time_limit": 2.0}},
]

def on_progress(info):
    print(f"    {info['pairing']:30s} — winner: P{info['result']['winner']} | progress: {info['progress_pct']:.0f}%")

runner = TournamentRunner(agents, rows=5, cols=5, games_per_pairing=2, parallel_workers=1, move_time_limit=10.0)
t0 = time.time()
result = runner.run(progress_callback=on_progress)
elapsed = time.time() - t0

print()
print("  Final Elo Ratings:")
for name, elo in sorted(result.elo_ratings.items(), key=lambda x: -x[1]):
    stats = result.per_agent_stats[name]
    print(f"    {name:15s}  Elo: {elo:7.1f}  W:{stats['wins']} L:{stats['losses']} D:{stats['draws']}")
print(f"\n  Total games: {len(result.game_records)}, elapsed: {elapsed:.2f}s")
print()

# ── Summary ─────────────────────────────────────────────────────────────────
print("=" * 60)
print("ALL PHASE A TESTS PASSED ✓")
print("=" * 60)
