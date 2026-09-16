import React, { useEffect, useState } from "react";
import { getAuditLogs } from "../api/admin";
import type { AuditLogEntry } from "../api/admin";
import { Card } from "../components/ui/Card";
import { Skeleton } from "../components/ui/Skeleton";
import { Shield, Fingerprint, Clock, User, Activity } from "lucide-react";
import "./AdminDashboard.css";

export const AdminDashboard: React.FC = () => {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const data = await getAuditLogs();
        setLogs(data);
      } catch (err) {
        console.error("Failed to fetch audit logs", err);
      } finally {
        setLoading(false);
      }
    };
    fetchLogs();
  }, []);

  return (
    <div className="admin-page">
      <div className="admin-header">
        <h1 className="page-title"><Shield className="inline mr-2 text-mint" /> System Audit Trail</h1>
        <p className="page-subtitle">Immutable chronological log of all platform operations</p>
      </div>

      <Card className="audit-card">
        <div className="card-header">
          <h2 className="card-title">Event Log</h2>
        </div>
        
        {loading ? (
          <div className="p-6"><Skeleton height="300px" /></div>
        ) : logs.length === 0 ? (
          <div className="clinical-empty-state">No audit logs recorded.</div>
        ) : (
          <div className="table-responsive">
            <table className="clinical-table audit-table">
              <thead>
                <tr>
                  <th><Clock size={14} className="inline mr-1" /> Timestamp</th>
                  <th>Action</th>
                  <th><User size={14} className="inline mr-1" /> Actor</th>
                  <th><Activity size={14} className="inline mr-1" /> Target</th>
                  <th><Fingerprint size={14} className="inline mr-1" /> Origin Hash</th>
                  <th>Payload Trace</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id}>
                    <td className="text-sm font-mono text-tertiary">{new Date(log.timestamp).toLocaleString()}</td>
                    <td>
                      <span className="action-badge">{log.action}</span>
                    </td>
                    <td className="text-sm font-medium">{log.actor}</td>
                    <td className="text-sm text-mono">
                      {log.target_type} <span className="text-tertiary">#{log.target_id}</span>
                    </td>
                    <td>
                      <span className="text-xs text-mono text-tertiary" title={log.ip_address_hash}>
                        {log.ip_address_hash.substring(0, 12)}...
                      </span>
                    </td>
                    <td>
                       <div className="payload-box">
                         {JSON.stringify(log.extra)}
                       </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
};
