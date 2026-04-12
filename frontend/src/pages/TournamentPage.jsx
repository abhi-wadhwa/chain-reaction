import { useState, useEffect } from 'react';
import { fetchAgentTypes, startTournament, connectTournamentWS } from '../api';
import EloChart from '../components/EloChart';
import HeadToHead from '../components/HeadToHead';
import { Plus, X, Settings, Trophy } from 'lucide-react';

function AgentSlot({ agent, agentTypes, onChange, onRemove }) {
  const [showParams, setShowParams] = useState(false);
  const typeSchema = agentTypes.find((t) => t.type === agent.type);

  return (
    <div className="glass-panel p-3 space-y-2 min-w-48">
      <div className="flex items-center justify-between gap-2">
        <input
          value={agent.name}
          onChange={(e) => onChange({ ...agent, name: e.target.value })}
          className="bg-transparent text-sm font-semibold text-[var(--color-text-primary)] border-b border-transparent hover:border-[var(--color-border)] focus:border-[var(--color-cyan)] outline-none w-24"
          placeholder="Name"
        />
        <div className="flex gap-1">
          <button onClick={() => setShowParams(!showParams)} className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]">
            <Settings size={14} />
          </button>
          <button onClick={onRemove} className="text-[var(--color-text-secondary)] hover:text-[var(--color-coral)]">
            <X size={14} />
          </button>
        </div>
      </div>
      <select
        value={agent.type}
        onChange={(e) => onChange({ ...agent, type: e.target.value, params: {} })}
        className="w-full bg-[var(--color-cell-empty)] text-[var(--color-text-primary)] border border-[var(--color-border)] rounded px-2 py-1 text-xs"
      >
        {agentTypes.map((t) => (
          <option key={t.type} value={t.type}>{t.name}</option>
        ))}
      </select>
      {showParams && typeSchema && (
        <div className="space-y-2 pt-1">
          {Object.entries(typeSchema.params).map(([key, p]) => (
            <div key={key} className="flex items-center justify-between text-xs">
              <span className="text-[var(--color-text-secondary)] truncate max-w-20">{p.label}</span>
              {p.type === 'select' ? (
                <select
                  value={agent.params[key] ?? p.value}
                  onChange={(e) => onChange({ ...agent, params: { ...agent.params, [key]: e.target.value } })}
                  className="bg-[var(--color-cell-empty)] text-[var(--color-text-primary)] border border-[var(--color-border)] rounded px-1 text-xs w-20"
                >
                  {p.options.map((o) => <option key={o} value={o}>{o}</option>)}
                </select>
              ) : (
                <input
                  type="number"
                  value={agent.params[key] ?? p.value}
                  min={p.min} max={p.max} step={p.step}
                  onChange={(e) => {
                    const val = p.type === 'float' ? parseFloat(e.target.value) : parseInt(e.target.value);
                    onChange({ ...agent, params: { ...agent.params, [key]: val } });
                  }}
                  className="bg-[var(--color-cell-empty)] text-[var(--color-text-primary)] border border-[var(--color-border)] rounded px-1 text-xs w-16 text-right"
                />
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function TournamentPage() {
  const [agentTypes, setAgentTypes] = useState([]);
  const [agents, setAgents] = useState([
    { name: 'Random', type: 'random', params: {} },
    { name: 'Greedy', type: 'greedy', params: {} },
  ]);
  const [rows, setRows] = useState(5);
  const [cols, setCols] = useState(5);
  const [gamesPerPairing, setGamesPerPairing] = useState(10);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [eloHistory, setEloHistory] = useState([]);
  const [winMatrix, setWinMatrix] = useState({});
  const [leaderboard, setLeaderboard] = useState([]);
  const [recentResults, setRecentResults] = useState([]);
  const [finalResult, setFinalResult] = useState(null);

  useEffect(() => {
    fetchAgentTypes().then(setAgentTypes).catch(() => {});
  }, []);

  const agentNames = agents.map((a) => a.name);

  const addAgent = () => {
    if (agents.length >= 8) return;
    const types = ['random', 'greedy', 'minimax', 'mcts'];
    const idx = agents.length % types.length;
    setAgents([...agents, { name: `Agent${agents.length + 1}`, type: types[idx], params: {} }]);
  };

  const updateAgent = (i, updated) => {
    const copy = [...agents];
    copy[i] = updated;
    setAgents(copy);
  };

  const removeAgent = (i) => {
    if (agents.length <= 2) return;
    setAgents(agents.filter((_, idx) => idx !== i));
  };

  const handleStart = async () => {
    setRunning(true);
    setProgress(0);
    setEloHistory([]);
    setWinMatrix({});
    setLeaderboard([]);
    setRecentResults([]);
    setFinalResult(null);

    const agentSpecs = agents.map((a) => ({ type: a.type, params: a.params, name: a.name }));

    try {
      const { tournament_id } = await startTournament(agentSpecs, rows, cols, gamesPerPairing);

      const ws = connectTournamentWS(tournament_id, (msg) => {
        if (msg.type === 'game_complete') {
          const d = msg.data;
          setProgress(d.progress_pct);
          setEloHistory((prev) => [...prev, d.elo_ratings]);
          setRecentResults((prev) => [d, ...prev].slice(0, 20));

          // Update leaderboard from elo_ratings
          const lb = Object.entries(d.elo_ratings)
            .map(([name, elo]) => ({ name, elo }))
            .sort((a, b) => b.elo - a.elo);
          setLeaderboard(lb);
        }
        if (msg.type === 'tournament_complete') {
          setFinalResult(msg.data);
          setWinMatrix(msg.data.win_matrix || {});
          setRunning(false);

          const lb = Object.entries(msg.data.elo_ratings)
            .map(([name, elo]) => ({ name, elo, ...(msg.data.per_agent_stats?.[name] || {}) }))
            .sort((a, b) => b.elo - a.elo);
          setLeaderboard(lb);
        }
      });
    } catch (err) {
      console.error(err);
      setRunning(false);
    }
  };

  return (
    <div className="h-full flex flex-col p-6 gap-4 overflow-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold flex items-center gap-2" style={{ fontFamily: 'var(--font-display)' }}>
          <Trophy size={20} className="text-[var(--color-cyan)]" />
          Tournament
        </h2>
      </div>

      {/* Agent Config Bar */}
      <div className="flex gap-3 overflow-x-auto pb-2">
        {agents.map((agent, i) => (
          <AgentSlot
            key={i}
            agent={agent}
            agentTypes={agentTypes}
            onChange={(updated) => updateAgent(i, updated)}
            onRemove={() => removeAgent(i)}
          />
        ))}
        {agents.length < 8 && (
          <button
            onClick={addAgent}
            className="glass-panel w-12 flex items-center justify-center text-[var(--color-text-secondary)] hover:text-[var(--color-cyan)] transition-colors"
          >
            <Plus size={20} />
          </button>
        )}
      </div>

      {/* Settings Row */}
      <div className="flex items-center gap-4 text-sm">
        <div className="flex items-center gap-2">
          <span className="text-[var(--color-text-secondary)]">Board:</span>
          <input type="number" min={2} max={10} value={rows}
            onChange={(e) => setRows(parseInt(e.target.value))}
            className="w-12 bg-[var(--color-cell-empty)] text-[var(--color-text-primary)] border border-[var(--color-border)] rounded px-2 py-1 text-xs text-center" />
          <span className="text-[var(--color-text-secondary)]">x</span>
          <input type="number" min={2} max={10} value={cols}
            onChange={(e) => setCols(parseInt(e.target.value))}
            className="w-12 bg-[var(--color-cell-empty)] text-[var(--color-text-primary)] border border-[var(--color-border)] rounded px-2 py-1 text-xs text-center" />
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[var(--color-text-secondary)]">Games/pair:</span>
          <input type="number" min={1} max={100} value={gamesPerPairing}
            onChange={(e) => setGamesPerPairing(parseInt(e.target.value))}
            className="w-14 bg-[var(--color-cell-empty)] text-[var(--color-text-primary)] border border-[var(--color-border)] rounded px-2 py-1 text-xs text-center" />
        </div>
        <button
          onClick={handleStart}
          disabled={running}
          className="px-6 py-2 rounded-lg font-bold text-sm bg-[var(--color-cyan)] text-black hover:brightness-110 disabled:opacity-50 transition-all"
          style={{ fontFamily: 'var(--font-display)' }}
        >
          {running ? 'Running...' : 'Start Tournament'}
        </button>
      </div>

      {/* Progress */}
      {(running || finalResult) && (
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-[var(--color-text-secondary)]">
            <span>{running ? 'In progress...' : 'Complete'}</span>
            <span>{Math.round(progress)}%</span>
          </div>
          <div className="h-1.5 bg-[var(--color-border)] rounded-full overflow-hidden">
            <div
              className="h-full bg-[var(--color-cyan)] rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Results Grid */}
      {eloHistory.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 flex-1">
          <div className="lg:col-span-2">
            <EloChart eloHistory={eloHistory} agentNames={agentNames} />
          </div>
          <div className="space-y-4">
            {/* Leaderboard */}
            <div className="glass-panel p-4">
              <h3 className="text-sm font-semibold mb-3" style={{ fontFamily: 'var(--font-display)' }}>
                Leaderboard
              </h3>
              <div className="space-y-1">
                {leaderboard.map((entry, i) => (
                  <div key={entry.name} className="flex items-center justify-between text-xs py-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[var(--color-text-secondary)] w-4">{i + 1}.</span>
                      <span className="text-[var(--color-text-primary)]">{entry.name}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-[var(--color-cyan)]">{Math.round(entry.elo)}</span>
                      {entry.wins !== undefined && (
                        <span className="text-[var(--color-text-secondary)]">
                          {entry.wins}W {entry.losses}L
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
            {/* Head to Head */}
            {Object.keys(winMatrix).length > 0 && (
              <HeadToHead winMatrix={winMatrix} agentNames={agentNames} />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
