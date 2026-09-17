import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { User, Lock, Eye, EyeOff, Activity, Shield, Heart } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { login } from "../api/auth";
import { Toast } from "../components/ui/Toast";
import "./LoginPage.css";

export const LoginPage: React.FC = () => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: "error" | "success" } | null>(null);

  const { setAuth } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from?.pathname || "/";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password) return;

    setIsLoading(true);
    try {
      const data = await login(username, password);
      setAuth(data.user, data.access, data.refresh);
      
      if (data.user.force_password_change) {
        navigate("/change-password", { replace: true, state: { tempPassword: password } });
      } else if (data.user.role === "ADMIN") {
        navigate("/admin", { replace: true });
      } else {
        navigate(from, { replace: true });
      }
    } catch (err: any) {
      setToast({
        message: err.response?.data?.detail || err.response?.data?.error || "Identifiants invalides ou compte suspendu.",
        type: "error",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="login-page">
      {/* ── Left panel (Logo and Taglines) ── */}
      <div className="login-left">
        <img src="/logo.png" alt="Qalb Logo" className="login-logo" />

        <p className="login-tagline">
          Acquisition et diagnostic ECG<br />
          pour une meilleure prise en charge
        </p>

        <div className="login-features">
          <span className="login-feature">
            <Activity size={20} color="#4dd9c0" strokeWidth={1.5} />
            <span>En temps réel</span>
          </span>
          <span className="login-divider">|</span>
          <span className="login-feature">
            <Shield size={20} color="#4dd9c0" strokeWidth={1.5} />
            <span>Fiable</span>
          </span>
          <span className="login-divider">|</span>
          <span className="login-feature">
            <Heart size={20} color="#4dd9c0" strokeWidth={1.5} />
            <span>Pour tous</span>
          </span>
        </div>
      </div>

      {/* ── Right — login card ── */}
      <div className="login-right">
        <div className="login-card">
          <div className="card-ecg-icon">
            <Activity size={28} color="#4dd9c0" strokeWidth={1.5} />
          </div>

          <h2 className="card-title">Bienvenue sur Qalb</h2>
          <p className="card-subtitle">
            Connectez-vous pour accéder à votre plateforme d'acquisition et de diagnostic ECG.
          </p>

          <form onSubmit={handleSubmit} className="login-form">
            <div className="form-group">
              <label htmlFor="username">Identifiant / Nom d'utilisateur</label>
              <div className="input-wrapper">
                <User size={18} className="input-icon" />
                <input
                  id="username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Entrez votre identifiant"
                  className="form-input"
                  required
                  autoComplete="username"
                />
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="password">Mot de passe</label>
              <div className="input-wrapper">
                <Lock size={18} className="input-icon" />
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Entrez votre mot de passe"
                  className="form-input"
                  required
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  className="eye-toggle"
                  onClick={() => setShowPassword(!showPassword)}
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            <button type="submit" className="login-btn" disabled={isLoading}>
              {isLoading ? "Connexion…" : "Connexion sécurisée →"}
            </button>

            <div className="forgot-link">
              <a href="#">Identifiants oubliés ? Contacter le support IT.</a>
            </div>
          </form>
        </div>
      </div>

      {toast && (
        <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />
      )}
    </div>
  );
};
