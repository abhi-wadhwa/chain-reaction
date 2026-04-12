import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const orbPositions = {
  1: [{ x: '50%', y: '50%' }],
  2: [{ x: '35%', y: '35%' }, { x: '65%', y: '65%' }],
  3: [{ x: '50%', y: '30%' }, { x: '30%', y: '65%' }, { x: '70%', y: '65%' }],
};

function Orbs({ count, color }) {
  const positions = orbPositions[Math.min(count, 3)] || orbPositions[3];
  const orbSize = count >= 3 ? '28%' : '24%';

  return positions.map((pos, i) => (
    <motion.div
      key={i}
      className="absolute rounded-full animate-orb"
      style={{
        left: pos.x,
        top: pos.y,
        width: orbSize,
        height: orbSize,
        transform: 'translate(-50%, -50%)',
        background: `radial-gradient(circle at 35% 35%, ${color}cc, ${color}88)`,
        boxShadow: `0 0 8px ${color}66`,
        animationDelay: `${i * 0.3}s`,
      }}
      initial={{ scale: 0 }}
      animate={{ scale: 1 }}
      transition={{ type: 'spring', stiffness: 500, damping: 20 }}
    />
  ));
}

export default function Cell({
  index,
  owner,
  count,
  critMass,
  isValid,
  isHumanTurn,
  onClick,
  exploding,
  rows,
  cols,
}) {
  const isLoaded = count > 0 && count === critMass - 1;
  const playerColor = owner === 1 ? 'var(--color-cyan)' : owner === 2 ? 'var(--color-coral)' : null;

  const row = Math.floor(index / cols);
  const col = index % cols;

  return (
    <motion.div
      className={`
        relative aspect-square rounded-lg cursor-default transition-all duration-200 overflow-hidden
        ${owner === 0 ? 'bg-[var(--color-cell-empty)]' : ''}
        ${isValid && isHumanTurn ? 'cursor-pointer hover:brightness-125 hover:ring-1 hover:ring-white/20' : ''}
        ${isLoaded ? 'animate-pulse-glow' : ''}
      `}
      style={{
        background: owner === 1
          ? 'linear-gradient(135deg, rgba(0,229,255,0.15), rgba(0,229,255,0.05))'
          : owner === 2
          ? 'linear-gradient(135deg, rgba(255,61,113,0.15), rgba(255,61,113,0.05))'
          : undefined,
        color: playerColor || 'transparent',
        boxShadow: owner !== 0
          ? `inset 0 0 20px ${playerColor}11`
          : 'inset 0 1px 3px rgba(0,0,0,0.3)',
      }}
      onClick={() => isValid && isHumanTurn && onClick?.(index)}
      whileTap={isValid && isHumanTurn ? { scale: 0.95 } : {}}
    >
      {/* Explosion overlay */}
      <AnimatePresence>
        {exploding && (
          <motion.div
            className="absolute inset-0 rounded-lg"
            style={{ background: playerColor }}
            initial={{ opacity: 0.8, scale: 1 }}
            animate={{ opacity: 0, scale: 2 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
          />
        )}
      </AnimatePresence>

      {/* Orbs */}
      {count > 0 && <Orbs count={count} color={playerColor} />}

      {/* Count indicator for high orb counts */}
      {count > 3 && (
        <span
          className="absolute bottom-0.5 right-1 text-[0.6em] font-bold opacity-60"
          style={{ color: playerColor, fontFamily: 'var(--font-mono)' }}
        >
          {count}
        </span>
      )}
    </motion.div>
  );
}
