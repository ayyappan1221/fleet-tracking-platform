import { useState, useEffect } from 'react'
import api from '../api.js'

const inputStyle = {
  width: '100%',
  marginTop: '6px',
  padding: '10px',
  border: '1px solid #ccd2d9',
  borderRadius: '8px',
  fontSize: '14px',
}

const labelStyle = {
  display: 'block',
  fontSize: '13px',
  fontWeight: 600,
  marginBottom: '14px',
}

const selectStyle = {
  width: '100%',
  marginTop: '6px',
  padding: '10px',
  border: '1px solid #ccd2d9',
  borderRadius: '8px',
  fontSize: '14px',
  background: '#fff',
}

const btnSmall = {
  width: 'auto',
  padding: '6px 14px',
  fontSize: '13px',
  cursor: 'pointer',
}

const STATUSES = ['planned', 'in_progress', 'completed']

export default function RoutesPage() {
  const [routes, setRoutes] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [statusFilter, setStatusFilter] = useState('')

  // Plan form
  const [vehicleId, setVehicleId] = useState('')
  const [stops, setStops] = useState([
    { latitude: '', longitude: '' },
    { latitude: '', longitude: '' },
  ])

  const token = localStorage.getItem('token')

  const fetchRoutes = async () => {
    try {
      const res = await api.get('/routes/', token)
      setRoutes(res.data.data.routes)
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to load routes.')
    }
  }

  useEffect(() => {
    fetchRoutes()
  }, [])

  const handleAddStop = () => {
    setStops([...stops, { latitude: '', longitude: '' }])
  }

  const handleRemoveStop = (index) => {
    if (stops.length <= 2) return
    setStops(stops.filter((_, i) => i !== index))
  }

  const handleStopChange = (index, field, value) => {
    const updated = [...stops]
    updated[index] = { ...updated[index], [field]: value }
    setStops(updated)
  }

  const handlePlanRoute = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const payload = {
        vehicle_id: Number(vehicleId),
        stops: stops.map((s, i) => ({
          latitude: Number(s.latitude),
          longitude: Number(s.longitude),
          sequence: i + 1,
        })),
      }
      await api.post('/routes/', payload, token)
      setVehicleId('')
      setStops([
        { latitude: '', longitude: '' },
        { latitude: '', longitude: '' },
      ])
      fetchRoutes()
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to plan route.')
    } finally {
      setLoading(false)
    }
  }

  const handleStart = async (id) => {
    setError('')
    try {
      await api.post(`/routes/${id}/start`, {}, token)
      fetchRoutes()
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to start route.')
    }
  }

  const handleComplete = async (id) => {
    setError('')
    try {
      await api.post(`/routes/${id}/complete`, {}, token)
      fetchRoutes()
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to complete route.')
    }
  }

  const handleArrive = async (stopId) => {
    setError('')
    try {
      await api.post(`/routes/stops/${stopId}/arrive`, {}, token)
      fetchRoutes()
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to mark stop arrived.')
    }
  }

  const filtered = statusFilter
    ? routes.filter((r) => r.status === statusFilter)
    : routes

  return (
    <div className='panel'>
      <h2>Routes</h2>
      {error && <p className='error'>{error}</p>}

      {/* Plan Route Form */}
      <div style={{ marginBottom: '24px' }}>
        <h3 style={{ fontSize: '14px', marginBottom: '12px' }}>Plan New Route</h3>
        <form onSubmit={handlePlanRoute}>
          <label style={labelStyle}>
            Vehicle ID
            <input
              style={inputStyle}
              type='number'
              value={vehicleId}
              onChange={(e) => setVehicleId(e.target.value)}
              required
              min='1'
            />
          </label>

          <div style={{ marginBottom: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
              <strong style={{ fontSize: '13px' }}>Stops (min 2)</strong>
              <button
                type='button'
                onClick={handleAddStop}
                style={{ ...btnSmall, background: '#059669' }}
              >
                + Add Stop
              </button>
            </div>
            {stops.map((stop, i) => (
              <div key={i} style={{ display: 'flex', gap: '8px', alignItems: 'flex-end', marginBottom: '8px' }}>
                <label style={{ ...labelStyle, flex: 1, marginBottom: 0 }}>
                  Lat (-90 to 90)
                  <input
                    style={inputStyle}
                    type='number'
                    step='any'
                    min='-90'
                    max='90'
                    placeholder='e.g. 40.7128'
                    value={stop.latitude}
                    onChange={(e) => handleStopChange(i, 'latitude', e.target.value)}
                    required
                  />
                </label>
                <label style={{ ...labelStyle, flex: 1, marginBottom: 0 }}>
                  Lng (-180 to 180)
                  <input
                    style={inputStyle}
                    type='number'
                    step='any'
                    min='-180'
                    max='180'
                    placeholder='e.g. -74.0060'
                    value={stop.longitude}
                    onChange={(e) => handleStopChange(i, 'longitude', e.target.value)}
                    required
                  />
                </label>
                <span style={{ fontSize: '13px', color: '#6b7684', paddingBottom: '12px', minWidth: '30px' }}>
                  #{i + 1}
                </span>
                {stops.length > 2 && (
                  <button
                    type='button'
                    onClick={() => handleRemoveStop(i)}
                    style={{ ...btnSmall, background: '#b91c1c', paddingBottom: '12px' }}
                  >
                    Remove
                  </button>
                )}
              </div>
            ))}
          </div>

          <button type='submit' disabled={loading}>
            {loading ? 'Planning...' : 'Plan Route'}
          </button>
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

      {/* Routes Table */}
      {filtered.length === 0 ? (
        <p className='empty'>No routes found.</p>
      ) : (
        <table className='data-table'>
          <thead>
            <tr>
              <th>ID</th>
              <th>Vehicle</th>
              <th>Driver</th>
              <th>Status</th>
              <th>Stops</th>
              <th>Distance</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((route) => (
              <tr key={route.id}>
                <td>{route.id}</td>
                <td>{route.vehicle_id}</td>
                <td>{route.driver_id || '-'}</td>
                <td>{route.status}</td>
                <td>{route.stops?.length || 0}</td>
                <td>{route.distance_km} km</td>
                <td style={{ whiteSpace: 'nowrap' }}>
                  {route.status === 'planned' && (
                    <button
                      type='button'
                      style={{ ...btnSmall, background: '#d97706' }}
                      onClick={() => handleStart(route.id)}
                    >
                      Start
                    </button>
                  )}
                  {route.status === 'in_progress' && (
                    <>
                      {route.stops?.filter((s) => s.status === 'pending').map((stop) => (
                        <button
                          key={stop.id}
                          type='button'
                          style={{ ...btnSmall, background: '#0e7490', marginRight: '4px', marginBottom: '4px' }}
                          onClick={() => handleArrive(stop.id)}
                        >
                          Arrive #{stop.sequence}
                        </button>
                      ))}
                      <button
                        type='button'
                        style={{ ...btnSmall, background: '#059669', marginTop: '4px' }}
                        onClick={() => handleComplete(route.id)}
                      >
                        Complete
                      </button>
                    </>
                  )}
                  {route.status === 'completed' && (
                    <span style={{ fontSize: '13px', color: '#6b7684' }}>Done</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
