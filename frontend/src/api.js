import axios from 'axios'

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || '/api' })

const AUTH_PATHS = ['/auth/login', '/auth/register']

// 401 on any non-auth request: clear session and return to login once.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status
    const url = error?.config?.url || ''
    const isAuthRequest = AUTH_PATHS.some((p) => url.includes(p))
    if (status === 401 && !isAuthRequest) {
      localStorage.removeItem('token')
      if (window.location.pathname !== '/login') {
        window.location.assign('/login')
      }
    }
    return Promise.reject(error)
  }
)

export function authHeaders(token) {
  if (!token) return {}
  return { Authorization: `Bearer ${token}` }
}

function apiRoot() {
  const base = import.meta.env.VITE_API_URL || '/api'
  return base.replace(/\/api\/?$/, '') || '/'
}

export function backendHealth() {
  return axios.get(`${apiRoot()}/health`, { timeout: 8000 })
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
  requestOtp(email, purpose) {
    return api.post('/auth/request-otp', { email, purpose }, { headers: { 'Content-Type': 'application/json' } })
  },
  verifySignup(email, code) {
    return api.post(
      '/auth/verify-signup',
      { email, code, purpose: 'signup_verify' },
      { headers: { 'Content-Type': 'application/json' } }
    )
  },
  loginWithOtp(email, code) {
    return api.post(
      '/auth/login/otp',
      { email, code, purpose: 'login_otp' },
      { headers: { 'Content-Type': 'application/json' } }
    )
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
