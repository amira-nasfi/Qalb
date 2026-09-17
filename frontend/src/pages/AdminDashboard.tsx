import React, { useEffect, useState } from "react";
import { getAuditLogs } from "../api/admin";
import type { AuditLogEntry } from "../api/admin";
import { Card } from "../components/ui/Card";
import { Skeleton } from "../components/ui/Skeleton";
import {
  Shield,
  Clock,
  User,
  Activity,
} from "lucide-react";
import "./AdminDashboard.css";

export const AdminDashboard: React.FC = () => {
  // System Audit Log
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [logsLoading, setLogsLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const data = await getAuditLogs();
        setLogs(data);
      } catch (err) {
        console.error("Failed to fetch audit logs", err);
      } finally {
        setLogsLoading(false);
      }
    })();
  }, []);

  return (
    <div className="admin-page">
      {/* ── Page header ──────────────────────────────────────────────────── */}
      <div className="admin-header">
        <h1 className="page-title">
          <Shield className="inline mr-2 text-mint" /> Administration — Traçabilité &amp; Audit
        </h1>
        <p className="page-subtitle">
          Journal chronologique immuable de toutes les opérations et accès à la plateforme
        </p>
      </div>

      {/* ══════════════════════════════════════════════════════════════════
          Piste d'Audit Système
          ══════════════════════════════════════════════════════════════════ */}
      <section className="system-audit-section" id="section-system-audit">
        <div className="section-header">
          <div className="section-title-row">
            <Shield size={20} className="text-mint mr-2" />
            <div>
              <h2 className="section-title">Piste d'Audit Système</h2>
              <p className="section-sub">
                Journal chronologique immuable de toutes les opérations et accès à la plateforme
              </p>
            </div>
          </div>
        </div>

        <Card className="audit-card">
          <div className="card-header">
            <h3 className="card-title">Historique des Événements</h3>
          </div>

          {logsLoading ? (
            <div className="p-6"><Skeleton height="300px" /></div>
          ) : logs.length === 0 ? (
            <div className="clinical-empty-state">Aucun événement d'audit enregistré.</div>
          ) : (
            <div className="table-responsive">
              <table className="clinical-table audit-table">
                <thead>
                  <tr>
                    <th><Clock size={14} className="inline mr-1" /> Horodatage</th>
                    <th>Action</th>
                    <th><User size={14} className="inline mr-1" /> Auteur</th>
                    <th><Activity size={14} className="inline mr-1" /> Cible</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log) => (
                    <tr key={log.id}>
                      <td className="text-sm font-mono text-tertiary">
                        {new Date(log.timestamp).toLocaleString("fr-FR")}
                      </td>
                      <td>
                        <span className="action-badge">{log.action}</span>
                      </td>
                      <td className="text-sm font-medium">
                        {log.actor_display || log.actor_label || "Système"}
                      </td>
                      <td className="text-sm text-mono">
                        {log.target_type} <span className="text-tertiary">#{log.target_id}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </section>
    </div>
  );
};
