import { useState, useEffect, useRef } from 'react';
import { startTraining, pauseTraining, resumeTraining, stopTraining, getTrainingStatus, connectTrainingWS } from '../api';
import LossChart from '../components/LossChart';
import WinRateChart from '../components/WinRateChart';
import TrainingProgress from '../components/TrainingProgress';
import NetworkArchViz from '../components/NetworkArchViz';
import { Brain, Pause, Play, Square } from 'lucide-react';

function ConfigSlider({ label, value, onChange, min, max, step = 1, suffix = '' }) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-[var(--color-text-secondary)]">{label}</span>
        <span className="font-mono text-[var(--color-text-primary)]">{value}{suffix}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value}
        onChange={(e) => onChange(step < 1 ? parseFloat(e.target.value) : parseInt(e.target.value))}
        className="w-full h-1 rounded-lg appearance-none bg-[var(--color-border)] accent-[#00ff88]" />
    </div>
  );
}

export default function TrainingPage() {
  // Config state
  const [boardRows, setBoardRows] = useState(5);
  const [boardCols, setBoardCols] = useState(5);
  const [resBlocks, setResBlocks] = useState(4);
  const [gamesPerIter, setGamesPerIter] = useState(100);
  const [mctsSims, setMctsSims] = useState(200);
  const [cPuct, setCPuct] = useState(1.5);
  const [tempMoves, setTempMoves] = useState(0);
  const [numIter, setNumIter] = useState(50);
  const [epochs, setEpochs] = useState(10);
  const [batchSize, setBatchSize] = useState(64);
  const [lr, setLr] = useState(0.001);
  const [lrSchedule, setLrSchedule] = useState('cosine');
  const [weightDecay, setWeightDecay] = useState(0.0001);
  const [replayWindow, setReplayWindow] = useState(5);
  const [evalGames, setEvalGames] = useState(100);
  const [evalThreshold, setEvalThreshold] = useState(0.55);

  // Training state
  const [trainingId, setTrainingId] = useState(null);
  const [running, setRunning] = useState(false);
  const [paused, setPaused] = useState(false);
  const [configCollapsed, setConfigCollapsed] = useState(false);

  // Metrics
  const [currentPhase, setCurrentPhase] = useState('idle');
  const [iteration, setIteration] = useState(0);
  const [totalIterations, setTotalIterations] = useState(0);
  const [valueLosses, setValueLosses] = useState([]);
  const [policyLosses, setPolicyLosses] = useState([]);
  const [winRateHistory, setWinRateHistory] = useState([]);
  const [selfPlayStats, setSelfPlayStats] = useState([]);
  const [bestIteration, setBestIteration] = useState(0);
  const [bestWinRates, setBestWinRates] = useState({});
  const [phaseData, setPhaseData] = useState({});

  const wsRef = useRef(null);

  const handleStart = async () => {
    const config = {
      board_rows: boardRows,
      board_cols: boardCols,
      num_iterations: numIter,
      games_per_iteration: gamesPerIter,
      mcts_simulations: mctsSims,
      training_epochs: epochs,
      batch_size: batchSize,
      learning_rate: lr,
      lr_schedule: lrSchedule,
      weight_decay: weightDecay,
      c_puct: cPuct,
      temperature_moves: tempMoves,
      replay_window: replayWindow,
      eval_games: evalGames,
      eval_threshold: evalThreshold,
      num_residual_blocks: resBlocks,
      device: 'auto',
    };

    const { training_id } = await startTraining(config);
    setTrainingId(training_id);
    setRunning(true);
    setConfigCollapsed(true);
    setTotalIterations(numIter);

    // Connect WebSocket
    const ws = connectTrainingWS(training_id, handleWSMessage);
    wsRef.current = ws;
  };

  const handleWSMessage = (msg) => {
    const phase = msg.phase;
    setCurrentPhase(phase);

    if (phase === 'self_play') {
      setIteration(msg.iteration);
      setPhaseData((prev) => ({
        ...prev,
        self_play: `Game ${msg.game}/${msg.total_games}`,
      }));
    }
    if (phase === 'buffer_update') {
      setPhaseData((prev) => ({
        ...prev,
        buffer_update: `${msg.buffer_size} examples`,
      }));
    }
    if (phase === 'training') {
      setValueLosses((prev) => [...prev, msg.value_loss]);
      setPolicyLosses((prev) => [...prev, msg.policy_loss]);
      setPhaseData((prev) => ({
        ...prev,
        training: `Epoch ${msg.epoch}/${msg.total_epochs}, Loss: ${msg.total_loss?.toFixed(3)}`,
      }));
    }
    if (phase === 'evaluation') {
      setPhaseData((prev) => ({
        ...prev,
        evaluation: `${msg.wins}W ${msg.losses}L ${msg.draws}D`,
      }));
    }
    if (phase === 'model_accepted') {
      setBestIteration(msg.iteration);
      setPhaseData((prev) => ({
        ...prev,
        model_decision: `Accepted (${(msg.win_rate * 100).toFixed(0)}%)`,
      }));
    }
    if (phase === 'model_rejected') {
      setPhaseData((prev) => ({
        ...prev,
        model_decision: `Rejected (${(msg.win_rate * 100).toFixed(0)}%)`,
      }));
    }
    if (phase === 'benchmark') {
      setPhaseData((prev) => ({
        ...prev,
        benchmark: `vs ${msg.opponent}: ${(msg.win_rate * 100).toFixed(0)}%`,
      }));
    }
    if (phase === 'iteration_complete') {
      setIteration(msg.iteration);
      setBestIteration(msg.best_model_iteration);
      if (msg.win_rates) {
        setWinRateHistory((prev) => [...prev, msg.win_rates]);
        setBestWinRates(msg.win_rates);
      }
      if (msg.self_play_stats) {
        setSelfPlayStats((prev) => [...prev, msg.self_play_stats]);
      }
    }
  };

  const handlePause = async () => {
    if (trainingId) {
      await pauseTraining(trainingId);
      setPaused(true);
    }
  };

  const handleResume = async () => {
    if (trainingId) {
      await resumeTraining(trainingId);
      setPaused(false);
    }
  };

  const handleStop = async () => {
    if (trainingId) {
      await stopTraining(trainingId);
      setRunning(false);
      setPaused(false);
    }
  };

  useEffect(() => {
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  const progressPct = totalIterations > 0 ? (iteration / totalIterations) * 100 : 0;

  return (
    <div className="h-full flex flex-col p-6 gap-4 overflow-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold flex items-center gap-2" style={{ fontFamily: 'var(--font-display)' }}>
          <Brain size={20} className="text-[#00ff88]" />
          RL Training
        </h2>
        {running && (
          <div className="text-xs text-[var(--color-text-secondary)]">
            Training {boardRows}x{boardCols} board, {numIter} iterations, {gamesPerIter} games/iter
          </div>
        )}
      </div>

      {/* Config Panel */}
      {!configCollapsed ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Card 1: Board & Network */}
          <div className="glass-panel p-4 space-y-3">
            <h3 className="text-xs font-semibold text-[#00ff88]">Board & Network</h3>
            <ConfigSlider label="Rows" value={boardRows} onChange={setBoardRows} min={2} max={10} />
            <ConfigSlider label="Cols" value={boardCols} onChange={setBoardCols} min={2} max={10} />
            <ConfigSlider label="Residual Blocks" value={resBlocks} onChange={setResBlocks} min={2} max={8} />
            <NetworkArchViz rows={boardRows} cols={boardCols} residualBlocks={resBlocks} />
          </div>

          {/* Card 2: Self-Play */}
          <div className="glass-panel p-4 space-y-3">
            <h3 className="text-xs font-semibold text-[#00ff88]">Self-Play</h3>
            <ConfigSlider label="Games per iteration" value={gamesPerIter} onChange={setGamesPerIter} min={20} max={500} step={10} />
            <ConfigSlider label="MCTS simulations" value={mctsSims} onChange={setMctsSims} min={50} max={1000} step={50} />
            <ConfigSlider label="PUCT constant" value={cPuct} onChange={setCPuct} min={0.5} max={5.0} step={0.1} />
            <ConfigSlider label="Exploration moves" value={tempMoves || Math.floor(boardRows * boardCols / 2)} onChange={setTempMoves} min={2} max={50} />
          </div>

          {/* Card 3: Training */}
          <div className="glass-panel p-4 space-y-3">
            <h3 className="text-xs font-semibold text-[#00ff88]">Training</h3>
            <ConfigSlider label="Total iterations" value={numIter} onChange={setNumIter} min={10} max={200} />
            <ConfigSlider label="Epochs per iteration" value={epochs} onChange={setEpochs} min={1} max={50} />
            <div className="space-y-1">
              <label className="text-xs text-[var(--color-text-secondary)]">Batch size</label>
              <select value={batchSize} onChange={(e) => setBatchSize(parseInt(e.target.value))}
                className="w-full bg-[var(--color-cell-empty)] text-[var(--color-text-primary)] border border-[var(--color-border)] rounded px-2 py-1 text-xs">
                {[32, 64, 128, 256].map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-xs text-[var(--color-text-secondary)]">Learning rate</label>
              <input type="number" value={lr} step={0.0001} min={0.00001} max={0.1}
                onChange={(e) => setLr(parseFloat(e.target.value))}
                className="w-full bg-[var(--color-cell-empty)] text-[var(--color-text-primary)] border border-[var(--color-border)] rounded px-2 py-1 text-xs" />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-[var(--color-text-secondary)]">LR schedule</label>
              <select value={lrSchedule} onChange={(e) => setLrSchedule(e.target.value)}
                className="w-full bg-[var(--color-cell-empty)] text-[var(--color-text-primary)] border border-[var(--color-border)] rounded px-2 py-1 text-xs">
                {['cosine', 'step', 'constant'].map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <ConfigSlider label="Replay buffer window" value={replayWindow} onChange={setReplayWindow} min={1} max={20} />
          </div>

          {/* Card 4: Evaluation */}
          <div className="glass-panel p-4 space-y-3">
            <h3 className="text-xs font-semibold text-[#00ff88]">Evaluation</h3>
            <ConfigSlider label="Evaluation games" value={evalGames} onChange={setEvalGames} min={20} max={400} step={10} />
            <ConfigSlider label="Accept threshold" value={evalThreshold} onChange={setEvalThreshold} min={0.50} max={0.70} step={0.01} suffix="%" />
          </div>
        </div>
      ) : (
        <button onClick={() => setConfigCollapsed(false)} className="text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] self-start">
          Show configuration...
        </button>
      )}

      {/* Start / Control buttons */}
      <div className="flex items-center gap-3">
        {!running ? (
          <button onClick={handleStart}
            className="px-8 py-3 rounded-lg font-bold text-sm text-black hover:brightness-110 transition-all"
            style={{ background: '#00ff88', fontFamily: 'var(--font-display)' }}>
            Start Training
          </button>
        ) : (
          <>
            {!paused ? (
              <button onClick={handlePause}
                className="px-4 py-2 rounded-lg text-sm glass-panel flex items-center gap-2 hover:bg-white/5">
                <Pause size={14} /> Pause
              </button>
            ) : (
              <button onClick={handleResume}
                className="px-4 py-2 rounded-lg text-sm flex items-center gap-2 hover:brightness-110"
                style={{ background: '#00ff88', color: 'black' }}>
                <Play size={14} /> Resume
              </button>
            )}
            <button onClick={handleStop}
              className="px-4 py-2 rounded-lg text-sm glass-panel flex items-center gap-2 text-[var(--color-coral)] hover:bg-[var(--color-coral)]/10">
              <Square size={14} /> Stop
            </button>
          </>
        )}
      </div>

      {/* Progress bar */}
      {running && (
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-[var(--color-text-secondary)]">
            <span>Iteration {iteration} / {totalIterations}</span>
            <span>{Math.round(progressPct)}%</span>
          </div>
          <div className="h-1.5 bg-[var(--color-border)] rounded-full overflow-hidden">
            <div className="h-full rounded-full transition-all duration-500"
              style={{ width: `${progressPct}%`, background: '#00ff88' }} />
          </div>
        </div>
      )}

      {/* Main monitoring area */}
      {(running || valueLosses.length > 0) && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 flex-1">
          {/* Left: Charts */}
          <div className="lg:col-span-2 space-y-4">
            <LossChart valueLosses={valueLosses} policyLosses={policyLosses} epochsPerIteration={epochs} />
            <WinRateChart winRateHistory={winRateHistory} />

            {/* Self-play stats */}
            {selfPlayStats.length > 0 && (
              <div className="glass-panel p-4">
                <h3 className="text-sm font-semibold mb-2" style={{ fontFamily: 'var(--font-display)' }}>
                  Self-Play Stats
                </h3>
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div>
                    <div className="text-lg font-bold font-mono text-[#00ff88]">
                      {selfPlayStats[selfPlayStats.length - 1]?.avg_game_length?.toFixed(1) || '-'}
                    </div>
                    <div className="text-xs text-[var(--color-text-secondary)]">Avg Game Length</div>
                  </div>
                  <div>
                    <div className="text-lg font-bold font-mono text-[var(--color-cyan)]">
                      {((selfPlayStats[selfPlayStats.length - 1]?.p1_win_rate || 0) * 100).toFixed(0)}%
                    </div>
                    <div className="text-xs text-[var(--color-text-secondary)]">P1 Win Rate</div>
                  </div>
                  <div>
                    <div className="text-lg font-bold font-mono text-[#ffd740]">
                      {valueLosses.length > 0 ? valueLosses[valueLosses.length - 1].toFixed(3) : '-'}
                    </div>
                    <div className="text-xs text-[var(--color-text-secondary)]">Latest Value Loss</div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Right: Status panel */}
          <div className="space-y-4">
            {/* Iteration counter */}
            <div className="glass-panel p-4 text-center">
              <div className="text-3xl font-bold font-mono" style={{ color: '#00ff88' }}>
                {iteration} <span className="text-lg text-[var(--color-text-secondary)]">/ {totalIterations}</span>
              </div>
              <div className="text-xs text-[var(--color-text-secondary)] mt-1">Iterations</div>
            </div>

            <TrainingProgress currentPhase={currentPhase} phaseData={phaseData} />

            {/* Best model info */}
            <div className="glass-panel p-4 space-y-2">
              <h3 className="text-xs font-semibold text-[#00ff88]">Best Model</h3>
              <div className="text-sm">
                Iteration <span className="font-bold text-[#00ff88]">{bestIteration}</span>
              </div>
              {Object.keys(bestWinRates).length > 0 && (
                <div className="space-y-1 text-xs">
                  {Object.entries(bestWinRates).map(([opp, wr]) => (
                    <div key={opp} className="flex justify-between">
                      <span className="text-[var(--color-text-secondary)]">vs {opp}:</span>
                      <span className="font-mono" style={{
                        color: wr >= 0.6 ? '#00ff88' : wr >= 0.4 ? '#ffd740' : 'var(--color-coral)',
                      }}>
                        {(wr * 100).toFixed(0)}%
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
