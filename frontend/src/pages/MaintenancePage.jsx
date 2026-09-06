import { useState, useEffect } from 'react';
import api from '../api';

const inputStyle = {
  width: '100%',
  marginTop: '6px',
  padding: '10px',
  border: '1px solid #ccd2d9',
  borderRadius: '8px',
  fontSize: '14px',
};

const labelStyle = {
  display: 'block',
  fontSize: '13px',
  fontWeight: 600,
  marginBottom: '14px',
};

const selectStyle = {
  width: '100%',
  marginTop: '6px',
  padding: '10px',
  border: '1px solid #ccd2d9',
  borderRadius: '8px',
  fontSize: '14px',
  background: '#fff',
};

const btnSmall = {
  width: 'auto',
  padding: '6px 14px',
  fontSize: '13px',
  cursor: 'pointer',
};

const TYPES = ['oil_change', 'tire', 'inspection', 'repair'];
const STATUSES = ['scheduled', 'in_progress', 'completed'];

export default function MaintenancePage() {
  const [records, setRecords] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Filter
  const [statusFilter, setStatusFilter] = useState('');

  // Create form
  const [vehicleId, setVehicleId] = useState('');
  const [type, setType] = useState('oil_change');
  const [status, setStatus] = useState('scheduled');
  const [dueMileage, setDueMileage] = useState('');
  const [notes, setNotes] = useState('');

  const token = localStorage.getItem('token');

  const fetchRecords = async () => {
    try {
      const res = await api.get('/maintenance/', token);
      setRecords(res.data.data.maintenance);
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to load maintenance records.');
    }
  };

  useEffect(() => {
    fetchRecords();
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const payload = {
        vehicle_id: Number(vehicleId),
        type,
        status,
      };
      if (dueMileage !== '') {
        payload.due_mileage = Number(dueMileage);
      }
      if (notes.trim()) {
        payload.notes = notes;
      }
      await api.post('/maintenance/', payload, token);
      setVehicleId('');
      setType('oil_change');
      setStatus('scheduled');
      setDueMileage('');
      setNotes('');
      fetchRecords();
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to create record.');
    } finally {
      setLoading(false);
    }
  };

  const handleStatusChange = async (id, newStatus) => {
    setError('');
    try {
      await api.patch(`/maintenance/${id}`, { status: newStatus }, token);
      fetchRecords();
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to update status.');
    }
  };

  const filtered = statusFilter
    ? records.filter((r) => r.status === statusFilter)
    : records;

  return (
    <div className='panel'>
      <h2>Maintenance</h2>
      {error && <p className='error'>{error}</p>}

      {/* Create Form */}
      <div style={{ marginBottom: '24px' }}>
        <h3 style={{ fontSize: '14px', marginBottom: '12px' }}>New Maintenance Record</h3>
        <form onSubmit={handleCreate} className='vehicle-form'>
          <label style={labelStyle}>
            Vehicle ID
            <input
              style={inputStyle}
              type='number'
              value={vehicleId}
              onChange={(e) => setVehicleId(e.target.value)}
              required
            />
          </label>
          <label style={labelStyle}>
            Type
            <select
              style={selectStyle}
              value={type}
              onChange={(e) => setType(e.target.value)}
            >
              {TYPES.map((t) => (
                <option key={t} value={t}>
                  {t.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                </option>
              ))}
            </select>
          </label>
          <label style={labelStyle}>
            Status
            <select
              style={selectStyle}
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                </option>
              ))}
            </select>
          </label>
          <label style={labelStyle}>
            Due Mileage
            <input
              style={inputStyle}
              type='number'
              value={dueMileage}
              onChange={(e) => setDueMileage(e.target.value)}
            />
          </label>
          <label style={labelStyle}>
            Notes
            <input
              style={inputStyle}
              type='text'
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </label>
          <div style={{ gridColumn: '1 / -1' }}>
            <button type='submit' disabled={loading}>
              {loading ? 'Creating...' : 'Create Record'}
            </button>
          </div>
        </form>
      </div>

      {/* Status Filter */}
      <div style={{ marginBottom: '20px', display: 'flex', gap: '8px', alignItems: 'center' }}>
        <strong style={{ fontSize: '13px' }}>Filter:</strong>
        <select
          style={{ ...selectStyle, width: 'auto', marginTop: 0 }}
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value=''>All Statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
            </option>
          ))}
        </select>
      </div>

      {/* Maintenance Table */}
      {filtered.length === 0 ? (
        <p className='empty'>No maintenance records found.</p>
      ) : (
        <table className='vehicles' style={{ width: '100%' }}>
          <thead>
            <tr>
              <th>ID</th>
              <th>Vehicle</th>
              <th>Type</th>
              <th>Status</th>
              <th>Due Mileage</th>
              <th>Notes</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((rec) => (
              <tr key={rec.id}>
                <td>{rec.id}</td>
                <td>{rec.vehicle_id}</td>
                <td>{rec.type}</td>
                <td>{rec.status}</td>
                <td>{rec.due_mileage != null ? rec.due_mileage : '-'}</td>
                <td>{rec.notes || '-'}</td>
                <td>
                  {rec.status === 'scheduled' && (
                    <button
                      type='button'
                      style={{ ...btnSmall, background: '#d97706' }}
                      onClick={() => handleStatusChange(rec.id, 'in_progress')}
                    >
                      Start
                    </button>
                  )}
                  {rec.status === 'in_progress' && (
                    <button
                      type='button'
                      style={{ ...btnSmall, background: '#059669' }}
                      onClick={() => handleStatusChange(rec.id, 'completed')}
                    >
                      Complete
                    </button>
                  )}
                  {rec.status === 'completed' && (
                    <span style={{ fontSize: '13px', color: '#6b7684' }}>Done</span>
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
