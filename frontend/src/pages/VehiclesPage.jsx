import { useEffect, useState } from 'react';
import api from '../api.js';
import { errorMessage } from '../utils/errors.js';

const STATUS_BADGE = {
  active: 'badge-success',
  inactive: 'badge-muted',
  maintenance: 'badge-warn',
};

const EMPTY_FORM = {
  license_plate: '',
  make: '',
  model: '',
  year: '',
  vin: '',
};

export default function VehiclesPage() {
  const [vehicles, setVehicles] = useState([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [formOpen, setFormOpen] = useState(false);
  const [formError, setFormError] = useState('');
  const [formSuccess, setFormSuccess] = useState('');
  const [listError, setListError] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [saving, setSaving] = useState(false);
  const [confirmId, setConfirmId] = useState(null);

  const token = localStorage.getItem('token');

  useEffect(() => {
    fetchVehicles();
  }, []);

  async function fetchVehicles() {
    setListError('');
    try {
      const res = await api.get('/vehicles/', token);
      setVehicles(res.data.data.vehicles || []);
    } catch (err) {
      setListError(errorMessage(err, 'Failed to load vehicles.'));
    }
  }

  async function handleAddVehicle(e) {
    e.preventDefault();
    setFormError('');
    setFormSuccess('');
    setSaving(true);
    const payload = { ...form, year: form.year === '' ? null : Number(form.year) };
    try {
      await api.post('/vehicles/', payload, token);
      setForm(EMPTY_FORM);
      setFormOpen(false);
      setFormSuccess(`Vehicle ${payload.license_plate} added.`);
      fetchVehicles();
    } catch (err) {
      setFormError(errorMessage(err, 'Could not add vehicle.'));
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteVehicle(id) {
    setListError('');
    try {
      await api.del('/vehicles/' + id, token);
      setConfirmId(null);
      fetchVehicles();
    } catch (err) {
      setListError(errorMessage(err, 'Failed to delete vehicle.'));
    }
  }

  const query = search.trim().toLowerCase();
  const filtered = vehicles.filter((v) => {
    if (statusFilter !== 'all' && v.status !== statusFilter) return false;
    if (!query) return true;
    return [v.license_plate, v.make, v.model].some((field) =>
      String(field || '').toLowerCase().includes(query)
    );
  });

  return (
    <>
      <header className='page-head'>
        <div>
          <h2 className='page-title'>Vehicles</h2>
          <p className='page-sub'>
            {vehicles.length} in fleet · filter by status or add a new unit
          </p>
        </div>
        <div className='page-actions'>
          <button
            type='button'
            className='btn'
            onClick={() => {
              setFormOpen((o) => !o);
              setFormError('');
              setFormSuccess('');
            }}
            aria-expanded={formOpen}
          >
            {formOpen ? 'Close form' : 'Add vehicle'}
          </button>
        </div>
      </header>

      {formOpen && (
        <section className='panel'>
          <h2 className='panel-title'>Add vehicle</h2>
          <p className='panel-sub'>Plate is required; the rest helps with reports later.</p>
          {formError && <p className='error'>{formError}</p>}
          <form onSubmit={handleAddVehicle}>
            <div className='form-grid'>
              <label>
                License plate
                <input
                  aria-label='License plate'
                  placeholder='e.g. KA-01-AB-1234'
                  value={form.license_plate}
                  onChange={(e) => setForm({ ...form, license_plate: e.target.value })}
                  required
                />
              </label>
              <label>
                Make
                <input
                  aria-label='Make'
                  placeholder='e.g. Tata'
                  value={form.make}
                  onChange={(e) => setForm({ ...form, make: e.target.value })}
                />
              </label>
              <label>
                Model
                <input
                  aria-label='Model'
                  placeholder='e.g. Ace'
                  value={form.model}
                  onChange={(e) => setForm({ ...form, model: e.target.value })}
                />
              </label>
              <label>
                Year
                <input
                  aria-label='Year'
                  placeholder='e.g. 2022'
                  type='number'
                  min='1980'
                  max='2100'
                  value={form.year}
                  onChange={(e) => setForm({ ...form, year: e.target.value })}
                />
              </label>
              <label>
                VIN
                <input
                  aria-label='VIN'
                  placeholder='17-character VIN (optional)'
                  value={form.vin}
                  onChange={(e) => setForm({ ...form, vin: e.target.value })}
                />
              </label>
            </div>
            <div className='form-row' style={{ marginTop: '14px' }}>
              <button type='submit' className='btn' disabled={saving}>
                {saving ? 'Saving…' : 'Add vehicle'}
              </button>
              <button
                type='button'
                className='btn btn-ghost'
                onClick={() => setFormOpen(false)}
              >
                Cancel
              </button>
            </div>
          </form>
        </section>
      )}

      {formSuccess && <p className='success-note'>{formSuccess}</p>}

      <section className='panel'>
        <div className='filter-bar'>
          <label className='filter-label' htmlFor='vehicle-search'>
            Search
          </label>
          <input
            id='vehicle-search'
            type='search'
            placeholder='Plate, make, or model'
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label='Search vehicles by plate, make, or model'
          />
          <p className='filter-label'>Status</p>
          <select
            aria-label='Filter by vehicle status'
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value='all'>All statuses</option>
            <option value='active'>Active</option>
            <option value='inactive'>Inactive</option>
            <option value='maintenance'>Maintenance</option>
          </select>
          <span className='spacer' />
          <span className='filter-count'>
            Showing {filtered.length} of {vehicles.length}
          </span>
        </div>

        {listError && <p className='error'>{listError}</p>}

        {filtered.length === 0 ? (
          <p className='empty'>
            <strong>No vehicles found</strong>
            {query
              ? 'Try a different plate, make, or model.'
              : statusFilter === 'all'
              ? 'Add your first vehicle to start tracking.'
              : 'No vehicles match this status filter.'}
          </p>
        ) : (
          <div className='table-wrap'>
            <table className='data-table'>
              <thead>
                <tr>
                  <th>Plate</th>
                  <th>Make</th>
                  <th>Model</th>
                  <th>Year</th>
                  <th>VIN</th>
                  <th>Status</th>
                  <th aria-label='Actions' />
                </tr>
              </thead>
              <tbody>
                {filtered.map((v) => (
                  <tr key={v.id}>
                    <td className='cell-strong'>{v.license_plate}</td>
                    <td>{v.make || '—'}</td>
                    <td>{v.model || '—'}</td>
                    <td>{v.year || '—'}</td>
                    <td className='cell-muted'>{v.vin || '—'}</td>
                    <td>
                      <span className={`badge ${STATUS_BADGE[v.status] || 'badge-muted'}`}>
                        {v.status}
                      </span>
                    </td>
                    <td>
                      {confirmId === v.id ? (
                        <span className='row-actions'>
                          <button
                            type='button'
                            className='btn btn-danger btn-sm'
                            onClick={() => handleDeleteVehicle(v.id)}
                          >
                            Confirm delete
                          </button>
                          <button
                            type='button'
                            className='btn btn-ghost btn-sm'
                            onClick={() => setConfirmId(null)}
                          >
                            Keep
                          </button>
                        </span>
                      ) : (
                        <button
                          type='button'
                          className='btn btn-ghost btn-sm'
                          onClick={() => setConfirmId(v.id)}
                        >
                          Delete
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
