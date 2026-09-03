import { useEffect, useState } from 'react'
import api from '../api.js'

export default function DashboardPage() {
  const [stats, setStats] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    const token = localStorage.getItem('token')
    api.get('/dashboard/summary', token)
      .then((res) => setStats(res.data.data))
      .catch((err) => {
        console.error(err)
        setError('Failed to load dashboard summary.')
      })
  }, [])

  if (error) {
    return (
      <section className='panel'>
        <p className='error'>{error}</p>
      </section>
    )
  }

  if (!stats) {
    return (
      <section className='panel'>
        <p className='empty'>Loading dashboard...</p>
      </section>
    )
  }

  const cards = [
    { label: 'Total Vehicles', value: stats.total_vehicles ?? 0 },
    { label: 'Active Vehicles', value: stats.active_vehicles ?? 0 },
    { label: 'Total Routes', value: stats.total_routes ?? 0 },
    { label: 'Active Routes', value: stats.active_routes ?? 0 },
    { label: 'Pending Maintenance', value: stats.pending_maintenance ?? 0 },
    { label: 'Unread Alerts', value: stats.unread_alerts ?? 0 },
    { label: 'Total Geofences', value: stats.total_geofences ?? 0 },
  ]

  return (
    <section className='panel'>
      <h2>Dashboard</h2>
      <div className='stat-grid'>
        {cards.map((card) => (
          <div key={card.label} className='stat-card'>
            <span className='stat-value'>{card.value}</span>
            <span className='stat-label'>{card.label}</span>
          </div>
        ))}
      </div>
    </section>
  )
}
