import { useEffect, useMemo, useState } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const FALLBACK_CENTER = [20, 0] // world view when no stops exist
const FALLBACK_ZOOM = 2

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

function numberedIcon(n, arrived = false) {
  return L.divIcon({
    className: arrived ? 'route-stop-icon is-arrived' : 'route-stop-icon',
    html: `<span>${n}</span>`,
    iconSize: [26, 26],
    iconAnchor: [13, 13],
    popupAnchor: [0, -12],
  })
}

const startIcon = L.divIcon({
  className: 'route-endpoint-icon route-start',
  html: '<span>A</span>',
  iconSize: [28, 28],
  iconAnchor: [14, 14],
  popupAnchor: [0, -12],
})

const endIcon = L.divIcon({
  className: 'route-endpoint-icon route-end',
  html: '<span>B</span>',
  iconSize: [28, 28],
  iconAnchor: [14, 14],
  popupAnchor: [0, -12],
})

function FitToPoints({ points }) {
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

function toLatLng(p) {
  if (!p) return null
  if (Array.isArray(p)) {
    const lat = Number(p[0])
    const lng = Number(p[1])
    if (Number.isFinite(lat) && Number.isFinite(lng)) return [lat, lng]
    return null
  }
  const lat = Number(p.latitude ?? p.lat)
  const lng = Number(p.longitude ?? p.lng ?? p.lon)
  if (Number.isFinite(lat) && Number.isFinite(lng)) return [lat, lng]
  return null
}

// RouteMap: route replay with stops.
//  - stops: [{ id, latitude, longitude, sequence, status, planned_at/arrived_at... }]
//  - path: optional actual GPS trail [[lat, lng], ...] or [{latitude, longitude}...]
//    falls back to stop order when omitted.
export default function RouteMap({ stops = [], path = [] }) {
  const [tileFailed, setTileFailed] = useState(false)

  const ordered = useMemo(() => {
    const list = [...(stops || [])].sort((a, b) => (a.sequence ?? 0) - (b.sequence ?? 0))
    return list
  }, [stops])

  const line = useMemo(() => {
    const fromPath = (path || []).map(toLatLng).filter(Boolean)
    if (fromPath.length >= 2) return fromPath
    const fromStops = ordered.map(toLatLng).filter(Boolean)
    return fromStops
  }, [path, ordered])

  const fitPoints = useMemo(() => {
    const pts = [...line]
    for (const s of ordered) {
      const p = toLatLng(s)
      if (p) pts.push(p)
    }
    return pts
  }, [line, ordered])

  return (
    <div className="fleet-map-wrap">
      <MapContainer
        center={fitPoints[0] || FALLBACK_CENTER}
        zoom={fitPoints.length === 1 ? 13 : FALLBACK_ZOOM}
        scrollWheelZoom
        className="fleet-map"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
        />
        <TileWatcher setFailed={setTileFailed} />
        <FitToPoints points={fitPoints} />
        {line.length >= 2 && (
          <Polyline positions={line} pathOptions={{ color: '#0f766e', weight: 4, opacity: 0.85 }} />
        )}
        {ordered.map((s, i) => {
          const pos = toLatLng(s)
          if (!pos) return null
          const isFirst = i === 0
          const isLast = i === ordered.length - 1
          const icon = isFirst ? startIcon : isLast ? endIcon : numberedIcon(s.sequence ?? i + 1, s.status === 'arrived')
          return (
            <Marker key={s.id ?? i} position={pos} icon={icon}>
              <Popup>
                <div className="map-popup">
                  <strong>Stop #{s.sequence ?? i + 1}</strong>
                  <br />
                  Status: {s.status ?? '-'}
                  <br />
                  Planned: {s.planned_at ?? s.plannedAt ?? '-'}
                  <br />
                  Arrived: {s.arrived_at ?? s.actual_at ?? s.arrivedAt ?? '-'}
                </div>
              </Popup>
            </Marker>
          )
        })}
      </MapContainer>
      {tileFailed && (
        <div className="map-tiles-hint">Map tiles load from OpenStreetMap — check network if the map is blank.</div>
      )}
      {ordered.length === 0 && <p className="empty">No stops to replay.</p>}
    </div>
  )
}
