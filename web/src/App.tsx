import React from 'react';
import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom';
import { PlaySquare, BarChart3, Compass, Crosshair } from 'lucide-react';
import { Analyze } from './pages/Analyze';
import { Results } from './pages/Results';
import { Explorer } from './pages/Explorer';
import { Dossier } from './pages/Dossier';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <div className="app-container">
        {/* Top Command Bar */}
        <header className="header">
          <div className="brand">
            <span className="brand-title">DRISHTI</span>
            <span className="brand-badge">AERIAL INTELLIGENCE CONSOLE</span>
          </div>

          <nav className="nav-links">
            <NavLink
              to="/analyze"
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              <PlaySquare size={16} />
              <span>Analyze</span>
            </NavLink>
            <NavLink
              to="/results"
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              <BarChart3 size={16} />
              <span>Results</span>
            </NavLink>
            <NavLink
              to="/explorer"
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              <Compass size={16} />
              <span>Run Explorer</span>
            </NavLink>
            <NavLink
              to="/dossier"
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              <Crosshair size={16} />
              <span>Object Dossier</span>
            </NavLink>
          </nav>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                backgroundColor: 'var(--ok)',
                boxShadow: '0 0 8px var(--ok)',
              }}
            />
            <span className="mono" style={{ fontSize: '0.72rem', color: 'var(--muted)' }}>
              SYSTEM READY
            </span>
          </div>
        </header>

        {/* Main Content Area */}
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Navigate to="/analyze" replace />} />
            <Route path="/analyze" element={<Analyze />} />
            <Route path="/results" element={<Results />} />
            <Route path="/explorer" element={<Explorer />} />
            <Route path="/dossier" element={<Dossier />} />
            <Route path="*" element={<Navigate to="/analyze" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
};

export default App;
