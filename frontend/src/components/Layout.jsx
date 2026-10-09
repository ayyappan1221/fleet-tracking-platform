import { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';

const TITLES = [
  { path: '/', title: 'Dashboard', sub: 'Fleet overview' },
  { path: '/vehicles', title: 'Vehicles', sub: 'Fleet inventory' },
  { path: '/routes', title: 'Routes', sub: 'Trips & stops' },
  { path: '/locations', title: 'Locations', sub: 'GPS pings' },
  { path: '/maintenance', title: 'Maintenance', sub: 'Service records' },
  { path: '/alerts', title: 'Alerts', sub: 'Notifications' },
  { path: '/drivers', title: 'Drivers', sub: 'Leaderboard' },
  { path: '/fuel', title: 'Fuel', sub: 'Fills & efficiency' },
  { path: '/inspections', title: 'Inspections', sub: 'Pre & post trip checks' },
  { path: '/geofences', title: 'Geofences', sub: 'Zones & boundaries' },
];

function resolveMeta(pathname) {
  return TITLES.find((t) => t.path === pathname) || { title: 'Fleet Tracker', sub: '' };
}

export default function Layout() {
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();
  const meta = resolveMeta(location.pathname);

  return (
    <div className="layout">
      <Sidebar open={menuOpen} onNavigate={() => setMenuOpen(false)} />
      <div className="main-wrapper">
        <header className="topbar">
          <div className="topbar-left">
            <button
              type="button"
              className="btn btn-ghost btn-sm menu-btn"
              aria-label="Toggle navigation menu"
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen((v) => !v)}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <div className="topbar-heading">
              <h1 className="topbar-title">{meta.title}</h1>
              {meta.sub ? <div className="topbar-sub">{meta.sub}</div> : null}
            </div>
          </div>
          <div className="topbar-right">
            <span className="badge badge-brand" aria-hidden="true">
              Live fleet
            </span>
          </div>
        </header>
        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
