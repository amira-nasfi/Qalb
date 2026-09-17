import React from "react";
import { Link } from "react-router-dom";
import { ShieldAlert } from "lucide-react";
import { Button } from "../components/ui/Button";
import "./ForbiddenPage.css";

export const ForbiddenPage: React.FC = () => {
  return (
    <div className="forbidden-page">
      <div className="forbidden-content">
        <ShieldAlert size={64} className="text-critical mb-6 mx-auto" />
        <h1 className="forbidden-title">403 Accès Refusé</h1>
        <p className="forbidden-description">
          Votre rôle actuel ne dispose pas des autorisations requises pour accéder à ce module médical.
        </p>
        <Link to="/">
          <Button size="lg" variant="secondary">Retour à l'accueil</Button>
        </Link>
      </div>
    </div>
  );
};
