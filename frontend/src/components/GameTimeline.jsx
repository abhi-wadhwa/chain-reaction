export default function GameTimeline({ moves, currentIdx, onSeek }) {
  if (!moves || moves.length === 0) return null;

  return (
    <div className="glass-panel p-3">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs text-[var(--color-text-secondary)]">Timeline</span>
        <span className="text-xs font-mono text-[var(--color-text-primary)]">
          {currentIdx + 1} / {moves.length}
        </span>
      </div>
      <div className="flex gap-0.5 overflow-x-auto py-1">
        {moves.map((move, i) => {
          const color = move.player === 1 ? 'var(--color-cyan)' : 'var(--color-coral)';
          const isActive = i === currentIdx;
          const hasExplosion = move.explosion_steps && move.explosion_steps.length > 0;
          return (
            <button
              key={i}
              onClick={() => onSeek(i)}
              className="flex-shrink-0 rounded-full transition-all"
              style={{
                width: isActive ? 12 : 6,
                height: isActive ? 12 : 6,
                background: color,
                opacity: i <= currentIdx ? 1 : 0.3,
                boxShadow: isActive ? `0 0 8px ${color}` : hasExplosion ? `0 0 4px ${color}` : 'none',
              }}
              title={`Move ${i + 1}: P${move.player} -> cell ${move.cell}`}
            />
          );
        })}
      </div>
    </div>
  );
}
