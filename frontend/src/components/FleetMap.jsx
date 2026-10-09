import { useEffect, useMemo, useState } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Circle, Polygon, Rectangle, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { parseGeofenceCoordinates } from '../utils/geofence.js'

// Markers are plain CSS divIcons — no CDN images, nothing to 404.
const vehicleIcon = L.divIcon({
  className: 'fleet-marker-dot',
  html: '<span></span>',
  iconSize: [16, 16],
  iconAnchor: [8, 8],
  popupAnchor: [0, -12],
})

// Surface a hint when OSM tiles cannot be fetched (offline / blocked).
function TileWatcher({ setFailed }) {
  const map = useMap()
  useEffect(() => {
    const onTileError = () => setFailed(true)
    map.on('tileerror', onTileError)
    return () => map.off('tileerror', onTileError)
  }, [map, setFailed])
  return null
}

const FALLBACK_CENTER = [20, 0] // world view when no markers exist
const FALLBACK_ZOOM = 2

function FitToMarkers({ points }) {
  const map = useMap()
  useEffect(() => {
    if (!points || points.length === 0) {
      map.setView(FALLBACK_CENTER, FALLBACK_ZOOM)
      return
    }
    if (points.length === 1) {
      map.setView(points[0], 13)
      return
    }
    map.fitBounds(L.latLngBounds(points), { padding: [32, 32] })
  }, [map, JSON.stringify(points)])
  return null
}

function GeofenceLayer({ geofence }) {
  const geom = useMemo(
    () => parseGeofenceCoordinates(geofence?.coordinates ?? geofence),
    [geofence?.coordinates, geofence],
  )
  if (!geom) return null
  const key = geofence?.id ?? geofence?.name ?? 'gf'
  if (geom.kind === 'circle') {
    return <Circle key={key} center={geom.center} radius={geom.radius} pathOptions={{ color: '#0f766e', weight: 2, fillOpacity: 0.12 }} />
  }
  if (geom.kind === 'bbox') {
    return <Rectangle key={key} bounds={geom.bounds} pathOptions={{ color: '#0f766e', weight: 2, fillOpacity: 0.12 }} />
  }
  return <Polygon key={key} positions={geom.positions} pathOptions={{ color: '#0f766e', weight: 2, fillOpacity: 0.12 }} />
}

// FleetMap: live vehicle positions + geofence overlays.
//  - vehicles: [{ id, license_plate, status, ... }]
//  - latestPositions: { [vehicleId]: { latitude, longitude, speed, recorded_at, ... } }
//    (also accepts a Map or an array of location rows with vehicle_id)
//  - geofences: [{ id, name, coordinates (JSON string), ... }]
export default function FleetMap({ vehicles = [], latestPositions = {}, geofences = [] }) {
  const [tileFailed, setTileFailed] = useState(false)

  const byId = useMemo(() => {
    const map = new Map(Object.entries(latestPositions || {}).map(([k, v]) => [String(k), v]))
    return map
  }, [latestPositions])

  const vehicleById = useMemo(() => {
    const m = new Map()
    for (const v of vehicles || []) m.set(String(v.id), v)
    return m
  }, [vehicles])

  const points = useMemo(() => {
    const pts = []
    // Vehicle positions
    for (const [, loc] of byId) {
      const lat = Number(loc?.latitude ?? loc?.lat)
      const lng = Number(loc?.longitude ?? loc?.lng ?? loc?.lon)
      if (Number.isFinite(lat) && Number.isFinite(lng)) pts.push([lat, lng])
    }
    // Include geofence corners so overlays stay in view when no vehicles
    if (pts.length === 0) {
      for (const g of geofences || []) {
        const geom = parseGeofenceCoordinates(g?.coordinates ?? g)
        if (!geom) continue
        if (geom.kind === 'circle') pts.push(geom.center)
        else if (geom.kind === 'bbox') pts.push(...geom.bounds)
        else if (geom.kind === 'polygon') pts.push(...geom.positions)
      }
    }
    return pts
  }, [byId, geofences])

  const markers = useMemo(() => {
    const rows = []
    for (const [vid, loc] of byId) {
      const lat = Number(loc?.latitude ?? loc?.lat)
      const lng = Number(loc?.longitude ?? loc?.lng ?? loc?.lon)
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) continue
      rows.push({ vid, loc, pos: [lat, lng], vehicle: vehicleById.get(String(vid)) })
    }
    return rows
  }, [byId, vehicleById])

  return (
    <div className="fleet-map-wrap">
      <MapContainer
        center={points[0] || FALLBACK_CENTER}
        zoom={points.length === 1 ? 13 : FALLBACK_ZOOM}
        scrollWheelZoom
        className="fleet-map"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
        />
        <TileWatcher setFailed={setTileFailed} />
        <FitToMarkers points={points} />
        {(geofences || []).map((g) => (
          <GeofenceLayer key={g.id ?? g.name} geofence={g} />
        ))}
        {markers.map(({ vid, loc, pos, vehicle }) => (
          <Marker key={vid} position={pos} icon={vehicleIcon}>
            <Popup>
              <div className="map-popup">
                <strong>{vehicle?.license_plate ?? `Vehicle ${vid}`}</strong>
                <br />
                Status: {vehicle?.status ?? '-'}
                <br />
                Speed: {loc?.speed != null ? `${loc.speed} km/h` : '-'}
                <br />
                Updated: {loc?.recorded_at ?? loc?.recordedAt ?? '-'}
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
      {tileFailed && (
        <div className="map-tiles-hint">Map tiles load from OpenStreetMap — check network if the map is blank.</div>
      )}
      {markers.length === 0 && (
        <p className="empty">
          No live positions yet — record a GPS ping to see vehicles on the map.
        </p>
      )}
    </div>
  )
}
