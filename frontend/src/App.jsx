import { Routes, Route } from 'react-router-dom'
import AuthPage from './pages/AuthPage.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import VehiclesPage from './pages/VehiclesPage.jsx'
import RoutesPage from './pages/RoutesPage.jsx'
import LocationsPage from './pages/LocationsPage.jsx'
import MaintenancePage from './pages/MaintenancePage.jsx'
import AlertsPage from './pages/AlertsPage.jsx'
import GeofencesPage from './pages/GeofencesPage.jsx'
import DriversPage from './pages/DriversPage.jsx'
import FuelPage from './pages/FuelPage.jsx'
import InspectionsPage from './pages/InspectionsPage.jsx'
import NotFound from './pages/NotFound.jsx'
import ProtectedRoute from './components/ProtectedRoute.jsx'
import Layout from './components/Layout.jsx'

function App() {
  return (
    <Routes>
      <Route path='/login' element={<AuthPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path='/' element={<DashboardPage />} />
          <Route path='/vehicles' element={<VehiclesPage />} />
          <Route path='/routes' element={<RoutesPage />} />
          <Route path='/locations' element={<LocationsPage />} />
          <Route path='/drivers' element={<DriversPage />} />
          <Route path='/fuel' element={<FuelPage />} />
          <Route path='/inspections' element={<InspectionsPage />} />
          <Route path='/maintenance' element={<MaintenancePage />} />
          <Route path='/alerts' element={<AlertsPage />} />
          <Route path='/geofences' element={<GeofencesPage />} />
          <Route path='*' element={<NotFound />} />
        </Route>
      </Route>
      <Route path='*' element={<NotFound />} />
    </Routes>
  )
}

export default App
