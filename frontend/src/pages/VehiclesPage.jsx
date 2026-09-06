import { useEffect, useState } from 'react'
import api from '../api.js'

export default function VehiclesPage() {
  const [vehicles, setVehicles] = useState([])
  const [form, setForm] = useState({
    license_plate: '',
    make: '',
    model: '',
    year: '',
    vin: '',
  })
  const [formError, setFormError] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')

  const token = localStorage.getItem('token')

  useEffect(() => {
    fetchVehicles()
  }, [])

  async function fetchVehicles() {
    try {
      const res = await api.get('/vehicles/', token)
      setVehicles(res.data.data.vehicles)
    } catch (err) {
      console.error(err)
    }
  }

  async function handleAddVehicle(e) {
    e.preventDefault()
    setFormError('')
    const payload = { ...form, year: Number(form.year) || null }
    try {
      await api.post('/vehicles/', payload, token)
      setForm({ license_plate: '', make: '', model: '', year: '', vin: '' })
      fetchVehicles()
    } catch (err) {
      setFormError(err.response?.data?.message || 'Could not add vehicle.')
    }
  }

  async function handleDeleteVehicle(id) {
    try {
      await api.del('/vehicles/' + id, token)
      fetchVehicles()
    } catch (err) {
      console.error(err)
    }
  }

  const filtered = statusFilter === 'all'
    ? vehicles
    : vehicles.filter((v) => v.status === statusFilter)

  return (
    <>
      <section className='panel'>
        <h2>Add vehicle</h2>
        <form className='vehicle-form' onSubmit={handleAddVehicle}>
          <input
            placeholder='License plate'
            value={form.license_plate}
            onChange={(e) => setForm({ ...form, license_plate: e.target.value })}
            required
          />
          <input
            placeholder='Make'
            value={form.make}
            onChange={(e) => setForm({ ...form, make: e.target.value })}
          />
          <input
            placeholder='Model'
            value={form.model}
            onChange={(e) => setForm({ ...form, model: e.target.value })}
          />
          <input
            placeholder='Year'
            type='number'
            value={form.year}
            onChange={(e) => setForm({ ...form, year: e.target.value })}
          />
          <input
            placeholder='VIN'
            value={form.vin}
            onChange={(e) => setForm({ ...form, vin: e.target.value })}
          />
          <button type='submit'>Add vehicle</button>
        </form>
        {formError && <p className='error'>{formError}</p>}
      </section>

      <section className='panel'>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <h2 style={{ margin: 0 }}>Vehicles</h2>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            style={{ padding: '8px 12px', borderRadius: '8px', border: '1px solid #ccd2d9', fontSize: '14px' }}
          >
            <option value='all'>All Statuses</option>
            <option value='active'>Active</option>
            <option value='inactive'>Inactive</option>
            <option value='maintenance'>Maintenance</option>
          </select>
        </div>
        {filtered.length === 0 ? (
          <p className='empty'>No vehicles found.</p>
        ) : (
          <table className='data-table'>
            <thead>
              <tr>
                <th>Plate</th>
                <th>Make</th>
                <th>Model</th>
                <th>Year</th>
                <th>VIN</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((v) => (
                <tr key={v.id}>
                  <td>{v.license_plate}</td>
                  <td>{v.make || '-'}</td>
                  <td>{v.model || '-'}</td>
                  <td>{v.year || '-'}</td>
                  <td>{v.vin || '-'}</td>
                  <td>{v.status}</td>
                  <td>
                    <button
                      type='button'
                      onClick={() => handleDeleteVehicle(v.id)}
                      style={{ width: 'auto', padding: '6px 12px', background: '#b91c1c', fontSize: '13px' }}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </>
  )
}
