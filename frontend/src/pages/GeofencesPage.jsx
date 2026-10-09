import { useState, useEffect } from 'react'
import api from '../api.js'
import { errorMessage } from '../utils/errors.js'
import { parseGeofenceCoordinates } from '../utils/geofence.js'
import FleetMap from '../components/FleetMap.jsx'

function describeShape(geo) {
  const parsed = parseGeofenceCoordinates(geo.coordinates)
  if (parsed.kind === 'circle') {
    return `Circle · center ${parsed.center[0]}, ${parsed.center[1]} · radius ${parsed.radius} m`
  }
  if (parsed.kind === 'bbox') {
    return `Bounding box · ${parsed.bbox.join(', ')}`
  }
  if (parsed.kind === 'polygon') {
    return `Polygon · ${parsed.points.length} points`
  }
  return 'Unknown shape'
}

export default function GeofencesPage() {
  const [geofences, setGeofences] = useState([])
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)
  const [confirmDeleteId, setConfirmDeleteId] = useState(null)

  // Form state
  const [name, setName] = useState('')
  const [kind, setKind] = useState('circle')
  const [centerLat, setCenterLat] = useState('')
  const [centerLng, setCenterLng] = useState('')
  const [radius, setRadius] = useState('')
  const [minLat, setMinLat] = useState('')
  const [minLng, setMinLng] = useState('')
  const [maxLat, setMaxLat] = useState('')
  const [maxLng, setMaxLng] = useState('')

  const token = localStorage.getItem('token')

  const fetchGeofences = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await api.get('/geofences/', token)
      setGeofences(res.data.data.geofences || [])
    } catch (err) {
      setError(errorMessage(err, 'Failed to load geofences.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchGeofences()
  }, [])

  const flash = (msg) => {
    setSuccess(msg)
    window.setTimeout(() => setSuccess(''), 2500)
  }

  const resetForm = () => {
    setName('')
    setKind('circle')
    setCenterLat('')
    setCenterLng('')
    setRadius('')
    setMinLat('')
    setMinLng('')
    setMaxLat('')
    setMaxLng('')
  }

  const buildCoordinates = () => {
    if (kind === 'circle') {
      return JSON.stringify({
        type: 'circle',
        center: [Number(centerLat), Number(centerLng)],
        radius: Number(radius),
      })
    }
    return JSON.stringify({
      type: 'bbox',
      bbox: [Number(minLat), Number(minLng), Number(maxLat), Number(maxLng)],
    })
  }

  const handleCreate = async (e) => {
    e.preventDefault()
    setError('')
    try {
      await api.post(
        '/geofences/',
        { name: name.trim(), coordinates: buildCoordinates() },
        token
      )
      resetForm()
      fetchGeofences()
      flash('Geofence created.')
    } catch (err) {
      setError(errorMessage(err, 'Failed to create geofence.'))
    }
  }

  const handleDelete = async (id) => {
    setError('')
    try {
      await api.del(`/geofences/${id}`, token)
      setConfirmDeleteId(null)
      fetchGeofences()
      flash('Geofence deleted.')
    } catch (err) {
      setError(errorMessage(err, 'Failed to delete geofence.'))
    }
  }

  return (
    <div>
      <div className='page-head'>
        <div>
          <h2 className='page-title'>Geofences</h2>
          <p className='page-sub'>Draw circular or rectangular zones. Alerts fire when vehicles cross them.</p>
        </div>
      </div>

      {error && <p className='error'>{error}</p>}
      {success && <p className='success-note'>{success}</p>}

      {/* Create form */}
      <div className='panel'>
        <p className='panel-title'>Create a geofence</p>
        <p className='panel-sub'>Pick a shape and enter its coordinates.</p>
        <form onSubmit={handleCreate}>
          <div className='form-grid'>
            <label>
              Name
              <input
                type='text'
                required
                maxLength={80}
                placeholder='e.g. Warehouse district'
                value={name}
                onChange={(e) => setName(e.target.value)}
                aria-label='Geofence name'
              />
            </label>
            <label>
              Shape
              <select value={kind} onChange={(e) => setKind(e.target.value)} aria-label='Geofence shape'>
                <option value='circle'>Circle (center + radius)</option>
                <option value='bbox'>Rectangle (bounding box)</option>
              </select>
            </label>
          </div>

          {kind === 'circle' ? (
            <div className='form-grid' style={{ marginTop: 12 }}>
              <label>
                Center latitude (-90 to 90)
                <input
                  type='number'
                  step='any'
                  min='-90'
                  max='90'
                  required
                  placeholder='e.g. 40.7128'
                  value={centerLat}
                  onChange={(e) => setCenterLat(e.target.value)}
                  aria-label='Center latitude'
                />
              </label>
              <label>
                Center longitude (-180 to 180)
                <input
                  type='number'
                  step='any'
                  min='-180'
                  max='180'
                  required
                  placeholder='e.g. -74.0060'
                  value={centerLng}
                  onChange={(e) => setCenterLng(e.target.value)}
                  aria-label='Center longitude'
                />
              </label>
              <label>
                Radius (meters)
                <input
                  type='number'
                  min='1'
                  required
                  placeholder='e.g. 500'
                  value={radius}
                  onChange={(e) => setRadius(e.target.value)}
                  aria-label='Radius in meters'
                />
              </label>
            </div>
          ) : (
            <div className='form-grid' style={{ marginTop: 12 }}>
              <label>
                Min latitude
                <input
                  type='number'
                  step='any'
                  min='-90'
                  max='90'
                  required
                  value={minLat}
                  onChange={(e) => setMinLat(e.target.value)}
                  aria-label='Minimum latitude'
                />
              </label>
              <label>
                Min longitude
                <input
                  type='number'
                  step='any'
                  min='-180'
                  max='180'
                  required
                  value={minLng}
                  onChange={(e) => setMinLng(e.target.value)}
                  aria-label='Minimum longitude'
                />
              </label>
              <label>
                Max latitude
                <input
                  type='number'
                  step='any'
                  min='-90'
                  max='90'
                  required
                  value={maxLat}
                  onChange={(e) => setMaxLat(e.target.value)}
                  aria-label='Maximum latitude'
                />
              </label>
              <label>
                Max longitude
                <input
                  type='number'
                  step='any'
                  min='-180'
                  max='180'
                  required
                  value={maxLng}
                  onChange={(e) => setMaxLng(e.target.value)}
                  aria-label='Maximum longitude'
                />
              </label>
            </div>
          )}

          <div style={{ marginTop: 16 }}>
            <button type='submit' className='btn'>
              Create geofence
            </button>
          </div>
        </form>
      </div>

      <div className='panel'>
        <p className='panel-title'>Zone map</p>
        <p className='panel-sub'>All zones currently defined.</p>
        <FleetMap vehicles={[]} latestPositions={{}} geofences={geofences} />
      </div>

      {/* List */}
      <div className='panel'>
        <p className='panel-title'>Zones</p>
        <p className='panel-sub'>Every zone currently defined for your fleet.</p>

        <div className='filter-bar'>
          <span className='filter-count'>
            {geofences.length} zone{geofences.length === 1 ? '' : 's'}
          </span>
        </div>

        {loading && geofences.length === 0 ? (
          <p className='empty'>Loading zones…</p>
        ) : geofences.length === 0 ? (
          <p className='empty'>
            <strong>No geofences yet</strong>
            Create your first zone above to start receiving entry/exit alerts.
          </p>
        ) : (
          <ul className='geofence-list'>
            {geofences.map((g) => (
              <li key={g.id} className='geofence-item'>
                <div className='geofence-info'>
                  <strong>{g.name}</strong>
                  <span className='cell-muted' style={{ fontSize: 13 }}>
                    {describeShape(g)}
                  </span>
                  {g.created_at && (
                    <span className='cell-muted' style={{ fontSize: 12 }}>
                      Created {g.created_at}
                    </span>
                  )}
                </div>
                {confirmDeleteId === g.id ? (
                  <div className='row-actions'>
                    <span className='hint'>Delete this zone?</span>
                    <button
                      type='button'
                      className='btn btn-sm btn-danger'
                      onClick={() => handleDelete(g.id)}
                    >
                      Yes, delete
                    </button>
                    <button
                      type='button'
                      className='btn btn-sm btn-ghost'
                      onClick={() => setConfirmDeleteId(null)}
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <div className='row-actions'>
                    <button
                      type='button'
                      className='btn btn-sm btn-ghost'
                      onClick={() => setConfirmDeleteId(g.id)}
                      aria-label={`Delete geofence ${g.name}`}
                    >
                      Delete
                    </button>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
