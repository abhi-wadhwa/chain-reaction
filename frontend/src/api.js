const BASE = '';

export async function fetchAgentTypes() {
  const res = await fetch(`${BASE}/api/agents/types`);
  return res.json();
}

export async function playGame(agent1, agent2, rows = 5, cols = 5) {
  const res = await fetch(`${BASE}/api/game/play`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ agent1, agent2, rows, cols }),
  });
  return res.json();
}

export async function startInteractiveGame(agent, rows = 5, cols = 5, humanPlayer = 1) {
  const res = await fetch(`${BASE}/api/game/play-interactive`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ agent, rows, cols, human_player: humanPlayer }),
  });
  return res.json();
}

export async function makeHumanMove(gameId, cell) {
  const res = await fetch(`${BASE}/api/game/${gameId}/move`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cell }),
  });
  return res.json();
}

export async function startTournament(agents, rows = 5, cols = 5, gamesPerPairing = 10) {
  const res = await fetch(`${BASE}/api/tournament/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ agents, rows, cols, games_per_pairing: gamesPerPairing }),
  });
  return res.json();
}

export async function getTournamentStatus(id) {
  const res = await fetch(`${BASE}/api/tournament/${id}/status`);
  return res.json();
}

export async function getTournamentResults(id) {
  const res = await fetch(`${BASE}/api/tournament/${id}/results`);
  return res.json();
}

export function connectTournamentWS(id, onMessage) {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const ws = new WebSocket(`${proto}//${window.location.host}/ws/tournament/${id}`);
  ws.onmessage = (e) => {
    const data = JSON.parse(e.data);
    if (data.type !== 'ping') onMessage(data);
  };
  return ws;
}

// ── Training API ────────────────────────────────────────────

export async function startTraining(config) {
  const res = await fetch(`${BASE}/api/training/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  return res.json();
}

export async function pauseTraining(id) {
  const res = await fetch(`${BASE}/api/training/${id}/pause`, { method: 'POST' });
  return res.json();
}

export async function resumeTraining(id) {
  const res = await fetch(`${BASE}/api/training/${id}/resume`, { method: 'POST' });
  return res.json();
}

export async function stopTraining(id) {
  const res = await fetch(`${BASE}/api/training/${id}/stop`, { method: 'POST' });
  return res.json();
}

export async function getTrainingStatus(id) {
  const res = await fetch(`${BASE}/api/training/${id}/status`);
  return res.json();
}

export async function getTrainingMetrics(id) {
  const res = await fetch(`${BASE}/api/training/${id}/metrics`);
  return res.json();
}

export async function getTrainingCheckpoints(id) {
  const res = await fetch(`${BASE}/api/training/${id}/checkpoints`);
  return res.json();
}

export function connectTrainingWS(id, onMessage) {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const ws = new WebSocket(`${proto}//${window.location.host}/ws/training/${id}`);
  ws.onmessage = (e) => {
    const data = JSON.parse(e.data);
    if (data.type !== 'ping') onMessage(data);
  };
  return ws;
}
