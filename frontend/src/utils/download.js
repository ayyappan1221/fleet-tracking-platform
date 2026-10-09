import axios from 'axios'
import { authHeaders } from '../api.js'

const baseURL = import.meta.env.VITE_API_URL || '/api'

/**
 * Download a CSV report from the backend as a browser file download.
 * Uses raw axios with responseType 'blob' because api.js only supports JSON.
 *
 * @param {string} path  API path relative to baseURL, e.g. '/reports/alerts.csv'
 * @param {string} filename  Downloaded file name, e.g. 'alerts.csv'
 * @param {string} token  JWT auth token
 * @param {Record<string, string|number>} [params]  Query string params
 * @returns {Promise<boolean>} true when the download triggered
 */
export async function downloadCsv(path, filename, token, params = undefined) {
  try {
    const res = await axios.get(baseURL + path, {
      params,
      headers: authHeaders(token),
      responseType: 'blob',
    })
    triggerDownload(res.data, filename)
    return true
  } catch (err) {
    throw new Error(await csvErrorMessage(err))
  }
}

function triggerDownload(blob, filename) {
  const url = URL.createObjectURL(new Blob([blob], { type: 'text/csv;charset=utf-8' }))
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}

/** Server errors arrive as a JSON blob when responseType is 'blob' — decode them. */
async function csvErrorMessage(err) {
  const fallback = 'CSV export failed.'
  try {
    const data = err?.response?.data
    if (data instanceof Blob) {
      const text = await data.text()
      try {
        const parsed = JSON.parse(text)
        const detail = parsed?.detail ?? parsed?.message
        if (typeof detail === 'string') return detail
        if (Array.isArray(detail)) {
          return detail.map((d) => d?.msg || JSON.stringify(d)).join('; ')
        }
      } catch {
        /* not JSON — keep fallback */
      }
    }
    const detail = err?.response?.data?.detail
    if (typeof detail === 'string') return detail
  } catch {
    /* decoding failed — keep fallback */
  }
  if (err?.message && !err.response) return err.message
  return fallback
}
