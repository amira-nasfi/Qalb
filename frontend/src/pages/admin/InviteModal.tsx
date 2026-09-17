import React, { useState } from "react";
import { inviteUser } from "../../api/admin";
import { UserPlus, CheckCircle, Stethoscope, UserCheck, Sparkles } from "lucide-react";
import "./InviteModal.css";

interface InviteModalProps {
  onClose: () => void;
  onSuccess: () => void;
}

export const InviteModal: React.FC<InviteModalProps> = ({ onClose, onSuccess }) => {
  const [role, setRole] = useState<"FIELD_AGENT" | "PHYSICIAN">("PHYSICIAN");
  const [formData, setFormData] = useState({
    first_name: "",
    last_name: "",
    date_of_birth: "",
    email: "",
    license_number: "",
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      await inviteUser({
        ...formData,
        role,
      });
      setSuccess(true);
      setTimeout(() => {
        onSuccess();
      }, 3500);
    } catch (err: any) {
      const detail =
        err.response?.data?.license_number?.[0] ||
        err.response?.data?.detail ||
        (typeof err.response?.data === "object"
          ? Object.values(err.response.data).flat().join(" ")
          : null) ||
        "Échec de la création du compte.";
      setError(detail);
    } finally {
      setIsLoading(false);
    }
  };

  const handleChange = (field: string) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [field]: e.target.value });
  };

  return (
    <div className="im-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="im-modal" style={{ maxWidth: "560px" }}>
        {/* Header */}
        <div className="im-header">
          <div className="im-header-icon">
            <UserPlus size={24} />
          </div>
          <h2 className="im-title">
            {role === "PHYSICIAN" ? "Créer un compte Médecin" : "Créer un compte Praticien"}
          </h2>
          <p className="im-subtitle">
            {role === "PHYSICIAN"
              ? "Le numéro de licence médicale saisi servira d'identifiant de connexion."
              : "Un identifiant unique à 8 chiffres sera généré automatiquement."}
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
                {role === "PHYSICIAN" ? (
                  <>
                    Le compte <strong>Médecin Télé-expert</strong> a été créé avec l'identifiant{" "}
                    <strong>{formData.license_number}</strong>. Les accès ont été envoyés à{" "}
                    <strong>{formData.email}</strong>.
                  </>
                ) : (
                  <>
                    Le compte <strong>Praticien de Terrain</strong> a été créé. L'identifiant unique
                    à 8 chiffres et le mot de passe temporaire ont été envoyés à{" "}
                    <strong>{formData.email}</strong>.
                  </>
                )}
              </p>
            </div>
          ) : (
            <form onSubmit={handleSubmit}>
              {/* Role Selection */}
              <div className="im-label" style={{ marginBottom: "8px" }}>
                Type de profil médical
              </div>
              <div className="im-role-selector">
                <button
                  type="button"
                  className={`im-role-card ${role === "PHYSICIAN" ? "active" : ""}`}
                  onClick={() => setRole("PHYSICIAN")}
                >
                  <div className="im-role-card-title">
                    <Stethoscope size={16} color="#0284c7" />
                    Médecin Télé-expert
                  </div>
                  <div className="im-role-card-desc">
                    Validation, signature et SAMU. Identifiant = N° de licence.
                  </div>
                </button>

                <button
                  type="button"
                  className={`im-role-card ${role === "FIELD_AGENT" ? "active" : ""}`}
                  onClick={() => setRole("FIELD_AGENT")}
                >
                  <div className="im-role-card-title">
                    <UserCheck size={16} color="#059669" />
                    Praticien de Terrain
                  </div>
                  <div className="im-role-card-desc">
                    Acquisition ECG et suivi. Identifiant = 8 chiffres auto.
                  </div>
                </button>
              </div>

              {/* Physician Specific Input: License Number */}
              {role === "PHYSICIAN" ? (
                <div className="im-field full-width" style={{ marginBottom: "16px" }}>
                  <label className="im-label" style={{ color: "#0284c7" }}>
                    N° de Licence Médicale / RPPS (Identifiant de connexion) *
                  </label>
                  <input
                    type="text"
                    className="im-input"
                    placeholder="ex: 10105678901 ou LIC-8942"
                    required
                    value={formData.license_number}
                    onChange={handleChange("license_number")}
                  />
                  <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
                    Ce numéro sera directement utilisé par le médecin pour s'authentifier.
                  </span>
                </div>
              ) : (
                <div className="im-info-banner">
                  <Sparkles size={16} />
                  <span>
                    Un <strong>identifiant unique à 8 chiffres</strong> sera généré automatiquement
                    par le système.
                  </span>
                </div>
              )}

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
                    placeholder={role === "PHYSICIAN" ? "docteur@chu.dz" : "praticien@dispensaire.dz"}
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
                    <><UserPlus size={16} /> {role === "PHYSICIAN" ? "Créer le compte Médecin" : "Générer le compte Praticien"}</>
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
