import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getReports } from "../api/reports";
import type { Report } from "../types";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Skeleton } from "../components/ui/Skeleton";
import { ChevronRight } from "lucide-react";
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

  const pending = reports.filter((r) => r.status === "PENDING_REVIEW");
  const signed = reports.filter((r) => r.status === "SIGNED");

  const renderTable = (list: Report[], isPending: boolean) => {
    if (list.length === 0) return <div className="clinical-empty-state">No records in this queue.</div>;

    return (
      <div className="table-responsive">
        <table className="clinical-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Pseudo ID</th>
              <th>Timestamp</th>
              <th>Triaged Severity</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {list.map((r) => (
              <tr key={r.id}>
                <td className="text-mono tnum text-secondary">#{r.id}</td>
                <td className="text-mono font-medium">{r.pseudo_id.split("-")[0]}...</td>
                <td className="text-sm">{new Date(r.created_at).toLocaleString()}</td>
                <td>
                  <Badge severity={r.severity}>{r.severity}</Badge>
                </td>
                <td>
                  {r.status === "SIGNED" ? (
                    <Badge severity="SUCCESS">Signed</Badge>
                  ) : (
                    <Badge severity="WARNING">Pending Review</Badge>
                  )}
                </td>
                <td className="action-cell">
                  <Link to={`/review/${r.id}`} className="clinical-link">
                    {isPending ? 'Review' : 'View'} <ChevronRight size={16} />
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <div className="dashboard-page">
      <div className="dashboard-header">
        <h1 className="page-title">Review Queue</h1>
        <p className="page-subtitle">Awaiting clinical validation and digital sign-off</p>
      </div>

      <div className="dashboard-content">
        <Card className="dashboard-card">
          <div className="card-header flex justify-between">
            <h2 className="card-title">Pending Clinical Validation</h2>
            <Badge severity="WARNING" showDot={false}>{pending.length} Action Required</Badge>
          </div>
          {loading ? <div className="p-6"><Skeleton height="200px" /></div> : renderTable(pending, true)}
        </Card>

        <Card className="dashboard-card mt-8">
          <div className="card-header">
            <h2 className="card-title">Completed & Signed</h2>
          </div>
          {loading ? <div className="p-6"><Skeleton height="200px" /></div> : renderTable(signed, false)}
        </Card>
      </div>
    </div>
  );
};
