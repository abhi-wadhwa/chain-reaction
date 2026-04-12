import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import Board from '../components/Board';
import StatsPanel from '../components/StatsPanel';
import GameTimeline from '../components/GameTimeline';
import { useApp } from '../store';
import { ChevronLeft, ChevronRight, Play, Pause } from 'lucide-react';

const EMPTY_STATE = (rows, cols) => ({
  rows, cols,
  owners: Array(rows * cols).fill(0),
  counts: Array(rows * cols).fill(0),
  current_player: 1,
  move_count: 0,
});

export default function ReplayPage() {
  const { gameId } = useParams();
  const { state: appState } = useApp();
  const [game, setGame] = useState(null);
  const [moveIdx, setMoveIdx] = useState(-1);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(500);
  const [explodingCells, setExplodingCells] = useState(new Set());

  useEffect(() => {
    const found = appState.recentGames.find((g) => g.game_id === gameId);
    if (found) {
      setGame(found);
      setMoveIdx(-1);
    }
  }, [gameId, appState.recentGames]);

  useEffect(() => {
    if (!playing || !game) return;
    const timer = setInterval(() => {
      setMoveIdx((prev) => {
        if (prev >= game.moves.length - 1) {
          setPlaying(false);
          return prev;
        }
        const next = prev + 1;
        const move = game.moves[next];
        if (move?.explosion_steps?.length > 0) {
          const cells = new Set(move.explosion_steps.map((s) => s.cell));
          setExplodingCells(cells);
          setTimeout(() => setExplodingCells(new Set()), 350);
        }
        return next;
      });
    }, speed);
    return () => clearInterval(timer);
  }, [playing, speed, game]);

  useEffect(() => {
    const handleKey = (e) => {
      if (!game) return;
      if (e.key === 'ArrowLeft') {
        setPlaying(false);
        setMoveIdx((prev) => Math.max(-1, prev - 1));
      }
      if (e.key === 'ArrowRight') {
        setPlaying(false);
        setMoveIdx((prev) => Math.min(game.moves.length - 1, prev + 1));
      }
      if (e.key === ' ') {
        e.preventDefault();
        setPlaying((p) => !p);
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [game]);

  if (!game) {
    return (
      <div className="h-full flex items-center justify-center text-[var(--color-text-secondary)]">
        <div className="text-center">
          <p className="text-lg mb-2">Game not found</p>
          <p className="text-sm">Play a game first, then come back to replay it.</p>
        </div>
      </div>
    );
  }

  const boardSize = game.board_size || { rows: 5, cols: 5 };
  const currentState = moveIdx >= 0 ? game.moves[moveIdx].board_after : EMPTY_STATE(boardSize.rows, boardSize.cols);
  const currentMove = moveIdx >= 0 ? game.moves[moveIdx] : null;
  const finished = moveIdx === game.moves.length - 1;

  return (
    <div className="h-full flex flex-col">
      {/* Main content */}
      <div className="flex-1 flex">
        {/* Board */}
        <div className="flex-1 flex flex-col items-center justify-center gap-4 p-6">
          <Board
            rows={boardSize.rows}
            cols={boardSize.cols}
            owners={currentState.owners}
            counts={currentState.counts}
            currentPlayer={currentState.current_player}
            explodingCells={explodingCells}
          />

          {/* Move annotation */}
          <div className="text-sm font-mono text-[var(--color-text-secondary)]">
            {currentMove ? (
              <span>
                Move {moveIdx + 1}: Player {currentMove.player} places at (
                {Math.floor(currentMove.cell / boardSize.cols)},{currentMove.cell % boardSize.cols})
                {currentMove.explosion_steps?.length > 0 && (
                  <span> — {currentMove.explosion_steps.length} explosion{currentMove.explosion_steps.length > 1 ? 's' : ''}</span>
                )}
              </span>
            ) : (
              <span>Start of game — use controls below</span>
            )}
          </div>
        </div>

        {/* Stats */}
        <div className="w-64 p-4 overflow-y-auto border-l border-[var(--color-border)]">
          <StatsPanel
            state={currentState}
            moves={game.moves.slice(0, moveIdx + 1)}
            finished={finished}
            result={finished ? game.result : null}
          />
        </div>
      </div>

      {/* Bottom controls */}
      <div className="border-t border-[var(--color-border)] p-4 space-y-3">
        <GameTimeline
          moves={game.moves}
          currentIdx={moveIdx}
          onSeek={(i) => { setPlaying(false); setMoveIdx(i); }}
        />

        <div className="flex items-center justify-center gap-4">
          <button
            onClick={() => { setPlaying(false); setMoveIdx((p) => Math.max(-1, p - 1)); }}
            className="p-2 rounded-lg glass-panel text-[var(--color-text-primary)] hover:bg-white/5"
          >
            <ChevronLeft size={18} />
          </button>
          <button
            onClick={() => setPlaying((p) => !p)}
            className="p-3 rounded-lg bg-[var(--color-cyan)] text-black hover:brightness-110"
          >
            {playing ? <Pause size={18} /> : <Play size={18} />}
          </button>
          <button
            onClick={() => { setPlaying(false); setMoveIdx((p) => Math.min(game.moves.length - 1, p + 1)); }}
            className="p-2 rounded-lg glass-panel text-[var(--color-text-primary)] hover:bg-white/5"
          >
            <ChevronRight size={18} />
          </button>
          <div className="flex items-center gap-2 ml-4">
            <span className="text-xs text-[var(--color-text-secondary)]">Speed:</span>
            <input
              type="range" min={50} max={2000} step={50} value={speed}
              onChange={(e) => setSpeed(parseInt(e.target.value))}
              className="w-24 h-1 rounded-lg appearance-none bg-[var(--color-border)] accent-[var(--color-cyan)]"
            />
            <span className="text-xs font-mono text-[var(--color-text-primary)]">{speed}ms</span>
          </div>
        </div>
      </div>
    </div>
  );
}
