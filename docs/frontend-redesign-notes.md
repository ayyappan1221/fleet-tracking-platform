# Frontend Redesign Notes

Scope: visual restyle of `frontend/src` (simple, classy, human-made look) plus reliable
free OSM map rendering. No backend changes, no API path/envelope changes, no new npm
dependencies, no paid map providers or keys. Pages, data flows, role gating, polling,
forms, filters, and the `{ success, data, message }` contract are untouched.

## Verification

- `npm run build` (Vite 6.4.3): **154 modules transformed, built in 2.94s**
  - `dist/index.html` — 0.40 kB (gzip 0.27 kB)
  - `dist/assets/index-B3HN4jfC.css` — 36.64 kB (gzip 11.06 kB)
  - `dist/assets/index-oQQjL086.js` — 449.78 kB (gzip 139.17 kB)
- Grep over `frontend/src` clean: no `gradient`, `@keyframes`, `animation`, `unpkg`,
  `#0e7490`, `#22d3ee`, `#06b6d4`, or background/gradient inline styles remain.
- LSP diagnostics tool was unavailable this session (server connection closed);
  build success is the syntax/transform gate (plain JS — no tsc).

## Changed files

### `frontend/src/index.css`

**Design tokens (`:root`)** — warm stone neutral palette, single teal accent:

- `--bg: #fafaf9`, `--surface-2: #f6f7f6`, `--ink: #1c1917`, `--muted: #78716c`,
  `--line: #e7e5e4`
- `--brand: #0f766e`, `--brand-600: #115e59`, `--brand-700: #134e4a`,
  `--brand-050: #f0fdfa`, `--navy: #1c1917`, `--navy-2: #292524`
- Shadows softened (`rgba(28, 25, 23, …)`), `--ring: rgba(15, 118, 110, 0.22)`

**Flash removed / flattened:**

- Skeleton shimmer → flat `#eceae8`; `@keyframes shimmer` deleted
- `.pulse-dot` pulse animation removed (static dot kept); `@keyframes pulse` deleted
- `.auth-brand` radial gradients → solid `var(--navy)`
- `.sidebar` gradient → solid `var(--navy)`; `.sidebar-link.active` glow removed
- `.brand-logo` / `.avatar` gradients → solid `var(--brand)`
- `.brand-points .tick` cyan → teal (`rgba(15,118,110,0.25)` / `#99f6e4`)
- `.map-placeholder` grid/gradient → `var(--surface-2)`
- `.badge-brand` border `#a5f3fc` → `#99f6e4`; `.step.active .step-dot` ring → teal
- Role chips: base teal, `.manager` solid brand, `.mechanic` neutral slate
- Kept intentionally: `.stat-icon` semantic tints, severity/badge status colors,
  `errorMessage` colors (semantic status colors are not "flash")

**New map section** (before pager styles) — fixes zero-height maps:

- `.fleet-map-wrap` — relative, 1px border, radius 12, overflow hidden, `--surface-2`
- `.fleet-map, .leaflet-container { height: 420px; width: 100%; border-radius: 12px }`
- `.leaflet-div-icon` white-square default neutralized (transparent bg, no border)
- `.fleet-marker-dot span` — 16px teal dot with 2px white border
- `.map-tiles-hint` — absolute bottom-center pill (z-index 500, pointer-events none)
- Leaflet popup restyled to app font/size + soft shadow

Required classes preserved: `.leaflet-container` (420px), `.stat-value`, `.stat-label`,
`.sidebar-signout`.

### `frontend/src/components/FleetMap.jsx`

- Removed unpkg CDN `DefaultIcon` override (no more network dependency for markers)
- Markers now explicit `L.divIcon` (`className: 'fleet-marker-dot'`, `<span></span>`,
  16×16, anchor `[8, 8]`, popupAnchor `[0, -12]`) via the `icon` prop — pure CSS dot
- `TileLayer` gains `maxZoom={19}`
- Added `TileWatcher` (`useMap` + `tileerror` listener) → shows `.map-tiles-hint`
  ("Map tiles load from OpenStreetMap — check network if the map is blank.")
- Removed inline `style={{ height: '100%' }}` — CSS (`.fleet-map` 420px) drives height
- Geofence shapes (Circle/Rectangle/Polygon) recolored `#0e7490` → `#0f766e`

### `frontend/src/components/RouteMap.jsx`

- `TileLayer` gains `maxZoom={19}`
- Added same `TileWatcher` + `.map-tiles-hint` fallback
- Recolored polyline, default stop color, and non-arrived stop icons
  `#0e7490` → `#0f766e` (start `#059669` / end `#b91c1c` kept — semantic A/B)
- Removed inline `style={{ height: '100%' }}` — CSS drives height

### No-JSX-change files (verified)

- `Sidebar.jsx`, `Layout.jsx` — CSS-only restyle applies; Layout's inline styles are
  layout-only (flex/gap/minWidth), Sidebar has none
- `api.js`, `App.jsx`, `main.jsx`, `ProtectedRoute.jsx`, `utils/*` — untouched
- All 9 pages — read for audit; no inline flashy styles found
