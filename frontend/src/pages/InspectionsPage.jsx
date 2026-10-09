import { useState, useEffect, useCallback } from 'react'
import api from '../api.js'
import { errorMessage } from '../utils/errors.js'

const CHECK_ITEMS = [
  { key: 'brakes', label: 'Brakes' },
  { key: 'lights', label: 'Lights' },
  { key: 'tires', label: 'Tires' },
  { key: 'mirrors', label: 'Mirrors' },
  { key: 'documents', label: 'Documents' },
]

function vehicleLabel(v) {
  const plate = v.license_plate || v.plate || `#${v.id}`
  const model = [v.make, v.model].filter(Boolean).join(' ')
  return model ? `${plate} · ${model}` : plate
}

function typeLabel(t) {
  if (t === 'pre_trip') return 'Pre-trip'
  if (t === 'post_trip') return 'Post-trip'
  return String(t || '').replace(/_/g, ' ')
}

export default function InspectionsPage() {
  const [vehicles, setVehicles] = useState([])
  const [vehicleId, setVehicleId] = useState('')
  const [inspections, setInspections] = useState([])
  const [total, setTotal] = useState(0)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)

  const [type, setType] = useState('pre_trip')
  const [checks, setChecks] = useState({
    brakes: false,
    lights: false,
    tires: false,
    mirrors: false,
    documents: false,
  })
  const [notes, setNotes] = useState('')

  const token = localStorage.getItem('token')

  // passed is derived: every checklist item must be checked
  const passed = CHECK_ITEMS.every((c) => checks[c.key])
  const checkedCount = CHECK_ITEMS.filter((c) => checks[c.key]).length

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

  const fetchInspections = useCallback(async () => {
    if (!vehicleId) {
      setInspections([])
      setTotal(0)
      return
    }
    setLoading(true)
    setError('')
    try {
      const res = await api.get(
        `/inspections/?vehicle_id=${vehicleId}&skip=0&limit=50`,
        token
      )
      setInspections(res.data.data.inspections || [])
      setTotal(res.data.data.total ?? 0)
    } catch (err) {
      setError(errorMessage(err, 'Failed to load inspections for this vehicle.'))
      setInspections([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }, [vehicleId, token])

  useEffect(() => {
    fetchInspections()
  }, [fetchInspections])

  const flash = (msg) => {
    setSuccess(msg)
    window.setTimeout(() => setSuccess(''), 2500)
  }

  const toggle = (key) => setChecks((prev) => ({ ...prev, [key]: !prev[key] }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    // Fold checklist details into notes so the record stays honest
    const itemSummary = CHECK_ITEMS.map(
      (c) => `${c.label}: ${checks[c.key] ? 'pass' : 'fail'}`
    ).join(', ')
    const fullNotes = [notes.trim() ? notes.trim() : '', `[${itemSummary}]`]
      .filter(Boolean)
      .join(' ')
    try {
      await api.post(
        '/inspections/',
        {
          vehicle_id: Number(vehicleId),
          type,
          passed,
          notes: fullNotes || null,
        },
        token
      )
      setChecks({ brakes: false, lights: false, tires: false, mirrors: false, documents: false })
      setNotes('')
      flash(passed ? 'Inspection recorded — passed.' : 'Inspection recorded — failed items flagged.')
      fetchInspections()
    } catch (err) {
      setError(errorMessage(err, 'Failed to record inspection.'))
    }
  }

  const passCount = inspections.filter((i) => i.passed).length
  const failCount = inspections.length - passCount

  return (
    <div>
      <div className='page-head'>
        <div>
          <h2 className='page-title'>Inspections</h2>
          <p className='page-sub'>
            Pre-trip and post-trip safety checks per vehicle.{' '}
            {vehicleId
              ? `${passCount} passed · ${failCount} failed${total > inspections.length ? ` (showing latest ${inspections.length} of ${total})` : ''}`
              : 'Select a vehicle to begin.'}
          </p>
        </div>
        <div className='page-actions'>
          <button type='button' className='btn btn-sm btn-ghost' onClick={fetchInspections} disabled={loading}>
            {loading ? 'Refreshing…' : 'Refresh'}
          </button>
        </div>
      </div>

      {error && <p className='error'>{error}</p>}
      {success && <p className='success-note'>{success}</p>}

      {/* New inspection */}
      <div className='panel'>
        <p className='panel-title'>Record an inspection</p>
        <p className='panel-sub'>
          The inspection passes only when every checklist item is checked. Failed items are stored
          in the notes and shown in the history below.
        </p>
        {!vehicleId ? (
          <p className='empty'>
            <strong>No vehicles yet</strong>
            Add a vehicle first — inspections attach to a specific vehicle.
          </p>
        ) : (
          <form onSubmit={handleSubmit}>
            <div className='form-grid'>
              <label>
                Vehicle
                <select
                  value={vehicleId}
                  onChange={(e) => setVehicleId(e.target.value)}
                  aria-label='Select vehicle for inspection'
                >
                  {vehicles.map((v) => (
                    <option key={v.id} value={String(v.id)}>
                      {vehicleLabel(v)}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Inspection type
                <select
                  value={type}
                  onChange={(e) => setType(e.target.value)}
                  aria-label='Inspection type'
                >
                  <option value='pre_trip'>Pre-trip</option>
                  <option value='post_trip'>Post-trip</option>
                </select>
              </label>
            </div>

            <p className='form-section-title'>Safety checklist</p>
            <div className='form-grid' role='group' aria-label='Safety checklist'>
              {CHECK_ITEMS.map((item) => (
                <label key={item.key} className='checkbox-label'>
                  <input
                    type='checkbox'
                    checked={checks[item.key]}
                    onChange={() => toggle(item.key)}
                    aria-label={`${item.label} check`}
                  />
                  {item.label}
                </label>
              ))}
            </div>
            <p className='hint' role='status'>
              {checkedCount} of {CHECK_ITEMS.length} items checked — inspection{' '}
              <strong>{passed ? 'passes' : 'fails'}</strong>.
            </p>

            <div className='form-grid' style={{ marginTop: 12 }}>
              <label className='full'>
                Notes (optional)
                <textarea
                  maxLength={2000}
                  placeholder='e.g. tire pressure topped up on rear left'
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  aria-label='Inspection notes'
                />
              </label>
            </div>

            <button
              type='submit'
              className={`btn ${passed ? 'btn-success' : 'btn-danger'}`}
              disabled={loading}
            >
              {passed ? 'Record as passed' : 'Record as failed'}
            </button>
          </form>
        )}
      </div>

      {/* History */}
      <div className='panel'>
        <p className='panel-title'>Inspection history</p>
        <p className='panel-sub'>Most recent 50 inspections for the selected vehicle.</p>

        {inspections.length === 0 ? (
          <p className='empty'>
            <strong>No inspections yet</strong>
            {loading
              ? 'Loading…'
              : vehicleId
                ? 'Record the first inspection above.'
                : 'Select a vehicle to see its history.'}
          </p>
        ) : (
          <div className='data-table-wrap'>
            <table className='data-table'>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Type</th>
                  <th>Result</th>
                  <th>Inspector</th>
                  <th>Notes</th>
                </tr>
              </thead>
              <tbody>
                {inspections.map((i) => (
                  <tr key={i.id}>
                    <td className='cell-muted'>{i.created_at ?? '—'}</td>
                    <td>{typeLabel(i.type)}</td>
                    <td>
                      <span className={`badge ${i.passed ? 'badge-success' : 'badge-danger'}`}>
                        {i.passed ? 'Passed' : 'Failed'}
                      </span>
                    </td>
                    <td className='cell-muted'>
                      {i.inspector_id != null ? `Inspector #${i.inspector_id}` : '—'}
                    </td>
                    <td className='cell-muted'>{i.notes || '—'}</td>
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
