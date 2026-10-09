import { useState, useEffect, useCallback } from 'react'
import api from '../api.js'
import { errorMessage } from '../utils/errors.js'
import { downloadCsv } from '../utils/download.js'

function fmt(v, digits = 2) {
  if (v === null || v === undefined) return '—'
  const n = Number(v)
  return Number.isFinite(n) ? n.toFixed(digits) : String(v)
}

function vehicleLabel(v) {
  const plate = v.license_plate || v.plate || `#${v.id}`
  const model = [v.make, v.model].filter(Boolean).join(' ')
  return model ? `${plate} · ${model}` : plate
}

export default function FuelPage() {
  const [vehicles, setVehicles] = useState([])
  const [vehicleId, setVehicleId] = useState('')
  const [logs, setLogs] = useState([])
  const [total, setTotal] = useState(0)
  const [stats, setStats] = useState(null)
  const [fuelAlerts, setFuelAlerts] = useState([])
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [form, setForm] = useState({ liters: '', cost: '', odometer_km: '', note: '' })

  const token = localStorage.getItem('token')

  // Load vehicle list once
  useEffect(() => {
    let alive = true
    ;(async () => {
      try {
        const res = await api.get('/vehicles/', token)
        if (!alive) return
        const list = res.data.data.vehicles || []
        setVehicles(list)
        if (list.length > 0) setVehicleId(String(list[0].id))
      } catch (err) {
        if (alive) setError(errorMessage(err, 'Failed to load vehicles.'))
      }
    })()
    return () => {
      alive = false
    }
  }, [token])

  const fetchData = useCallback(async () => {
    if (!vehicleId) {
      setLogs([])
      setStats(null)
      setFuelAlerts([])
      setTotal(0)
      return
    }
    setLoading(true)
    setError('')
    try {
      const [logRes, effRes, alertRes] = await Promise.all([
        api.get(`/fuel/vehicle/${vehicleId}?skip=0&limit=50`, token),
        api.get(`/fuel/vehicle/${vehicleId}/efficiency`, token),
        api.get(`/alerts/?vehicle_id=${vehicleId}&skip=0&limit=50`, token),
      ])
      setLogs(logRes.data.data.fuel_logs || [])
      setTotal(logRes.data.data.total ?? 0)
      setStats(effRes.data.data)
      const alerts = alertRes.data.data.alerts || []
      setFuelAlerts(
        alerts.filter((a) => String(a.type || '').toLowerCase().includes('fuel'))
      )
    } catch (err) {
      setError(errorMessage(err, 'Failed to load fuel data for this vehicle.'))
      setLogs([])
      setStats(null)
      setFuelAlerts([])
    } finally {
      setLoading(false)
    }
  }, [vehicleId, token])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const flash = (msg) => {
    setSuccess(msg)
    window.setTimeout(() => setSuccess(''), 2500)
  }

  const handleLogFill = async (e) => {
    e.preventDefault()
    setError('')
    try {
      await api.post(
        '/fuel/',
        {
          vehicle_id: Number(vehicleId),
          liters: Number(form.liters),
          cost: form.cost === '' ? 0 : Number(form.cost),
          odometer_km: Number(form.odometer_km),
          note: form.note.trim() === '' ? null : form.note.trim(),
        },
        token
      )
      setForm({ liters: '', cost: '', odometer_km: '', note: '' })
      flash('Fuel fill logged.')
      fetchData()
    } catch (err) {
      setError(errorMessage(err, 'Failed to log fuel fill.'))
    }
  }

  const handleExport = async () => {
    setExporting(true)
    setError('')
    try {
      await downloadCsv(
        '/reports/fuel.csv',
        `fuel-vehicle-${vehicleId}.csv`,
        token,
        vehicleId ? { vehicle_id: Number(vehicleId) } : undefined
      )
      flash('Fuel CSV downloaded.')
    } catch (err) {
      setError(err.message || 'Fuel CSV export failed.')
    } finally {
      setExporting(false)
    }
  }

  const selected = vehicles.find((v) => String(v.id) === String(vehicleId))

  return (
    <div>
      <div className='page-head'>
        <div>
          <h2 className='page-title'>Fuel</h2>
          <p className='page-sub'>
            Log fill-ups and track fuel efficiency (km/L, cost per km) per vehicle.
          </p>
        </div>
        <div className='page-actions'>
          <button
            type='button'
            className='btn btn-sm btn-ghost'
            onClick={handleExport}
            disabled={exporting || !vehicleId}
            aria-label='Download fuel report as CSV'
          >
            {exporting ? 'Preparing…' : 'Export CSV'}
          </button>
          <button type='button' className='btn btn-sm btn-ghost' onClick={fetchData} disabled={loading}>
            {loading ? 'Refreshing…' : 'Refresh'}
          </button>
        </div>
      </div>

      {error && <p className='error'>{error}</p>}
      {success && <p className='success-note'>{success}</p>}

      {/* Vehicle selector */}
      <div className='panel'>
        <div className='filter-bar'>
          <label className='filter-label' htmlFor='fuel-vehicle'>
            Vehicle
          </label>
          <select
            id='fuel-vehicle'
            value={vehicleId}
            onChange={(e) => setVehicleId(e.target.value)}
            aria-label='Select vehicle for fuel logs'
            style={{ maxWidth: 280 }}
          >
            {vehicles.length === 0 && <option value=''>No vehicles yet</option>}
            {vehicles.map((v) => (
              <option key={v.id} value={String(v.id)}>
                {vehicleLabel(v)}
              </option>
            ))}
          </select>
          <span className='spacer' />
          <span className='filter-count'>
            {vehicleId ? `${total} fill${total === 1 ? '' : 's'} recorded` : 'Select a vehicle'}
          </span>
        </div>
      </div>

      {/* Efficiency drop warning (server-detected) */}
      {fuelAlerts.length > 0 && (
        <p className='error' role='status'>
          ⚠ {fuelAlerts[0].message ||
            'Efficiency drop detected for this vehicle — latest km/L is more than 20% below the prior average.'}
        </p>
      )}

      {/* Stat cards */}
      <div className='stat-grid'>
        <div className='stat-card'>
          <span className='stat-label'>Fuel efficiency</span>
          <strong className='stat-value'>{stats ? fmt(stats.km_per_liter, 1) : '—'}</strong>
          <span className='stat-hint'>km per liter</span>
        </div>
        <div className='stat-card'>
          <span className='stat-label'>Fuel cost per km</span>
          <strong className='stat-value'>{stats ? fmt(stats.cost_per_km, 2) : '—'}</strong>
          <span className='stat-hint'>currency units / km</span>
        </div>
        <div className='stat-card'>
          <span className='stat-label'>Total fuel</span>
          <strong className='stat-value'>{stats ? fmt(stats.total_liters, 1) : '—'}</strong>
          <span className='stat-hint'>liters across {stats ? stats.fills : 0} fills</span>
        </div>
        <div className='stat-card'>
          <span className='stat-label'>Total fuel cost</span>
          <strong className='stat-value'>{stats ? fmt(stats.total_cost, 2) : '—'}</strong>
          <span className='stat-hint'>
            over {stats ? fmt(stats.total_km, 0) : '0'} km
          </span>
        </div>
      </div>

      {/* Log a fill-up */}
      <div className='panel'>
        <p className='panel-title'>Log a fill-up</p>
        <p className='panel-sub'>
          Odometer reading is required — efficiency is computed from odometer deltas between fills.
        </p>
        {!vehicleId ? (
          <p className='empty'>
            <strong>No vehicle selected</strong>
            Add a vehicle first, then log fills here.
          </p>
        ) : (
          <form onSubmit={handleLogFill}>
            <div className='form-grid'>
              <label>
                Liters
                <input
                  type='number'
                  step='any'
                  min='0.01'
                  required
                  placeholder='e.g. 45.2'
                  value={form.liters}
                  onChange={(e) => setForm({ ...form, liters: e.target.value })}
                  aria-label='Liters refueled'
                />
              </label>
              <label>
                Cost (optional)
                <input
                  type='number'
                  step='any'
                  min='0'
                  placeholder='e.g. 70.50'
                  value={form.cost}
                  onChange={(e) => setForm({ ...form, cost: e.target.value })}
                  aria-label='Fuel cost'
                />
              </label>
              <label>
                Odometer (km)
                <input
                  type='number'
                  step='any'
                  min='0'
                  required
                  placeholder='e.g. 152430'
                  value={form.odometer_km}
                  onChange={(e) => setForm({ ...form, odometer_km: e.target.value })}
                  aria-label='Odometer reading in kilometers'
                />
              </label>
              <label>
                Note (optional)
                <input
                  type='text'
                  maxLength={2000}
                  placeholder='e.g. Shell A3 highway'
                  value={form.note}
                  onChange={(e) => setForm({ ...form, note: e.target.value })}
                  aria-label='Fuel fill note'
                />
              </label>
            </div>
            <button type='submit' className='btn' disabled={loading}>
              Save fill-up
            </button>
          </form>
        )}
      </div>

      {/* Fill history */}
      <div className='panel'>
        <p className='panel-title'>Fill history{selected ? ` — ${vehicleLabel(selected)}` : ''}</p>
        <p className='panel-sub'>Most recent 50 fills for the selected vehicle.</p>

        {logs.length === 0 ? (
          <p className='empty'>
            <strong>No fuel fills yet</strong>
            {loading
              ? 'Loading…'
              : 'Log the first fill-up above — efficiency stats appear once two fills exist.'}
          </p>
        ) : (
          <div className='data-table-wrap'>
            <table className='data-table'>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Liters</th>
                  <th>Cost</th>
                  <th>Odometer (km)</th>
                  <th>Note</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((l) => (
                  <tr key={l.id}>
                    <td className='cell-muted'>{l.filled_at ?? '—'}</td>
                    <td className='cell-strong'>{fmt(l.liters, 2)} L</td>
                    <td>{l.cost != null ? fmt(l.cost, 2) : '—'}</td>
                    <td>{fmt(l.odometer_km, 0)}</td>
                    <td className='cell-muted'>{l.note || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
