import { useState, useEffect, useCallback } from 'react'
import api from '../api.js'
import { errorMessage } from '../utils/errors.js'
import { isManager } from '../utils/auth.js'
import { downloadCsv } from '../utils/download.js'

const SEVERITIES = ['info', 'warning', 'critical']
const EXPORT_DAY_OPTIONS = [7, 30, 90, 365]

const SEVERITY_BADGE = {
  info: 'severity-info',
  warning: 'severity-warning',
  critical: 'severity-critical',
}

function severityLabel(s) {
  if (s === 'critical') return 'Critical'
  if (s === 'warning') return 'Warning'
  if (s === 'info') return 'Info'
  return String(s).replace(/\b\w/g, (c) => c.toUpperCase())
}

export default function AlertsPage() {
  const [alerts, setAlerts] = useState([])
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)
  const [severityFilter, setSeverityFilter] = useState('')
  const [readFilter, setReadFilter] = useState('') // '', 'unread', 'read'
  const [exportDays, setExportDays] = useState(30)
  const [exporting, setExporting] = useState(false)

  const token = localStorage.getItem('token')
  const manager = isManager(token)

  const fetchAlerts = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await api.get('/alerts/', token)
      setAlerts(res.data.data.alerts || [])
    } catch (err) {
      setError(errorMessage(err, 'Failed to load alerts.'))
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    fetchAlerts()
  }, [fetchAlerts])

  const flash = (msg) => {
    setSuccess(msg)
    window.setTimeout(() => setSuccess(''), 2500)
  }

  const handleMarkRead = async (id) => {
    setError('')
    try {
      await api.patch(`/alerts/${id}/read`, {}, token)
      setAlerts((prev) => prev.map((a) => (a.id === id ? { ...a, is_read: true } : a)))
      flash('Marked as read.')
    } catch (err) {
      setError(errorMessage(err, 'Failed to mark alert as read.'))
    }
  }

  const handleExport = async () => {
    setExporting(true)
    setError('')
    try {
      await downloadCsv(
        '/reports/alerts.csv',
        `alerts-last-${exportDays}d.csv`,
        token,
        { days: exportDays }
      )
      flash('Alerts CSV downloaded.')
    } catch (err) {
      setError(err?.message || errorMessage(err, 'Alerts CSV export failed.'))
    } finally {
      setExporting(false)
    }
  }

  // Visible alerts: manager sees all; driver only vehicle-linked or non-manager-owned
  const visible = alerts.filter(
    (a) => manager || a.vehicle_id != null || !a.is_system
  )

  const filtered = visible.filter((a) => {
    if (severityFilter && a.severity !== severityFilter) return false
    if (readFilter === 'unread' && a.is_read) return false
    if (readFilter === 'read' && !a.is_read) return false
    return true
  })

  const unreadCount = visible.filter((a) => !a.is_read).length

  return (
    <div>
      <div className='page-head'>
        <div>
          <h2 className='page-title'>Alerts</h2>
          <p className='page-sub'>
            Geofence breaches, maintenance warnings, and system notices.{' '}
            {unreadCount > 0 ? `${unreadCount} unread.` : 'All caught up.'}
          </p>
        </div>
        <div className='page-actions'>
          <label className='filter-label' htmlFor='alerts-export-days'>
            Export days
          </label>
          <select
            id='alerts-export-days'
            value={exportDays}
            onChange={(e) => setExportDays(Number(e.target.value))}
            aria-label='Number of days to include in the alerts CSV export'
            style={{ maxWidth: 110 }}
          >
            {EXPORT_DAY_OPTIONS.map((d) => (
              <option key={d} value={d}>
                Last {d}d
              </option>
            ))}
          </select>
          <button
            type='button'
            className='btn btn-sm btn-ghost'
            onClick={handleExport}
            disabled={exporting}
            aria-label='Download alerts CSV'
          >
            {exporting ? 'Preparing…' : 'Export CSV'}
          </button>
          <button type='button' className='btn btn-sm btn-ghost' onClick={fetchAlerts} disabled={loading}>
            {loading ? 'Refreshing…' : 'Refresh'}
          </button>
        </div>
      </div>

      {error && <p className='error'>{error}</p>}
      {success && <p className='success-note'>{success}</p>}

      <div className='panel'>
        <p className='panel-title'>Alert feed</p>
        <p className='panel-sub'>Filter by severity or read state. Mark items as read when handled.</p>

        <div className='filter-bar'>
          <div className='tabs' role='tablist' aria-label='Alert severity'>
            <button
              type='button'
              role='tab'
              aria-selected={severityFilter === ''}
              className={`tab ${severityFilter === '' ? 'active' : ''}`}
              onClick={() => setSeverityFilter('')}
            >
              All severities
            </button>
            {SEVERITIES.map((s) => (
              <button
                key={s}
                type='button'
                role='tab'
                aria-selected={severityFilter === s}
                className={`tab ${severityFilter === s ? 'active' : ''}`}
                onClick={() => setSeverityFilter(s)}
              >
                {severityLabel(s)}
              </button>
            ))}
          </div>
          <div className='tabs' role='tablist' aria-label='Alert read state'>
            <button
              type='button'
              role='tab'
              aria-selected={readFilter === ''}
              className={`tab ${readFilter === '' ? 'active' : ''}`}
              onClick={() => setReadFilter('')}
            >
              All
            </button>
            <button
              type='button'
              role='tab'
              aria-selected={readFilter === 'unread'}
              className={`tab ${readFilter === 'unread' ? 'active' : ''}`}
              onClick={() => setReadFilter('unread')}
            >
              Unread
            </button>
            <button
              type='button'
              role='tab'
              aria-selected={readFilter === 'read'}
              className={`tab ${readFilter === 'read' ? 'active' : ''}`}
              onClick={() => setReadFilter('read')}
            >
              Read
            </button>
          </div>
          <span className='spacer' />
          <span className='filter-count'>
            {filtered.length} of {visible.length} alerts
          </span>
        </div>

        {filtered.length === 0 ? (
          <div className='empty'>
            <strong>All clear</strong>
            No alerts match the current filters.
          </div>
        ) : (
          <ul className='alert-feed'>
            {filtered.map((a) => (
              <li key={a.id} className={`alert-item ${a.is_read ? 'is-read' : ''}`}>
                <span className={`severity-dot ${a.severity || 'info'}`} aria-hidden='true' />
                <div className='alert-body'>
                  <div className='alert-head'>
                    <span className={`badge ${SEVERITY_BADGE[a.severity] || 'badge-muted'}`}>
                      {severityLabel(a.severity)}
                    </span>
                    <strong className='alert-type'>{a.type || a.kind || 'Alert'}</strong>
                    {a.vehicle_id != null && <span className='cell-muted'>Vehicle #{a.vehicle_id}</span>}
                    {a.route_id != null && <span className='cell-muted'>Route #{a.route_id}</span>}
                    {a.geofence_id != null && <span className='cell-muted'>Zone #{a.geofence_id}</span>}
                    <span className='spacer' />
                    <span className='cell-muted alert-time'>{a.created_at || a.time || ''}</span>
                    {a.is_read ? (
                      <span className='badge badge-muted'>Read</span>
                    ) : (
                      <span className='badge badge-warn'>Unread</span>
                    )}
                  </div>
                  {a.message && <p className='alert-message'>{a.message}</p>}
                </div>
                {!a.is_read && (
                  <button
                    type='button'
                    className='btn btn-sm btn-ghost'
                    onClick={() => handleMarkRead(a.id)}
                    aria-label={`Mark alert ${a.id} as read`}
                  >
                    Mark read
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
