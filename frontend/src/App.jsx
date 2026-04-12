import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import GameLab from './pages/GameLab';
import TournamentPage from './pages/TournamentPage';
import TrainingPage from './pages/TrainingPage';
import ReplayPage from './pages/ReplayPage';

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/game" element={<GameLab />} />
        <Route path="/tournament" element={<TournamentPage />} />
        <Route path="/training" element={<TrainingPage />} />
        <Route path="/replay/:gameId" element={<ReplayPage />} />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </Layout>
  );
}
