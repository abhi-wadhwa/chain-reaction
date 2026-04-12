function StatCard({ label, value, color }) {
  return (
    <div className="glass-panel p-3">
      <div className="text-xs text-[var(--color-text-secondary)] mb-1">{label}</div>
      <div className="text-lg font-bold font-mono" style={{ color }}>
        {value}
      </div>
    </div>
  );
}

export default function StatsPanel({ state, moves = [], finished, result }) {
  if (!state) return null;

  const { owners, counts, rows, cols } = state;

  let p1Orbs = 0, p2Orbs = 0, p1Cells = 0, p2Cells = 0, p1Loaded = 0, p2Loaded = 0;

  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const idx = r * cols + c;
      const owner = owners[idx];
      const count = counts[idx];
      if (owner === 1) {
        p1Orbs += count;
        p1Cells++;
        let critMass = 0;
        if (r > 0) critMass++;
        if (r < rows - 1) critMass++;
        if (c > 0) critMass++;
        if (c < cols - 1) critMass++;
        if (count === critMass - 1) p1Loaded++;
      } else if (owner === 2) {
        p2Orbs += count;
        p2Cells++;
        let critMass = 0;
        if (r > 0) critMass++;
        if (r < rows - 1) critMass++;
        if (c > 0) critMass++;
        if (c < cols - 1) critMass++;
        if (count === critMass - 1) p2Loaded++;
      }
    }
  }

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold" style={{ fontFamily: 'var(--font-display)' }}>
        Live Stats
      </h3>

      <div className="grid grid-cols-2 gap-2">
        <StatCard label="P1 Orbs" value={p1Orbs} color="var(--color-cyan)" />
        <StatCard label="P2 Orbs" value={p2Orbs} color="var(--color-coral)" />
        <StatCard label="P1 Cells" value={p1Cells} color="var(--color-cyan)" />
        <StatCard label="P2 Cells" value={p2Cells} color="var(--color-coral)" />
        <StatCard label="P1 Loaded" value={p1Loaded} color="var(--color-cyan)" />
        <StatCard label="P2 Loaded" value={p2Loaded} color="var(--color-coral)" />
      </div>

      {/* Move History */}
      <div className="glass-panel p-3 max-h-64 overflow-y-auto">
        <div className="text-xs text-[var(--color-text-secondary)] mb-2">Move History</div>
        {moves.length === 0 && (
          <p className="text-xs text-[var(--color-text-secondary)] italic">No moves yet</p>
        )}
        {[...moves].reverse().slice(0, 30).map((move, i) => {
          const moveNum = moves.length - i;
          const r = Math.floor(move.cell / cols);
          const c = move.cell % cols;
          const color = move.player === 1 ? 'var(--color-cyan)' : 'var(--color-coral)';
          const explosions = move.explosion_steps?.length || 0;
          return (
            <div key={moveNum} className="flex items-center gap-2 py-0.5 text-xs">
              <span className="text-[var(--color-text-secondary)] w-8">#{moveNum}</span>
              <span className="w-2 h-2 rounded-full" style={{ background: color }} />
              <span>({r},{c})</span>
              {explosions > 0 && (
                <span className="text-[var(--color-text-secondary)]">
                  {explosions} explosion{explosions > 1 ? 's' : ''}
                </span>
              )}
            </div>
          );
        })}
      </div>

      {finished && result && (
        <div
          className="glass-panel p-3 text-center font-bold text-sm"
          style={{
            color: result.winner === 1 ? 'var(--color-cyan)' : 'var(--color-coral)',
            fontFamily: 'var(--font-display)',
          }}
        >
          Player {result.winner} wins!
          <div className="text-xs text-[var(--color-text-secondary)] font-normal mt-1">
            {result.reason} — {moves.length} moves
          </div>
        </div>
      )}
    </div>
  );
}
