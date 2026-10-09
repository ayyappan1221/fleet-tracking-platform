import { useState, useEffect, useCallback, useRef } from 'react'
import api from '../api.js'
import { errorMessage } from '../utils/errors.js'
import { downloadCsv } from '../utils/download.js'
import FleetMap from '../components/FleetMap.jsx'

const POLL_MS = 30000
const PAGE_SIZE = 20
const DAY_MS = 86400000

function fmt(v, digits = 2) {
  if (v === null || v === undefined) return '—'
  const n = Number(v)
  return Number.isFinite(n) ? n.toFixed(digits) : String(v)
}

function isoDay(d) {
  return d.toISOString().slice(0, 10)
}

function lastNDates(n) {
  const out = []
  const now = Date.now()
  for (let i = n - 1; i >= 0; i--) out.push(isoDay(new Date(now - i * DAY_MS)))
  return out
}

function daysInSpan(fromStr, toStr) {
  const from = Date.parse(`${fromStr}T00:00:00`)
  const to = Date.parse(`${toStr}T00:00:00`)
  if (!Number.isFinite(from) || !Number.isFinite(to)) return 7
  return Math.min(365, Math.max(1, Math.round((to - from) / DAY_MS) + 1))
}

function vehicleLabel(v) {
  const plate = v.license_plate || v.plate || `#${v.id}`
  const model = [v.make, v.model].filter(Boolean).join(' ')
  return model ? `${plate} · ${model}` : plate
}

export default function LocationsPage() {
  const [locations, setLocations] = useState([])
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)
  const [skip, setSkip] = useState(0)
  const [hasMore, setHasMore] = useState(false)
  const [latestVehicleId, setLatestVehicleId] = useState('')
  const [latest, setLatest] = useState(null)
  const [latestError, setLatestError] = useState('')
  const [ping, setPing] = useState({ vehicle_id: '', latitude: '', longitude: '', speed: '', heading: '' })
  const [rangeFrom, setRangeFrom] = useState(() => isoDay(new Date(Date.now() - 6 * DAY_MS)))
  const [rangeTo, setRangeTo] = useState(() => isoDay(new Date()))
  const [exporting, setExporting] = useState(false)
  const [vehicles, setVehicles] = useState([])
  const [idleVehicleId, setIdleVehicleId] = useState('')
  const [idle, setIdle] = useState([])
  const [idleError, setIdleError] = useState('')

  const token = localStorage.getItem('token')
  const mounted = useRef(false)

  const fetchPage = useCallback(
    async (from = 0) => {
      setLoading(true)
      setError('')
      try {
        const res = await api.get(`/locations/?skip=${from}&limit=${PAGE_SIZE}`, token)
        const payload = res.data.data
        const list = payload.locations || payload.items || []
        setLocations(from === 0 ? list : (prev) => [...prev, ...list])
        setSkip(from + list.length)
        setHasMore(list.length === PAGE_SIZE)
      } catch (err) {
        setError(errorMessage(err, 'Failed to load locations.'))
      } finally {
        setLoading(false)
      }
    },
    [token]
  )

  useEffect(() => {
    fetchPage(0)
    const id = window.setInterval(() => fetchPage(0), POLL_MS)
    return () => window.clearInterval(id)
  }, [fetchPage])

  useEffect(() => {
    let alive = true
    api
      .get('/vehicles/', token)
      .then((res) => {
        if (!alive) return
        const list = res.data.data.vehicles || []
        setVehicles(list)
        if (list.length > 0) setIdleVehicleId((prev) => prev || String(list[0].id))
      })
      .catch(() => {
        if (alive) setVehicles([])
      })
    return () => {
      alive = false
    }
  }, [token])

  useEffect(() => {
    if (!idleVehicleId) {
      setIdle([])
      return
    }
    let alive = true
    ;(async () => {
      try {
        const res = await api.get(
          `/locations/vehicle/${idleVehicleId}/idle-days?days=7`,
          token
        )
        if (!alive) return
        const payload = res.data.data
        setIdle(Array.isArray(payload) ? payload : payload?.days || [])
        setIdleError('')
      } catch (err) {
        if (!alive) return
        setIdle([])
        setIdleError(errorMessage(err, 'Could not load idle time for that vehicle.'))
      }
    })()
    return () => {
      alive = false
    }
  }, [idleVehicleId, token])

  const flash = (msg) => {
    setSuccess(msg)
    window.setTimeout(() => setSuccess(''), 2500)
  }

  const handleRefresh = () => {
    setSkip(0)
    fetchPage(0)
  }

  const handleLoadMore = () => {
    fetchPage(skip)
  }

  const handleLatest = async (e) => {
    e.preventDefault()
    setLatestError('')
    setLatest(null)
    try {
      const res = await api.get(`/locations/vehicle/${latestVehicleId}/latest`, token)
      const payload = res.data.data
      setLatest(payload.location ?? payload)
    } catch (err) {
      setLatestError(errorMessage(err, 'No location found for that vehicle.'))
    }
  }

  const handlePing = async (e) => {
    e.preventDefault()
    setError('')
    try {
      await api.post(
        '/locations/',
        {
          vehicle_id: Number(ping.vehicle_id),
          latitude: Number(ping.latitude),
          longitude: Number(ping.longitude),
          speed: ping.speed === '' ? null : Number(ping.speed),
          heading: ping.heading === '' ? null : Number(ping.heading),
        },
        token
      )
      setPing({ vehicle_id: '', latitude: '', longitude: '', speed: '', heading: '' })
      flash('Location ping saved.')
      handleRefresh()
    } catch (err) {
      setError(errorMessage(err, 'Failed to save location ping.'))
    }
  }

  const handleExport = async () => {
    const days = daysInSpan(rangeFrom, rangeTo)
    setExporting(true)
    setError('')
    try {
      await downloadCsv(
        '/reports/locations.csv',
        `locations-last-${days}d.csv`,
        token,
        { days }
      )
      flash('Locations CSV downloaded.')
    } catch (err) {
      setError(err.message || 'Locations CSV export failed.')
    } finally {
      setExporting(false)
    }
  }

  // Deduplicate latest ping per vehicle
  const latestByVehicle = new Map()
  for (const loc of locations) {
    if (!latestByVehicle.has(loc.vehicle_id)) {
      latestByVehicle.set(loc.vehicle_id, loc)
    }
  }
  const uniqueLocations = [...latestByVehicle.values()]

  const rangeDays = daysInSpan(rangeFrom, rangeTo)
  const idleByDate = new Map(
    idle.map((d) => [String(d.date || '').slice(0, 10), Number(d.idle_minutes) || 0])
  )
  const idleBars = lastNDates(7).map((date) => ({
    date,
    minutes: idleByDate.get(date) ?? 0,
  }))
  const idleMax = Math.max(1, ...idleBars.map((b) => b.minutes))
  const idleTotal = idleBars.reduce((sum, b) => sum + b.minutes, 0)

  return (
    <div>
      <div className='page-head'>
        <div>
          <h2 className='page-title'>Locations</h2>
          <p className='page-sub'>Live and recent GPS pings across the fleet. Refreshes every 30 seconds.</p>
        </div>
        <div className='page-actions'>
          <button
            type='button'
            className='btn btn-sm btn-ghost'
            onClick={handleExport}
            disabled={exporting}
            aria-label='Download locations CSV for selected date range'
          >
            {exporting ? 'Preparing…' : 'Export CSV'}
          </button>
          <button type='button' className='btn btn-sm btn-ghost' onClick={handleRefresh} disabled={loading}>
            {loading ? 'Refreshing…' : 'Refresh'}
          </button>
        </div>
      </div>

      {error && <p className='error'>{error}</p>}
      {success && <p className='success-note'>{success}</p>}

      <div className='stat-grid'>
        <div className='stat-card'>
          <span className='stat-label'>Latest ping (unfiltered)</span>
          <strong className='stat-value'>{locations.length}</strong>
          <span className='stat-hint'>rows loaded</span>
        </div>
        <div className='stat-card'>
          <span className='stat-label'>Vehicles with pings</span>
          <strong className='stat-value'>{uniqueLocations.length}</strong>
          <span className='stat-hint'>unique in this page</span>
        </div>
      </div>

      <div className='panel'>
        <p className='panel-title'>Date range</p>
        <p className='panel-sub'>
          CSV export covers the last {rangeDays} day{rangeDays === 1 ? '' : 's'} ending today
          (the backend accepts a trailing days window).
        </p>
        <div className='filter-bar'>
          <label className='filter-label' htmlFor='loc-from'>
            From
          </label>
          <input
            id='loc-from'
            type='date'
            value={rangeFrom}
            max={rangeTo}
            onChange={(e) => setRangeFrom(e.target.value)}
            aria-label='Export range start'
          />
          <label className='filter-label' htmlFor='loc-to'>
            To
          </label>
          <input
            id='loc-to'
            type='date'
            value={rangeTo}
            min={rangeFrom}
            max={isoDay(new Date())}
            onChange={(e) => setRangeTo(e.target.value)}
            aria-label='Export range end'
          />
          <span className='spacer' />
          <span className='filter-count'>{rangeDays}-day window</span>
        </div>
      </div>

      <div className='panel'>
        <p className='panel-title'>Idle time — last 7 days</p>
        <p className='panel-sub'>
          Idle minutes per day for the selected vehicle. Days without idle events show 0.
        </p>
        <div className='filter-bar'>
          <label className='filter-label' htmlFor='idle-vehicle'>
            Vehicle
          </label>
          <select
            id='idle-vehicle'
            value={idleVehicleId}
            onChange={(e) => setIdleVehicleId(e.target.value)}
            aria-label='Select vehicle for idle time strip'
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
            {idleTotal > 0
              ? `${idleTotal} idle min total`
              : idleVehicleId
                ? 'No idle events this week'
                : ''}
          </span>
        </div>
        {idleError && <p className='error'>{idleError}</p>}
        {!idleVehicleId ? (
          <p className='empty'>
            <strong>No vehicle selected</strong>
            Add a vehicle to see idle-time trends.
          </p>
        ) : (
          <div
            style={{ display: 'flex', alignItems: 'flex-end', gap: 12, marginTop: 12 }}
            role='img'
            aria-label={`Idle minutes per day for the last 7 days, total ${idleTotal} minutes`}
          >
            {idleBars.map((b) => (
              <div
                key={b.date}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: 4,
                  flex: 1,
                }}
              >
                <span style={{ fontSize: 11, color: 'var(--ink, #2b2620)' }}>{b.minutes}</span>
                <div
                  style={{
                    width: '100%',
                    maxWidth: 40,
                    minHeight: 3,
                    height: Math.max(3, Math.round((b.minutes / idleMax) * 72)),
                    background: b.minutes > 0 ? 'var(--honey, #b98a1f)' : '#d9d2c4',
                    borderRadius: '4px 4px 0 0',
                  }}
                />
                <span style={{ fontSize: 11, color: 'var(--ink, #2b2620)', opacity: 0.7 }}>
                  {b.date.slice(5)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className='panel'>
        <p className='panel-title'>Live track</p>
        <p className='panel-sub'>Latest ping per vehicle from the current page.</p>
        <FleetMap
          vehicles={[]}
          latestPositions={Object.fromEntries(uniqueLocations.map((l) => [String(l.vehicle_id), l]))}
          geofences={[]}
        />
      </div>

      {/* Latest lookup */}
      <div className='panel'>
        <p className='panel-title'>Latest ping for a vehicle</p>
        <p className='panel-sub'>Enter a vehicle id to see its most recent recorded position.</p>
        <form onSubmit={handleLatest} className='filter-bar'>
          <label className='filter-label' htmlFor='latest-vehicle-id'>
            Vehicle ID
          </label>
          <input
            id='latest-vehicle-id'
            type='number'
            min='1'
            required
            placeholder='e.g. 3'
            value={latestVehicleId}
            onChange={(e) => setLatestVehicleId(e.target.value)}
            aria-label='Vehicle ID for latest ping lookup'
            style={{ maxWidth: 140 }}
          />
          <button type='submit' className='btn btn-sm'>
            Look up
          </button>
        </form>
        {latestError && <p className='error'>{latestError}</p>}
        {latest && (
          <div className='data-table-wrap'>
            <table className='data-table'>
              <thead>
                <tr>
                  <th>Vehicle</th>
                  <th>Latitude</th>
                  <th>Longitude</th>
                  <th>Speed</th>
                  <th>Heading</th>
                  <th>Recorded at</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>#{latest.vehicle_id}</td>
                  <td>{fmt(latest.latitude, 5)}</td>
                  <td>{fmt(latest.longitude, 5)}</td>
                  <td>{latest.speed != null ? `${fmt(latest.speed, 1)} km/h` : '—'}</td>
                  <td>{latest.heading != null ? `${fmt(latest.heading, 0)}°` : '—'}</td>
                  <td className='cell-muted'>{latest.recorded_at ?? latest.created_at ?? '—'}</td>
                </tr>
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Ping form */}
      <div className='panel'>
        <p className='panel-title'>Send a location ping</p>
        <p className='panel-sub'>Manually record a position (useful for demos and tests).</p>
        <form onSubmit={handlePing}>
          <div className='form-grid'>
            <label>
              Vehicle ID
              <input
                type='number'
                min='1'
                required
                value={ping.vehicle_id}
                onChange={(e) => setPing({ ...ping, vehicle_id: e.target.value })}
                aria-label='Vehicle ID for ping'
              />
            </label>
            <label>
              Latitude (-90 to 90)
              <input
                type='number'
                step='any'
                min='-90'
                max='90'
                required
                placeholder='e.g. 40.7128'
                value={ping.latitude}
                onChange={(e) => setPing({ ...ping, latitude: e.target.value })}
                aria-label='Ping latitude'
              />
            </label>
            <label>
              Longitude (-180 to 180)
              <input
                type='number'
                step='any'
                min='-180'
                max='180'
                required
                placeholder='e.g. -74.0060'
                value={ping.longitude}
                onChange={(e) => setPing({ ...ping, longitude: e.target.value })}
                aria-label='Ping longitude'
              />
            </label>
            <label>
              Speed (km/h, optional)
              <input
                type='number'
                step='any'
                min='0'
                value={ping.speed}
                onChange={(e) => setPing({ ...ping, speed: e.target.value })}
                aria-label='Ping speed'
              />
            </label>
            <label>
              Heading (degrees, optional)
              <input
                type='number'
                step='any'
                min='0'
                max='360'
                value={ping.heading}
                onChange={(e) => setPing({ ...ping, heading: e.target.value })}
                aria-label='Ping heading'
              />
            </label>
          </div>
          <div style={{ marginTop: 16 }}>
            <button type='submit' className='btn'>
              Save ping
            </button>
          </div>
        </form>
      </div>

      {/* Map placeholder + table */}
      <div className='panel'>
        <p className='panel-title'>Fleet overview</p>
        <p className='panel-sub'>
          Showing the most recent ping per vehicle on this page (up to {PAGE_SIZE} rows per load).
        </p>

        <FleetMap vehicles={vehicles} latestPositions={uniqueLocations} geofences={[]} />

        <div className='filter-bar'>
          <span className='filter-count'>
            {uniqueLocations.length} vehicles · {locations.length} pings loaded
          </span>
          <span className='spacer' />
          <button
            type='button'
            className='btn btn-sm btn-ghost'
            onClick={handleLoadMore}
            disabled={loading || !hasMore}
          >
            {loading ? 'Loading…' : hasMore ? 'Load more' : 'No more rows'}
          </button>
        </div>

        {uniqueLocations.length === 0 && !loading ? (
          <p className='empty'>
            <strong>No locations yet</strong>
            Ping a vehicle above or wait for the tracker to report.
          </p>
        ) : (
          <div className='data-table-wrap'>
            <table className='data-table'>
              <thead>
                <tr>
                  <th>Vehicle</th>
                  <th>Latitude</th>
                  <th>Longitude</th>
                  <th>Speed</th>
                  <th>Heading</th>
                  <th>Recorded at</th>
                </tr>
              </thead>
              <tbody>
                {uniqueLocations.map((loc) => (
                  <tr key={`${loc.vehicle_id}-${loc.id ?? loc.recorded_at ?? loc.created_at}`}>
                    <td>#{loc.vehicle_id}</td>
                    <td>{fmt(loc.latitude, 5)}</td>
                    <td>{fmt(loc.longitude, 5)}</td>
                    <td>{loc.speed != null ? `${fmt(loc.speed, 1)} km/h` : '—'}</td>
                    <td>{loc.heading != null ? `${fmt(loc.heading, 0)}°` : '—'}</td>
                    <td className='cell-muted'>{loc.recorded_at ?? loc.created_at ?? '—'}</td>
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
