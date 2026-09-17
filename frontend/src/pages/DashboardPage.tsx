import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getReports } from "../api/reports";
import type { Report } from "../types";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Skeleton } from "../components/ui/Skeleton";
import {
  ChevronRight,
  User,
  RotateCcw,
  Siren,
  CheckCircle2,
  PhoneCall,
  UploadCloud,
} from "lucide-react";
import "./DashboardPage.css";

export const DashboardPage: React.FC = () => {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchReports = async () => {
      try {
        const data = await getReports();
        setReports(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchReports();
  }, []);

  const emergencies = reports.filter((r) => r.status === "EMERGENCY_TRANSFER");
  const retakes = reports.filter((r) => r.status === "RETAKE_REQUESTED");
  const signed = reports.filter((r) => r.status === "SIGNED");
  const inProgress = reports.filter((r) =>
    ["PENDING_REVIEW", "IN_REVIEW"].includes(r.status)
  );

  const getSeverityLabel = (severity: string) => {
    switch (severity) {
      case "CRITICAL":
        return "CRITIQUE";
      case "URGENT":
        return "URGENT";
      case "ROUTINE":
        return "ROUTINE";
      default:
        return severity;
    }
  };

  return (
    <div className="dashboard-page">
      <div className="dashboard-header">
        <h1 className="page-title">Suivi des Examens ECG</h1>
        <p className="page-subtitle">
          Consultez les validations, demandes de réacquisition et alertes SAMU des médecins télé-experts
        </p>
      </div>

      <div className="dashboard-content">
        {/* 🚨 Section 1: Urgences SAMU */}
        {emergencies.length > 0 && (
          <div
            style={{
              background: "#fee2e2",
              border: "2px solid #ef4444",
              borderRadius: "12px",
              padding: "16px 20px",
              marginBottom: "24px",
            }}
          >
            <div className="flex items-center gap-2" style={{ color: "#991b1b", fontWeight: 700, fontSize: "1.1rem" }}>
              <Siren size={24} className="text-critical animate-pulse" />
              <span>Alerte Urgence Vitale SAMU déclenchée ({emergencies.length})</span>
            </div>
            <p style={{ color: "#7f1d1d", fontSize: "0.88rem", marginTop: "4px" }}>
              Le médecin télé-expert a identifié une urgence absolue. Appelez immédiatement le SAMU (15) ou appliquez les consignes ci-dessous.
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginTop: "12px" }}>
              {emergencies.map((r) => (
                <div
                  key={r.id}
                  style={{
                    background: "white",
                    borderRadius: "8px",
                    padding: "12px 16px",
                    border: "1px solid #fca5a5",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    flexWrap: "wrap",
                    gap: "8px",
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 700, color: "#1e293b" }}>
                      Patient : {r.patient_name || `Dossier #${r.id}`} (IPP: {r.patient_identifier || r.pseudo_id})
                    </div>
                    {r.emergency_notes && (
                      <div style={{ color: "#b91c1c", fontSize: "0.85rem", marginTop: "4px", fontStyle: "italic" }}>
                        Consignes médecin : « {r.emergency_notes} »
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <a
                      href="tel:15"
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "6px",
                        background: "#dc2626",
                        color: "white",
                        padding: "8px 14px",
                        borderRadius: "6px",
                        fontWeight: 600,
                        fontSize: "0.85rem",
                        textDecoration: "none",
                      }}
                    >
                      <PhoneCall size={16} /> Appeler SAMU 15
                    </a>
                    <Link to={`/review/${r.id}`} className="clinical-link" style={{ fontSize: "0.85rem" }}>
                      Détails <ChevronRight size={14} />
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 🔄 Section 2: Réacquisitions demandées */}
        {retakes.length > 0 && (
          <div
            style={{
              background: "#fef3c7",
              border: "1.5px solid #f59e0b",
              borderRadius: "12px",
              padding: "16px 20px",
              marginBottom: "24px",
            }}
          >
            <div className="flex items-center gap-2" style={{ color: "#92400e", fontWeight: 700, fontSize: "1.05rem" }}>
              <RotateCcw size={20} style={{ color: "#d97706" }} />
              <span>Nouveaux enregistrements demandés par le médecin ({retakes.length})</span>
            </div>
            <p style={{ color: "#78350f", fontSize: "0.85rem", marginTop: "4px" }}>
              Le tracé initial était inexploitable (artéfacts, inversion d'électrodes). Veuillez réaliser une nouvelle acquisition pour ces patients.
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "12px" }}>
              {retakes.map((r) => (
                <div
                  key={r.id}
                  style={{
                    background: "white",
                    borderRadius: "8px",
                    padding: "12px 16px",
                    border: "1px solid #fde68a",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    flexWrap: "wrap",
                    gap: "8px",
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 600, color: "#1e293b" }}>
                      Patient : {r.patient_name || `Dossier #${r.id}`} (IPP: {r.patient_identifier || r.pseudo_id})
                    </div>
                    {r.retake_reason && (
                      <div style={{ color: "#b45309", fontSize: "0.85rem", marginTop: "2px" }}>
                        Motif : <strong>{r.retake_reason}</strong>
                      </div>
                    )}
                  </div>
                  <Link
                    to="/upload"
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "6px",
                      background: "#d97706",
                      color: "white",
                      padding: "7px 12px",
                      borderRadius: "6px",
                      fontWeight: 600,
                      fontSize: "0.82rem",
                      textDecoration: "none",
                    }}
                  >
                    <UploadCloud size={15} /> Réenregistrer l'ECG
                  </Link>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ⏳ Section 3: En cours d'analyse */}
        {inProgress.length > 0 && (
          <div style={{ marginBottom: "24px" }}>
            <Card className="dashboard-card mb-6">
              <div className="card-header flex justify-between">
                <h2 className="card-title">En attente d'avis médical</h2>
                <Badge severity="WARNING" showDot={false}>{inProgress.length} en cours</Badge>
              </div>
            <div className="table-responsive">
              <table className="clinical-table">
                <thead>
                  <tr>
                    <th>Dossier</th>
                    <th>Patient</th>
                    <th>Date d'acquisition</th>
                    <th>Gravité estimée</th>
                    <th>Statut télé-expertise</th>
                  </tr>
                </thead>
                <tbody>
                  {inProgress.map((r) => (
                    <tr key={r.id}>
                      <td className="text-mono tnum text-secondary">#{r.id}</td>
                      <td>
                        <div className="flex items-center gap-2">
                          <User size={15} className="text-tertiary" />
                          <div className="font-semibold text-main">
                            {r.patient_name || `Patient ${r.pseudo_id.split("-")[0]}`}
                          </div>
                        </div>
                      </td>
                      <td className="text-sm">{new Date(r.created_at).toLocaleString("fr-FR")}</td>
                      <td>
                        <Badge severity={r.severity}>{getSeverityLabel(r.severity)}</Badge>
                      </td>
                      <td>
                        <Badge severity="NEUTRAL">
                          {r.status === "IN_REVIEW" ? "Pris en charge par un médecin" : "Transmis aux cardiologues"}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
        )}

        {/* ✅ Section 4: Rapports validés & signés */}
        <Card className="dashboard-card">
          <div className="card-header flex justify-between">
            <h2 className="card-title">Rapports Validés & Signés</h2>
            <Badge severity="SUCCESS" showDot={false}>{signed.length} validés</Badge>
          </div>
          {loading ? (
            <div className="p-6"><Skeleton height="150px" /></div>
          ) : signed.length === 0 ? (
            <div className="clinical-empty-state">Aucun rapport signé pour l'instant.</div>
          ) : (
            <div className="table-responsive">
              <table className="clinical-table">
                <thead>
                  <tr>
                    <th>Dossier</th>
                    <th>Patient</th>
                    <th>Date validation</th>
                    <th>Gravité</th>
                    <th>Statut</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {signed.map((r) => (
                    <tr key={r.id}>
                      <td className="text-mono tnum text-secondary">#{r.id}</td>
                      <td>
                        <div className="flex items-center gap-2">
                          <User size={15} className="text-tertiary" />
                          <div>
                            <div className="font-semibold text-main">
                              {r.patient_name || `Patient ${r.pseudo_id.split("-")[0]}`}
                            </div>
                            <div className="text-xs text-muted text-mono">
                              {r.patient_identifier || r.pseudo_id.split("-")[0]}
                              {r.patient_age ? ` · ${r.patient_age} ans` : ""}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="text-sm">{r.signed_at ? new Date(r.signed_at).toLocaleString("fr-FR") : new Date(r.created_at).toLocaleString("fr-FR")}</td>
                      <td>
                        <Badge severity={r.severity}>{getSeverityLabel(r.severity)}</Badge>
                      </td>
                      <td>
                        <span style={{ display: "inline-flex", alignItems: "center", gap: "4px", color: "#059669", fontWeight: 600, fontSize: "0.85rem" }}>
                          <CheckCircle2 size={15} /> Signé & Conforme
                        </span>
                      </td>
                      <td className="action-cell">
                        <Link to={`/review/${r.id}`} className="clinical-link">
                          Consulter rapport <ChevronRight size={16} />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};
