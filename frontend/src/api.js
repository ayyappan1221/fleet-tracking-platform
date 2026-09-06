import axios from 'axios'

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || '/api' })

export function authHeaders(token) {
  if (!token) return {}
  return { Authorization: `Bearer ${token}` }
}

export default {
  login(email, password) {
    const body = new URLSearchParams()
    body.append('username', email)
    body.append('password', password)
    return api.post('/auth/login', body)
  },
  register(data) {
    return api.post('/auth/register', data, { headers: { 'Content-Type': 'application/json' } })
  },
  get(path, token) {
    const headers = token ? authHeaders(token) : {}
    return api.get(path, { headers })
  },
  post(path, data, token) {
    const headers = { 'Content-Type': 'application/json', ...authHeaders(token) }
    return api.post(path, data, { headers })
  },
  patch(path, data, token) {
    const headers = { 'Content-Type': 'application/json', ...authHeaders(token) }
    return api.patch(path, data, { headers })
  },
  del(path, token) {
    const headers = token ? authHeaders(token) : {}
    return api.delete(path, { headers })
  },
}
