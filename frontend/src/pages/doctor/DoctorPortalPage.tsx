import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getReports, claimReport } from "../../api/reports";
import type { Report } from "../../types";
import { useAuth } from "../../contexts/AuthContext";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Toast } from "../../components/ui/Toast";
import {
  Stethoscope,
  Clock,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Siren,
  ArrowRight,
  User,
} from "lucide-react";
import "./DoctorPortalPage.css";

/* ─── helpers ─────────────────────────────────────────────── */
const severityOrder: Record<string, number> = {
  CRITICAL: 0,
  URGENT: 1,
  ROUTINE: 2,
};

const statusLabel: Record<string, string> = {
  PENDING_REVIEW: "En attente",
  IN_REVIEW: "En cours",
  SIGNED: "Validé",
  RETAKE_REQUESTED: "Réacquisition demandée",
  EMERGENCY_TRANSFER: "Urgence SAMU",
};

const getSeverityLabel = (sev: string) =>
  ({ CRITICAL: "CRITIQUE", URGENT: "URGENT", ROUTINE: "ROUTINE" }[sev] ?? sev);

/* ─── component ───────────────────────────────────────────── */
export const DoctorPortalPage: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [claimingId, setClaimingId] = useState<number | null>(null);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  const fetchReports = async () => {
    try {
      const all = await getReports();
      // Sort by severity then date
      const sorted = [...all].sort((a, b) => {
        const sevDiff = (severityOrder[a.severity] ?? 3) - (severityOrder[b.severity] ?? 3);
        if (sevDiff !== 0) return sevDiff;
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      });
      setReports(sorted);
    } catch {
      setToast({ message: "Impossible de charger les dossiers.", type: "error" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
    // Auto-refresh every 30 s
    const iv = setInterval(fetchReports, 30_000);
    return () => clearInterval(iv);
  }, []);

  const handleClaim = async (reportId: number) => {
    setClaimingId(reportId);
    try {
      await claimReport(reportId);
      setToast({ message: "Dossier pris en charge. Ouverture du poste de lecture…", type: "success" });
      setTimeout(() => navigate(`/review/${reportId}`), 800);
    } catch (err: any) {
      const msg =
        err?.response?.data?.error ?? "Impossible de prendre en charge ce dossier.";
      setToast({ message: msg, type: "error" });
    } finally {
      setClaimingId(null);
    }
  };

  /* KPI counters */
  const pending = reports.filter((r) => r.status === "PENDING_REVIEW").length;
  const mine = reports.filter(
    (r) => r.status === "IN_REVIEW" && r.claimed_by_user?.username === user?.username
  ).length;
  const done = reports.filter((r) =>
    ["SIGNED", "RETAKE_REQUESTED", "EMERGENCY_TRANSFER"].includes(r.status)
  ).length;

  const openCases = reports.filter((r) =>
    ["PENDING_REVIEW", "IN_REVIEW"].includes(r.status)
  );
  const closedCases = reports.filter((r) =>
    ["SIGNED", "RETAKE_REQUESTED", "EMERGENCY_TRANSFER"].includes(r.status)
  );

  return (
    <div className="doctor-portal">
      {/* ── Header ── */}
      <div className="portal-header">
        <div>
          <h1 className="portal-title">
            <Stethoscope size={28} className="inline mr-3 text-teal" />
            Portail de Télé-Interprétation
          </h1>
          <p className="portal-subtitle">
            File d'expertise cardiologique · Mise à jour automatique toutes les 30 s
          </p>
        </div>
      </div>

      {/* ── KPI strip ── */}
      <div className="kpi-strip">
        <div className="kpi-card kpi-pending">
          <Clock size={22} />
          <div>
            <span className="kpi-value">{pending}</span>
            <span className="kpi-label">En attente</span>
          </div>
        </div>
        <div className="kpi-card kpi-inreview">
          <Stethoscope size={22} />
          <div>
            <span className="kpi-value">{mine}</span>
            <span className="kpi-label">Mes dossiers en cours</span>
          </div>
        </div>
        <div className="kpi-card kpi-done">
          <CheckCircle2 size={22} />
          <div>
            <span className="kpi-value">{done}</span>
            <span className="kpi-label">Dossiers traités</span>
          </div>
        </div>
      </div>

      {/* ── Open queue ── */}
      <section className="portal-section">
        <h2 className="section-title">
          <AlertTriangle size={18} className="text-warning inline mr-2" />
          File d'expertise — Dossiers ouverts
        </h2>

        {loading ? (
          <div className="empty-state">Chargement des dossiers…</div>
        ) : openCases.length === 0 ? (
          <div className="empty-state">
            <CheckCircle2 size={36} className="text-success mb-2" />
            <p>Aucun dossier en attente. File d'expertise à jour ✓</p>
          </div>
        ) : (
          <div className="report-table">
            <div className="table-header">
              <span>Patient</span>
              <span>Gravité</span>
              <span>Statut</span>
              <span>Arrivée</span>
              <span>Médecin</span>
              <span></span>
            </div>
            {openCases.map((r) => {
              const isMyClaim =
                r.status === "IN_REVIEW" &&
                r.claimed_by_user?.username === user?.username;
              const otherClaim =
                r.status === "IN_REVIEW" &&
                r.claimed_by_user &&
                r.claimed_by_user.username !== user?.username;

              return (
                <div
                  key={r.id}
                  className={`table-row ${r.severity === "CRITICAL" ? "row-critical" : r.severity === "URGENT" ? "row-urgent" : ""}`}
                >
                  {/* Patient */}
                  <div className="cell-patient">
                    <User size={15} style={{ color: "#0284c7" }} className="mr-1" />
                    <span className="patient-name" style={{ color: "#0f172a", fontWeight: 700 }}>
                      {r.patient_name || `Patient ${r.pseudo_id.slice(0, 8)}`}
                    </span>
                    {r.patient_age && (
                      <span className="patient-age">
                        {r.patient_age} ans
                      </span>
                    )}
                  </div>

                  {/* Severity */}
                  <div>
                    <Badge severity={r.severity}>{getSeverityLabel(r.severity)}</Badge>
                  </div>

                  {/* Status */}
                  <div>
                    <span className={`status-chip status-${r.status.toLowerCase()}`}>
                      {statusLabel[r.status] ?? r.status}
                    </span>
                  </div>

                  {/* Date */}
                  <div className="text-sm text-secondary">
                    {new Date(r.created_at).toLocaleString("fr-FR", {
                      day: "2-digit",
                      month: "2-digit",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </div>

                  {/* Claimed by */}
                  <div className="text-sm text-secondary">
                    {r.claimed_by_user
                      ? `Dr. ${r.claimed_by_user.last_name}`
                      : "—"}
                  </div>

                  {/* Action */}
                  <div className="cell-action">
                    {isMyClaim ? (
                      <Button
                        size="sm"
                        variant="primary"
                        onClick={() => navigate(`/review/${r.id}`)}
                      >
                        Reprendre <ArrowRight size={14} className="ml-1" />
                      </Button>
                    ) : otherClaim ? (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => navigate(`/review/${r.id}`)}
                      >
                        Consulter
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        variant="secondary"
                        isLoading={claimingId === r.id}
                        onClick={() => handleClaim(r.id)}
                      >
                        Prendre en charge
                      </Button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* ── Closed / historical ── */}
      {closedCases.length > 0 && (
        <section className="portal-section mt-8">
          <h2 className="section-title">
            <CheckCircle2 size={18} className="text-success inline mr-2" />
            Historique — Dossiers traités
          </h2>
          <div className="report-table">
            <div className="table-header">
              <span>Patient</span>
              <span>Gravité</span>
              <span>Issue</span>
              <span>Traité le</span>
              <span>Médecin signataire</span>
              <span></span>
            </div>
            {closedCases.map((r) => (
              <div key={r.id} className="table-row row-closed">
                <div className="cell-patient">
                  <User size={15} style={{ color: "#0284c7" }} className="mr-1" />
                  <span className="patient-name" style={{ color: "#0f172a", fontWeight: 700 }}>
                    {r.patient_name || `Patient ${r.pseudo_id.slice(0, 8)}`}
                  </span>
                </div>
                <div>
                  <Badge severity={r.severity}>{getSeverityLabel(r.severity)}</Badge>
                </div>
                <div>
                  {r.status === "SIGNED" && (
                    <span className="status-chip status-signed">
                      <CheckCircle2 size={12} className="inline mr-1" />Validé & Signé
                    </span>
                  )}
                  {r.status === "RETAKE_REQUESTED" && (
                    <span className="status-chip status-retake_requested">
                      <RotateCcw size={12} className="inline mr-1" />Réacquisition
                    </span>
                  )}
                  {r.status === "EMERGENCY_TRANSFER" && (
                    <span className="status-chip status-emergency_transfer">
                      <Siren size={12} className="inline mr-1" />Urgence SAMU
                    </span>
                  )}
                </div>
                <div className="text-sm text-secondary">
                  {r.signed_at
                    ? new Date(r.signed_at).toLocaleString("fr-FR", {
                        day: "2-digit",
                        month: "2-digit",
                        hour: "2-digit",
                        minute: "2-digit",
                      })
                    : "—"}
                </div>
                <div className="text-sm text-secondary">
                  {r.signed_by_user
                    ? `Dr. ${r.signed_by_user.first_name} ${r.signed_by_user.last_name}`
                    : "—"}
                </div>
                <div className="cell-action">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => navigate(`/review/${r.id}`)}
                  >
                    Voir le dossier
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {toast && (
        <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />
      )}
    </div>
  );
};
