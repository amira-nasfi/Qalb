import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Lock, Eye, EyeOff, ShieldAlert } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import apiClient from "../api/client";
import { Toast } from "../components/ui/Toast";
import "./LoginPage.css";

export const ChangePasswordPage: React.FC = () => {
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showOld, setShowOld] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: "error" | "success" } | null>(null);

  const { clearAuth } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (newPassword !== confirmPassword) {
      setToast({ message: "Les mots de passe ne correspondent pas.", type: "error" });
      return;
    }
    if (newPassword.length < 12) {
      setToast({ message: "Le mot de passe doit contenir au moins 12 caractères.", type: "error" });
      return;
    }
    if (newPassword === oldPassword) {
      setToast({ message: "Le nouveau mot de passe doit être différent de l'ancien.", type: "error" });
      return;
    }

    setIsLoading(true);
    try {
      await apiClient.post("/api/auth/change-password/", {
        old_password: oldPassword,
        new_password: newPassword,
      });

      setToast({ message: "Mot de passe mis à jour. Redirection en cours...", type: "success" });
      setTimeout(() => {
        navigate("/", { replace: true });
        window.location.reload();
      }, 1500);

    } catch (err: any) {
      const data = err.response?.data;
      let msg = "Erreur lors du changement de mot de passe.";
      if (typeof data === "string") {
        msg = data;
      } else if (data?.old_password) {
        msg = "Mot de passe temporaire incorrect.";
      } else if (data?.new_password) {
        msg = Array.isArray(data.new_password) ? data.new_password.join(" ") : data.new_password;
      } else if (data?.detail) {
        msg = data.detail;
      } else if (data?.non_field_errors) {
        msg = Array.isArray(data.non_field_errors) ? data.non_field_errors[0] : data.non_field_errors;
      }
      setToast({ message: msg, type: "error" });
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = () => {
    clearAuth();
    navigate("/login", { replace: true });
  };

  return (
    <div className="login-page" style={{ justifyContent: "center" }}>
      <div className="login-card" style={{ maxWidth: "500px", margin: "0 auto" }}>
        <div className="card-ecg-icon" style={{ marginBottom: "1rem" }}>
          <ShieldAlert size={36} color="#f59e0b" strokeWidth={1.5} />
        </div>

        <h2 className="card-title">Sécurisation du compte</h2>
        <p className="card-subtitle" style={{ marginBottom: "1.5rem" }}>
          Pour des raisons de sécurité, vous devez modifier votre mot de passe temporaire avant d'accéder à la plateforme.
        </p>

        <form onSubmit={handleSubmit} className="login-form">

          <div className="form-group">
            <label htmlFor="old_password">Mot de passe temporaire (reçu par email)</label>
            <div className="input-wrapper">
              <Lock size={18} className="input-icon" />
              <input
                id="old_password"
                type={showOld ? "text" : "password"}
                value={oldPassword}
                onChange={(e) => setOldPassword(e.target.value)}
                placeholder="Copiez le mot de passe de l'email"
                className="form-input"
                required
              />
              <button type="button" className="eye-toggle" onClick={() => setShowOld(!showOld)} tabIndex={-1}>
                {showOld ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="new_password">Nouveau mot de passe</label>
            <div className="input-wrapper">
              <Lock size={18} className="input-icon" />
              <input
                id="new_password"
                type={showNew ? "text" : "password"}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Minimum 12 caractères"
                className="form-input"
                required
                minLength={12}
              />
              <button type="button" className="eye-toggle" onClick={() => setShowNew(!showNew)} tabIndex={-1}>
                {showNew ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="confirm_password">Confirmer le mot de passe</label>
            <div className="input-wrapper">
              <Lock size={18} className="input-icon" />
              <input
                id="confirm_password"
                type={showNew ? "text" : "password"}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Retapez votre nouveau mot de passe"
                className="form-input"
                required
                minLength={12}
              />
            </div>
          </div>

          <button type="submit" className="login-btn" disabled={isLoading} style={{ marginTop: "1rem" }}>
            {isLoading ? "Mise à jour..." : "Confirmer le mot de passe"}
          </button>

          <div style={{ marginTop: "1rem", textAlign: "center" }}>
            <button
              type="button"
              onClick={handleLogout}
              style={{ background: "none", border: "none", color: "#607080", cursor: "pointer", textDecoration: "underline" }}
            >
              Annuler et se déconnecter
            </button>
          </div>
        </form>
      </div>

      {toast && (
        <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />
      )}
    </div>
  );
};
