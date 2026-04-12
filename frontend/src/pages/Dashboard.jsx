import { useNavigate } from 'react-router-dom';
import { useApp } from '../store';
import { FlaskConical, Trophy, Play } from 'lucide-react';

export default function Dashboard() {
  const navigate = useNavigate();
  const { state } = useApp();
  const { recentGames } = state;

  return (
    <div className="h-full p-6 grid grid-cols-4 gap-4">
      {/* Left — Agent Leaderboard */}
      <div className="glass-panel p-4 col-span-1">
        <h3 className="text-sm font-semibold mb-4" style={{ fontFamily: 'var(--font-display)' }}>
          Agent Types
        </h3>
        <div className="space-y-3">
          {['RandomAgent', 'GreedyAgent', 'MinimaxAgent', 'MCTSAgent'].map((name, i) => (
            <div key={name} className="flex items-center gap-2 text-sm">
              <div
                className="w-2 h-2 rounded-full"
                style={{ background: ['#00e5ff', '#ff3d71', '#7c4dff', '#ffd740'][i] }}
              />
              <span>{name}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Center — Recent Games */}
      <div className="col-span-2 space-y-4">
        <h3 className="text-sm font-semibold" style={{ fontFamily: 'var(--font-display)' }}>
          Recent Games
        </h3>
        {recentGames.length === 0 ? (
          <div className="glass-panel p-8 text-center">
            <p className="text-[var(--color-text-secondary)] mb-4">No games played yet</p>
            <button
              onClick={() => navigate('/game')}
              className="px-6 py-2 rounded-lg text-sm bg-[var(--color-cyan)] text-black font-bold hover:brightness-110 transition-all"
            >
              Play Your First Game
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            {recentGames.slice(0, 5).map((game) => (
              <div
                key={game.game_id}
                className="glass-panel p-3 flex items-center justify-between cursor-pointer hover:bg-white/5 transition-colors"
                onClick={() => navigate(`/replay/${game.game_id}`)}
              >
                <div className="flex items-center gap-3">
                  <div className="text-xs text-[var(--color-text-secondary)]">
                    {game.agent_configs?.[0]?.name} vs {game.agent_configs?.[1]?.name}
                  </div>
                </div>
                <div className="flex items-center gap-3 text-xs">
                  <span
                    style={{
                      color: game.result?.winner === 1 ? 'var(--color-cyan)' : 'var(--color-coral)',
                    }}
                  >
                    P{game.result?.winner} wins
                  </span>
                  <span className="text-[var(--color-text-secondary)]">{game.total_moves} moves</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Right — Quick Actions */}
      <div className="col-span-1 space-y-4">
        <h3 className="text-sm font-semibold" style={{ fontFamily: 'var(--font-display)' }}>
          Quick Actions
        </h3>
        <button
          onClick={() => navigate('/game')}
          className="w-full glass-panel p-4 flex items-center gap-3 hover:bg-white/5 transition-colors text-left"
        >
          <FlaskConical size={18} className="text-[var(--color-cyan)]" />
          <div>
            <div className="text-sm font-semibold">New Game</div>
            <div className="text-xs text-[var(--color-text-secondary)]">Configure and watch AI play</div>
          </div>
        </button>
        <button
          onClick={() => navigate('/tournament')}
          className="w-full glass-panel p-4 flex items-center gap-3 hover:bg-white/5 transition-colors text-left"
        >
          <Trophy size={18} className="text-[var(--color-coral)]" />
          <div>
            <div className="text-sm font-semibold">New Tournament</div>
            <div className="text-xs text-[var(--color-text-secondary)]">Run round-robin with Elo</div>
          </div>
        </button>

        <div className="glass-panel p-4">
          <div className="text-xs text-[var(--color-text-secondary)] mb-2">Stats</div>
          <div className="text-2xl font-bold font-mono text-[var(--color-text-primary)]">
            {recentGames.length}
          </div>
          <div className="text-xs text-[var(--color-text-secondary)]">games played this session</div>
        </div>
      </div>
    </div>
  );
}
