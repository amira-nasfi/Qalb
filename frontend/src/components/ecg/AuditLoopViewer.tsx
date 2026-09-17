import React, { useState, useEffect } from "react";
import type { StudyAuditResponse } from "../../types";
import { getStudyAudit, deliverStudy } from "../../api/ecg";
import { Button } from "../ui/Button";
import { Toast } from "../ui/Toast";
import {
  Clock,
  AlertTriangle,
  Send,
  RefreshCw,
  Server,
  ArrowRight,
  Zap,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import "./AuditLoopViewer.css";

interface AuditLoopViewerProps {
  studyId: number;
  currentState: string;
  onStateChange?: (newState: string) => void;
}

export const AuditLoopViewer: React.FC<AuditLoopViewerProps> = ({
  studyId,
  currentState,
  onStateChange,
}) => {
  const [auditData, setAuditData] = useState<StudyAuditResponse | null>(null);
  const [delivering, setDelivering] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  const fetchAudit = async () => {
    try {
      const data = await getStudyAudit(studyId);
      setAuditData(data);
    } catch {
      // Ignore initial silent fail
    }
  };

  useEffect(() => {
    fetchAudit();
  }, [studyId, currentState]);

  const handleDeliver = async (simulateFailure: boolean) => {
    setDelivering(true);
    try {
      const res = await deliverStudy(studyId, simulateFailure);
      setToast({
        message: "Compte rendu transmis avec succès au SIH (Ressource FHIR DiagnosticReport créée).",
        type: "success",
      });
      if (onStateChange) onStateChange(res.state);
      await fetchAudit();
    } catch (err: any) {
      if (simulateFailure) {
        setToast({
          message: "Démonstration d'erreur réussie : 502 Bad Gateway (HIS Timeout) consigné dans l'audit.",
          type: "error",
        });
      } else {
        setToast({
          message: err?.response?.data?.detail || "Erreur de transmission au SIH.",
          type: "error",
        });
      }
      await fetchAudit();
    } finally {
      setDelivering(false);
    }
  };

  if (!auditData) {
    return (
      <div className="audit-loading">
        <RefreshCw size={18} className="animate-spin text-primary" />
        <span className="ml-2">Chargement de l'audit de boucle médicale...</span>
      </div>
    );
  }

  // Bar chart data from loop timings
  const chartData = (auditData.loop_timings || []).map((t) => ({
    name: t.leg,
    seconds: t.seconds,
  }));

  const COLORS = ["#3b82f6", "#06b6d4", "#8b5cf6", "#f59e0b", "#10b981"];

  return (
    <div className="audit-loop-card" id="audit-medical-loop">
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}

      {/* Header with Turnaround Time KPI */}
      <div className="audit-header">
        <div className="audit-title-block">
          <Clock size={22} className="text-primary mr-2" />
          <div>
            <h3 className="audit-heading">Audit Clinique de la Boucle Médicale (Traçabilité Append-Only)</h3>
            <p className="audit-sub">
              Mesure précise des temps de réaction entre acquisition au dispensaire et restitution SIH
            </p>
          </div>
        </div>

        {/* Big Turnaround KPI Chip */}
        <div className="turnaround-kpi-chip">
          <div className="kpi-label">DÉLAI GLOBAL (Turnaround)</div>
          <div className="kpi-value">
            {auditData.turnaround_s !== null ? (
              <>
                <span className="kpi-number">{auditData.turnaround_s.toFixed(1)}</span>
                <span className="kpi-unit">secondes</span>
              </>
            ) : (
              <span className="kpi-pending">En cours de boucle</span>
            )}
          </div>
          <div className="kpi-desc">Acquisition dispensaire ➔ Signature médecin</div>
        </div>
      </div>

      {/* Loop Legs Summary Badges */}
      <div className="loop-legs-grid">
        {(auditData.loop_timings || []).map((leg, idx) => (
          <div key={idx} className="loop-leg-card">
            <div className="leg-name">{leg.leg}</div>
            <div className="leg-value">{leg.seconds.toFixed(1)} s</div>
          </div>
        ))}
      </div>

      {/* Recharts Bar Chart of Delays */}
      {chartData.length > 0 && (
        <div className="loop-chart-section">
          <h4 className="chart-title">Répartition temporelle par étape du parcours patient (secondes)</h4>
          <div className="loop-chart-wrapper">
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 20 }}>
                <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} />
                <YAxis unit="s" tick={{ fontSize: 11 }} />
                <Tooltip
                  formatter={(value: any) => [`${value} s`, "Durée"]}
                  contentStyle={{ borderRadius: 6, fontSize: 12 }}
                />
                <Bar dataKey="seconds" radius={[4, 4, 0, 0]}>
                  {chartData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Internal pipeline timings */}
      {auditData.analysis_timings?.steps && (
        <div className="pipeline-timings-strip">
          <div className="pipeline-header">
            <Zap size={14} className="text-warning mr-1" />
            <span className="pipeline-title">
              Délais internes du moteur d'analyse : {auditData.analysis_timings.total_ms?.toFixed(1)} ms au total
            </span>
          </div>
          <div className="pipeline-steps-chips">
            {auditData.analysis_timings.steps.map((st, sIdx) => (
              <span key={sIdx} className="pipeline-chip">
                {st.step}: <strong>{st.duration_ms?.toFixed(1)} ms</strong>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* HIS Restitution Demonstration Actions */}
      <div className="his-delivery-actions">
        <div className="delivery-info">
          <Server size={18} className="text-primary mr-2" />
          <div>
            <span className="font-semibold text-slate-800">Restitution au SIH Hospitalier (FHIR HL7) :</span>
            <p className="text-xs text-slate-500 m-0">
              {auditData.state === "delivered"
                ? "Compte rendu délivré et archivé dans le dossier patient informatisé (DPI)."
                : "Permet de transmettre le compte rendu validé ou de simuler une coupure de passerelle."}
            </p>
          </div>
        </div>

        <div className="delivery-buttons">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleDeliver(true)}
            disabled={delivering || auditData.state !== "signed"}
            className="sim-failure-btn"
            title="Démontre le comportement en cas de timeout réseau hospitalier"
          >
            <AlertTriangle size={15} className="mr-1 text-warning" />
            Simuler Échec SIH (504)
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={() => handleDeliver(false)}
            disabled={delivering || auditData.state !== "signed"}
            className="deliver-btn"
          >
            <Send size={15} className="mr-1" />
            {auditData.state === "delivered" ? "Déjà Restitué au SIH" : "Restituer au SIH"}
          </Button>
        </div>
      </div>

      {/* Audit Event Trail Table */}
      <div className="audit-trail-table-section">
        <h4 className="table-title">Journal d'Audit Immuable (Registre Sécurisé)</h4>
        <div className="audit-table-wrapper">
          <table className="audit-table">
            <thead>
              <tr>
                <th>Horodatage</th>
                <th>Action</th>
                <th>Acteur</th>
                <th>Transition d'État</th>
                <th>Détails & Métriques</th>
              </tr>
            </thead>
            <tbody>
              {auditData.events.map((ev, eIdx) => {
                const isError = ev.action === "erreur_transmission" || ev.action === "erreur_lecture";
                const isSuccess = ev.action === "restitution_sih" || ev.action === "signature";
                return (
                  <tr key={eIdx} className={isError ? "row-error" : isSuccess ? "row-success" : ""}>
                    <td className="font-mono text-xs">{new Date(ev.at).toLocaleTimeString()}</td>
                    <td>
                      <span className={`action-badge ${isError ? "badge-error" : ""}`}>
                        {ev.action}
                      </span>
                    </td>
                    <td className="text-xs">{ev.actor || "Système / Automate"}</td>
                    <td className="text-xs font-mono">
                      {ev.from} <ArrowRight size={12} className="inline mx-1 text-slate-400" /> {ev.to}
                    </td>
                    <td className="text-xs text-slate-600">
                      {isError ? (
                        <span className="text-critical font-medium">
                          {ev.detail?.error || JSON.stringify(ev.detail)}
                        </span>
                      ) : (
                        <span>{JSON.stringify(ev.detail)}</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
