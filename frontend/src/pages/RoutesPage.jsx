import { useState, useEffect } from 'react'
import api from '../api.js'
import { errorMessage } from '../utils/errors.js'
import RouteMap from '../components/RouteMap.jsx'

const STATUSES = ['planned', 'in_progress', 'completed']

const STATUS_BADGE = {
  planned: 'badge-info',
  in_progress: 'badge-warn',
  completed: 'badge-success',
}

function statusLabel(s) {
  return s.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function StatusStepper({ status }) {
  const order = ['planned', 'in_progress', 'completed']
  const current = order.indexOf(status)
  return (
    <div className='stepper' aria-label={`Route status: ${statusLabel(status)}`}>
      {order.map((s, i) => (
        <span key={s} style={{ display: 'contents' }}>
          {i > 0 && <span className='step-line' />}
          <span className={`step ${i < current ? 'done' : ''} ${i === current ? 'active' : ''}`}>
            <span className='step-dot'>{i + 1}</span>
            {statusLabel(s)}
          </span>
        </span>
      ))}
    </div>
  )
}

export default function RoutesPage() {
  const [routes, setRoutes] = useState([])
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)
  const [statusFilter, setStatusFilter] = useState('')
  const [expandedId, setExpandedId] = useState(null)
  const [details, setDetails] = useState({})
  const [detailLoading, setDetailLoading] = useState(false)

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
      setError(errorMessage(err, 'Failed to load routes.'))
    }
  }

  useEffect(() => {
    fetchRoutes()
  }, [])

  const flash = (msg) => {
    setSuccess(msg)
    window.setTimeout(() => setSuccess(''), 2500)
  }

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
      flash('Route planned.')
    } catch (err) {
      setError(errorMessage(err, 'Failed to plan route.'))
    } finally {
      setLoading(false)
    }
  }

  const handleStart = async (id) => {
    setError('')
    try {
      await api.post(`/routes/${id}/start`, {}, token)
      fetchRoutes()
      flash('Route started.')
    } catch (err) {
      setError(errorMessage(err, 'Failed to start route.'))
    }
  }

  const handleComplete = async (id) => {
    setError('')
    try {
      await api.post(`/routes/${id}/complete`, {}, token)
      fetchRoutes()
      flash('Route completed.')
    } catch (err) {
      setError(errorMessage(err, 'Failed to complete route.'))
    }
  }

  const handleArrive = async (stopId) => {
    setError('')
    try {
      await api.post(`/routes/stops/${stopId}/arrive`, {}, token)
      fetchRoutes()
      if (expandedId) fetchDetail(expandedId, true)
      flash('Stop marked arrived.')
    } catch (err) {
      setError(errorMessage(err, 'Failed to mark stop arrived.'))
    }
  }

  const fetchDetail = async (id, force = false) => {
    if (details[id] && !force) return details[id]
    setDetailLoading(true)
    try {
      const res = await api.get(`/routes/${id}`, token)
      const payload = res.data.data.route ?? res.data.data
      setDetails((d) => ({ ...d, [id]: payload }))
      return payload
    } catch (err) {
      setError(errorMessage(err, 'Failed to load route detail.'))
      return null
    } finally {
      setDetailLoading(false)
    }
  }

  const toggleExpand = async (route) => {
    if (expandedId === route.id) {
      setExpandedId(null)
      return
    }
    setExpandedId(route.id)
    if (!route.stops || route.stops.length === 0) {
      await fetchDetail(route.id)
    } else if (!details[route.id]) {
      setDetails((d) => ({ ...d, [route.id]: route }))
      fetchDetail(route.id, true)
    }
  }

  const filtered = statusFilter
    ? routes.filter((r) => r.status === statusFilter)
    : routes

  const expandedRoute = expandedId ? (details[expandedId] || routes.find((r) => r.id === expandedId)) : null
  const expandedStops = expandedRoute?.stops || []

  return (
    <div>
      <div className='page-head'>
        <div>
          <h2 className='page-title'>Routes</h2>
          <p className='page-sub'>Plan multi-stop routes, track progress, and mark stops as arrived.</p>
        </div>
      </div>

      {error && <p className='error'>{error}</p>}
      {success && <p className='success-note'>{success}</p>}

      {/* Plan form */}
      <div className='panel'>
        <p className='panel-title'>Plan a new route</p>
        <p className='panel-sub'>Pick a vehicle and add at least two stops in order.</p>
        <form onSubmit={handlePlanRoute}>
          <div className='form-grid'>
            <label>
              Vehicle ID
              <input
                type='number'
                min='1'
                required
                value={vehicleId}
                onChange={(e) => setVehicleId(e.target.value)}
                aria-label='Vehicle ID'
              />
            </label>
          </div>

          <p className='form-section-title' style={{ marginTop: 18 }}>
            Stops (min 2)
          </p>
          {stops.map((stop, i) => (
            <div key={i} className='stop-row'>
              <span className='stop-index'>#{i + 1}</span>
              <label>
                Latitude (-90 to 90)
                <input
                  type='number'
                  step='any'
                  min='-90'
                  max='90'
                  placeholder='e.g. 40.7128'
                  required
                  value={stop.latitude}
                  onChange={(e) => handleStopChange(i, 'latitude', e.target.value)}
                  aria-label={`Stop ${i + 1} latitude`}
                />
              </label>
              <label>
                Longitude (-180 to 180)
                <input
                  type='number'
                  step='any'
                  min='-180'
                  max='180'
                  placeholder='e.g. -74.0060'
                  required
                  value={stop.longitude}
                  onChange={(e) => handleStopChange(i, 'longitude', e.target.value)}
                  aria-label={`Stop ${i + 1} longitude`}
                />
              </label>
              {stops.length > 2 && (
                <button
                  type='button'
                  className='btn btn-sm btn-ghost'
                  onClick={() => handleRemoveStop(i)}
                  aria-label={`Remove stop ${i + 1}`}
                >
                  Remove
                </button>
              )}
            </div>
          ))}
          <div className='row-actions' style={{ marginTop: 4 }}>
            <button type='button' className='btn btn-sm btn-ghost' onClick={handleAddStop}>
              + Add stop
            </button>
          </div>

          <div style={{ marginTop: 16 }}>
            <button type='submit' className='btn' disabled={loading}>
              {loading ? 'Planning…' : 'Plan route'}
            </button>
          </div>
        </form>
      </div>

      {/* Routes list */}
      <div className='panel'>
        <p className='panel-title'>Your routes</p>
        <p className='panel-sub'>Start, progress, and complete routes from here.</p>

        <div className='filter-bar'>
          <label className='filter-label' htmlFor='route-status-filter'>
            Status
          </label>
          <select
            id='route-status-filter'
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value=''>All statuses</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {statusLabel(s)}
              </option>
            ))}
          </select>
          <span className='spacer' />
          <span className='filter-count'>
            {filtered.length} of {routes.length} routes
          </span>
        </div>

        {filtered.length === 0 ? (
          <p className='empty'>
            <strong>No routes yet</strong>
            Plan your first route above to get started.
          </p>
        ) : (
          filtered.map((route) => {
            const stopsForRoute = expandedId === route.id ? expandedStops : route.stops || []
            const isExpanded = expandedId === route.id
            return (
              <div key={route.id} className='route-card'>
                <div className='route-card-head'>
                  <div>
                    <div className='route-meta'>
                      <strong>Route #{route.id}</strong>
                      <span className={`badge ${STATUS_BADGE[route.status] || 'badge-muted'}`}>
                        {statusLabel(route.status)}
                      </span>
                      {route.score != null && (
                        <span className='badge badge-violet'>Score {route.score}</span>
                      )}
                      <span>Vehicle #{route.vehicle_id}</span>
                      {route.driver_id != null && <span>Driver #{route.driver_id}</span>}
                      {route.distance_km != null && <span>{route.distance_km} km</span>}
                      <span>{route.stops?.length || 0} stops</span>
                    </div>
                  </div>
                  <div className='row-actions'>
                    <button
                      type='button'
                      className='btn btn-sm btn-ghost'
                      onClick={() => toggleExpand(route)}
                    >
                      {isExpanded ? 'Hide stops' : 'View stops'}
                    </button>
                    {route.status === 'planned' && (
                      <button
                        type='button'
                        className='btn btn-sm btn-warn'
                        onClick={() => handleStart(route.id)}
                      >
                        Start
                      </button>
                    )}
                    {route.status === 'in_progress' && (
                      <button
                        type='button'
                        className='btn btn-sm btn-success'
                        onClick={() => handleComplete(route.id)}
                      >
                        Complete
                      </button>
                    )}
                  </div>
                </div>

                <StatusStepper status={route.status} />

                {isExpanded && (
                  <div style={{ marginTop: 14 }}>
                    {stopsForRoute.length > 0 && <RouteMap stops={stopsForRoute} />}
                    {detailLoading && stopsForRoute.length === 0 ? (
                      <p className='empty'>Loading stops…</p>
                    ) : stopsForRoute.length === 0 ? (
                      <p className='empty'>No stops recorded for this route.</p>
                    ) : (
                      <ul className='stops-list'>
                        {[...stopsForRoute]
                          .sort((a, b) => (a.sequence ?? 0) - (b.sequence ?? 0))
                          .map((s) => {
                            const done = s.status === 'arrived' || s.status === 'completed'
                            return (
                              <li key={s.id ?? s.sequence} className={done ? 'stop-done' : ''}>
                                <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                  <span className='stop-seq'>{s.sequence}</span>
                                  <span>
                                    {s.latitude ?? s.lat}, {s.longitude ?? s.lng ?? s.lon}
                                  </span>
                                  <span className={`badge ${done ? 'badge-success' : 'badge-muted'}`}>
                                    {s.status ?? 'pending'}
                                  </span>
                                  {s.arrived_at && (
                                    <span className='cell-muted' style={{ fontSize: 12 }}>
                                      arrived {s.arrived_at}
                                    </span>
                                  )}
                                </span>
                                {route.status === 'in_progress' && s.status === 'pending' && (
                                  <button
                                    type='button'
                                    className='btn btn-sm'
                                    onClick={() => handleArrive(s.id)}
                                  >
                                    Mark arrived
                                  </button>
                                )}
                              </li>
                            )
                          })}
                      </ul>
                    )}
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
