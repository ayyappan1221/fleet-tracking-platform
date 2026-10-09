import { useState, useEffect, useCallback } from 'react'
import api from '../api.js'
import { errorMessage } from '../utils/errors.js'
import { isManager } from '../utils/auth.js'

const TYPES = ['oil_change', 'tire', 'inspection', 'repair']
const STATUSES = ['scheduled', 'in_progress', 'completed']

const STATUS_BADGE = {
  scheduled: 'badge-info',
  in_progress: 'badge-warn',
  completed: 'badge-success',
}

const TYPE_LABEL = {
  oil_change: 'Oil change',
  tire: 'Tires',
  inspection: 'Inspection',
  repair: 'Repair',
}

function label(s) {
  if (TYPE_LABEL[s]) return TYPE_LABEL[s]
  return String(s).replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function daysUntil(dateStr) {
  if (!dateStr) return null
  const due = new Date(dateStr)
  if (Number.isNaN(due.getTime())) return null
  const now = new Date()
  const diffMs = due.getTime() - now.getTime()
  return Math.ceil(diffMs / (1000 * 60 * 60 * 24))
}

export default function MaintenancePage() {
  const [records, setRecords] = useState([])
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)
  const [typeFilter, setTypeFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [confirmDeleteId, setConfirmDeleteId] = useState(null)

  // Form
  const [vehicleId, setVehicleId] = useState('')
  const [type, setType] = useState('oil_change')
  const [status, setStatus] = useState('scheduled')
  const [dueDate, setDueDate] = useState('')
  const [notes, setNotes] = useState('')

  const token = localStorage.getItem('token')
  const manager = isManager(token)
  const [checking, setChecking] = useState(false)

  const runDueCheck = async () => {
    setChecking(true)
    setError('')
    try {
      const res = await api.post('/maintenance/check-due', {}, token)
      const created = res.data.data?.created ?? 0
      flash(
        created > 0
          ? `Due check finished — ${created} new alert(s) created.`
          : 'Due check finished — nothing newly overdue.'
      )
      fetchRecords()
    } catch (err) {
      setError(errorMessage(err, 'Due check failed.'))
    } finally {
      setChecking(false)
    }
  }

  const fetchRecords = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await api.get('/maintenance/', token)
      setRecords(res.data.data.maintenance || res.data.data.records || [])
    } catch (err) {
      setError(errorMessage(err, 'Failed to load maintenance records.'))
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    fetchRecords()
  }, [fetchRecords])

  const flash = (msg) => {
    setSuccess(msg)
    window.setTimeout(() => setSuccess(''), 2500)
  }

  const resetForm = () => {
    setVehicleId('')
    setType('oil_change')
    setStatus('scheduled')
    setDueDate('')
    setNotes('')
  }

  const createRecord = async (overrides = {}) => {
    setError('')
    try {
      await api.post(
        '/maintenance/',
        {
          vehicle_id: Number(vehicleId),
          type,
          status,
          due_date: dueDate || null,
          notes: notes.trim() || null,
          ...overrides,
        },
        token
      )
      resetForm()
      fetchRecords()
      flash('Maintenance record created.')
    } catch (err) {
      setError(errorMessage(err, 'Failed to create maintenance record.'))
    }
  }

  const handleCreate = (e) => {
    e.preventDefault()
    const intent = e.nativeEvent?.submitter?.value
    const overrides = intent === 'report' ? { type: 'repair', status: 'scheduled' } : {}
    return createRecord(overrides)
  }

  const handleStatusChange = async (id, nextStatus) => {
    setError('')
    try {
      await api.patch(`/maintenance/${id}`, { status: nextStatus }, token)
      setRecords((prev) =>
        prev.map((r) => (r.id === id ? { ...r, status: nextStatus } : r))
      )
      flash(`Marked ${label(nextStatus).toLowerCase()}.`)
    } catch (err) {
      setError(errorMessage(err, 'Failed to update status.'))
    }
  }

  const handleDelete = async (id) => {
    setError('')
    try {
      await api.del(`/maintenance/${id}`, token)
      setConfirmDeleteId(null)
      fetchRecords()
      flash('Record deleted.')
    } catch (err) {
      setError(errorMessage(err, 'Failed to delete record.'))
    }
  }

  const filtered = records.filter((r) => {
    if (typeFilter && r.type !== typeFilter) return false
    if (statusFilter && r.status !== statusFilter) return false
    return true
  })

  const pending = records.filter((r) => r.status !== 'completed').length

  return (
    <div>
      <div className='page-head'>
        <div>
          <h2 className='page-title'>Maintenance</h2>
          <p className='page-sub'>
            Schedule work, track progress, and log issues. {pending} open item{pending === 1 ? '' : 's'}.
          </p>
        </div>
        {manager && (
          <div className='page-actions'>
            <button
              type='button'
              className='btn btn-sm btn-ghost'
              onClick={runDueCheck}
              disabled={checking}
              aria-label='Run maintenance due check now'
            >
              {checking ? 'Checking…' : 'Run due check'}
            </button>
          </div>
        )}
      </div>

      {error && <p className='error'>{error}</p>}
      {success && <p className='success-note'>{success}</p>}

      {/* Create form */}
      <div className='panel'>
        <p className='panel-title'>Schedule maintenance</p>
        <p className='panel-sub'>Pick a vehicle, choose a type, and set a due date.</p>
        <form onSubmit={handleCreate}>
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
            <label>
              Type
              <select value={type} onChange={(e) => setType(e.target.value)} aria-label='Maintenance type'>
                {TYPES.map((t) => (
                  <option key={t} value={t}>
                    {label(t)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Status
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                aria-label='Maintenance status'
              >
                {STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {label(s)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Due date (optional)
              <input
                type='date'
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                aria-label='Due date'
              />
            </label>
          </div>
          <label style={{ display: 'block', marginTop: 12 }}>
            Notes (optional)
            <textarea
              rows={3}
              placeholder='e.g. Brake pads at 4 mm, replace next service.'
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              aria-label='Maintenance notes'
            />
          </label>
          <div className='form-row' style={{ marginTop: 16 }}>
            <button type='submit' className='btn'>
              Save record
            </button>
            <button type='submit' className='btn btn-ghost' value='report'>
              Report issue
            </button>
          </div>
        </form>
      </div>

      {/* List */}
      <div className='panel'>
        <p className='panel-title'>Maintenance log</p>
        <p className='panel-sub'>Filter by type or status, update progress, or remove old records.</p>

        <div className='filter-bar'>
          <label className='filter-label' htmlFor='maint-type'>
            Type
          </label>
          <select id='maint-type' value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
            <option value=''>All types</option>
            {TYPES.map((t) => (
              <option key={t} value={t}>
                {label(t)}
              </option>
            ))}
          </select>
          <label className='filter-label' htmlFor='maint-status'>
            Status
          </label>
          <select
            id='maint-status'
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value=''>All statuses</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {label(s)}
              </option>
            ))}
          </select>
          <span className='spacer' />
          <span className='filter-count'>
            {filtered.length} of {records.length} records
          </span>
        </div>

        {loading && records.length === 0 ? (
          <p className='empty'>Loading records…</p>
        ) : filtered.length === 0 ? (
          <p className='empty'>
            <strong>No maintenance records</strong>
            Schedule your first item above to get started.
          </p>
        ) : (
          <div className='data-table-wrap'>
            <table className='data-table'>
              <thead>
                <tr>
                  <th>Vehicle</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Due</th>
                  <th>Notes</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((r) => {
                  const days = daysUntil(r.due_date)
                  const dueSoon =
                    r.status !== 'completed' && days !== null && days >= 0 && days <= 7
                  const overdue =
                    r.status !== 'completed' && days !== null && days < 0
                  return (
                    <tr key={r.id} className={dueSoon ? 'row-due-soon' : overdue ? 'row-overdue' : ''}>
                      <td>#{r.vehicle_id}</td>
                      <td>{label(r.type)}</td>
                      <td>
                        <span className={`badge ${STATUS_BADGE[r.status] || 'badge-muted'}`}>
                          {label(r.status)}
                        </span>
                      </td>
                      <td className={overdue ? 'text-danger' : dueSoon ? 'text-warn' : 'cell-muted'}>
                        {r.due_date || '—'}
                        {dueSoon && <span className='hint'> · due soon</span>}
                        {overdue && <span className='hint'> · overdue</span>}
                      </td>
                      <td className='cell-muted'>{r.notes || '—'}</td>
                      <td>
                        <div className='row-actions'>
                          {r.status === 'scheduled' && (
                            <button
                              type='button'
                              className='btn btn-sm btn-warn'
                              onClick={() => handleStatusChange(r.id, 'in_progress')}
                            >
                              Start
                            </button>
                          )}
                          {r.status === 'in_progress' && (
                            <button
                              type='button'
                              className='btn btn-sm btn-success'
                              onClick={() => handleStatusChange(r.id, 'completed')}
                            >
                              Complete
                            </button>
                          )}
                          {confirmDeleteId === r.id ? (
                            <>
                              <button
                                type='button'
                                className='btn btn-sm btn-danger'
                                onClick={() => handleDelete(r.id)}
                              >
                                Confirm
                              </button>
                              <button
                                type='button'
                                className='btn btn-sm btn-ghost'
                                onClick={() => setConfirmDeleteId(null)}
                              >
                                Cancel
                              </button>
                            </>
                          ) : (
                            <button
                              type='button'
                              className='btn btn-sm btn-ghost'
                              onClick={() => setConfirmDeleteId(r.id)}
                              aria-label={`Delete maintenance record ${r.id}`}
                            >
                              Delete
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
