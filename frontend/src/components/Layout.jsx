import { NavLink } from 'react-router-dom';
import { Home, FlaskConical, Trophy, Brain, Play } from 'lucide-react';

const navItems = [
  { to: '/', icon: Home, label: 'Dashboard' },
  { to: '/game', icon: FlaskConical, label: 'Game Lab' },
  { to: '/tournament', icon: Trophy, label: 'Tournament' },
  { to: '/training', icon: Brain, label: 'Training' },
];

export default function Layout({ children }) {
  return (
    <div className="flex h-screen overflow-hidden bg-[var(--color-bg)]">
      {/* Sidebar */}
      <nav className="w-16 flex flex-col items-center py-6 gap-6 border-r border-[var(--color-border)] bg-[var(--color-bg-card)]">
        <div className="w-8 h-8 rounded-lg bg-[var(--color-cyan)] flex items-center justify-center mb-4">
          <Play size={16} className="text-black" fill="black" />
        </div>
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `w-10 h-10 rounded-lg flex items-center justify-center transition-all duration-200 ${
                isActive
                  ? to === '/training'
                    ? 'bg-[#00ff88]/20 text-[#00ff88]'
                    : 'bg-[var(--color-cyan)]/20 text-[var(--color-cyan)]'
                  : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-white/5'
              }`
            }
            title={label}
          >
            <Icon size={20} />
          </NavLink>
        ))}
      </nav>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  );
}
