import { NavLink, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { decodeToken } from '../utils/auth.js';
import { backendHealth } from '../api.js';

const svg = {
  width: 16,
  height: 16,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
};

const ICONS = {
  dashboard: (
    <svg {...svg}>
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
    </svg>
  ),
  route: (
    <svg {...svg}>
      <path d="M3 11l19-9-9 19-2-8-8-2z" />
    </svg>
  ),
  truck: (
    <svg {...svg}>
      <path d="M3 7h11v9H3z" />
      <path d="M14 10h3.6l3.4 3.4V16H14z" />
      <circle cx="7" cy="18" r="2" />
      <circle cx="17.5" cy="18" r="2" />
    </svg>
  ),
  pin: (
    <svg {...svg}>
      <path d="M12 21s7-6.1 7-11a7 7 0 1 0-14 0c0 4.9 7 11 7 11z" />
      <circle cx="12" cy="10" r="2.5" />
    </svg>
  ),
  bell: (
    <svg {...svg}>
      <path d="M18 8a6 6 0 1 0-12 0c0 7-3 8-3 8h18s-3-1-3-8" />
      <path d="M13.73 21a2 2 0 0 1-3.46 0" />
    </svg>
  ),
  wrench: (
    <svg {...svg}>
      <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
    </svg>
  ),
  hexagon: (
    <svg {...svg}>
      <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
    </svg>
  ),
  flag: (
    <svg {...svg}>
      <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" />
      <path d="M4 22v-7" />
    </svg>
  ),
  drop: (
    <svg {...svg}>
      <path d="M12 2.7l5.7 5.7a8 8 0 1 1-11.4 0z" />
    </svg>
  ),
  clipboard: (
    <svg {...svg}>
      <path d="M9 3h6v3H9z" />
      <path d="M15 5h2a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h2" />
      <path d="M9 13l2 2 4-4" />
    </svg>
  ),
};

const SECTIONS = [
  {
    label: 'Operate',
    links: [
      { to: '/', label: 'Dashboard', end: true, ico: 'dashboard' },
      { to: '/routes', label: 'Routes', ico: 'route' },
      { to: '/vehicles', label: 'Vehicles', ico: 'truck' },
    ],
  },
  {
    label: 'Monitor',
    links: [
      { to: '/locations', label: 'Locations', ico: 'pin' },
      { to: '/alerts', label: 'Alerts', ico: 'bell' },
      { to: '/drivers', label: 'Drivers', ico: 'flag' },
      { to: '/fuel', label: 'Fuel', ico: 'drop' },
    ],
  },
  {
    label: 'Manage',
    links: [
      { to: '/maintenance', label: 'Maintenance', ico: 'wrench' },
      { to: '/inspections', label: 'Inspections', ico: 'clipboard' },
      { to: '/geofences', label: 'Geofences', ico: 'hexagon' },
    ],
  },
];

function userFromToken() {
  const token = localStorage.getItem('token');
  const payload = decodeToken(token);
  if (!payload) return { name: 'Signed in', role: 'user', initials: '?' };
  const raw =
    payload.name || payload.sub || payload.email || payload.username || 'Signed in';
  const name = String(raw).split('@')[0];
  const role = payload.role || 'user';
  const initials = name
    .split(/[\s._-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0])
    .join('');
  return { name, role, initials: initials || '?' };
}

export default function Sidebar({ open = false, onNavigate }) {
  const navigate = useNavigate();
  const user = userFromToken();
  const [backendUp, setBackendUp] = useState(null);

  useEffect(() => {
    let alive = true;
    backendHealth()
      .then(() => alive && setBackendUp(true))
      .catch(() => alive && setBackendUp(false));
    const id = window.setInterval(() => {
      backendHealth()
        .then(() => alive && setBackendUp(true))
        .catch(() => alive && setBackendUp(false));
    }, 60000);
    return () => {
      alive = false;
      window.clearInterval(id);
    };
  }, []);

  const handleSignOut = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  const go = () => {
    if (onNavigate) onNavigate();
  };

  return (
    <aside className={`sidebar${open ? ' open' : ''}`}>
      <div className="sidebar-brand">
        <span className="brand-logo" aria-hidden="true">
          F
        </span>
        <span className="brand-text">
          <span className="brand-name">Fleet Tracker</span>
          <span className="brand-status">
            <span className="pulse-dot" aria-hidden="true" />
            {backendUp === null ? 'Checking backend…' : backendUp ? 'Backend live' : 'Backend offline'}
          </span>
        </span>
      </div>

      {SECTIONS.map((section) => (
        <div key={section.label}>
          <div className="sidebar-section">{section.label}</div>
          <nav className="sidebar-nav" aria-label={section.label}>
            {section.links.map(({ to, label, end, ico }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                onClick={go}
                className={({ isActive }) =>
                  `sidebar-link${isActive ? ' active' : ''}`
                }
              >
                <span className="nav-ico" aria-hidden="true">
                  {ICONS[ico]}
                </span>
                {label}
              </NavLink>
            ))}
          </nav>
        </div>
      ))}

      <div className="sidebar-foot">
        <div className="user-card">
          <span className="avatar" aria-hidden="true">
            {user.initials}
          </span>
          <span className="user-meta">
            <span className="user-name" title={user.name}>
              {user.name}
            </span>
            <span
              className={`role-chip${user.role === 'manager' ? ' manager' : ''}${
                user.role === 'mechanic' ? ' mechanic' : ''
              }`}
            >
              {user.role}
            </span>
          </span>
        </div>
        <button
          type="button"
          className="btn btn-ghost btn-sm sidebar-signout"
          onClick={handleSignOut}
        >
          Sign out
        </button>
      </div>
    </aside>
  );
}
