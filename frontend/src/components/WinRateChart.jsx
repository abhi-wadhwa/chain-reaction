import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, ReferenceLine } from 'recharts';

export default function WinRateChart({ winRateHistory }) {
  if (!winRateHistory || winRateHistory.length === 0) return null;

  const data = winRateHistory.map((wr, i) => ({
    iteration: i + 1,
    random: (wr.random ?? 0) * 100,
    greedy: (wr.greedy ?? 0) * 100,
    minimax_d3: (wr.minimax_d3 ?? 0) * 100,
  }));

  return (
    <div className="glass-panel p-4">
      <h3 className="text-sm font-semibold mb-3" style={{ fontFamily: 'var(--font-display)' }}>
        Win Rate vs Baselines
      </h3>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data}>
          <XAxis dataKey="iteration" stroke="#555" fontSize={10} />
          <YAxis domain={[0, 100]} stroke="#555" fontSize={10} tickFormatter={(v) => `${v}%`} />
          <Tooltip
            contentStyle={{
              background: '#1a1a2e', border: '1px solid #2a2a3e',
              borderRadius: 8, fontSize: 11,
            }}
            formatter={(v) => `${v.toFixed(0)}%`}
          />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <ReferenceLine y={50} stroke="#555" strokeDasharray="3 3" label={{ value: '50%', fill: '#555', fontSize: 10 }} />
          <Line type="monotone" dataKey="random" stroke="#69f0ae" strokeWidth={2} dot={{ r: 3 }} name="vs Random" />
          <Line type="monotone" dataKey="greedy" stroke="#ffd740" strokeWidth={2} dot={{ r: 3 }} name="vs Greedy" />
          <Line type="monotone" dataKey="minimax_d3" stroke="#ff6e40" strokeWidth={2} dot={{ r: 3 }} name="vs Minimax" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
