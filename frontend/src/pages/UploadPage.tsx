import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Toast } from "../components/ui/Toast";
import { createPatient } from "../api/patients";
import { uploadAndAnalyseECG, transmitStudy } from "../api/ecg";
import type { EcgStudy } from "../types";
import "./UploadPage.css";
import {
  UploadCloud,
  File,
  X,
  User,
  HeartPulse,
  ShieldCheck,
  AlertOctagon,
  CheckCircle2,
  Send,
  RotateCcw,
  Eye,
} from "lucide-react";

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

  // Regulatory Identity Verification
  const [identityVerified, setIdentityVerified] = useState(true);
  const [identityMethod, setIdentityMethod] = useState("CIN");

  // Signal parameters
  const [fmt, setFmt] = useState("csv");
  const [samplingRate, setSamplingRate] = useState<number>(500);
  const [isUploading, setIsUploading] = useState(false);
  const [isTransmitting, setIsTransmitting] = useState(false);

  // Result state
  const [analysisResult, setAnalysisResult] = useState<EcgStudy | null>(null);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!identityVerified) {
      setToast({
        message: "L'identité du patient doit être formellement vérifiée avant l'acquisition (Obligation réglementaire).",
        type: "error",
      });
      return;
    }

    if (!file || !lastName || !firstName || !birthDate) {
      setToast({
        message: "Veuillez renseigner les informations patient et sélectionner un fichier ECG.",
        type: "error",
      });
      return;
    }

    setIsUploading(true);
    setAnalysisResult(null);

    try {
      // 1. Create Patient record in database
      const patient = await createPatient({
        patient_identifier: patientId.trim() || `IPP-${Date.now().toString().slice(-6)}`,
        last_name: lastName.trim(),
        first_name: firstName.trim(),
        birth_date: birthDate,
        gender: gender,
        sex: gender === "female" ? "F" : "M",
        facility_id: facilityId.trim(),
      });

      // 2. Synchronous acquisition, quality control and automated analysis
      const study = await uploadAndAnalyseECG({
        file,
        patient_id: patient.pseudo_id,
        patient_name: `${patient.first_name} ${patient.last_name}`.trim(),
        patient_birth: patient.birth_date,
        patient_sex: patient.sex,
        identity_verified: identityVerified,
        identity_method: identityMethod,
        fs: samplingRate,
      });

      setAnalysisResult(study);

      if (study.state === "rejected") {
        setToast({
          message: "Contrôle qualité échoué : tracé inexploitable. Réacquisition requise.",
          type: "error",
        });
      } else {
        setToast({
          message: "Analyse automatisée terminée avec succès. Prêt pour transmission au médecin.",
          type: "success",
        });
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.response?.data?.error || "Erreur lors de l'analyse du tracé ECG.";
      setToast({ message: msg, type: "error" });
    } finally {
      setIsUploading(false);
    }
  };

  const handleTransmit = async () => {
    if (!analysisResult) return;
    setIsTransmitting(true);
    try {
      await transmitStudy(analysisResult.study_id);
      setToast({
        message: "Tracé transmis au médecin télé-interprète avec priorité clinique.",
        type: "success",
      });
      setTimeout(() => {
        navigate(`/review/${analysisResult.study_id}`);
      }, 1000);
    } catch (err: any) {
      setToast({
        message: err.response?.data?.detail || "Erreur lors de la transmission.",
        type: "error",
      });
    } finally {
      setIsTransmitting(false);
    }
  };

  return (
    <div className="upload-page">
      <div className="upload-header">
        <h1 className="page-title">Nouvelle Acquisition ECG 12 Dérivations</h1>
        <p className="page-subtitle">
          Vérification d'identité réglementaire, contrôle qualité instantané et transmission télé-expertise
        </p>
      </div>

      <div className="upload-container">
        {/* Quality Rejection Screen */}
        {analysisResult && analysisResult.state === "rejected" && (
          <div className="quality-rejection-card mb-6" id="quality-rejection-screen">
            <div className="rejection-header">
              <AlertOctagon size={32} className="text-critical mr-3" />
              <div>
                <h3 className="rejection-title">Tracé Rejeté au Contrôle Qualité Préalable</h3>
                <p className="rejection-sub">
                  Le signal enregistré est jugé non exploitable cliniquement selon les critères de rapport signal/bruit.
                </p>
              </div>
            </div>

            <div className="rejection-body">
              {analysisResult.blocks?.error?.message ? (
                <div className="rejection-box">
                  <span className="box-title">Motif du rejet technique :</span>
                  <span className="box-val text-critical">
                    {analysisResult.blocks.error.message}
                  </span>
                </div>
              ) : (
                <div className="rejection-box">
                  <span className="box-title">Dérivations dégradées ou bruitées :</span>
                  <span className="box-val text-critical">
                    {analysisResult.blocks?.quality?.failed_leads?.length
                      ? analysisResult.blocks.quality.failed_leads.join(", ")
                      : "Signal saturé / artéfacts majeurs"}
                  </span>
                </div>
              )}

              {analysisResult.blocks?.quality?.missing_leads?.length ? (
                <div className="rejection-box">
                  <span className="box-title">Dérivations manquantes :</span>
                  <span className="box-val text-warning">
                    {analysisResult.blocks.quality.missing_leads.join(", ")}
                  </span>
                </div>
              ) : null}

              <div className="rejection-advice">
                <strong>Consignes pour l'opérateur de terrain :</strong>
                <ul>
                  <li>Vérifier l'adhésion des électrodes et nettoyer la peau du patient à l'alcool.</li>
                  <li>S'assurer que le patient est au repos strict et ne parle pas pendant l'acquisition.</li>
                  <li>Vérifier le branchement du câble patient et l'absence de parasite secteur 50 Hz.</li>
                </ul>
              </div>

              <div className="rejection-actions">
                <Button
                  variant="secondary"
                  onClick={() => {
                    setFile(null);
                    setAnalysisResult(null);
                  }}
                >
                  <RotateCcw size={16} className="mr-1" />
                  Réacquérir le tracé maintenant
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Successful Analysis Ready for Transmission */}
        {analysisResult && analysisResult.state === "analysed" && (
          <div className="analysis-success-card mb-6" id="analysis-success-screen">
            <div className="success-header">
              <CheckCircle2 size={28} className="text-success mr-3" />
              <div>
                <h3 className="success-title">Contrôle Qualité & Délignage Validés</h3>
                <p className="success-sub">
                  Niveau de triage : <strong>{analysisResult.triage_level}</strong> (Priorité {analysisResult.triage_priority})
                  {analysisResult.escalated && " — Escalade d'urgence médicale activée"}
                </p>
              </div>
            </div>

            <div className="success-summary-grid">
              <div className="summary-item">
                <span className="lbl">Patient</span>
                <span className="val font-semibold">{analysisResult.patient_name}</span>
              </div>
              <div className="summary-item">
                <span className="lbl">Identité Vérifiée</span>
                <span className="val text-success font-semibold">Oui ({analysisResult.identity_method})</span>
              </div>
              <div className="summary-item">
                <span className="lbl">Durée de l'analyse</span>
                <span className="val font-mono">
                  {analysisResult.blocks?.header?.total_ms?.toFixed(1) || 0} ms
                </span>
              </div>
              <div className="summary-item">
                <span className="lbl">État du Dossier</span>
                <span className="val badge-analysed">Prêt pour transmission</span>
              </div>
            </div>

            <div className="success-actions">
              <Button
                variant="ghost"
                onClick={() => navigate(`/review/${analysisResult.study_id}`)}
              >
                <Eye size={16} className="mr-1" />
                Prévisualiser le tracé
              </Button>
              <Button
                variant="primary"
                onClick={handleTransmit}
                isLoading={isTransmitting}
              >
                <Send size={16} className="mr-1" />
                Transmettre au Médecin Télé-interprète
              </Button>
            </div>
          </div>
        )}

        {/* Acquisition Form */}
        <Card>
          <div className="clinical-notice">
            <ShieldCheck size={18} className="text-primary" />
            <span>
              Toutes les données saisies sont conformes au standard <strong>HL7 FHIR R4</strong> et cryptées à l'état
              de repos.
            </span>
          </div>

          <form onSubmit={handleSubmit} className="upload-form">
            {/* Identity Verification Section */}
            <div className="identity-verification-box">
              <div className="flex items-center justify-between mb-2">
                <h3 className="form-section-title m-0">
                  <ShieldCheck size={18} className="inline mr-2 text-primary" />
                  Vérification Réglementaire de l'Identité Patient
                </h3>
                <span className="badge-mandatory">OBLIGATOIRE</span>
              </div>

              <p className="text-xs text-slate-600 mb-3">
                Un tracé ECG non apparié à une identité certifiée ne peut être routé vers le médecin ni restitué au SIH.
              </p>

              <div className="identity-controls-row">
                <label className="checkbox-container">
                  <input
                    type="checkbox"
                    checked={identityVerified}
                    onChange={(e) => setIdentityVerified(e.target.checked)}
                  />
                  <span className="checkmark" />
                  <span className="checkbox-label">
                    <strong>J'atteste avoir vérifié l'identité physique du patient</strong>
                  </span>
                </label>

                <div className="identity-method-group">
                  <label htmlFor="idMethod" className="text-xs font-medium text-slate-600 mr-2">
                    Méthode :
                  </label>
                  <select
                    id="idMethod"
                    value={identityMethod}
                    onChange={(e) => setIdentityMethod(e.target.value)}
                    className="form-select text-xs py-1"
                  >
                    <option value="CIN">Carte Nationale d'Identité (CIN)</option>
                    <option value="Passeport">Passeport</option>
                    <option value="Bracelet">Bracelet d'admission dispensaire</option>
                    <option value="Dossier National">Dossier Médical Informatisé</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Patient Info Section */}
            <h3 className="form-section-title mt-6">
              <User size={18} className="inline mr-2" /> Informations du Patient
            </h3>

            <div className="form-row">
              <div className="form-group flex-1">
                <label htmlFor="patientId">Identifiant Patient (IPP / CIN)</label>
                <input
                  id="patientId"
                  type="text"
                  value={patientId}
                  onChange={(e) => setPatientId(e.target.value)}
                  placeholder="Ex : CIN-08912345 ou IPP-2026-0042"
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
                  placeholder="Ex : Dispensaire Rural El Kef"
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
                <label htmlFor="gender">Sexe biologique (Seuils QTc Rautaharju) *</label>
                <select
                  id="gender"
                  value={gender}
                  onChange={(e) => setGender(e.target.value as any)}
                  className="form-select"
                >
                  <option value="male">Masculin (Homme)</option>
                  <option value="female">Féminin (Femme)</option>
                  <option value="other">Autre / Non renseigné</option>
                </select>
              </div>
            </div>

            {/* Signal Specifications */}
            <h3 className="form-section-title mt-6">
              <HeartPulse size={18} className="inline mr-2" /> Fichier ECG 12 Dérivations
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
                  <option value="csv">CSV (12 colonnes, tensions en mV ou µV)</option>
                  <option value="wfdb">WFDB PhysioNet (.mat / .hea)</option>
                  <option value="edf">EDF / EDF+ standard clinique</option>
                </select>
              </div>

              <div className="form-group flex-1">
                <label htmlFor="fs">Fréquence d'échantillonnage (Hz)</label>
                <input
                  id="fs"
                  type="number"
                  value={samplingRate}
                  onChange={(e) => setSamplingRate(Number(e.target.value))}
                  min={250}
                  max={1000}
                  className="form-input text-mono"
                />
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
                  <p className="text-xs text-muted mt-1">
                    Formats acceptés : .csv, .mat, .edf (fréquence recommandée : 500 Hz)
                  </p>
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
                  setPatientId("");
                  setLastName("");
                  setFirstName("");
                  setBirthDate("");
                  setAnalysisResult(null);
                }}
              >
                Réinitialiser
              </Button>
              <Button
                type="submit"
                disabled={!file || !lastName || !firstName || !birthDate || !identityVerified}
                isLoading={isUploading}
              >
                Lancer l'Acquisition & l'Analyse Immédiate
              </Button>
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
