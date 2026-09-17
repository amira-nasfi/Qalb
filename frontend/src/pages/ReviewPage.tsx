import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  getReport,
  updateReportNotes,
  signReport,
  claimReport,
  requestRetake,
} from "../api/reports";
import {
  getStudy,
  getWaveform,
  openStudy,
  signStudy,
  getECGSignal,
} from "../api/ecg";
import { downloadFHIRExport } from "../api/fhir";
import type { Report, EcgStudy, WaveformData } from "../types";
import { useAuth } from "../contexts/AuthContext";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Toast } from "../components/ui/Toast";
import { ECGViewer12Lead } from "../components/ecg/ECGViewer12Lead";
import { ClinicalLimitsBanner } from "../components/ecg/ClinicalLimitsBanner";
import { AuditLoopViewer } from "../components/ecg/AuditLoopViewer";
import {
  Activity,
  Download,
  CheckCircle,
  Edit3,
  ShieldAlert,
  User,
  Stethoscope,
  RotateCcw,
  ArrowLeft,
  FileCheck,
} from "lucide-react";
import "./ReviewPage.css";

/* ── Retake modal ──────────────────────────────────────────── */
const RetakeModal: React.FC<{
  onConfirm: (reason: string) => void;
  onCancel: () => void;
}> = ({ onConfirm, onCancel }) => {
  const [reason, setReason] = useState("");
  return (
    <div className="modal-overlay">
      <div className="modal-box">
        <h3 className="modal-title">
          <RotateCcw size={18} className="mr-2 text-warning" />
          Demander une réacquisition ECG
        </h3>
        <p className="modal-desc">
          Décrivez le problème technique qui rend ce tracé inexploitable (artéfacts, inversion d'électrodes, bruit de ligne…).
        </p>
        <textarea
          className="modal-textarea"
          placeholder="Ex : Inversion des électrodes V1-V2, artéfacts musculaires importants sur les dérivations précordiales…"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          rows={4}
          autoFocus
        />
        <div className="modal-actions">
          <Button variant="ghost" size="sm" onClick={onCancel}>Annuler</Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => reason.trim() && onConfirm(reason)}
            disabled={!reason.trim()}
          >
            Envoyer la demande
          </Button>
        </div>
      </div>
    </div>
  );
};


/* ── Electronic Signature Modal ────────────────────────────── */
const SignModal: React.FC<{
  physicianName: string;
  onConfirm: (signature: string) => void;
  onCancel: () => void;
}> = ({ physicianName, onConfirm, onCancel }) => {
  const [signatureText, setSignatureText] = useState(
    physicianName ? `Dr. ${physicianName}` : "Dr. Télé-expert Cardiologue"
  );
  return (
    <div className="modal-overlay">
      <div className="modal-box">
        <h3 className="modal-title">
          <FileCheck size={20} className="mr-2 text-primary" />
          Validation et Signature Électronique
        </h3>
        <p className="modal-desc">
          En apposant votre signature électronique, vous validez les conclusions diagnostiques, certifiez l'interprétation
          clinique et verrouillez définitivement le compte rendu médical.
        </p>
        <div className="form-group mb-4">
          <label className="text-xs font-semibold text-slate-700 block mb-1">
            Nom et Titre du Médecin Interprète :
          </label>
          <input
            type="text"
            className="form-input text-mono font-bold"
            value={signatureText}
            onChange={(e) => setSignatureText(e.target.value)}
            placeholder="Ex : Dr. Mohamed Ben Salah — Cardiologue"
            autoFocus
          />
        </div>
        <div className="modal-actions">
          <Button variant="ghost" size="sm" onClick={onCancel}>Annuler</Button>
          <Button
            variant="primary"
            size="sm"
            onClick={() => signatureText.trim() && onConfirm(signatureText.trim())}
            disabled={!signatureText.trim()}
          >
            Confirmer la Signature & Verrouiller
          </Button>
        </div>
      </div>
    </div>
  );
};

export const ReviewPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();

  // Unified EcgStudy state
  const [study, setStudy] = useState<EcgStudy | null>(null);
  const [waveform, setWaveform] = useState<WaveformData | null>(null);

  // Legacy Report fallback state
  const [report, setReport] = useState<Report | null>(null);

  const [notes, setNotes] = useState("");
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);
  const [isSigning, setIsSigning] = useState(false);
  const [isClaiming, setIsClaiming] = useState(false);

  // Modals
  const [showRetake, setShowRetake] = useState(false);
  const [showSignModal, setShowSignModal] = useState(false);

  useEffect(() => {
    if (!id) return;
    const fetchData = async () => {
      // 1. Try unified EcgStudy first
      try {
        const s = await getStudy(id);
        setStudy(s);
        // Clinical validation is filled manually by the physician; leave undone studies empty
        setNotes(s.physician_report || "");

        // If physician opens it, record open timestamp
        if (user?.role === "PHYSICIAN" && s.state === "transmitted") {
          openStudy(id).catch(() => {});
        }

        // Fetch 12-lead waveform
        try {
          const w = await getWaveform(id);
          setWaveform(w);
        } catch (wErr) {
          console.warn("Waveform not available:", wErr);
        }
        return;
      } catch {
        // Not an EcgStudy ID, try legacy Report
      }

      // 2. Fallback to legacy Report
      try {
        const r = await getReport(id);
        setReport(r);
        setNotes(r.physician_notes || "");

        const sigData = await getECGSignal(r.job_id);
        setWaveform({
          study_id: r.id,
          fs: sigData.fs_display || 250,
          leads: ["II"],
          samples: { II: sigData.samples },
          n_samples: sigData.samples.length,
          overlay_scale_factor: 2.0,
          raw: true,
        });
      } catch (err) {
        console.error("Failed to load study/report:", err);
      }
    };
    fetchData();
  }, [id, user]);

  const isPhysician = user?.role === "PHYSICIAN";
  const currentState = study ? study.state : report?.status || "";
  const isSigned = study ? (study.state === "signed" || study.state === "delivered") : report?.status === "SIGNED";
  const isLocked = isSigned || report?.status === "EMERGENCY_TRANSFER" || report?.status === "RETAKE_REQUESTED";
  const isCritical = study
    ? (study.triage_priority === 1 || study.triage_level === "RED" || study.escalated)
    : report?.severity === "CRITICAL";

  const handleSaveNotes = async () => {
    if (study) {
      setToast({ message: "Brouillon sauvegardé localement.", type: "success" });
    } else if (report) {
      try {
        await updateReportNotes(report.id, notes);
        setToast({ message: "Brouillon sauvegardé.", type: "success" });
      } catch {
        setToast({ message: "Échec de l'enregistrement du brouillon.", type: "error" });
      }
    }
  };

  const handleConfirmSign = async (signatureText: string) => {
    setShowSignModal(false);
    setIsSigning(true);
    try {
      if (study) {
        const res = await signStudy(study.study_id || id!, notes, signatureText);
        setStudy((prev) => (prev ? { ...prev, state: res.state, signed_at: res.signed_at, turnaround_s: res.turnaround_s } : prev));
        setToast({
          message: `Compte rendu validé et signé électroniquement (Turnaround: ${res.turnaround_s?.toFixed(1)} s).`,
          type: "success",
        });
      } else if (report) {
        await updateReportNotes(report.id, notes);
        const updated = await signReport(report.id);
        setReport(updated);
        setToast({ message: "Rapport signé électroniquement et verrouillé.", type: "success" });
      }
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Échec lors de la signature.";
      setToast({ message: msg, type: "error" });
    } finally {
      setIsSigning(false);
    }
  };

  const handleClaim = async () => {
    if (study) {
      await openStudy(study.study_id || id!);
      setStudy((prev) => (prev ? { ...prev, state: "reviewing" } : prev));
      setToast({ message: "Dossier pris en charge.", type: "success" });
    } else if (report) {
      setIsClaiming(true);
      try {
        const updated = await claimReport(report.id);
        setReport(updated);
        setToast({ message: "Dossier pris en charge.", type: "success" });
      } catch (err: any) {
        setToast({ message: err?.response?.data?.error ?? "Erreur lors de la prise en charge.", type: "error" });
      } finally {
        setIsClaiming(false);
      }
    }
  };

  const handleRetake = async (reason: string) => {
    setShowRetake(false);
    if (report) {
      try {
        const updated = await requestRetake(report.id, reason);
        setReport(updated);
        setToast({ message: "Demande de réacquisition transmise au dispensaire.", type: "success" });
      } catch {
        setToast({ message: "Échec de la demande de réacquisition.", type: "error" });
      }
    } else {
      setToast({ message: "Demande de réacquisition signalée.", type: "success" });
    }
  };


  const handleExportFHIR = async () => {
    try {
      await downloadFHIRExport(study?.patient_id || report?.pseudo_id || "");
      setToast({ message: "Exportation FHIR téléchargée.", type: "success" });
    } catch {
      setToast({ message: "Échec du téléchargement FHIR.", type: "error" });
    }
  };

  if (!study && !report) {
    return (
      <div className="flex items-center justify-center p-12 text-slate-500">
        Chargement du dossier cardiologique...
      </div>
    );
  }

  const patientDisplayName = study?.patient_name || report?.patient_name || report?.patient?.full_name || "Patient";
  const patientIdentifier = study?.patient_id || report?.patient_identifier || report?.pseudo_id?.slice(0, 8) || "N/A";

  return (
    <div className="review-page">
      {/* Back button */}
      {isPhysician && (
        <button className="back-btn" onClick={() => navigate("/doctor")}>
          <ArrowLeft size={16} className="mr-1" />
          Retour au portail médecin
        </button>
      )}

      {/* Header */}
      <div className={`review-header ${isCritical && !isLocked ? "header-critical" : ""}`}>
        <div className="header-info">
          <h1 className="page-title">
            Dossier d'Expertise #{study?.study_id || report?.id}
          </h1>
          <div className="patient-id flex items-center gap-2 mt-1">
            <User size={16} className="text-secondary" />
            <span className="font-semibold text-main">{patientDisplayName}</span>
            <span className="text-muted">·</span>
            <span className="text-mono text-sm text-tertiary">IPP / ID : {patientIdentifier}</span>
            {study?.identity_verified && (
              <span className="text-xs bg-emerald-100 text-emerald-800 font-bold px-2 py-0.5 rounded">
                Identité Certifiée ({study.identity_method})
              </span>
            )}
          </div>
        </div>

        <div className="header-actions flex items-center gap-2">
          {isCritical && <Badge severity="CRITICAL">🚨 Priorité Critique</Badge>}
          {isSigned && <Badge severity="SUCCESS">Validé & Signé</Badge>}
          {study?.state === "delivered" && <Badge severity="SUCCESS">Restitué au SIH</Badge>}
          {study?.state === "reviewing" && <Badge severity="URGENT">En cours de lecture</Badge>}
          {study?.state === "transmitted" && <Badge severity="WARNING">Transmis au médecin</Badge>}
        </div>
      </div>

      {/* Critical Alert Banner */}
      {isCritical && !isLocked && (
        <div className="critical-banner">
          <ShieldAlert size={20} />
          <span>
            Intervention clinique prioritaire requise selon le triage algorithmique (Triage {study?.triage_level || "CRITIQUE"}).
          </span>
        </div>
      )}

      {/* ── 1. Pure SVG 12-Lead ECG Viewer ── */}
      {waveform && (
        <ECGViewer12Lead
          waveform={waveform}
          segmentationLabels={study?.analysis?.segmentation?.labels}
          labelLead={study?.analysis?.segmentation?.label_lead || "II"}
          overlayScaleFactor={waveform.overlay_scale_factor || 2.0}
        />
      )}

      <div className="review-grid">
        {/* Main Column */}
        <div className="review-main">
          {/* Automated Report Blocks */}
          <Card className="mb-6">
            <div className="card-header">
              <h2 className="flex items-center">
                <Activity size={18} className="inline mr-2 text-teal" />
                Compte Rendu d'Analyse Automatisée
              </h2>
            </div>
            <div className="card-body">
              {study?.analysis ? (
                <div className="analysis-summary-view">
                  {/* Measurements grid */}
                  <div className="measurements-table-wrapper mb-4">
                    <table className="measurements-table">
                      <thead>
                        <tr>
                          <th>Paramètre</th>
                          <th>Mesure</th>
                          <th>Norme Référence</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr>
                          <td>Fréquence Cardiaque</td>
                          <td className="font-mono font-bold">
                            {study.analysis.measurements?.hr_bpm ? `${study.analysis.measurements.hr_bpm} bpm` : "—"}
                          </td>
                          <td className="text-muted text-xs">60 - 90 bpm</td>
                        </tr>
                        <tr>
                          <td>Intervalle PR</td>
                          <td className="font-mono">
                            {study.analysis.measurements?.pr_ms ? `${study.analysis.measurements.pr_ms} ms` : "Non calculable"}
                          </td>
                          <td className="text-muted text-xs">120 - 200 ms</td>
                        </tr>
                        <tr>
                          <td>Durée QRS</td>
                          <td className="font-mono">
                            {study.analysis.measurements?.qrs_ms ? `${study.analysis.measurements.qrs_ms} ms` : "—"}
                          </td>
                          <td className="text-muted text-xs">&lt; 120 ms</td>
                        </tr>
                        <tr>
                          <td>QTc Fridericia / Bazett</td>
                          <td className="font-mono font-bold">
                            {study.analysis.measurements?.qtc_fridericia_ms ? `${study.analysis.measurements.qtc_fridericia_ms} ms` : "—"}
                          </td>
                          <td className="text-muted text-xs">≤ 450 H / 460 F ms</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  {/* Findings list */}
                  {study.analysis.findings && study.analysis.findings.length > 0 && (
                    <div className="findings-box mb-4">
                      <h4 className="findings-heading">Signaux et critères cliniques détectés :</h4>
                      <ul className="findings-list">
                        {study.analysis.findings.map((f: any, fIdx: number) => (
                          <li key={fIdx} className={`finding-item finding-${f.severity?.toLowerCase()}`}>
                            <div className="finding-main-row">
                              <span className="finding-comp">[{f.component}]</span>
                              <span className="finding-text">{f.finding}</span>
                              {f.citation && <span className="finding-cite">({f.citation})</span>}
                            </div>
                            {/* Clinical anomaly association */}
                            {f.diagnosis?.label && (f.severity !== "GREEN" || f.diagnosis?.icd10) && (
                              <div className="finding-diagnosis">
                                <span className="diagnosis-badge">Anomalie associée :</span>
                                <span className="diagnosis-label">{f.diagnosis.label}</span>
                                {f.diagnosis.icd10 && (
                                  <span className="diagnosis-icd10">CIM-10 : {f.diagnosis.icd10}</span>
                                )}
                              </div>
                            )}
                            {/* measured / threshold / meaning */}
                            {(f.measured || f.threshold) && (
                              <div className="finding-detail-row">
                                {f.measured && <span className="finding-measured">mesure : {f.measured}</span>}
                                {f.threshold && <span className="finding-threshold">seuil : {f.threshold}</span>}
                                {f.meaning && <span className="finding-meaning">{f.meaning}</span>}
                              </div>
                            )}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Raw text preview */}
                  {study.report_text && (
                    <div className="draft-text bg-slate-50 p-3 rounded text-xs font-mono border">
                      <pre className="whitespace-pre-wrap">{study.report_text}</pre>
                    </div>
                  )}
                </div>
              ) : (
                <div className="draft-text">
                  {(study?.report_text || report?.draft_text || "").split("\n").map((line, i) => (
                    <p key={i}>{line}</p>
                  ))}
                </div>
              )}
            </div>
          </Card>

          {/* ── 2. Permanent Mandatory Clinical Limits Banner ── */}
          <ClinicalLimitsBanner limits={study?.analysis?.limits} />

          {/* ── 3. Medical Loop Audit & HIS Delivery Actions ── */}
          {(study?.study_id || id) && (
            <AuditLoopViewer
              studyId={Number(study?.study_id || id)}
              currentState={currentState}
              onStateChange={(newState) => {
                if (study) setStudy({ ...study, state: newState });
              }}
            />
          )}
        </div>

        {/* Right Sidebar: Physician conclusions and actions */}
        <div className="review-sidebar">
          <Card className="mb-6">
            <div className="card-header">
              <h2>
                <Edit3 size={18} className="inline mr-2 text-teal" />
                Conclusion & Avis Spécialisé
              </h2>
            </div>
            <div className="card-body p-0">
              <textarea
                className="notes-textarea"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder={isPhysician ? "Saisissez l'avis clinique du cardiologue, les recommandations thérapeutiques et la validation..." : "Avis clinique réservé au médecin télé-expert (lecture seule pour le praticien)."}
                disabled={isLocked || !isPhysician}
                rows={9}
              />
              {!isLocked && isPhysician && (
                <div className="notes-actions p-3">
                  <Button variant="ghost" size="sm" onClick={handleSaveNotes}>
                    Enregistrer le brouillon
                  </Button>
                </div>
              )}
            </div>
          </Card>

          {/* Action buttons */}
          <Card className="actions-card">
            <div className="card-body">
              {/* Field agent informative notice */}
              {!isPhysician && (
                <div style={{
                  background: "#eff6ff",
                  border: "1px solid #bfdbfe",
                  borderRadius: "8px",
                  padding: "12px",
                  marginBottom: "16px",
                  color: "#1e40af",
                  fontSize: "0.82rem",
                  lineHeight: "1.4"
                }}>
                  <p style={{ fontWeight: 700, marginBottom: "4px" }}>Mode Consultation (Praticien)</p>
                  <p style={{ margin: 0 }}>
                    Vous visualisez les résultats et analyses générées. Vous ne pouvez ni valider ni signer ce dossier (action réservée aux médecins télé-experts).
                  </p>
                </div>
              )}

              {/* Physician: claim if transmitted / pending */}
              {isPhysician && (study?.state === "transmitted" || report?.status === "PENDING_REVIEW") && (
                <Button
                  size="lg"
                  variant="secondary"
                  className="w-full mb-4"
                  onClick={handleClaim}
                  isLoading={isClaiming}
                >
                  <Stethoscope size={16} className="mr-2" />
                  Prendre en charge l'examen
                </Button>
              )}

              {/* Sign button (Physician only) */}
              {isPhysician && !isLocked && (
                <>
                  <Button
                    size="lg"
                    variant={isCritical ? "danger" : "primary"}
                    className="w-full mb-3"
                    onClick={() => setShowSignModal(true)}
                    isLoading={isSigning}
                  >
                    <CheckCircle size={16} className="mr-2" />
                    Valider & Signer la télé-expertise
                  </Button>

                  <Button
                    size="md"
                    variant="secondary"
                    className="w-full mb-3"
                    onClick={() => setShowRetake(true)}
                  >
                    <RotateCcw size={16} className="mr-2" />
                    Demander une réacquisition ECG
                  </Button>
                </>
              )}

              {/* Signed state info */}
              {isSigned && (
                <div className="signed-info mb-4">
                  <CheckCircle size={24} className="text-success mb-2 mx-auto" />
                  <p className="text-sm font-medium">Validé & Signé Électroniquement</p>
                  <p className="text-xs text-secondary mt-1">
                    {study?.signature || `${report?.signed_by_user?.first_name} ${report?.signed_by_user?.last_name}`}
                  </p>
                  <p className="text-xs text-mono text-tertiary mt-1">
                    {study?.signed_at
                      ? new Date(study.signed_at).toLocaleString("fr-FR")
                      : report?.signed_at
                      ? new Date(report.signed_at).toLocaleString("fr-FR")
                      : ""}
                  </p>
                </div>
              )}

              {/* FHIR export button */}
              <Button
                variant="secondary"
                className="w-full"
                onClick={handleExportFHIR}
                disabled={!isSigned}
              >
                <Download size={16} className="inline mr-2" />
                Exporter Ressource FHIR R4
              </Button>
            </div>
          </Card>
        </div>
      </div>

      {/* Modals */}
      {showRetake && (
        <RetakeModal onConfirm={handleRetake} onCancel={() => setShowRetake(false)} />
      )}
      {showSignModal && (
        <SignModal
          physicianName={`${user?.first_name || ""} ${user?.last_name || user?.username || ""}`.trim()}
          onConfirm={handleConfirmSign}
          onCancel={() => setShowSignModal(false)}
        />
      )}

      {toast && (
        <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />
      )}
    </div>
  );
};
