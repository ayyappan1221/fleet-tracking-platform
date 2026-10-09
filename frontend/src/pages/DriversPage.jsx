import { useState, useEffect, useCallback } from 'react'
import api from '../api.js'
import { errorMessage } from '../utils/errors.js'
import { isManager } from '../utils/auth.js'

const MEDALS = ['🥇', '🥈', '🥉']

// Alerts that reflect driving behaviour (vs. geofence / maintenance / system notices)
function isBehaviorAlert(type) {
  const t = String(type || '').toLowerCase()
  return t.includes('speed') || t.includes('brak') || t.includes('accel') || t.includes('behavior') || t.includes('behaviour')
}

function vehicleLabel(v) {
  const plate = v.license_plate || v.plate || `#${v.id}`
  const model = [v.make, v.model].filter(Boolean).join(' ')
  return model ? `${plate} · ${model}` : plate
}

export default function DriversPage() {
  const [vehicles, setVehicles] = useState([])
  const [alerts, setAlerts] = useState([])
  const [myScore, setMyScore] = useState(null)
  const [serverScores, setServerScores] = useState({})
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const token = localStorage.getItem('token')
  const manager = isManager(token)

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [vehRes, alertRes, scoreRes] = await Promise.all([
        api.get('/vehicles/', token),
        api.get('/alerts/?skip=0&limit=200', token),
        api.get('/drivers/me/score', token),
      ])
      setVehicles(vehRes.data.data.vehicles || [])
      setAlerts(alertRes.data.data.alerts || [])
      setMyScore(scoreRes.data.data)
      const list = vehRes.data.data.vehicles || []
      const scoreEntries = await Promise.all(
        list.slice(0, 20).map((v) =>
          api
            .get(`/vehicles/${v.id}/score`, token)
            .then((r) => [v.id, r.data.data])
            .catch(() => [v.id, null])
        )
      )
      setServerScores(Object.fromEntries(scoreEntries))
    } catch (err) {
      setError(errorMessage(err, 'Failed to load leaderboard data.'))
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  // Behaviour alerts visible to this role (mirrors AlertsPage visibility rule)
  const visibleAlerts = alerts.filter(
    (a) => manager || a.vehicle_id != null || !a.is_system
  )

  // Per-vehicle behaviour counts
  const perVehicle = new Map()
  for (const a of visibleAlerts) {
    if (a.vehicle_id == null || !isBehaviorAlert(a.type)) continue
    const cur = perVehicle.get(a.vehicle_id) || { speeding: 0, behavior: 0 }
    const t = String(a.type || '').toLowerCase()
    if (t.includes('speed')) cur.speeding += 1
    cur.behavior += 1
    perVehicle.set(a.vehicle_id, cur)
  }

  // Honest, transparent scoring: 100 points, minus 10 per behaviour alert, floored at 0.
  const rows = vehicles
    .map((v) => {
      const counts = perVehicle.get(v.id) || { speeding: 0, behavior: 0 }
      const score = Math.max(0, 100 - counts.behavior * 10)
      return { vehicle: v, ...counts, score }
    })
    .sort((a, b) => b.score - a.score || a.behavior - b.behavior || a.vehicle.id - b.vehicle.id)

  const maxScore = rows.length > 0 ? Math.max(...rows.map((r) => r.score)) : 100

  return (
    <div>
      <div className='page-head'>
        <div>
          <h2 className='page-title'>Drivers leaderboard</h2>
          <p className='page-sub'>
            Vehicles ranked by driving-behaviour alerts — fewer events, higher score.{' '}
            {loading ? 'Loading…' : `${rows.length} vehicles ranked.`}
          </p>
        </div>
        <div className='page-actions'>
          <button type='button' className='btn btn-sm btn-ghost' onClick={fetchData} disabled={loading}>
            {loading ? 'Refreshing…' : 'Refresh'}
          </button>
        </div>
      </div>

      {error && <p className='error'>{error}</p>}

      <div className='stat-grid'>
        <div className='stat-card'>
          <span className='stat-label'>My driving score</span>
          <strong className='stat-value'>
            {myScore && myScore.score != null ? Number(myScore.score).toFixed(0) : '—'}
          </strong>
          <span className='stat-hint'>
            {myScore
              ? `${myScore.samples ?? 0} GPS samples · ${myScore.routes ?? 0} routes · ${myScore.vehicles ?? 0} vehicles`
              : 'Server-side telematics score'}
          </span>
        </div>
      </div>

      <div className='panel'>
        <p className='panel-title'>Safety standings</p>
        <p className='panel-sub'>
          Score starts at 100 and drops 10 points per recorded behaviour alert (speeding, harsh
          braking, rapid acceleration) for this account. Vehicles without alerts keep a full score.
        </p>

        {rows.length === 0 ? (
          <div className='empty'>
            <strong>No vehicles to rank yet</strong>
            Add vehicles on the Vehicles page and they will appear here automatically.
          </div>
        ) : (
          <ul className='alert-feed' role='list' aria-label='Vehicle safety leaderboard'>
            {rows.map((r, i) => (
              <li key={r.vehicle.id} className='alert-item'>
                <span
                  aria-hidden='true'
                  style={{
                    width: 34,
                    textAlign: 'center',
                    fontSize: 18,
                    flex: '0 0 auto',
                  }}
                >
                  {i < 3 ? MEDALS[i] : `#${i + 1}`}
                </span>
                <div className='alert-body'>
                  <div className='alert-head'>
                    <strong className='alert-type'>{vehicleLabel(r.vehicle)}</strong>
                    <span className='cell-muted'>Vehicle #{r.vehicle.id}</span>
                    <span className='spacer' />
                    {r.behavior === 0 ? (
                      <span className='badge badge-success'>No behaviour alerts</span>
                    ) : (
                      <span className='badge badge-warn'>
                        {r.behavior} behaviour {r.behavior === 1 ? 'alert' : 'alerts'}
                        {r.speeding > 0 ? ` · ${r.speeding} speeding` : ''}
                      </span>
                    )}
                    <span className='badge badge-brand'>{r.score} pts</span>
                    {serverScores[r.vehicle.id] && serverScores[r.vehicle.id].score != null && (
                      <span
                        className='badge badge-success'
                        title={`Server telematics score from ${serverScores[r.vehicle.id].samples ?? 0} GPS samples`}
                      >
                        server {Number(serverScores[r.vehicle.id].score).toFixed(0)}
                      </span>
                    )}
                  </div>
                  <div
                    role='progressbar'
                    aria-label={`${vehicleLabel(r.vehicle)} safety score ${r.score} of 100`}
                    aria-valuenow={r.score}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    style={{
                      marginTop: 8,
                      height: 8,
                      borderRadius: 'var(--radius-pill)',
                      background: 'var(--surface-2)',
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        height: '100%',
                        width: `${maxScore > 0 ? (r.score / 100) * 100 : 0}%`,
                        background: r.score >= 80 ? 'var(--brand)' : r.score >= 50 ? 'var(--honey)' : 'var(--danger)',
                        borderRadius: 'var(--radius-pill)',
                      }}
                    />
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className='panel'>
        <p className='panel-title'>How this ranking works</p>
        <p className='panel-sub'>
          The score is calculated in your browser from behaviour alerts already recorded for these
          vehicles — it is not a server-side telematics score, and it only reflects alerts this
          account can see{manager ? '' : ' (vehicles linked to your account)'}. Wider tracking data
          may change the picture.
        </p>
      </div>
    </div>
  )
}
