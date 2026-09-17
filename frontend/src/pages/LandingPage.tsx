import React from "react";
import { Link } from "react-router-dom";
import { Activity, ShieldCheck, UserCheck } from "lucide-react";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import "./LandingPage.css";

export const LandingPage: React.FC = () => {
  return (
    <div className="landing-page">
      <div className="hero-section">
        <div className="hero-content">
          <img src="/logo.png" alt="Logo Qalb" className="landing-logo" />
          <h2 className="hero-subtitle">
            Système Clinique de Dépistage & Triage ECG
          </h2>
          <p className="hero-description">
            Plateforme médicale opérationnelle pour les centres de soins de première ligne et services d'urgence.
            Traitement déterministe du signal avec règles cliniques rigoureusement traçables.
          </p>
          <div className="hero-actions">
            <Link to="/upload">
              <Button size="lg" className="w-full">Nouvelle acquisition ECG</Button>
            </Link>
            <Link to="/dashboard">
              <Button variant="secondary" size="lg" className="w-full">Accéder à la file clinique</Button>
            </Link>
          </div>
        </div>
      </div>

      <div className="system-features">
        <div className="features-grid">
          <Card className="feature-card">
            <Activity size={24} className="feature-icon text-mint" />
            <h3 className="feature-title">Traitement Déterministe</h3>
            <p className="feature-desc">Pipeline NeuroKit2 transparent et explicable, sans modèle opaque boîte noire.</p>
          </Card>
          <Card className="feature-card">
            <ShieldCheck size={24} className="feature-icon text-mint" />
            <h3 className="feature-title">Conformité AHA / ESC</h3>
            <p className="feature-desc">8 règles cliniques déterministes appuyées sur la littérature internationale.</p>
          </Card>
          <Card className="feature-card">
            <UserCheck size={24} className="feature-icon text-mint" />
            <h3 className="feature-title">Validation Médicale</h3>
            <p className="feature-desc">Revue obligatoire par le médecin avec signature électronique irréversible.</p>
          </Card>
        </div>
      </div>
    </div>
  );
};
