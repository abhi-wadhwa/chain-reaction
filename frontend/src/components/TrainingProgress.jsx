import { Gamepad2, Database, Brain, Trophy, Check, X, BarChart3 } from 'lucide-react';

const PHASES = [
  { key: 'self_play', icon: Gamepad2, label: 'Self-Play' },
  { key: 'buffer_update', icon: Database, label: 'Buffer Update' },
  { key: 'training', icon: Brain, label: 'Network Training' },
  { key: 'evaluation', icon: Trophy, label: 'Model Evaluation' },
  { key: 'model_decision', icon: Check, label: 'Model Decision' },
  { key: 'benchmark', icon: BarChart3, label: 'Benchmark' },
];

function getPhaseIndex(phase) {
  const idx = PHASES.findIndex((p) => p.key === phase);
  return idx >= 0 ? idx : -1;
}

export default function TrainingProgress({ currentPhase, phaseData = {} }) {
  const activeIdx = getPhaseIndex(currentPhase);

  return (
    <div className="glass-panel p-4">
      <h3 className="text-sm font-semibold mb-4" style={{ fontFamily: 'var(--font-display)' }}>
        Current Phase
      </h3>
      <div className="space-y-2">
        {PHASES.map((phase, i) => {
          const Icon = phase.icon;
          const isActive = i === activeIdx;
          const isComplete = i < activeIdx;
          const isFuture = i > activeIdx;

          return (
            <div
              key={phase.key}
              className={`flex items-center gap-3 p-2 rounded-lg transition-all ${
                isActive
                  ? 'bg-[#00ff88]/10 border border-[#00ff88]/30'
                  : isComplete
                  ? 'opacity-70'
                  : 'opacity-30'
              }`}
            >
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center ${
                  isActive
                    ? 'bg-[#00ff88]/20 animate-pulse-glow'
                    : isComplete
                    ? 'bg-[#00ff88]/10'
                    : 'bg-white/5'
                }`}
                style={{ color: isActive ? '#00ff88' : isComplete ? '#00ff88' : '#555' }}
              >
                {isComplete ? <Check size={14} /> : <Icon size={14} />}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-xs font-semibold" style={{
                  color: isActive ? '#00ff88' : 'var(--color-text-primary)',
                }}>
                  {phase.label}
                </div>
                {isActive && phaseData[phase.key] && (
                  <div className="text-[10px] text-[var(--color-text-secondary)] truncate">
                    {phaseData[phase.key]}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
