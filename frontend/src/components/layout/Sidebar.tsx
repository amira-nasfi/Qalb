import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { LayoutDashboard, UploadCloud, FileText, ShieldAlert, Users, LogOut, HeartPulse } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { logout } from '../../api/auth';
import './Sidebar.css';

export const Sidebar: React.FC = () => {
  const { user, role, clearAuth } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    const refresh = localStorage.getItem("refresh_token");
    if (refresh) {
      await logout(refresh);
    }
    clearAuth();
    navigate("/login");
  };

  const isFieldAgent = role === 'FIELD_AGENT';
  const isPhysician = role === 'PHYSICIAN';
  const isAdmin = role === 'ADMIN';

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <img src="/logo.png" alt="Qalb Logo" className="h-10 w-auto object-contain drop-shadow-sm" />
      </div>
      
      <nav className="sidebar-nav">
        <div className="nav-section">
          <p className="nav-section-title">Home</p>
          <NavLink to="/" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} end>
            <LayoutDashboard size={20} />
            <span>Overview</span>
          </NavLink>
        </div>

        {(isFieldAgent || isPhysician) && (
          <div className="nav-section">
            <p className="nav-section-title">Operations</p>
            <NavLink to="/upload" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <UploadCloud size={20} />
              <span>Upload ECG</span>
            </NavLink>
          </div>
        )}

        {(isPhysician || isAdmin) && (
          <div className="nav-section">
            <p className="nav-section-title">Clinical</p>
            <NavLink to="/dashboard" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <FileText size={20} />
              <span>Review Queue</span>
            </NavLink>
          </div>
        )}

        {isAdmin && (
          <div className="nav-section">
            <p className="nav-section-title">System</p>
            <NavLink to="/admin" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} end>
              <ShieldAlert size={20} />
              <span>Audit Log</span>
            </NavLink>
            <NavLink to="/admin/users" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <Users size={20} />
              <span>Users</span>
            </NavLink>
          </div>
        )}
      </nav>

      <div className="sidebar-footer">
        <button className="nav-item text-critical hover:bg-red-50 w-full justify-start" onClick={handleLogout}>
          <LogOut size={20} />
          <span>Logout</span>
        </button>
        <div className="user-profile">
          <div className="avatar">
            {user?.first_name?.[0]}{user?.last_name?.[0] || user?.username?.[0]}
          </div>
          <div className="user-info">
            <span className="user-name">{user?.full_name || user?.username}</span>
            <span className="user-role">{role}</span>
          </div>
        </div>
      </div>
    </aside>
  );
};
