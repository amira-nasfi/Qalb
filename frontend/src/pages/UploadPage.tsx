import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Toast } from "../components/ui/Toast";
import { createPatient } from "../api/patients";
import { uploadECG } from "../api/ecg";
import "./UploadPage.css";
import { UploadCloud, File, X, User, HeartPulse } from "lucide-react";

export const UploadPage: React.FC = () => {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  
  // Patient demographic & FHIR fields
  const [patientId, setPatientId] = useState("");
  const [lastName, setLastName] = useState("");
  const [firstName, setFirstName] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [gender, setGender] = useState<"male" | "female" | "other">("male");
  const [facilityId, setFacilityId] = useState("DISP-CENTRE-01");
  
  const [fmt, setFmt] = useState("csv");
  const [isUploading, setIsUploading] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !lastName || !firstName || !birthDate) {
      setToast({ message: "Veuillez renseigner les informations patient et sélectionner un fichier ECG.", type: "error" });
      return;
    }

    setIsUploading(true);
    try {
      // 1. Create Patient (FHIR compliant)
      const patient = await createPatient({
        patient_identifier: patientId.trim() || `IPP-${Date.now().toString().slice(-6)}`,
        last_name: lastName.trim(),
        first_name: firstName.trim(),
        birth_date: birthDate,
        gender: gender,
        sex: gender === "female" ? "F" : "M",
        facility_id: facilityId.trim(),
      });

      // 2. Upload ECG attached to this patient
      const res = await uploadECG(file, patient.pseudo_id, fmt);
      setToast({ message: "Patient enregistré et ECG téléversé. Traitement du signal en cours...", type: "success" });
      setTimeout(() => {
        navigate(`/result/${res.job_id}`);
      }, 1500);
    } catch (err: any) {
      setToast({ message: err.response?.data?.error || "Erreur lors de l'envoi de l'ECG.", type: "error" });
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="upload-page">
      <div className="upload-header">
        <h1 className="page-title">Nouvelle Acquisition ECG</h1>
        <p className="page-subtitle">Saisie des données patient et transmission sécurisée du tracé 12 dérivations</p>
      </div>

      <div className="upload-container">
        <Card>
          <div className="clinical-notice">
            <User size={18} className="text-primary" />
            <span>Les données saisies sont structurées et gérées conformément au standard <strong>HL7 FHIR R4</strong>.</span>
          </div>
          
          <form onSubmit={handleSubmit} className="upload-form">
            <h3 className="form-section-title">
              <User size={18} className="inline mr-2" /> Informations du Patient
            </h3>
            
            <div className="form-row">
              <div className="form-group flex-1">
                <label htmlFor="patientId">Identifiant Patient (IPP)</label>
                <input
                  id="patientId"
                  type="text"
                  value={patientId}
                  onChange={(e) => setPatientId(e.target.value)}
                  placeholder="Ex : IPP-2026-0042"
                  className="form-input text-mono"
                />
              </div>

              <div className="form-group flex-1">
                <label htmlFor="facilityId">Établissement / Dispensaire</label>
                <input
                  id="facilityId"
                  type="text"
                  value={facilityId}
                  onChange={(e) => setFacilityId(e.target.value)}
                  placeholder="Ex : Dispensaire Tunis Sud"
                  className="form-input"
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group flex-1">
                <label htmlFor="lastName">Nom de famille *</label>
                <input
                  id="lastName"
                  type="text"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  placeholder="Ex : Ben Salem"
                  required
                  className="form-input"
                />
              </div>

              <div className="form-group flex-1">
                <label htmlFor="firstName">Prénom *</label>
                <input
                  id="firstName"
                  type="text"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  placeholder="Ex : Mohamed"
                  required
                  className="form-input"
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group flex-1">
                <label htmlFor="birthDate">Date de naissance *</label>
                <input
                  id="birthDate"
                  type="date"
                  value={birthDate}
                  onChange={(e) => setBirthDate(e.target.value)}
                  required
                  className="form-input"
                />
              </div>

              <div className="form-group flex-1">
                <label htmlFor="gender">Sexe biologique (Requis pour seuils QTc) *</label>
                <select
                  id="gender"
                  value={gender}
                  onChange={(e) => setGender(e.target.value as any)}
                  className="form-select"
                >
                  <option value="male">Masculin (Homme)</option>
                  <option value="female">Féminin (Femme)</option>
                  <option value="other">Autre / Indéterminé</option>
                </select>
              </div>
            </div>

            <h3 className="form-section-title mt-6">
              <HeartPulse size={18} className="inline mr-2" /> Signal Électrocardiographique
            </h3>

            <div className="form-row">
              <div className="form-group flex-1">
                <label htmlFor="fmt">Format du signal</label>
                <select
                  id="fmt"
                  value={fmt}
                  onChange={(e) => setFmt(e.target.value)}
                  className="form-select"
                >
                  <option value="csv">CSV (12 dérivations, tensions en mV)</option>
                  <option value="wfdb">WFDB (.mat / .hea)</option>
                  <option value="edf">EDF / EDF+</option>
                </select>
              </div>
            </div>

            <div className="form-group">
              <label>Fichier d'enregistrement ECG</label>
              {!file ? (
                <div
                  className="clinical-dropzone"
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={handleDrop}
                  onClick={() => document.getElementById("file-upload")?.click()}
                >
                  <UploadCloud size={32} className="dropzone-icon" />
                  <p className="dropzone-text">Cliquez pour parcourir ou glissez le fichier ici</p>
                  <p className="text-xs text-muted mt-1">Formats acceptés : .csv, .mat, .edf (fréquence recommandée : 500 Hz)</p>
                  <input
                    id="file-upload"
                    type="file"
                    className="hidden-input"
                    onChange={(e) => e.target.files && setFile(e.target.files[0])}
                  />
                </div>
              ) : (
                <div className="file-selected-box">
                  <File size={20} className="file-icon" />
                  <div className="file-info">
                    <span className="file-name text-mono">{file.name}</span>
                    <span className="file-size text-mono">{(file.size / 1024).toFixed(1)} KB</span>
                  </div>
                  <button type="button" className="btn-remove-file" onClick={() => setFile(null)}>
                    <X size={16} />
                  </button>
                </div>
              )}
            </div>

            <div className="form-actions">
              <Button 
                variant="secondary" 
                type="button" 
                onClick={() => { 
                  setFile(null); 
                  setPatientId(''); 
                  setLastName(''); 
                  setFirstName(''); 
                  setBirthDate(''); 
                }}
              >
                Réinitialiser
              </Button>
              <Button type="submit" disabled={!file || !lastName || !firstName || !birthDate} isLoading={isUploading}>
                Enregistrer le patient & Lancer l'analyse
              </Button>
            </div>
          </form>
        </Card>
      </div>

      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
    </div>
  );
};
