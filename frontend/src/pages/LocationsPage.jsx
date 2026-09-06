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

export default function LocationsPage() {
  const [locations, setLocations] = useState([])
  const [total, setTotal] = useState(0)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  // Filters
  const [vehicleFilter, setVehicleFilter] = useState('')
  const [skip, setSkip] = useState(0)
  const limit = 20

  // Pinger form
  const [pingVehicleId, setPingVehicleId] = useState('')
  const [pingLat, setPingLat] = useState('')
  const [pingLng, setPingLng] = useState('')
  const [pingSpeed, setPingSpeed] = useState('')
  const [pingHeading, setPingHeading] = useState('')

  // Latest lookup
  const [lookupId, setLookupId] = useState('')
  const [latestLocation, setLatestLocation] = useState(null)
  const [latestError, setLatestError] = useState('')

  const token = localStorage.getItem('token')

  const fetchLocations = async () => {
    try {
      let url = `/locations/?skip=${skip}&limit=${limit}`
      if (vehicleFilter) {
        url += `&vehicle_id=${vehicleFilter}`
      }
      const res = await api.get(url, token)
      setLocations(res.data.data.locations)
      setTotal(res.data.data.total)
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to load locations.')
    }
  }

  useEffect(() => {
    fetchLocations()
  }, [skip, vehicleFilter])

  const handlePing = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const payload = {
        vehicle_id: Number(pingVehicleId),
        latitude: Number(pingLat),
        longitude: Number(pingLng),
      }
      if (pingSpeed !== '') payload.speed = Number(pingSpeed)
      if (pingHeading !== '') payload.heading = Number(pingHeading)

      await api.post('/locations/', payload, token)
      setPingVehicleId('')
      setPingLat('')
      setPingLng('')
      setPingSpeed('')
      setPingHeading('')
      fetchLocations()
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to record location.')
    } finally {
      setLoading(false)
    }
  }

  const handleLatestLookup = async () => {
    setLatestError('')
    setLatestLocation(null)
    if (!lookupId) return
    try {
      const res = await api.get(`/locations/vehicle/${lookupId}/latest`, token)
      setLatestLocation(res.data.data)
    } catch (err) {
      if (err.response?.status === 404) {
        setLatestError('No locations found for this vehicle yet.')
      } else {
        setLatestError(err.response?.data?.message || 'Failed to look up location.')
      }
    }
  }

  const handleFilterChange = (val) => {
    setVehicleFilter(val)
    setSkip(0)
  }

  const hasNext = skip + limit < total
  const hasPrev = skip > 0

  return (
    <div className='panel'>
      <h2>Locations</h2>
      {error && <p className='error'>{error}</p>}

      {/* Pinger Form */}
      <div style={{ marginBottom: '24px' }}>
        <h3 style={{ fontSize: '14px', marginBottom: '12px' }}>Record Location (GPS Pinger)</h3>
        <form onSubmit={handlePing} className='vehicle-form'>
          <label style={labelStyle}>
            Vehicle ID
            <input
              style={inputStyle}
              type='number'
              value={pingVehicleId}
              onChange={(e) => setPingVehicleId(e.target.value)}
              required
              min='1'
            />
          </label>
          <label style={labelStyle}>
            Latitude (-90 to 90)
            <input
              style={inputStyle}
              type='number'
              step='any'
              min='-90'
              max='90'
              placeholder='e.g. 40.7128'
              value={pingLat}
              onChange={(e) => setPingLat(e.target.value)}
              required
            />
          </label>
          <label style={labelStyle}>
            Longitude (-180 to 180)
            <input
              style={inputStyle}
              type='number'
              step='any'
              min='-180'
              max='180'
              placeholder='e.g. -74.0060'
              value={pingLng}
              onChange={(e) => setPingLng(e.target.value)}
              required
            />
          </label>
          <label style={labelStyle}>
            Speed (km/h, optional)
            <input
              style={inputStyle}
              type='number'
              step='any'
              min='0'
              placeholder='0 or more'
              value={pingSpeed}
              onChange={(e) => setPingSpeed(e.target.value)}
            />
          </label>
          <label style={labelStyle}>
            Heading (0-360, optional)
            <input
              style={inputStyle}
              type='number'
              step='any'
              min='0'
              max='360'
              placeholder='0-360 degrees'
              value={pingHeading}
              onChange={(e) => setPingHeading(e.target.value)}
            />
          </label>
          <div style={{ gridColumn: '1 / -1' }}>
            <button type='submit' disabled={loading}>
              {loading ? 'Recording...' : 'Record Location'}
            </button>
          </div>
        </form>
      </div>

      {/* Latest Lookup */}
      <div style={{ marginBottom: '24px' }}>
        <h3 style={{ fontSize: '14px', marginBottom: '12px' }}>Latest Location Lookup</h3>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-end' }}>
          <label style={{ ...labelStyle, flex: 1, marginBottom: 0 }}>
            Vehicle ID
            <input
              style={inputStyle}
              type='number'
              min='1'
              placeholder='Enter vehicle ID'
              value={lookupId}
              onChange={(e) => setLookupId(e.target.value)}
            />
          </label>
          <button
            type='button'
            style={{ ...btnSmall, marginBottom: '14px' }}
            onClick={handleLatestLookup}
          >
            Look Up
          </button>
        </div>
        {latestError && <p className='error'>{latestError}</p>}
        {latestLocation && (
          <table className='data-table' style={{ marginTop: '12px' }}>
            <thead>
              <tr>
                <th>Vehicle</th>
                <th>Latitude</th>
                <th>Longitude</th>
                <th>Speed</th>
                <th>Heading</th>
                <th>Recorded At</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>{latestLocation.vehicle_id}</td>
                <td>{latestLocation.latitude}</td>
                <td>{latestLocation.longitude}</td>
                <td>{latestLocation.speed != null ? latestLocation.speed : '-'}</td>
                <td>{latestLocation.heading != null ? latestLocation.heading : '-'}</td>
                <td>{latestLocation.recorded_at}</td>
              </tr>
            </tbody>
          </table>
        )}
      </div>

      {/* Filter + Pagination */}
      <div style={{ marginBottom: '20px', display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
        <strong style={{ fontSize: '13px' }}>Filter by Vehicle:</strong>
        <input
          type='number'
          min='1'
          placeholder='Vehicle ID'
          value={vehicleFilter}
          onChange={(e) => handleFilterChange(e.target.value)}
          style={{ ...inputStyle, width: '120px', marginTop: 0 }}
        />
        <span style={{ fontSize: '13px', color: '#6b7684' }}>
          {total} total
        </span>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: '6px' }}>
          <button
            type='button'
            style={{ ...btnSmall, background: hasPrev ? '#0e7490' : '#94a3b8' }}
            disabled={!hasPrev}
            onClick={() => setSkip(Math.max(0, skip - limit))}
          >
            Previous
          </button>
          <button
            type='button'
            style={{ ...btnSmall, background: hasNext ? '#0e7490' : '#94a3b8' }}
            disabled={!hasNext}
            onClick={() => setSkip(skip + limit)}
          >
            Next
          </button>
        </div>
      </div>

      {/* Locations Table */}
      {locations.length === 0 ? (
        <p className='empty'>No locations found.</p>
      ) : (
        <table className='data-table'>
          <thead>
            <tr>
              <th>ID</th>
              <th>Vehicle</th>
              <th>Latitude</th>
              <th>Longitude</th>
              <th>Speed</th>
              <th>Heading</th>
              <th>Recorded At</th>
            </tr>
          </thead>
          <tbody>
            {locations.map((loc) => (
              <tr key={loc.id}>
                <td>{loc.id}</td>
                <td>{loc.vehicle_id}</td>
                <td>{loc.latitude}</td>
                <td>{loc.longitude}</td>
                <td>{loc.speed != null ? loc.speed : '-'}</td>
                <td>{loc.heading != null ? loc.heading : '-'}</td>
                <td>{loc.recorded_at}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
