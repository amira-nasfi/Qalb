import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Sidebar } from './components/layout/Sidebar';
import { Topbar } from './components/layout/Topbar';
import { LandingPage } from './pages/LandingPage';
import { UploadPage } from './pages/UploadPage';
import { DashboardPage } from './pages/DashboardPage';
import { ReviewPage } from './pages/ReviewPage';
import { AdminDashboard } from './pages/AdminDashboard';
import { UserManagementPage } from './pages/admin/UserManagementPage';
import { LoginPage } from './pages/LoginPage';
import { ForbiddenPage } from './pages/ForbiddenPage';
import { AuthProvider } from './contexts/AuthContext';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import './styles/index.css';

const AppLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="app-layout">
    <Sidebar />
    <div className="main-wrapper">
      <Topbar />
      <main className="main-content">
        {children}
      </main>
    </div>
  </div>
);

const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/403" element={<ForbiddenPage />} />

          {/* Authenticated routes */}
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<AppLayout><LandingPage /></AppLayout>} />
            
            {/* Field Agent & Physician */}
            <Route element={<ProtectedRoute allowedRoles={['FIELD_AGENT', 'PHYSICIAN']} />}>
              <Route path="/upload" element={<AppLayout><UploadPage /></AppLayout>} />
            </Route>

            {/* Physician & Admin */}
            <Route element={<ProtectedRoute allowedRoles={['PHYSICIAN', 'ADMIN']} />}>
              <Route path="/dashboard" element={<AppLayout><DashboardPage /></AppLayout>} />
              <Route path="/review/:id" element={<AppLayout><ReviewPage /></AppLayout>} />
              <Route path="/result/:id" element={<AppLayout><ReviewPage /></AppLayout>} />
            </Route>

            {/* Admin only */}
            <Route element={<ProtectedRoute allowedRoles={['ADMIN']} />}>
              <Route path="/admin" element={<AppLayout><AdminDashboard /></AppLayout>} />
              <Route path="/admin/audit" element={<AppLayout><AdminDashboard /></AppLayout>} />
              <Route path="/admin/users" element={<AppLayout><UserManagementPage /></AppLayout>} />
            </Route>
          </Route>
          
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
};

export default App;
