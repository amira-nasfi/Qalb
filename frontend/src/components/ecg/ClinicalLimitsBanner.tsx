import React from "react";
import { AlertCircle, ShieldAlert, CheckSquare } from "lucide-react";
import "./ClinicalLimitsBanner.css";

interface ClinicalLimitsBannerProps {
  limits?: string[];
  version?: string;
}

const DEFAULT_LIMITS = [
  "Absence de critères de voltage : élévation/dépression du segment ST, HVG (Sokolow-Lyon, Cornell), microvoltage et axe QRS non évalués.",
  "Absence de détection de spicules de stimulateur cardiaque (pacemaker).",
  "Applicabilité clinique restreinte aux adultes (âge ≥ 18 ans). Valeurs pédiatriques non étalonnées.",
  "Délignage morphologique par ondelettes continues (DWT) déterministe, sans réseau de neurones convolutif ou boîte noire.",
  "Document d'aide à la décision clinique : l'algorithme signale des anomalies mesurables, seul un médecin interprète, signe et engage la décision médicale.",
];

export const ClinicalLimitsBanner: React.FC<ClinicalLimitsBannerProps> = ({
  limits,
  version = "1.0-clinical-wavelet",
}) => {
  const displayLimits = limits && limits.length > 0 ? limits : DEFAULT_LIMITS;

  return (
    <div className="clinical-limits-card" id="clinical-limits-banner">
      <div className="clinical-limits-header">
        <div className="limits-header-left">
          <ShieldAlert className="text-warning-amber" size={22} />
          <div>
            <h4 className="limits-title">Limites Cliniques et Périmètre Règlementaire du Compte Rendu</h4>
            <p className="limits-subtitle">
              Normes d'interprétation automatisée selon les recommandations internationales AHA/ACC/HRS
            </p>
          </div>
        </div>
        <div className="limits-badge-version">
          <span>Moteur v{version}</span>
        </div>
      </div>

      <div className="clinical-limits-body">
        <ul className="limits-list">
          {displayLimits.map((limit, idx) => (
            <li key={idx} className="limits-item">
              <CheckSquare size={16} className="limit-icon" />
              <span className="limit-text">{limit}</span>
            </li>
          ))}
        </ul>

        <div className="clinical-legal-disclaimer">
          <AlertCircle size={16} className="disclaimer-icon" />
          <span className="disclaimer-text">
            <strong>AVERTISSEMENT MÉDICAL LÉGAL :</strong> Ce document d'aide au diagnostic ne constitue pas une
            ordonnance ou un diagnostic définitif. L'algorithme automatisé ne remplace en aucun cas l'expertise clinique.
            La validation finale, la signature électronique et l'engagement thérapeutique incombent exclusivement au
            médecin spécialiste habilité.
          </span>
        </div>
      </div>
    </div>
  );
};
