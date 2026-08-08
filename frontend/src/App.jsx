import { useEffect, useState } from 'react'
import api from './api.js'

function App() {
  const [token, setToken] = useState(() => localStorage.getItem('token') || '')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loginError, setLoginError] = useState('')
  const [vehicles, setVehicles] = useState([])
  const [form, setForm] = useState({
    license_plate: '',
    make: '',
    model: '',
    year: '',
    vin: '',
  })
  const [formError, setFormError] = useState('')

  useEffect(() => {
    if (token) fetchVehicles()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  async function fetchVehicles() {
    try {
      const res = await api.get('/vehicles/', token)
      setVehicles(res.data.data.vehicles)
    } catch (err) {
      console.error(err)
    }
  }

  async function handleLogin(e) {
    e.preventDefault()
    setLoginError('')
    try {
      const res = await api.login(email, password)
      const newToken = res.data.data.access_token
      localStorage.setItem('token', newToken)
      setToken(newToken)
    } catch (err) {
      setLoginError(
        err.response?.data?.message || 'Login failed. Check your credentials.'
      )
    }
  }

  function handleLogout() {
    localStorage.removeItem('token')
    setToken('')
    setVehicles([])
  }

  async function handleAddVehicle(e) {
    e.preventDefault()
    setFormError('')
    const payload = { ...form, year: Number(form.year) || null }
    try {
      await api.post('/vehicles/', payload, token)
      setForm({ license_plate: '', make: '', model: '', year: '', vin: '' })
      fetchVehicles()
    } catch (err) {
      setFormError(err.response?.data?.message || 'Could not add vehicle.')
    }
  }

  if (!token) {
    return (
      <div className="auth-wrap">
        <form className="auth-card" onSubmit={handleLogin}>
          <h1>Fleet Tracking</h1>
          <p className="sub">Vehicle tracking &amp; fleet monitoring platform</p>
          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>
          {loginError && <p className="error">{loginError}</p>}
          <button type="submit">Sign in</button>
        </form>
      </div>
    )
  }

  return (
    <div className="app">
      <header className="topbar">
        <h1>Fleet Tracking</h1>
        <div className="topbar-right">
          <span className="user">{email}</span>
          <button onClick={handleLogout}>Sign out</button>
        </div>
      </header>

      <main>
        <section className="panel">
          <h2>Add vehicle</h2>
          <form className="vehicle-form" onSubmit={handleAddVehicle}>
            <input
              placeholder="License plate"
              value={form.license_plate}
              onChange={(e) =>
                setForm({ ...form, license_plate: e.target.value })
              }
              required
            />
            <input
              placeholder="Make"
              value={form.make}
              onChange={(e) => setForm({ ...form, make: e.target.value })}
            />
            <input
              placeholder="Model"
              value={form.model}
              onChange={(e) => setForm({ ...form, model: e.target.value })}
            />
            <input
              placeholder="Year"
              type="number"
              value={form.year}
              onChange={(e) => setForm({ ...form, year: e.target.value })}
            />
            <input
              placeholder="VIN"
              value={form.vin}
              onChange={(e) => setForm({ ...form, vin: e.target.value })}
            />
            <button type="submit">Add vehicle</button>
          </form>
          {formError && <p className="error">{formError}</p>}
        </section>

        <section className="panel">
          <h2>Vehicles</h2>
          {vehicles.length === 0 ? (
            <p className="empty">No vehicles yet. Add your first one above.</p>
          ) : (
            <table className="vehicles">
              <thead>
                <tr>
                  <th>Plate</th>
                  <th>Make</th>
                  <th>Model</th>
                  <th>Year</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {vehicles.map((v) => (
                  <tr key={v.id}>
                    <td>{v.license_plate}</td>
                    <td>{v.make || '-'}</td>
                    <td>{v.model || '-'}</td>
                    <td>{v.year}</td>
                    <td>{v.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </main>
    </div>
  )
}

export default App