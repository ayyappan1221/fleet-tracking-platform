import { useState, useEffect, useCallback } from 'react';
import api from '../api';

export default function AlertsPage() {
  const [alerts, setAlerts] = useState([]);
  const [severityFilter, setSeverityFilter] = useState('');
  const [readFilter, setReadFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const token = localStorage.getItem('token');

  const fetchAlerts = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.get('/alerts/', token);
      setAlerts(res.data.data.alerts);
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to load alerts.');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  const handleMarkRead = async (id) => {
    try {
      await api.patch('/alerts/' + id + '/read', {}, token);
      fetchAlerts();
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to mark alert as read.');
    }
  };

  const filtered = alerts.filter((a) => {
    if (severityFilter && a.severity !== severityFilter) return false;
    if (readFilter === 'read' && !a.is_read) return false;
    if (readFilter === 'unread' && a.is_read) return false;
    return true;
  });

  return (
    <div>
      <div className='tabs'>
        <button
          className={'tab' + (severityFilter === '' ? ' active' : '')}
          onClick={() => setSeverityFilter('')}
        >
          All
        </button>
        <button
          className={'tab' + (severityFilter === 'info' ? ' active' : '')}
          onClick={() => setSeverityFilter('info')}
        >
          Info
        </button>
        <button
          className={'tab' + (severityFilter === 'warning' ? ' active' : '')}
          onClick={() => setSeverityFilter('warning')}
        >
          Warning
        </button>
        <button
          className={'tab' + (severityFilter === 'critical' ? ' active' : '')}
          onClick={() => setSeverityFilter('critical')}
        >
          Critical
        </button>
      </div>

      <div style={{ marginBottom: '16px', display: 'flex', gap: '8px', alignItems: 'center' }}>
        <label style={{ margin: 0, fontSize: '13px', fontWeight: 600 }}>
          Read status:
          <select
            style={{
              marginLeft: '6px',
              padding: '6px 10px',
              border: '1px solid #ccd2d9',
              borderRadius: '6px',
              fontSize: '13px',
              background: '#fff',
            }}
            value={readFilter}
            onChange={(e) => setReadFilter(e.target.value)}
          >
            <option value=''>All</option>
            <option value='unread'>Unread</option>
            <option value='read'>Read</option>
          </select>
        </label>
      </div>

      {error && <p className='error'>{error}</p>}

      {loading ? (
        <p className='empty'>Loading alerts...</p>
      ) : filtered.length === 0 ? (
        <p className='empty'>No alerts found.</p>
      ) : (
        <table className='data-table'>
          <thead>
            <tr>
              <th>Vehicle</th>
              <th>Type</th>
              <th>Severity</th>
              <th>Message</th>
              <th>Read</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((a) => (
              <tr key={a.id} style={{ opacity: a.is_read ? 0.6 : 1 }}>
                <td>{a.vehicle || '-'}</td>
                <td>{a.type || '-'}</td>
                <td>
                  <span className={'severity-' + a.severity}>{a.severity}</span>
                </td>
                <td>{a.message}</td>
                <td>{a.is_read ? 'Yes' : 'No'}</td>
                <td>
                  {!a.is_read && (
                    <button
                      style={{
                        width: 'auto',
                        padding: '6px 12px',
                        fontSize: '13px',
                        background: '#334155',
                      }}
                      onClick={() => handleMarkRead(a.id)}
                    >
                      Mark read
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
