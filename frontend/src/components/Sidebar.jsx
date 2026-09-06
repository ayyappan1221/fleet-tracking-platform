import { NavLink, useNavigate } from 'react-router-dom';

const links = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/vehicles', label: 'Vehicles' },
  { to: '/routes', label: 'Routes' },
  { to: '/locations', label: 'Locations' },
  { to: '/maintenance', label: 'Maintenance' },
  { to: '/alerts', label: 'Alerts' },
  { to: '/geofences', label: 'Geofences' },
];

export default function Sidebar() {
  const navigate = useNavigate();

  const handleSignOut = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  return (
    <aside className="sidebar">
      <nav className="sidebar-nav">
        {links.map(({ to, label, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `sidebar-link${isActive ? ' active' : ''}`
            }
          >
            {label}
          </NavLink>
        ))}
      </nav>
      <button type="button" className="sidebar-signout" onClick={handleSignOut}>
        Sign out
      </button>
    </aside>
  );
}
