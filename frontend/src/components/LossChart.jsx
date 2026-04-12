import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, ReferenceLine } from 'recharts';

export default function LossChart({ valueLosses, policyLosses, epochsPerIteration = 10 }) {
  if (!valueLosses || valueLosses.length === 0) return null;

  const data = valueLosses.map((vl, i) => ({
    step: i + 1,
    value_loss: vl,
    policy_loss: policyLosses?.[i] ?? 0,
  }));

  // Iteration boundaries
  const iterBoundaries = [];
  if (epochsPerIteration > 0) {
    for (let i = epochsPerIteration; i < data.length; i += epochsPerIteration) {
      iterBoundaries.push(i);
    }
  }

  return (
    <div className="glass-panel p-4">
      <h3 className="text-sm font-semibold mb-3" style={{ fontFamily: 'var(--font-display)' }}>
        Training Loss
      </h3>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data}>
          <XAxis dataKey="step" stroke="#555" fontSize={10} />
          <YAxis yAxisId="left" stroke="#00e5ff" fontSize={10} />
          <YAxis yAxisId="right" orientation="right" stroke="#ff3d71" fontSize={10} />
          <Tooltip
            contentStyle={{
              background: '#1a1a2e', border: '1px solid #2a2a3e',
              borderRadius: 8, fontSize: 11,
            }}
          />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          {iterBoundaries.map((x) => (
            <ReferenceLine key={x} x={x} yAxisId="left" stroke="#333" strokeDasharray="3 3" />
          ))}
          <Line yAxisId="left" type="monotone" dataKey="value_loss" stroke="#00e5ff" strokeWidth={1.5} dot={false} name="Value Loss" />
          <Line yAxisId="right" type="monotone" dataKey="policy_loss" stroke="#ff3d71" strokeWidth={1.5} dot={false} name="Policy Loss" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
