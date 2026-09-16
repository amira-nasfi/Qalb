import React from "react";
import { Link } from "react-router-dom";
import { HeartPulse, Activity, ShieldCheck, UserCheck } from "lucide-react";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import "./LandingPage.css";

export const LandingPage: React.FC = () => {
  return (
    <div className="landing-page">
      <div className="hero-section">
        <div className="hero-content">
          <div className="brand-header">
            <HeartPulse size={48} className="text-mint" />
            <h1 className="hero-title">
              Qalb <span lang="ar" className="text-ar">قلب</span>
            </h1>
          </div>
          <h2 className="hero-subtitle">
            Clinical ECG Interpretation & Triage System
          </h2>
          <p className="hero-description">
            A mission-critical operational platform designed for SAMU and emergency medical services.
            Deterministic signal processing with fully traceable clinical rules.
          </p>
          <div className="hero-actions">
            <Link to="/upload">
              <Button size="lg" className="w-full">Initiate Field Upload</Button>
            </Link>
            <Link to="/dashboard">
              <Button variant="secondary" size="lg" className="w-full">Access Clinical Queue</Button>
            </Link>
          </div>
        </div>
      </div>

      <div className="system-features">
        <div className="features-grid">
          <Card className="feature-card">
            <Activity size={24} className="feature-icon text-mint" />
            <h3 className="feature-title">Deterministic Processing</h3>
            <p className="feature-desc">Explainable NeuroKit2 pipeline without opaque ML scoring.</p>
          </Card>
          <Card className="feature-card">
            <ShieldCheck size={24} className="feature-icon text-mint" />
            <h3 className="feature-title">AHA/ESC Compliant</h3>
            <p className="feature-desc">8 clinical rules fully traceable to published guidelines.</p>
          </Card>
          <Card className="feature-card">
            <UserCheck size={24} className="feature-icon text-mint" />
            <h3 className="feature-title">Physician Validation</h3>
            <p className="feature-desc">Mandatory human-in-the-loop review and digital sign-off.</p>
          </Card>
        </div>
      </div>
    </div>
  );
};
