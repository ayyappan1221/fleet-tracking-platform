/**
 * Extract a human-readable message from an axios/FastAPI error.
 * Success envelope uses `data.message`; HTTP errors use FastAPI `detail`
 * (string or validation-error array).
 */
export function errorMessage(err, fallback = 'Something went wrong.') {
  const data = err?.response?.data;
  const detail = data?.detail ?? data?.message;
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (Array.isArray(detail) && detail.length) {
    return detail
      .map((d) => (typeof d === 'string' ? d : d?.msg || JSON.stringify(d)))
      .join('; ');
  }
  return fallback;
}
