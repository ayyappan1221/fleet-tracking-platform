// Shared geofence coordinate parsing.
// Backend stores `coordinates` as a JSON *string*. Supported shapes:
//  - bbox: [minLat, minLng, maxLat, maxLng]
//  - polygon: [[lat, lng], [lat, lng], ...]
//  - center+radius: { lat, lng, radius } (radius in meters; also accepts
//    { latitude, longitude, radius } / { center: [lat, lng], radius })
export function parseGeofenceCoordinates(input) {
  if (input == null) return null
  let parsed = input
  if (typeof parsed === 'string') {
    const trimmed = parsed.trim()
    if (!trimmed) return null
    try {
      parsed = JSON.parse(trimmed)
    } catch {
      return null
    }
  }
  if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
    const lat = Number(parsed.lat ?? parsed.latitude ?? parsed.center?.[0])
    const lng = Number(parsed.lng ?? parsed.lon ?? parsed.longitude ?? parsed.center?.[1])
    const radius = Number(parsed.radius ?? parsed.radius_m ?? parsed.radiusMeters ?? 500)
    if (Number.isFinite(lat) && Number.isFinite(lng)) {
      return { kind: 'circle', center: [lat, lng], radius: Number.isFinite(radius) && radius > 0 ? radius : 500 }
    }
    // { coordinates: [...] } wrapper
    if (parsed.coordinates) return parseGeofenceCoordinates(parsed.coordinates)
    // { points: [...] } wrapper
    if (parsed.points) return parseGeofenceCoordinates(parsed.points)
    return null
  }
  if (!Array.isArray(parsed) || parsed.length === 0) return null

  const nums = parsed.map(Number)
  // bbox: exactly 4 finite numbers
  if (parsed.length === 4 && nums.every(Number.isFinite)) {
    const [minLat, minLng, maxLat, maxLng] = nums
    if (Math.abs(minLat) <= 90 && Math.abs(maxLat) <= 90 && Math.abs(minLng) <= 180 && Math.abs(maxLng) <= 180) {
      return { kind: 'bbox', bounds: [[Math.min(minLat, maxLat), Math.min(minLng, maxLng)], [Math.max(minLat, maxLat), Math.max(minLng, maxLng)]] }
    }
    return null
  }
  // polygon: array of [lat, lng] pairs (also accept {lat,lng} objects)
  const pts = []
  for (const p of parsed) {
    let lat
    let lng
    if (Array.isArray(p) && p.length >= 2) {
      lat = Number(p[0])
      lng = Number(p[1])
    } else if (p && typeof p === 'object') {
      lat = Number(p.lat ?? p.latitude)
      lng = Number(p.lng ?? p.lon ?? p.longitude)
    } else {
      return null
    }
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null
    if (Math.abs(lat) > 90 || Math.abs(lng) > 180) return null
    pts.push([lat, lng])
  }
  if (pts.length === 1) {
    return { kind: 'circle', center: pts[0], radius: 500 }
  }
  if (pts.length === 2) {
    // Two points -> treat as bbox corners
    const [[a1, b1], [a2, b2]] = pts
    return { kind: 'bbox', bounds: [[Math.min(a1, a2), Math.min(b1, b2)], [Math.max(a1, a2), Math.max(b1, b2)]] }
  }
  return { kind: 'polygon', positions: pts }
}

export function geofenceBounds(geom) {
  if (!geom) return null
  if (geom.kind === 'circle') return null
  if (geom.kind === 'bbox') return geom.bounds
  if (geom.kind === 'polygon') return geom.positions
  return null
}
