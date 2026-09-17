import React, { useState, useMemo } from "react";
import type { WaveformData } from "../../types";
import { Eye, EyeOff, ZoomIn, ZoomOut, Layers, Activity } from "lucide-react";
import "./ECGViewer12Lead.css";

interface ECGViewer12LeadProps {
  waveform: WaveformData;
  segmentationLabels?: number[];
  labelLead?: string;
  overlayScaleFactor?: number;
}

const LEADS_12 = ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"];

export const ECGViewer12Lead: React.FC<ECGViewer12LeadProps> = ({
  waveform,
  segmentationLabels = [],
  labelLead = "II",
  overlayScaleFactor = 2.0,
}) => {
  const [viewMode, setViewMode] = useState<"standard_12" | "rhythm_strip" | "precordial" | "limb">("standard_12");
  const [showOverlay, setShowOverlay] = useState(true);
  const [gain, setGain] = useState<number>(10); // 10 mm/mV standard
  const [selectedLead, setSelectedLead] = useState<string>("II");

  // SVG dimensions
  const svgWidth = 1100;
  const standardLeadHeight = 120;
  const rhythmStripHeight = 160;

  // Render a single lead's polyline
  const renderLeadPolyline = (_leadName: string, samples: number[], width: number, height: number) => {
    if (!samples || samples.length === 0) return "";
    const n = samples.length;
    const midY = height / 2;
    // Standard gain: 1 mV = 40 pixels at default scale
    const scaleY = (height / 2.8) * (gain / 10);
    const stepX = width / Math.max(1, n - 1);

    const points: string[] = [];
    for (let i = 0; i < n; i++) {
      const x = (i * stepX).toFixed(1);
      // Invert Y because SVG coordinates go top-to-bottom
      const y = (midY - samples[i] * scaleY).toFixed(1);
      points.push(`${x},${y}`);
    }
    return points.join(" ");
  };

  // Convert segmentation labels to contiguous blocks of <rect>
  const segmentationRects = useMemo(() => {
    if (!segmentationLabels || segmentationLabels.length === 0) return [];
    const rects: Array<{ start: number; end: number; cls: number }> = [];
    let currentCls = segmentationLabels[0];
    let startIdx = 0;

    for (let i = 1; i < segmentationLabels.length; i++) {
      if (segmentationLabels[i] !== currentCls) {
        if (currentCls !== 0) {
          rects.push({ start: startIdx, end: i, cls: currentCls });
        }
        currentCls = segmentationLabels[i];
        startIdx = i;
      }
    }
    if (currentCls !== 0) {
      rects.push({ start: startIdx, end: segmentationLabels.length, cls: currentCls });
    }
    return rects;
  }, [segmentationLabels]);

  // Colors for PQRST classes
  const getPQRSTColor = (cls: number) => {
    switch (cls) {
      case 1:
        return "#7C6FE8"; // Onde P (violet)
      case 2:
        return "#D85A30"; // Complexe QRS (orange corail)
      case 3:
        return "#2E9E8F"; // Onde T (vert canard)
      default:
        return "transparent";
    }
  };

  return (
    <div className="ecg-viewer-container">
      {/* Top Controls Toolbar */}
      <div className="ecg-viewer-toolbar">
        <div className="toolbar-left">
          <span className="toolbar-title">
            <Activity size={18} className="text-primary mr-1" />
            Tracé Électrocardiographique 12 Dérivations (SVG Pur)
          </span>
          <span className="toolbar-meta">
            {waveform.fs} Hz · {waveform.n_samples} éch/dér. · 25 mm/s · {gain} mm/mV
          </span>
        </div>

        <div className="toolbar-controls">
          {/* View Modes */}
          <div className="mode-toggle-group">
            <button
              className={`toggle-btn ${viewMode === "standard_12" ? "active" : ""}`}
              onClick={() => setViewMode("standard_12")}
            >
              12 Dérivations
            </button>
            <button
              className={`toggle-btn ${viewMode === "rhythm_strip" ? "active" : ""}`}
              onClick={() => setViewMode("rhythm_strip")}
            >
              Bande DII
            </button>
            <button
              className={`toggle-btn ${viewMode === "limb" ? "active" : ""}`}
              onClick={() => setViewMode("limb")}
            >
              Périphériques
            </button>
            <button
              className={`toggle-btn ${viewMode === "precordial" ? "active" : ""}`}
              onClick={() => setViewMode("precordial")}
            >
              Précordiales
            </button>
          </div>

          {/* Gain Controls */}
          <div className="gain-controls">
            <span className="gain-label">Gain:</span>
            <button
              className="gain-btn"
              onClick={() => setGain((g) => Math.max(5, g - 2.5))}
              title="Diminuer le gain"
            >
              <ZoomOut size={14} />
            </button>
            <span className="gain-value">{gain} mm/mV</span>
            <button
              className="gain-btn"
              onClick={() => setGain((g) => Math.min(20, g + 2.5))}
              title="Augmenter le gain"
            >
              <ZoomIn size={14} />
            </button>
          </div>

          {/* Overlay Toggle */}
          <button
            className={`overlay-toggle-btn ${showOverlay ? "active" : ""}`}
            onClick={() => setShowOverlay(!showOverlay)}
            title="Afficher/masquer la segmentation PQRST"
          >
            <Layers size={14} className="mr-1" />
            {showOverlay ? <Eye size={14} /> : <EyeOff size={14} />}
            <span className="ml-1">Overlay PQRST</span>
          </button>
        </div>
      </div>

      {/* PQRST Color Legend */}
      {showOverlay && segmentationLabels.length > 0 && (
        <div className="pqrst-legend-bar">
          <span className="legend-title">Segmentation automatique ondelettes (Dérivation {labelLead}) :</span>
          <div className="legend-item">
            <span className="legend-box p-wave-box" />
            <span className="legend-text">Onde P (7C6FE8)</span>
          </div>
          <div className="legend-item">
            <span className="legend-box qrs-box" />
            <span className="legend-text">Complexe QRS (D85A30)</span>
          </div>
          <div className="legend-item">
            <span className="legend-box t-wave-box" />
            <span className="legend-text">Onde T (2E9E8F)</span>
          </div>
        </div>
      )}

      {/* SVG Canvas Area */}
      <div className="ecg-canvas-scroll">
        {viewMode === "standard_12" && (
          <div className="ecg-grid-standard">
            {/* 3 rows x 4 columns of standard leads */}
            <div className="standard-leads-grid">
              {[
                ["I", "aVR", "V1", "V4"],
                ["II", "aVL", "V2", "V5"],
                ["III", "aVF", "V3", "V6"],
              ].map((row, rowIdx) => (
                <div key={`row-${rowIdx}`} className="ecg-grid-row">
                  {row.map((leadName) => {
                    const samples = waveform.samples[leadName] || [];
                    const isLabelLead = leadName === labelLead;
                    return (
                      <div key={leadName} className="ecg-lead-cell">
                        <div className="lead-header">
                          <span className="lead-name">{leadName}</span>
                          {isLabelLead && showOverlay && (
                            <span className="lead-segmented-badge">Délignage PQRST</span>
                          )}
                        </div>
                        <svg
                          viewBox={`0 0 280 ${standardLeadHeight}`}
                          className="ecg-lead-svg"
                          preserveAspectRatio="none"
                        >
                          {/* Diagnostic Grid Background */}
                          <defs>
                            <pattern id="smallGrid" width="6" height="6" patternUnits="userSpaceOnUse">
                              <path d="M 6 0 L 0 0 0 6" fill="none" stroke="rgba(220, 80, 80, 0.15)" strokeWidth="0.5" />
                            </pattern>
                            <pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse">
                              <rect width="30" height="30" fill="url(#smallGrid)" />
                              <path d="M 30 0 L 0 0 0 30" fill="none" stroke="rgba(220, 60, 60, 0.35)" strokeWidth="1" />
                            </pattern>
                          </defs>
                          <rect width="280" height={standardLeadHeight} fill="url(#grid)" />

                          {/* Calibration pulse at origin */}
                          <polyline
                            points={`2,${standardLeadHeight / 2} 8,${standardLeadHeight / 2} 8,${
                              standardLeadHeight / 2 - 30 * (gain / 10)
                            } 18,${standardLeadHeight / 2 - 30 * (gain / 10)} 18,${standardLeadHeight / 2} 24,${
                              standardLeadHeight / 2
                            }`}
                            fill="none"
                            stroke="#555"
                            strokeWidth="1.2"
                          />

                          {/* Segmentation Overlay on Label Lead */}
                          {isLabelLead &&
                            showOverlay &&
                            segmentationRects.map((r, rIdx) => {
                              const totalSamples = samples.length || 1;
                              const sampleToSvg = 280 / totalSamples;
                              // Rescale segmentation indices from 500 Hz space to display space
                              const startSample = r.start / overlayScaleFactor;
                              const endSample = r.end / overlayScaleFactor;
                              const x = startSample * sampleToSvg;
                              const w = Math.max(1, (endSample - startSample) * sampleToSvg);

                              return (
                                <rect
                                  key={`seg-${rIdx}`}
                                  x={x}
                                  y={4}
                                  width={w}
                                  height={standardLeadHeight - 8}
                                  fill={getPQRSTColor(r.cls)}
                                  opacity="0.25"
                                  rx="2"
                                />
                              );
                            })}

                          {/* Signal Polyline (Single DOM node!) */}
                          <polyline
                            points={renderLeadPolyline(leadName, samples, 280, standardLeadHeight)}
                            fill="none"
                            stroke="#0f172a"
                            strokeWidth="1.3"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        </svg>
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>

            {/* Rhythm strip (Lead II) full width at the bottom */}
            <div className="ecg-rhythm-strip-card">
              <div className="lead-header">
                <span className="lead-name">Bande de Rythme Continue — Dérivation II (10 secondes)</span>
                {showOverlay && <span className="lead-segmented-badge">Délignage PQRST actif</span>}
              </div>
              <svg
                viewBox={`0 0 ${svgWidth} ${rhythmStripHeight}`}
                className="ecg-rhythm-svg"
                preserveAspectRatio="none"
              >
                <rect width={svgWidth} height={rhythmStripHeight} fill="url(#grid)" />

                {/* Segmentation Overlay on full rhythm strip */}
                {showOverlay &&
                  segmentationRects.map((r, rIdx) => {
                    const totalSamples = (waveform.samples["II"] || []).length || 1;
                    const sampleToSvg = svgWidth / totalSamples;
                    const startSample = r.start / overlayScaleFactor;
                    const endSample = r.end / overlayScaleFactor;
                    const x = startSample * sampleToSvg;
                    const w = Math.max(1, (endSample - startSample) * sampleToSvg);

                    return (
                      <g key={`rhythm-seg-${rIdx}`}>
                        <rect
                          x={x}
                          y={8}
                          width={w}
                          height={rhythmStripHeight - 16}
                          fill={getPQRSTColor(r.cls)}
                          opacity="0.22"
                          rx="3"
                        />
                      </g>
                    );
                  })}

                {/* Lead II signal full strip */}
                <polyline
                  points={renderLeadPolyline("II", waveform.samples["II"] || [], svgWidth, rhythmStripHeight)}
                  fill="none"
                  stroke="#0284c7"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
          </div>
        )}

        {viewMode === "rhythm_strip" && (
          <div className="ecg-full-strip-view">
            <div className="ecg-rhythm-strip-card large">
              <div className="lead-header">
                <span className="lead-name">Tracé Longitudinal Pleine Échelle — Dérivation {selectedLead}</span>
                <select
                  className="lead-select"
                  value={selectedLead}
                  onChange={(e) => setSelectedLead(e.target.value)}
                >
                  {LEADS_12.map((l) => (
                    <option key={l} value={l}>
                      Dérivation {l}
                    </option>
                  ))}
                </select>
              </div>
              <svg viewBox={`0 0 ${svgWidth} 320`} className="ecg-rhythm-svg-large" preserveAspectRatio="none">
                <rect width={svgWidth} height="320" fill="url(#grid)" />
                {selectedLead === labelLead &&
                  showOverlay &&
                  segmentationRects.map((r, rIdx) => {
                    const totalSamples = (waveform.samples[selectedLead] || []).length || 1;
                    const sampleToSvg = svgWidth / totalSamples;
                    const startSample = r.start / overlayScaleFactor;
                    const endSample = r.end / overlayScaleFactor;
                    const x = startSample * sampleToSvg;
                    const w = Math.max(1, (endSample - startSample) * sampleToSvg);

                    return (
                      <rect
                        key={`large-seg-${rIdx}`}
                        x={x}
                        y={10}
                        width={w}
                        height={300}
                        fill={getPQRSTColor(r.cls)}
                        opacity="0.24"
                        rx="3"
                      />
                    );
                  })}
                <polyline
                  points={renderLeadPolyline(selectedLead, waveform.samples[selectedLead] || [], svgWidth, 320)}
                  fill="none"
                  stroke="#09090b"
                  strokeWidth="1.6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
          </div>
        )}

        {(viewMode === "limb" || viewMode === "precordial") && (
          <div className="ecg-subgroup-view">
            {(viewMode === "limb"
              ? ["I", "II", "III", "aVR", "aVL", "aVF"]
              : ["V1", "V2", "V3", "V4", "V5", "V6"]
            ).map((leadName) => {
              const samples = waveform.samples[leadName] || [];
              const isLabelLead = leadName === labelLead;
              return (
                <div key={leadName} className="ecg-lead-cell expanded">
                  <div className="lead-header">
                    <span className="lead-name">Dérivation {leadName}</span>
                    {isLabelLead && showOverlay && (
                      <span className="lead-segmented-badge">Délignage PQRST</span>
                    )}
                  </div>
                  <svg viewBox={`0 0 ${svgWidth} 140`} className="ecg-lead-svg" preserveAspectRatio="none">
                    <rect width={svgWidth} height="140" fill="url(#grid)" />
                    {isLabelLead &&
                      showOverlay &&
                      segmentationRects.map((r, rIdx) => {
                        const totalSamples = samples.length || 1;
                        const sampleToSvg = svgWidth / totalSamples;
                        const startSample = r.start / overlayScaleFactor;
                        const endSample = r.end / overlayScaleFactor;
                        const x = startSample * sampleToSvg;
                        const w = Math.max(1, (endSample - startSample) * sampleToSvg);

                        return (
                          <rect
                            key={`sub-seg-${rIdx}`}
                            x={x}
                            y={6}
                            width={w}
                            height={128}
                            fill={getPQRSTColor(r.cls)}
                            opacity="0.22"
                            rx="2"
                          />
                        );
                      })}
                    <polyline
                      points={renderLeadPolyline(leadName, samples, svgWidth, 140)}
                      fill="none"
                      stroke="#0f172a"
                      strokeWidth="1.4"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Footer calibration specs */}
      <div className="ecg-viewer-footer">
        <span>Standard Électrocardiographique International : Étalonnage 10 mm = 1 mV · Vitesse de défilement 25 mm/s</span>
        <span>Moteur d'ondelettes NeuroKit2 & MNE · Tracé brut sans filtre destructif</span>
      </div>
    </div>
  );
};
