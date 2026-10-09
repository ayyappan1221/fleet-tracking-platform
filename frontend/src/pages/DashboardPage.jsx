import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api.js';
import { errorMessage } from '../utils/errors.js';
import { decodeToken } from '../utils/auth.js';
import FleetMap from '../components/FleetMap.jsx';

const SEVERITY_CLASS = {
  info: 'severity-info',
  warning: 'severity-warning',
  critical: 'severity-critical',
};

function fmtNum(v, digits = 2) {
  if (v === null || v === undefined) return '—';
  const n = Number(v);
  return Number.isFinite(n) ? n.toFixed(digits) : '—';
}

function fmtPct(v) {
  if (v === null || v === undefined) return '—';
  const n = Number(v);
  if (!Number.isFinite(n)) return '—';
  const pct = Math.abs(n) <= 1 ? n * 100 : n;
  return `${pct.toFixed(0)}%`;
}

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 18) return 'Good afternoon';
  return 'Good evening';
}

function todayLabel() {
  return new Date().toLocaleDateString(undefined, {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

export default function DashboardPage() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState('');
  const [alerts, setAlerts] = useState([]);
  const [alertsError, setAlertsError] = useState('');
  const [vehicles, setVehicles] = useState([]);
  const [positions, setPositions] = useState({});
  const [geofences, setGeofences] = useState([]);
  const [report, setReport] = useState(null);

  const token = localStorage.getItem('token');
  const user = decodeToken(token);
  const displayName = user?.name || user?.sub || user?.email || 'there';

  useEffect(() => {
    api
      .get('/dashboard/summary', token)
      .then((res) => setStats(res.data.data))
      .catch((err) => setError(errorMessage(err, 'Failed to load dashboard summary.')));
  }, []);

  // Manager-only 30-day report — non-managers (403) or errors just show "—" on the KPI cards.
  useEffect(() => {
    api
      .get('/dashboard/report?days=30', token)
      .then((res) => setReport(res.data.data))
      .catch(() => setReport(null));
  }, [token]);

  useEffect(() => {
    api
      .get('/alerts/', token)
      .then((res) => {
        const list = res.data.data.alerts || [];
        setAlerts(list.slice(0, 5));
      })
      .catch((err) => setAlertsError(errorMessage(err, 'Could not load recent alerts.')));
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function loadFleet() {
      try {
        const vRes = await api.get('/vehicles/', token);
        const vList = vRes.data.data.vehicles || vRes.data.data.items || [];
        if (cancelled) return;
        setVehicles(vList);
        const slice = vList.slice(0, 20);
        const entries = await Promise.all(
          slice.map(async (v) => {
            try {
              const r = await api.get(`/locations/vehicle/${v.id}/latest`, token);
              const loc = r.data.data.location ?? r.data.data;
              if (loc) return [String(v.id), loc];
            } catch {
              return null;
            }
            return null;
          })
        );
        if (cancelled) return;
        const map = {};
        for (const e of entries) if (e) map[e[0]] = e[1];
        setPositions(map);
      } catch {
      }
      try {
        const gRes = await api.get('/geofences/', token);
        if (!cancelled) setGeofences(gRes.data.data.geofences || []);
      } catch {
      }
    }
    if (token) loadFleet();
    const id = window.setInterval(loadFleet, 30000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [token]);

  if (error) {
    return (
      <section className='panel'>
        <p className='error'>{error}</p>
      </section>
    );
  }

  if (!stats) {
    return (
      <section className='panel'>
        <p className='loading-line'>
          <span className='skeleton' />
          Loading dashboard…
        </p>
      </section>
    );
  }

  const cards = [
    { label: 'Total vehicles', value: stats.total_vehicles ?? 0, icon: '🚙', tone: '' },
    { label: 'Active vehicles', value: stats.active_vehicles ?? 0, icon: '●', tone: 'green' },
    { label: 'Total routes', value: stats.total_routes ?? 0, icon: '🗺', tone: 'blue' },
    { label: 'Active routes', value: stats.active_routes ?? 0, icon: '▶', tone: 'violet' },
    { label: 'Pending maintenance', value: stats.pending_maintenance ?? 0, icon: '🔧', tone: 'amber' },
    { label: 'Unread alerts', value: stats.unread_alerts ?? 0, icon: '!', tone: 'red' },
    { label: 'Geofences', value: stats.total_geofences ?? 0, icon: '⬡', tone: '' },
    { label: 'Cost / km', value: report ? fmtNum(report.cost_per_km) : '—', icon: '◉', tone: 'amber' },
    { label: 'Fuel cost (30d)', value: report ? fmtNum(report.fuel_cost_total, 0) : '—', icon: '⛽', tone: '' },
    { label: 'Utilization', value: report ? fmtPct(report.utilization) : '—', icon: '◔', tone: 'blue' },
    { label: 'On-time', value: report ? fmtPct(report.on_time_rate) : '—', icon: '✓', tone: 'green' },
  ];

  return (
    <>
      <header className='page-head'>
        <div>
          <h2 className='page-title'>
            {greeting()}, {displayName}
          </h2>
          <p className='page-sub greeting-date'>{todayLabel()}</p>
        </div>
        <div className='page-actions'>
          <Link to='/alerts' className='btn btn-ghost btn-sm'>
            View alerts
          </Link>
          <Link to='/vehicles' className='btn btn-sm'>
            Add vehicle
          </Link>
        </div>
      </header>

      <div className='stat-grid'>
        {cards.map((card) => (
          <article key={card.label} className='stat-card'>
            <div className='stat-top'>
              <span className={`stat-icon${card.tone ? ` ${card.tone}` : ''}`} aria-hidden='true'>
                {card.icon}
              </span>
            </div>
            <span className='stat-value'>{card.value}</span>
            <span className='stat-label'>{card.label}</span>
          </article>
        ))}
      </div>

      <section className='panel'>
        <h2>Live fleet map</h2>
        <p className='panel-sub'>Latest positions for up to 20 vehicles, refreshed every 30 seconds</p>
        <FleetMap vehicles={vehicles} latestPositions={positions} geofences={geofences} />
      </section>

      <div className='dash-columns'>
        <section className='panel'>
          <h2>Recent alerts</h2>
          <p className='panel-sub'>Latest activity across the fleet</p>
          {alertsError && <p className='error'>{alertsError}</p>}
          {!alertsError && alerts.length === 0 && (
            <p className='empty'>
              <strong>All clear</strong>
              No alerts yet. New geofence and severity events will show up here.
            </p>
          )}
          {alerts.length > 0 && (
            <ul className='alert-feed'>
              {alerts.map((a) => (
                <li key={a.id}>
                  <span
                    className={`severity-dot ${a.severity || 'info'}`}
                    aria-hidden='true'
                  />
                  <span className='msg'>
                    {a.message || a.type || 'Alert'}
                    <span className='meta'>
                      {a.severity || 'info'}
                      {a.vehicle_id != null ? ` · vehicle #${a.vehicle_id}` : ''}
                      {a.created_at ? ` · ${a.created_at}` : ''}
                      {a.is_read ? ' · read' : ' · unread'}
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className='panel'>
          <h2>Quick actions</h2>
          <p className='panel-sub'>Jump straight into common tasks</p>
          <div className='quick-actions'>
            <Link to='/vehicles' className='quick-action'>
              <span className='qa-icon' aria-hidden='true'>
                +
              </span>
              Add vehicle
            </Link>
            <Link to='/routes' className='quick-action'>
              <span className='qa-icon' aria-hidden='true'>
                ⇢
              </span>
              Plan route
            </Link>
            <Link to='/locations' className='quick-action'>
              <span className='qa-icon' aria-hidden='true'>
                ⚲
              </span>
              Record ping
            </Link>
            <Link to='/maintenance' className='quick-action'>
              <span className='qa-icon' aria-hidden='true'>
                🔧
              </span>
              Maintenance
            </Link>
            <Link to='/geofences' className='quick-action'>
              <span className='qa-icon' aria-hidden='true'>
                ⬡
              </span>
              Geofences
            </Link>
          </div>
        </section>
      </div>
    </>
  );
}
