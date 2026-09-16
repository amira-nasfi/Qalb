import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { HeartPulse, Lock } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { login } from "../api/auth";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Toast } from "../components/ui/Toast";
import "./LoginPage.css";

export const LoginPage: React.FC = () => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
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
      navigate(from, { replace: true });
    } catch (err: any) {
      setToast({
        message: err.response?.data?.detail || err.response?.data?.error || "Invalid credentials or account suspended.",
        type: "error",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-container">
        <div className="login-brand text-center">
          <img src="/logo.png" alt="Qalb Logo" className="h-20 w-auto object-contain drop-shadow-md mx-auto mb-2" />
          <p className="login-subtitle">Plateforme Médicale</p>
        </div>

        <Card className="login-card">
          <div className="clinical-notice">
            <Lock size={16} className="text-mint flex-shrink-0" />
            <span>Accès restreint au personnel médical autorisé.</span>
          </div>

          <form onSubmit={handleSubmit} className="login-form">
            <div className="form-group">
              <label htmlFor="username">Identifiant / Nom d'utilisateur</label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="form-input"
                required
                autoComplete="username"
              />
            </div>
            
            <div className="form-group">
              <label htmlFor="password">Mot de passe</label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="form-input"
                required
                autoComplete="current-password"
              />
            </div>

            <Button type="submit" className="w-full mt-4" size="lg" isLoading={isLoading}>
              Connexion sécurisée
            </Button>
            
            <div className="forgot-password text-center mt-4">
              <a href="#" className="text-sm text-tertiary hover-mint">Identifiants oubliés ? Contacter le support IT.</a>
            </div>
          </form>
        </Card>
      </div>
      
      {toast && (
        <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />
      )}
    </div>
  );
};
