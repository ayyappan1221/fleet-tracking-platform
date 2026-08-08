import axios from 'axios'

// axios instance pointed at the Vite proxy (/api goes to :8000).
const client = axios.create({ baseURL: '/api' })

export function authHeaders(token) {
  return { Authorization: `Bearer ${token}` }
}

export default {
  login(email, password) {
    const body = new URLSearchParams()
    body.append('username', email)
    body.append('password', password)
    return client.post('/auth/login', body)
  },
  get(path, token) {
    return client.get(path, { headers: authHeaders(token) })
  },
  post(path, data, token) {
    return client.post(path, data, { headers: authHeaders(token) })
  },
}