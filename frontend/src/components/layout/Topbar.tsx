import React, { useState, useEffect } from "react";
import apiClient from "../../api/client";
import { Activity } from "lucide-react";
import "./Topbar.css";

interface KPIs {
  uploads_today: number;
  pending_reviews: number;
  signed_today: number;
  critical_active: number;
  avg_processing_ms: number;
}

export const Topbar: React.FC = () => {
  const [kpis, setKpis] = useState<KPIs | null>(null);

  useEffect(() => {
    const fetchKPIs = async () => {
      try {
        const response = await apiClient.get<KPIs>("/api/admin/kpis/");
        setKpis(response.data);
      } catch (err) {
        console.error("Failed to fetch KPIs");
      }
    };

    fetchKPIs();
    const interval = setInterval(fetchKPIs, 30000); // 30s refresh
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="topbar">
      <div className="topbar-left">
        {/* Placeholder for page specific title/breadcrumbs if needed */}
      </div>
      
      <div className="topbar-right">
        {!kpis ? (
          <div className="kpi-skeleton text-sm text-secondary">Connexion aux métriques opérationnelles...</div>
        ) : (
          <div className="kpi-group">
            <div className="kpi-metric">
              <span className="kpi-label">Uploads (24h)</span>
              <span className="kpi-value text-mono tnum">{kpis.uploads_today}</span>
            </div>
            <div className="kpi-metric">
              <span className="kpi-label">En attente</span>
              <span className="kpi-value text-mono tnum">{kpis.pending_reviews}</span>
            </div>
            <div className={`kpi-metric ${kpis.critical_active > 0 ? "kpi-alert" : ""}`}>
              <Activity size={14} className="mr-1" />
              <span className="kpi-label">Critiques</span>
              <span className="kpi-value text-mono tnum">{kpis.critical_active}</span>
            </div>
            <div className="kpi-metric">
              <span className="kpi-label">Temps moyen</span>
              <span className="kpi-value text-mono tnum">{kpis.avg_processing_ms}ms</span>
            </div>
          </div>
        )}
      </div>
    </header>
  );
};
