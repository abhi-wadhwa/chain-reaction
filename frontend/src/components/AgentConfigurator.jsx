import { useState } from 'react';

function ParamControl({ name, param, value, onChange }) {
  if (param.type === 'select') {
    return (
      <div className="flex flex-col gap-1">
        <label className="text-xs text-[var(--color-text-secondary)]">{param.label}</label>
        <select
          value={value}
          onChange={(e) => onChange(name, e.target.value)}
          className="bg-[var(--color-cell-empty)] text-[var(--color-text-primary)] border border-[var(--color-border)] rounded px-2 py-1 text-xs"
        >
          {param.options.map((opt) => (
            <option key={opt} value={opt}>{opt}</option>
          ))}
        </select>
      </div>
    );
  }

  const isFloat = param.type === 'float';
  const step = param.step || (isFloat ? 0.1 : 1);

  return (
    <div className="flex flex-col gap-1">
      <div className="flex justify-between items-center">
        <label className="text-xs text-[var(--color-text-secondary)]">{param.label}</label>
        <span className="text-xs font-mono text-[var(--color-text-primary)]">
          {isFloat ? Number(value).toFixed(1) : value}
        </span>
      </div>
      <input
        type="range"
        min={param.min}
        max={param.max}
        step={step}
        value={value}
        onChange={(e) => onChange(name, isFloat ? parseFloat(e.target.value) : parseInt(e.target.value))}
        className="w-full h-1 rounded-lg appearance-none bg-[var(--color-border)] accent-[var(--color-cyan)]"
      />
    </div>
  );
}

export default function AgentConfigurator({
  label,
  playerColor,
  agentTypes,
  selectedType,
  params,
  onTypeChange,
  onParamChange,
}) {
  const typeSchema = agentTypes.find((t) => t.type === selectedType);

  return (
    <div className="glass-panel p-4 space-y-3">
      <div className="flex items-center gap-2 mb-2">
        <div
          className="w-3 h-3 rounded-full"
          style={{ background: playerColor }}
        />
        <h3
          className="text-sm font-semibold"
          style={{ fontFamily: 'var(--font-display)' }}
        >
          {label}
        </h3>
      </div>

      <select
        value={selectedType}
        onChange={(e) => onTypeChange(e.target.value)}
        className="w-full bg-[var(--color-cell-empty)] text-[var(--color-text-primary)] border border-[var(--color-border)] rounded-lg px-3 py-2 text-sm"
      >
        {agentTypes.map((t) => (
          <option key={t.type} value={t.type}>{t.name}</option>
        ))}
        <option value="human">Human</option>
      </select>

      {typeSchema && typeSchema.params && (
        <div className="space-y-3 pt-2">
          {Object.entries(typeSchema.params).map(([key, paramSchema]) => (
            <ParamControl
              key={key}
              name={key}
              param={paramSchema}
              value={params[key] ?? paramSchema.value}
              onChange={onParamChange}
            />
          ))}
        </div>
      )}

      {selectedType === 'human' && (
        <p className="text-xs text-[var(--color-text-secondary)] italic">
          Click cells on the board to play
        </p>
      )}
    </div>
  );
}
