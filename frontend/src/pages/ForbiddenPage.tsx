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
        <h1 className="forbidden-title">403 Forbidden</h1>
        <p className="forbidden-description">
          Your current role does not have the necessary security clearance to access this module.
        </p>
        <Link to="/">
          <Button size="lg" variant="secondary">Return to Dashboard</Button>
        </Link>
      </div>
    </div>
  );
};
