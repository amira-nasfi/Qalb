import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  getReport,
  updateReportNotes,
  signReport,
  claimReport,
  requestRetake,
  triggerEmergency,
} from "../api/reports";
import { downloadFHIRExport } from "../api/fhir";
import { getECGSignal } from "../api/ecg";
import type { Report } from "../types";
import { useAuth } from "../contexts/AuthContext";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Toast } from "../components/ui/Toast";
import {
  Activity,
  Download,
  CheckCircle,
  Edit3,
  ShieldAlert,
  User,
  Stethoscope,
  RotateCcw,
  Siren,
  ArrowLeft,
} from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
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

/* ── Emergency modal ───────────────────────────────────────── */
const EmergencyModal: React.FC<{
  onConfirm: (notes: string) => void;
  onCancel: () => void;
}> = ({ onConfirm, onCancel }) => {
  const [notes, setNotes] = useState("");
  return (
    <div className="modal-overlay modal-overlay-danger">
      <div className="modal-box modal-box-danger">
        <h3 className="modal-title text-critical">
          <Siren size={20} className="mr-2" />
          Déclencher une Alerte Urgence SAMU
        </h3>
        <p className="modal-desc">
          ⚠️ Cette action est <strong>irréversible</strong>. Elle verrouille le dossier et transmet instantanément les consignes au dispensaire. Réservez-la aux urgences vitales absolues.
        </p>
        <textarea
          className="modal-textarea modal-textarea-danger"
          placeholder="Consignes immédiates : appel SAMU 15, position de sécurité, défibrillation si disponible…"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={5}
          autoFocus
        />
        <div className="modal-actions">
          <Button variant="ghost" size="sm" onClick={onCancel}>Annuler</Button>
          <Button
            variant="danger"
            size="sm"
            onClick={() => notes.trim() && onConfirm(notes)}
            disabled={!notes.trim()}
          >
            <Siren size={14} className="mr-1" />
            Confirmer l'alerte SAMU
          </Button>
        </div>
      </div>
    </div>
  );
};

/* ── Main component ────────────────────────────────────────── */
export const ReviewPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user, role } = useAuth();

  const [report, setReport] = useState<Report | null>(null);
  const [signal, setSignal] = useState<any[]>([]);
  const [notes, setNotes] = useState("");
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);
  const [isSigning, setIsSigning] = useState(false);
  const [isClaiming, setIsClaiming] = useState(false);

  // Modals
  const [showRetake, setShowRetake] = useState(false);
  const [showEmergency, setShowEmergency] = useState(false);

  useEffect(() => {
    if (!id) return;
    const fetchData = async () => {
      try {
        const r = await getReport(id);
        setReport(r);
        setNotes(r.physician_notes || "");

        const sigData = await getECGSignal(r.job_id);
        const chartData = sigData.samples.map((val: number, idx: number) => ({
          time: idx,
          mv: val,
        }));
        setSignal(chartData);
      } catch (err) {
        console.error(err);
      }
    };
    fetchData();
  }, [id]);

  const handleSaveNotes = async () => {
    if (!report) return;
    try {
      await updateReportNotes(report.id, notes);
      setToast({ message: "Brouillon sauvegardé.", type: "success" });
    } catch {
      setToast({ message: "Échec de l'enregistrement du brouillon.", type: "error" });
    }
  };

  const handleSign = async () => {
    if (!report) return;
    if (!notes.trim()) {
      setToast({ message: "Une conclusion médicale est requise avant de signer.", type: "error" });
      return;
    }
    setIsSigning(true);
    try {
      await updateReportNotes(report.id, notes);
      const updated = await signReport(report.id);
      setReport(updated);
      setToast({ message: "Rapport signé électroniquement et verrouillé.", type: "success" });
    } catch {
      setToast({ message: "Échec lors de la signature du rapport.", type: "error" });
    } finally {
      setIsSigning(false);
    }
  };

  const handleClaim = async () => {
    if (!report) return;
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
  };

  const handleRetake = async (reason: string) => {
    if (!report) return;
    setShowRetake(false);
    try {
      const updated = await requestRetake(report.id, reason);
      setReport(updated);
      setToast({ message: "Demande de réacquisition transmise au dispensaire.", type: "success" });
    } catch {
      setToast({ message: "Échec de la demande de réacquisition.", type: "error" });
    }
  };

  const handleEmergency = async (emergencyNotes: string) => {
    if (!report) return;
    setShowEmergency(false);
    try {
      const updated = await triggerEmergency(report.id, emergencyNotes);
      setReport(updated);
      setToast({ message: "🚨 Alerte SAMU déclenchée. Consignes transmises.", type: "success" });
    } catch {
      setToast({ message: "Échec du déclenchement de l'alerte.", type: "error" });
    }
  };

  const handleExportFHIR = async () => {
    if (!report) return;
    try {
      await downloadFHIRExport(report.id);
      setToast({ message: "Bundle HL7 FHIR R4 exporté avec succès.", type: "success" });
    } catch {
      setToast({ message: "Échec lors de l'export FHIR.", type: "error" });
    }
  };

  if (!report) return <div className="clinical-empty-state">Chargement du dossier clinique...</div>;

  const isPhysician = role === "PHYSICIAN";
  const isSigned = report.status === "SIGNED";
  const isEmergency = report.status === "EMERGENCY_TRANSFER";
  const isRetake = report.status === "RETAKE_REQUESTED";
  const isLocked = isSigned || isEmergency || isRetake;
  const isCritical = report.severity === "CRITICAL";

  const isMyClaim =
    report.status === "IN_REVIEW" &&
    report.claimed_by_user?.username === user?.username;
  const isOtherClaim =
    report.status === "IN_REVIEW" &&
    report.claimed_by_user &&
    report.claimed_by_user.username !== user?.username;
  const isPending = report.status === "PENDING_REVIEW";

  const getSeverityLabel = (sev: string) =>
    ({ CRITICAL: "CRITIQUE", URGENT: "URGENT", ROUTINE: "ROUTINE" }[sev] ?? sev);

  const patientDisplayName =
    report.patient_name || report.patient?.full_name || `Patient ${report.pseudo_id.slice(0, 8)}`;
  const patientIdentifier =
    report.patient_identifier || report.patient?.patient_identifier || report.pseudo_id.slice(0, 8);
  const patientAge = report.patient_age || report.patient?.age;
  const patientGender =
    (report.patient_gender || report.patient?.gender) === "female" ? "Femme" : "Homme";

  return (
    <div className="review-page">
      {/* ── Back button ── */}
      {isPhysician && (
        <button className="back-btn" onClick={() => navigate("/doctor")}>
          <ArrowLeft size={16} className="mr-1" />
          Retour au portail
        </button>
      )}

      {/* ── Header ── */}
      <div className={`review-header ${isCritical && !isLocked ? "header-critical" : ""}`}>
        <div className="header-info">
          <h1 className="page-title">Dossier #{report.id}</h1>
          <div className="patient-id flex items-center gap-2 mt-1">
            <User size={16} className="text-secondary" />
            <span className="font-semibold text-main">{patientDisplayName}</span>
            <span className="text-muted">·</span>
            <span className="text-mono text-sm text-tertiary">IPP : {patientIdentifier}</span>
            {patientAge && (
              <>
                <span className="text-muted">·</span>
                <span className="text-sm text-secondary">
                  {patientAge} ans ({patientGender})
                </span>
              </>
            )}
          </div>
        </div>
        <div className="header-actions">
          <Badge severity={report.severity} className="mr-4">
            {getSeverityLabel(report.severity)}
          </Badge>
          {isSigned && <Badge severity="SUCCESS">Validé & Signé</Badge>}
          {isEmergency && <Badge severity="CRITICAL">🚨 Urgence SAMU</Badge>}
          {isRetake && <Badge severity="WARNING">Réacquisition demandée</Badge>}
          {report.status === "IN_REVIEW" && <Badge severity="URGENT">En cours d'analyse</Badge>}
          {isPending && <Badge severity="WARNING">En attente</Badge>}
        </div>
      </div>

      {/* ── Critical alert banner ── */}
      {isCritical && !isLocked && (
        <div className="critical-banner">
          <ShieldAlert size={20} />
          <span>Intervention clinique urgente requise sur la base du triage déterministe.</span>
        </div>
      )}

      {/* ── Claim status banner ── */}
      {report.status === "IN_REVIEW" && report.claimed_by_user && (
        <div className={`claim-banner ${isMyClaim ? "claim-banner-mine" : "claim-banner-other"}`}>
          <Stethoscope size={18} />
          <span>
            {isMyClaim
              ? `Vous avez pris en charge ce dossier le ${report.claimed_at ? new Date(report.claimed_at).toLocaleString("fr-FR") : "—"}.`
              : `Pris en charge par Dr. ${report.claimed_by_user.first_name} ${report.claimed_by_user.last_name} · N° Licence : ${report.claimed_by_user.username}`}
          </span>
        </div>
      )}

      {/* ── Retake banner ── */}
      {isRetake && report.retake_reason && (
        <div className="retake-banner">
          <RotateCcw size={18} />
          <div>
            <strong>Réacquisition demandée :</strong>
            <span className="ml-2">{report.retake_reason}</span>
          </div>
        </div>
      )}

      {/* ── Emergency banner ── */}
      {isEmergency && report.emergency_notes && (
        <div className="emergency-banner">
          <Siren size={18} />
          <div>
            <strong>🚨 Consignes SAMU transmises :</strong>
            <span className="ml-2">{report.emergency_notes}</span>
          </div>
        </div>
      )}

      <div className="review-grid">
        {/* ── Main column ── */}
        <div className="review-main">
          <Card className="mb-6 chart-card">
            <div className="card-header">
              <h2>
                <Activity size={18} className="inline mr-2 text-teal" />
                Moniteur ECG (Dérivation II)
              </h2>
            </div>
            <div className="chart-container">
              {signal.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={signal}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" vertical={false} />
                    <XAxis dataKey="time" hide />
                    <YAxis domain={["auto", "auto"]} hide />
                    <Tooltip
                      labelFormatter={() => ""}
                      formatter={(val: any) => [`${Number(val).toFixed(2)} mV`, "Amplitude"]}
                      contentStyle={{
                        backgroundColor: "var(--navy-dark)",
                        color: "white",
                        border: "none",
                        borderRadius: "4px",
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="mv"
                      stroke={
                        isEmergency
                          ? "#ef4444"
                          : isCritical && !isLocked
                          ? "var(--status-critical)"
                          : "var(--mint-dark)"
                      }
                      dot={false}
                      strokeWidth={1.5}
                      isAnimationActive={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-full text-tertiary">
                  Chargement du signal...
                </div>
              )}
            </div>
          </Card>

          <Card className="mb-6">
            <div className="card-header">
              <h2>Synthèse Clinique Automatique</h2>
            </div>
            <div className="draft-text">
              {report.draft_text.split("\n").map((line, i) => (
                <p key={i}>{line}</p>
              ))}
            </div>
          </Card>
        </div>

        {/* ── Right panel ── */}
        <div className="review-sidebar">
          {/* Notes card */}
          <Card className="mb-6">
            <div className="card-header">
              <h2>
                <Edit3 size={18} className="inline mr-2 text-teal" />
                Conclusions du Médecin
              </h2>
            </div>
            <div className="card-body p-0">
              <textarea
                className="notes-textarea"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Saisissez l'impression clinique, les conclusions diagnostiques et la conduite à tenir..."
                disabled={isLocked}
                rows={10}
              />
              {!isLocked && (
                <div className="notes-actions">
                  <Button variant="ghost" size="sm" onClick={handleSaveNotes}>
                    Enregistrer brouillon
                  </Button>
                </div>
              )}
            </div>
          </Card>

          {/* Decision actions card */}
          <Card className="actions-card">
            <div className="card-body">
              {/* Physician: claim if pending */}
              {isPhysician && isPending && (
                <Button
                  size="lg"
                  variant="secondary"
                  className="w-full mb-4"
                  onClick={handleClaim}
                  isLoading={isClaiming}
                >
                  <Stethoscope size={16} className="mr-2" />
                  Prendre en charge ce dossier
                </Button>
              )}

              {/* Physician: decision buttons when case is mine */}
              {isPhysician && !isLocked && (isMyClaim || isOtherClaim === false) && !isPending && (
                <>
                  <Button
                    size="lg"
                    variant={isCritical ? "danger" : "primary"}
                    className="w-full mb-3"
                    onClick={handleSign}
                    isLoading={isSigning}
                  >
                    <CheckCircle size={16} className="mr-2" />
                    Valider &amp; Signer la télé-expertise
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

                  <Button
                    size="md"
                    variant="danger"
                    className="w-full mb-4"
                    onClick={() => setShowEmergency(true)}
                  >
                    <Siren size={16} className="mr-2" />
                    Déclencher Urgence SAMU
                  </Button>
                </>
              )}

              {/* Signed state */}
              {isSigned && (
                <div className="signed-info mb-4">
                  <CheckCircle size={24} className="text-success mb-2 mx-auto" />
                  <p className="text-sm font-medium">Signé électroniquement</p>
                  <p className="text-xs text-tertiary mt-1">
                    {report.signed_by_user?.first_name} {report.signed_by_user?.last_name}
                  </p>
                  <p className="text-xs text-mono text-tertiary mt-1">
                    {new Date(report.signed_at!).toLocaleString("fr-FR")}
                  </p>
                </div>
              )}

              {/* FHIR export */}
              <Button
                variant="secondary"
                className="w-full"
                onClick={handleExportFHIR}
                disabled={!isSigned}
              >
                <Download size={16} className="inline mr-2" />
                Exporter au format HL7 FHIR
              </Button>
            </div>
          </Card>
        </div>
      </div>

      {/* ── Modals ── */}
      {showRetake && (
        <RetakeModal
          onConfirm={handleRetake}
          onCancel={() => setShowRetake(false)}
        />
      )}
      {showEmergency && (
        <EmergencyModal
          onConfirm={handleEmergency}
          onCancel={() => setShowEmergency(false)}
        />
      )}

      {toast && (
        <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />
      )}
    </div>
  );
};
