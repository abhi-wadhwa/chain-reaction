export default function NetworkArchViz({ rows, cols, residualBlocks }) {
  return (
    <div className="glass-panel p-4">
      <h3 className="text-xs font-semibold mb-3 text-[var(--color-text-secondary)]">
        Network Architecture
      </h3>
      <div className="flex items-center gap-1 overflow-x-auto text-[10px] font-mono">
        {/* Input */}
        <div className="flex-shrink-0 px-2 py-1 rounded bg-[#00e5ff]/10 text-[#00e5ff] border border-[#00e5ff]/20">
          Input<br/>{rows}x{cols}x6
        </div>
        <span className="text-[var(--color-text-secondary)]">&rarr;</span>

        {/* Conv */}
        <div className="flex-shrink-0 px-2 py-1 rounded bg-[#7c4dff]/10 text-[#7c4dff] border border-[#7c4dff]/20">
          Conv 64
        </div>
        <span className="text-[var(--color-text-secondary)]">&rarr;</span>

        {/* Residual blocks */}
        <div className="flex-shrink-0 px-2 py-1 rounded bg-[#ffd740]/10 text-[#ffd740] border border-[#ffd740]/20">
          Res x{residualBlocks}
        </div>
        <span className="text-[var(--color-text-secondary)]">&rarr;</span>

        {/* Heads */}
        <div className="flex flex-col gap-1">
          <div className="px-2 py-0.5 rounded bg-[#00e5ff]/10 text-[#00e5ff] border border-[#00e5ff]/20">
            Value &rarr; [-1,1]
          </div>
          <div className="px-2 py-0.5 rounded bg-[#ff3d71]/10 text-[#ff3d71] border border-[#ff3d71]/20">
            Policy &rarr; {rows*cols}
          </div>
        </div>
      </div>
    </div>
  );
}
