export default function HeadToHead({ winMatrix, agentNames }) {
  if (!winMatrix || agentNames.length === 0) return null;

  return (
    <div className="glass-panel p-4">
      <h3 className="text-sm font-semibold mb-3" style={{ fontFamily: 'var(--font-display)' }}>
        Head-to-Head Matrix
      </h3>
      <div className="overflow-x-auto">
        <table className="text-xs font-mono w-full">
          <thead>
            <tr>
              <th className="p-1 text-left text-[var(--color-text-secondary)]">vs</th>
              {agentNames.map((name) => (
                <th key={name} className="p-1 text-center text-[var(--color-text-secondary)] max-w-16 truncate">
                  {name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {agentNames.map((rowName) => (
              <tr key={rowName}>
                <td className="p-1 text-[var(--color-text-secondary)] max-w-20 truncate">{rowName}</td>
                {agentNames.map((colName) => {
                  if (rowName === colName) {
                    return (
                      <td key={colName} className="p-1 text-center text-[var(--color-text-secondary)]">-</td>
                    );
                  }
                  const wins = winMatrix[rowName]?.[colName] || 0;
                  const losses = winMatrix[colName]?.[rowName] || 0;
                  const total = wins + losses;
                  const winRate = total > 0 ? wins / total : 0.5;

                  // Color scale: cyan (100%) -> gray (50%) -> coral (0%)
                  const r = Math.round(255 * (1 - winRate));
                  const g = Math.round(100 + 60 * (winRate > 0.5 ? (winRate - 0.5) * 2 : 0));
                  const b = Math.round(255 * winRate);

                  return (
                    <td
                      key={colName}
                      className="p-1 text-center"
                      style={{
                        background: `rgba(${r}, ${g}, ${b}, 0.15)`,
                        color: winRate > 0.5 ? 'var(--color-cyan)' : winRate < 0.5 ? 'var(--color-coral)' : 'var(--color-text-secondary)',
                      }}
                    >
                      {wins}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
