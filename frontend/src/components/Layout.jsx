import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';

export default function Layout() {
  return (
    <div className="layout">
      <Sidebar />
      <div className="main-wrapper">
        <header className="topbar">
          <h1 className="topbar-title">Fleet Tracking</h1>
        </header>
        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
