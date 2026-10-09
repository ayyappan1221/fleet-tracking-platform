import { Navigate, Outlet } from 'react-router-dom';
import { isTokenExpired } from '../utils/auth.js';

export default function ProtectedRoute() {
  const token = localStorage.getItem('token');

  if (!token || isTokenExpired(token)) {
    localStorage.removeItem('token');
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
