import { useState, useEffect, useRef, useCallback } from 'react';
import Board from '../components/Board';
import AgentConfigurator from '../components/AgentConfigurator';
import StatsPanel from '../components/StatsPanel';
import { fetchAgentTypes, playGame, startInteractiveGame, makeHumanMove } from '../api';
import { useApp } from '../store';

const EMPTY_STATE = (rows, cols) => ({
  rows,
  cols,
  owners: Array(rows * cols).fill(0),
  counts: Array(rows * cols).fill(0),
  current_player: 1,
  move_count: 0,
});

export default function GameLab() {
  const { state: appState, dispatch } = useApp();
  const [agentTypes, setAgentTypes] = useState([]);
  const [p1Type, setP1Type] = useState('greedy');
  const [p2Type, setP2Type] = useState('mcts');
  const [p1Params, setP1Params] = useState({});
  const [p2Params, setP2Params] = useState({});
  const [rows, setRows] = useState(5);
  const [cols, setCols] = useState(5);
  const [speed, setSpeed] = useState(300);

  const [gameState, setGameState] = useState(null);
  const [moves, setMoves] = useState([]);
  const [currentMoveIdx, setCurrentMoveIdx] = useState(-1);
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(false);
  const [finished, setFinished] = useState(false);
  const [result, setResult] = useState(null);
  const [explodingCells, setExplodingCells] = useState(new Set());

  // Interactive game state
  const [interactiveGameId, setInteractiveGameId] = useState(null);
  const [isHumanTurn, setIsHumanTurn] = useState(false);

  const playingRef = useRef(false);
  const movesRef = useRef([]);
  const moveIdxRef = useRef(-1);
  const speedRef = useRef(speed);

  useEffect(() => { speedRef.current = speed; }, [speed]);
  useEffect(() => { movesRef.current = moves; }, [moves]);
  useEffect(() => { moveIdxRef.current = currentMoveIdx; }, [currentMoveIdx]);

  useEffect(() => {
    fetchAgentTypes().then((types) => {
      setAgentTypes(types);
      dispatch({ type: 'SET_AGENT_TYPES', payload: types });
    }).catch(() => {});
  }, []);

  const isHumanGame = p1Type === 'human' || p2Type === 'human';

  const handlePlay = async () => {
    setLoading(true);
    setFinished(false);
    setResult(null);
    setMoves([]);
    setCurrentMoveIdx(-1);
    setGameState(EMPTY_STATE(rows, cols));
    setInteractiveGameId(null);
    setExplodingCells(new Set());

    try {
      if (isHumanGame) {
        const aiType = p1Type === 'human' ? p2Type : p1Type;
        const aiParams = p1Type === 'human' ? p2Params : p1Params;
        const humanPlayer = p1Type === 'human' ? 1 : 2;
        const data = await startInteractiveGame(
          { type: aiType, params: aiParams },
          rows, cols, humanPlayer
        );
        setInteractiveGameId(data.game_id);
        setGameState(data.state);
        setMoves(data.moves || []);
        setCurrentMoveIdx((data.moves || []).length - 1);
        setIsHumanTurn(data.state.current_player === humanPlayer);
        if (data.finished) {
          setFinished(true);
          setResult(data.result);
        }
      } else {
        const agent1 = { type: p1Type, params: p1Params };
        const agent2 = { type: p2Type, params: p2Params };
        const data = await playGame(agent1, agent2, rows, cols);
        dispatch({ type: 'ADD_GAME', payload: data });

        const allMoves = data.moves || [];
        setMoves(allMoves);
        movesRef.current = allMoves;

        if (allMoves.length > 0 && speed > 0) {
          // Animate playback
          playingRef.current = true;
          setPlaying(true);
          animatePlayback(allMoves, 0, data.result);
        } else {
          // Instant result
          if (allMoves.length > 0) {
            const lastMove = allMoves[allMoves.length - 1];
            setGameState(lastMove.board_after);
            setCurrentMoveIdx(allMoves.length - 1);
          }
          setFinished(true);
          setResult(data.result);
        }
      }
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  };

  const animatePlayback = useCallback((allMoves, startIdx, gameResult) => {
    let idx = startIdx;

    const step = () => {
      if (!playingRef.current || idx >= allMoves.length) {
        playingRef.current = false;
        setPlaying(false);
        if (idx >= allMoves.length) {
          setFinished(true);
          setResult(gameResult);
        }
        return;
      }

      const move = allMoves[idx];
      setGameState(move.board_after);
      setCurrentMoveIdx(idx);

      // Show explosion animation
      if (move.explosion_steps && move.explosion_steps.length > 0) {
        const cells = new Set(move.explosion_steps.map((s) => s.cell));
        setExplodingCells(cells);
        setTimeout(() => setExplodingCells(new Set()), 350);
      }

      idx++;
      setTimeout(step, speedRef.current);
    };

    step();
  }, []);

  const handlePause = () => {
    playingRef.current = false;
    setPlaying(false);
  };

  const handleResume = () => {
    if (currentMoveIdx < moves.length - 1) {
      playingRef.current = true;
      setPlaying(true);
      animatePlayback(moves, currentMoveIdx + 1, result);
    }
  };

  const handleCellClick = async (cellIndex) => {
    if (!interactiveGameId || !isHumanTurn) return;
    setLoading(true);
    try {
      const data = await makeHumanMove(interactiveGameId, cellIndex);
      setGameState(data.state);
      setMoves((prev) => [...prev, ...(data.moves || [])]);
      setCurrentMoveIdx((prev) => prev + (data.moves || []).length);
      if (data.finished) {
        setFinished(true);
        setResult(data.result);
        setIsHumanTurn(false);
      } else {
        const humanPlayer = p1Type === 'human' ? 1 : 2;
        setIsHumanTurn(data.state.current_player === humanPlayer);
      }
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  };

  const handleP1ParamChange = (name, value) => setP1Params((p) => ({ ...p, [name]: value }));
  const handleP2ParamChange = (name, value) => setP2Params((p) => ({ ...p, [name]: value }));

  const currentState = gameState || EMPTY_STATE(rows, cols);

  return (
    <div className="h-full flex">
      {/* Left panel — Config */}
      <div className="w-72 p-4 space-y-4 overflow-y-auto border-r border-[var(--color-border)]">
        <h2 className="text-lg font-bold" style={{ fontFamily: 'var(--font-display)' }}>
          Game Lab
        </h2>

        <AgentConfigurator
          label="Player 1"
          playerColor="var(--color-cyan)"
          agentTypes={agentTypes}
          selectedType={p1Type}
          params={p1Params}
          onTypeChange={(t) => { setP1Type(t); setP1Params({}); }}
          onParamChange={handleP1ParamChange}
        />

        <AgentConfigurator
          label="Player 2"
          playerColor="var(--color-coral)"
          agentTypes={agentTypes}
          selectedType={p2Type}
          params={p2Params}
          onTypeChange={(t) => { setP2Type(t); setP2Params({}); }}
          onParamChange={handleP2ParamChange}
        />

        {/* Board Size */}
        <div className="glass-panel p-4 space-y-3">
          <h3 className="text-sm font-semibold" style={{ fontFamily: 'var(--font-display)' }}>
            Board Size
          </h3>
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="text-xs text-[var(--color-text-secondary)]">Rows: {rows}</label>
              <input
                type="range" min={2} max={10} value={rows}
                onChange={(e) => setRows(parseInt(e.target.value))}
                className="w-full h-1 rounded-lg appearance-none bg-[var(--color-border)] accent-[var(--color-cyan)]"
              />
            </div>
            <div className="flex-1">
              <label className="text-xs text-[var(--color-text-secondary)]">Cols: {cols}</label>
              <input
                type="range" min={2} max={10} value={cols}
                onChange={(e) => setCols(parseInt(e.target.value))}
                className="w-full h-1 rounded-lg appearance-none bg-[var(--color-border)] accent-[var(--color-cyan)]"
              />
            </div>
          </div>
        </div>

        {/* Speed Control */}
        {!isHumanGame && (
          <div className="glass-panel p-4 space-y-2">
            <div className="flex justify-between text-xs text-[var(--color-text-secondary)]">
              <span>Speed</span>
              <span>{speed === 0 ? 'Instant' : `${speed}ms`}</span>
            </div>
            <input
              type="range" min={0} max={2000} step={50} value={speed}
              onChange={(e) => setSpeed(parseInt(e.target.value))}
              className="w-full h-1 rounded-lg appearance-none bg-[var(--color-border)] accent-[var(--color-cyan)]"
            />
          </div>
        )}

        {/* Controls */}
        <button
          onClick={handlePlay}
          disabled={loading || playing}
          className="w-full py-3 rounded-lg font-bold text-sm bg-[var(--color-cyan)] text-black hover:brightness-110 disabled:opacity-50 transition-all"
          style={{ fontFamily: 'var(--font-display)' }}
        >
          {loading ? 'Running...' : 'Play Game'}
        </button>

        {playing && (
          <button
            onClick={handlePause}
            className="w-full py-2 rounded-lg text-sm border border-[var(--color-border)] text-[var(--color-text-primary)] hover:bg-white/5"
          >
            Pause
          </button>
        )}

        {!playing && currentMoveIdx >= 0 && currentMoveIdx < moves.length - 1 && (
          <button
            onClick={handleResume}
            className="w-full py-2 rounded-lg text-sm border border-[var(--color-border)] text-[var(--color-text-primary)] hover:bg-white/5"
          >
            Resume
          </button>
        )}
      </div>

      {/* Center — Board */}
      <div className="flex-1 flex flex-col items-center justify-center gap-4 p-6">
        <Board
          rows={currentState.rows}
          cols={currentState.cols}
          owners={currentState.owners}
          counts={currentState.counts}
          currentPlayer={currentState.current_player}
          isHumanTurn={isHumanTurn && !loading}
          onCellClick={handleCellClick}
          explodingCells={explodingCells}
        />

        <div className="text-sm text-[var(--color-text-secondary)] font-mono">
          {finished && result ? (
            <span style={{ color: result.winner === 1 ? 'var(--color-cyan)' : 'var(--color-coral)' }}>
              Player {result.winner} wins in {moves.length} moves!
            </span>
          ) : currentMoveIdx >= 0 ? (
            <span>
              Move {currentMoveIdx + 1} / {moves.length} — Player {currentState.current_player}'s turn
            </span>
          ) : (
            <span>Configure agents and click Play</span>
          )}
        </div>
      </div>

      {/* Right — Stats */}
      <div className="w-64 p-4 overflow-y-auto border-l border-[var(--color-border)]">
        <StatsPanel
          state={currentState}
          moves={moves.slice(0, currentMoveIdx + 1)}
          finished={finished}
          result={result}
        />
      </div>
    </div>
  );
}
