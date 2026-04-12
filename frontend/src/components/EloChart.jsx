import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts';

const COLORS = [
  '#00e5ff', '#ff3d71', '#7c4dff', '#ffd740',
  '#69f0ae', '#ff6e40', '#40c4ff', '#eeff41',
];

export default function EloChart({ eloHistory, agentNames }) {
  if (!eloHistory || eloHistory.length === 0) return null;

  const data = eloHistory.map((snapshot, i) => ({
    game: i + 1,
    ...snapshot,
  }));

  return (
    <div className="glass-panel p-4">
      <h3 className="text-sm font-semibold mb-3" style={{ fontFamily: 'var(--font-display)' }}>
        Elo Ratings Over Time
      </h3>
      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={data}>
          <XAxis dataKey="game" stroke="#555" fontSize={10} />
          <YAxis stroke="#555" fontSize={10} domain={['auto', 'auto']} />
          <Tooltip
            contentStyle={{
              background: '#1a1a2e',
              border: '1px solid #2a2a3e',
              borderRadius: 8,
              fontSize: 11,
            }}
          />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          {agentNames.map((name, i) => (
            <Line
              key={name}
              type="monotone"
              dataKey={name}
              stroke={COLORS[i % COLORS.length]}
              strokeWidth={2}
              dot={false}
              animationDuration={300}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
