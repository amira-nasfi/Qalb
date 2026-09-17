import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { UploadCloud, FileText, ShieldAlert, Users, LogOut, Stethoscope } from 'lucide-react';
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

  const roleLabel = 
    role === 'PHYSICIAN' ? 'Médecin' :
    role === 'FIELD_AGENT' ? 'Agent de terrain' :
    role === 'ADMIN' ? 'Administrateur' : role;

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <img src="/logo.png" alt="Qalb Logo" className="sidebar-logo" />
      </div>
      
      <nav className="sidebar-nav">

        {/* Praticien de terrain (FIELD_AGENT) */}
        {isFieldAgent && (
          <div className="nav-section">
            <p className="nav-section-title">Dispensaire</p>
            <NavLink to="/upload" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <UploadCloud size={20} />
              <span>Acquisition ECG</span>
            </NavLink>
            <NavLink to="/dashboard" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <FileText size={20} />
              <span>Suivi des examens</span>
            </NavLink>
          </div>
        )}

        {/* Médecin Télé-expert (PHYSICIAN) */}
        {isPhysician && (
          <div className="nav-section">
            <p className="nav-section-title">Télé-Expertise</p>
            <NavLink to="/doctor" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <Stethoscope size={20} />
              <span>Portail Télé-Interprétation</span>
            </NavLink>
          </div>
        )}

        {isAdmin && (
          <div className="nav-section">
            <p className="nav-section-title">Système</p>
            <NavLink to="/admin" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} end>
              <ShieldAlert size={20} />
              <span>Journal d'audit</span>
            </NavLink>
            <NavLink to="/admin/users" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <Users size={20} />
              <span>Gestion utilisateurs</span>
            </NavLink>
          </div>
        )}
      </nav>

      <div className="sidebar-footer">
        <button className="nav-item text-critical hover:bg-red-50 w-full justify-start" onClick={handleLogout}>
          <LogOut size={20} />
          <span>Déconnexion</span>
        </button>
        <div className="user-profile">
          <div className="avatar">
            {user?.first_name?.[0]}{user?.last_name?.[0] || user?.username?.[0]}
          </div>
          <div className="user-info">
            <span className="user-name">{user?.full_name || user?.username}</span>
            <span className="user-role">{roleLabel}</span>
          </div>
        </div>
      </div>
    </aside>
  );
};
