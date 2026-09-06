import { useState, useEffect, useCallback } from 'react';
import api from '../api';

export default function GeofencesPage() {
  const [geofences, setGeofences] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [formName, setFormName] = useState('');
  const [formType, setFormType] = useState('inclusion');
  const [formCoords, setFormCoords] = useState('');
  const [formActive, setFormActive] = useState(true);

  const [editId, setEditId] = useState(null);
  const [editName, setEditName] = useState('');

  const token = localStorage.getItem('token');

  const fetchGeofences = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.get('/geofences/', token);
      setGeofences(res.data.data.geofences);
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to load geofences.');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchGeofences();
  }, [fetchGeofences]);

  const handleAdd = async (e) => {
    e.preventDefault();
    setError('');
    let coords;
    try {
      coords = JSON.parse(formCoords);
    } catch {
      setError('Coordinates must be valid JSON.');
      return;
    }
    try {
      await api.post('/geofences/', {
        name: formName,
        type: formType,
        coordinates: coords,
        is_active: formActive,
      }, token);
      setFormName('');
      setFormType('inclusion');
      setFormCoords('');
      setFormActive(true);
      fetchGeofences();
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to add geofence.');
    }
  };

  const handleUpdate = async (id) => {
    setError('');
    try {
      await api.patch('/geofences/' + id, { name: editName }, token);
      setEditId(null);
      setEditName('');
      fetchGeofences();
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to update geofence.');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this geofence?')) return;
    setError('');
    try {
      await api.del('/geofences/' + id, token);
      fetchGeofences();
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to delete geofence.');
    }
  };

  const inputStyle = {
    width: '100%',
    marginTop: '6px',
    padding: '10px',
    border: '1px solid #ccd2d9',
    borderRadius: '8px',
    fontSize: '14px',
  };

  return (
    <div>
      <section className='panel'>
        <h2>Add geofence</h2>
        <form onSubmit={handleAdd} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '10px' }}>
          <label>
            Name
            <input
              style={inputStyle}
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              required
            />
          </label>
          <label>
            Type
            <select
              style={{ ...inputStyle, background: '#fff' }}
              value={formType}
              onChange={(e) => setFormType(e.target.value)}
            >
              <option value='inclusion'>Inclusion</option>
              <option value='exclusion'>Exclusion</option>
            </select>
          </label>
          <label style={{ gridColumn: 'span 2' }}>
            Coordinates (JSON)
            <textarea
              style={{ ...inputStyle, minHeight: '60px', fontFamily: 'monospace' }}
              value={formCoords}
              onChange={(e) => setFormCoords(e.target.value)}
              placeholder='[[lat, lng], [lat, lng], ...]'
              required
            />
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '24px' }}>
            <input
              type='checkbox'
              checked={formActive}
              onChange={(e) => setFormActive(e.target.checked)}
            />
            Active
          </label>
          <div style={{ gridColumn: '1 / -1' }}>
            <button type='submit' style={{ width: 'auto', padding: '10px 20px' }}>Add geofence</button>
          </div>
        </form>
      </section>

      {error && <p className='error'>{error}</p>}

      <section className='panel'>
        <h2>Geofences</h2>
        {loading ? (
          <p className='empty'>Loading geofences...</p>
        ) : geofences.length === 0 ? (
          <p className='empty'>No geofences configured.</p>
        ) : (
          <table className='data-table'>
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Coordinates</th>
                <th>Active</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {geofences.map((g) => (
                <tr key={g.id}>
                  <td>
                    {editId === g.id ? (
                      <div style={{ display: 'flex', gap: '6px' }}>
                        <input
                          style={{ ...inputStyle, margin: 0 }}
                          value={editName}
                          onChange={(e) => setEditName(e.target.value)}
                        />
                        <button
                          style={{ width: 'auto', padding: '6px 10px', fontSize: '13px', margin: 0 }}
                          onClick={() => handleUpdate(g.id)}
                        >
                          Save
                        </button>
                        <button
                          style={{ width: 'auto', padding: '6px 10px', fontSize: '13px', margin: 0, background: '#6b7684' }}
                          onClick={() => { setEditId(null); setEditName(''); }}
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      g.name
                    )}
                  </td>
                  <td>{g.type}</td>
                  <td style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {typeof g.coordinates === 'string' ? g.coordinates : JSON.stringify(g.coordinates)}
                  </td>
                  <td>{g.is_active ? 'Yes' : 'No'}</td>
                  <td>
                    {editId !== g.id && (
                      <div style={{ display: 'flex', gap: '6px' }}>
                        <button
                          style={{ width: 'auto', padding: '6px 10px', fontSize: '13px', margin: 0 }}
                          onClick={() => { setEditId(g.id); setEditName(g.name); }}
                        >
                          Edit
                        </button>
                        <button
                          style={{ width: 'auto', padding: '6px 10px', fontSize: '13px', margin: 0, background: '#b91c1c' }}
                          onClick={() => handleDelete(g.id)}
                        >
                          Delete
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
