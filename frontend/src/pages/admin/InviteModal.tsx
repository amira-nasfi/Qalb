import React, { useState } from "react";
import { inviteUser } from "../../api/admin";
import { UserPlus, CheckCircle } from "lucide-react";
import "./InviteModal.css";

interface InviteModalProps {
  onClose: () => void;
  onSuccess: () => void;
}

export const InviteModal: React.FC<InviteModalProps> = ({ onClose, onSuccess }) => {
  const [formData, setFormData] = useState({
    first_name: "",
    last_name: "",
    date_of_birth: "",
    email: "",
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      await inviteUser(formData);
      setSuccess(true);
      setTimeout(() => {
        onSuccess();
      }, 3500);
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
        JSON.stringify(err.response?.data) ||
        "Échec de la création du compte."
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleChange = (field: string) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [field]: e.target.value });
  };

  return (
    <div className="im-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="im-modal">
        {/* Header */}
        <div className="im-header">
          <div className="im-header-icon">
            <UserPlus size={24} />
          </div>
          <h2 className="im-title">Créer un compte Praticien</h2>
          <p className="im-subtitle">
            Un identifiant unique et un mot de passe temporaire seront générés et envoyés par email.
          </p>
          <button className="im-close-btn" onClick={onClose} aria-label="Fermer">✕</button>
        </div>

        {/* Body */}
        <div className="im-body">
          {error && <div className="im-error">⚠ {error}</div>}

          {success ? (
            <div className="im-success-box">
              <div className="im-success-icon">
                <CheckCircle size={32} />
              </div>
              <div className="im-success-title">Compte créé avec succès !</div>
              <p className="im-success-desc">
                Un email contenant l'identifiant unique à 8 chiffres et le mot de passe temporaire
                a été envoyé à <strong>{formData.email}</strong>.
              </p>
            </div>
          ) : (
            <form onSubmit={handleSubmit}>
              <div className="im-form-grid">
                <div className="im-field">
                  <label className="im-label">Prénom</label>
                  <input
                    type="text"
                    className="im-input"
                    placeholder="ex: Fatima"
                    required
                    value={formData.first_name}
                    onChange={handleChange("first_name")}
                  />
                </div>
                <div className="im-field">
                  <label className="im-label">Nom</label>
                  <input
                    type="text"
                    className="im-input"
                    placeholder="ex: Benali"
                    required
                    value={formData.last_name}
                    onChange={handleChange("last_name")}
                  />
                </div>
                <div className="im-field">
                  <label className="im-label">Date de naissance</label>
                  <input
                    type="date"
                    className="im-input"
                    required
                    value={formData.date_of_birth}
                    onChange={handleChange("date_of_birth")}
                  />
                </div>
                <div className="im-field">
                  <label className="im-label">Adresse Email</label>
                  <input
                    type="email"
                    className="im-input"
                    placeholder="praticien@hopital.dz"
                    required
                    value={formData.email}
                    onChange={handleChange("email")}
                  />
                </div>
              </div>

              <div className="im-actions">
                <button type="button" className="im-btn-cancel" onClick={onClose}>
                  Annuler
                </button>
                <button type="submit" className="im-btn-submit" disabled={isLoading}>
                  {isLoading ? (
                    <><div className="im-spinner" /> Création en cours...</>
                  ) : (
                    <><UserPlus size={16} /> Générer les accès</>
                  )}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
