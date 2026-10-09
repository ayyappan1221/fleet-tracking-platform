/**
 * Client-side helpers for the JWT stored in localStorage.
 * Payload is decoded only (base64) — signature is verified server-side.
 */
export function decodeToken(token) {
  if (!token) return null;
  try {
    const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    return JSON.parse(atob(base64));
  } catch {
    return null;
  }
}

export function isTokenExpired(token) {
  const payload = decodeToken(token);
  if (!payload || typeof payload.exp !== 'number') return false;
  return payload.exp * 1000 < Date.now();
}

export function getTokenRole(token) {
  const payload = decodeToken(token);
  return payload?.role || null;
}

export function isManager(token) {
  return getTokenRole(token) === 'manager';
}
