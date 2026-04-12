import { useState, useEffect, useCallback } from 'react';
import Cell from './Cell';

function computeCriticalMass(row, col, rows, cols) {
  let n = 0;
  if (row > 0) n++;
  if (row < rows - 1) n++;
  if (col > 0) n++;
  if (col < cols - 1) n++;
  return n;
}

export default function Board({
  rows,
  cols,
  owners,
  counts,
  currentPlayer,
  isHumanTurn = false,
  onCellClick,
  explodingCells = new Set(),
}) {
  const cells = [];
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const idx = r * cols + c;
      const owner = owners[idx];
      const count = counts[idx];
      const critMass = computeCriticalMass(r, c, rows, cols);
      const isValid = owner === 0 || owner === currentPlayer;

      cells.push(
        <Cell
          key={idx}
          index={idx}
          owner={owner}
          count={count}
          critMass={critMass}
          isValid={isValid}
          isHumanTurn={isHumanTurn}
          onClick={onCellClick}
          exploding={explodingCells.has(idx)}
          rows={rows}
          cols={cols}
        />
      );
    }
  }

  const maxBoardSize = 560;
  const cellSize = Math.min(
    Math.floor(maxBoardSize / Math.max(rows, cols)),
    120
  );
  const gap = Math.max(2, Math.floor(cellSize * 0.06));

  return (
    <div className="flex items-center justify-center">
      <div
        className="grid"
        style={{
          gridTemplateColumns: `repeat(${cols}, ${cellSize}px)`,
          gridTemplateRows: `repeat(${rows}, ${cellSize}px)`,
          gap: `${gap}px`,
        }}
      >
        {cells}
      </div>
    </div>
  );
}
