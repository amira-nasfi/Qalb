import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getReport, updateReportNotes, signReport } from "../api/reports";
import { downloadFHIRExport } from "../api/fhir";
import { getECGSignal } from "../api/ecg";
import type { Report } from "../types";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Toast } from "../components/ui/Toast";
import { Activity, Download, CheckCircle, Edit3, ShieldAlert } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import "./ReviewPage.css";

export const ReviewPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [report, setReport] = useState<Report | null>(null);
  const [signal, setSignal] = useState<any[]>([]);
  const [notes, setNotes] = useState("");
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);
  const [isSigning, setIsSigning] = useState(false);

  useEffect(() => {
    if (!id) return;
    const fetchData = async () => {
      try {
        const r = await getReport(id);
        setReport(r);
        setNotes(r.physician_notes || "");

        const sigData = await getECGSignal(r.job_id);
        const chartData = sigData.samples.map((val: number, idx: number) => ({
          time: idx,
          mv: val,
        }));
        setSignal(chartData);
      } catch (err) {
        console.error(err);
      }
    };
    fetchData();
  }, [id]);

  const handleSaveNotes = async () => {
    if (!report) return;
    try {
      await updateReportNotes(report.id, notes);
      setToast({ message: "Draft saved.", type: "success" });
    } catch (err) {
      setToast({ message: "Failed to save draft.", type: "error" });
    }
  };

  const handleSign = async () => {
    if (!report) return;
    if (!notes.trim()) {
      setToast({ message: "Clinical notes are required before signing.", type: "error" });
      return;
    }
    setIsSigning(true);
    try {
      await updateReportNotes(report.id, notes);
      const updated = await signReport(report.id);
      setReport(updated);
      setToast({ message: "Report electronically signed and locked.", type: "success" });
    } catch (err) {
      setToast({ message: "Failed to sign report.", type: "error" });
    } finally {
      setIsSigning(false);
    }
  };

  const handleExportFHIR = async () => {
    if (!report) return;
    try {
      await downloadFHIRExport(report.id);
      setToast({ message: "FHIR bundle exported.", type: "success" });
    } catch (err) {
      setToast({ message: "Export failed.", type: "error" });
    }
  };

  if (!report) return <div className="clinical-empty-state">Retrieving clinical record...</div>;

  const isSigned = report.status === "SIGNED";
  const isCritical = report.severity === "CRITICAL";

  return (
    <div className="review-page">
      <div className={`review-header ${isCritical && !isSigned ? 'header-critical' : ''}`}>
        <div className="header-info">
          <h1 className="page-title">
            Case #{report.id}
          </h1>
          <div className="patient-id">
            <span className="text-tertiary">ID:</span> <span className="text-mono">{report.pseudo_id}</span>
          </div>
        </div>
        <div className="header-actions">
          <Badge severity={report.severity} className="mr-4">
            {report.severity}
          </Badge>
          {isSigned ? (
            <Badge severity="SUCCESS">Signed</Badge>
          ) : (
            <Badge severity="WARNING">Pending Validation</Badge>
          )}
        </div>
      </div>

      {isCritical && !isSigned && (
        <div className="critical-banner">
          <ShieldAlert size={20} />
          <span>Immediate clinical intervention required based on deterministic triage.</span>
        </div>
      )}

      <div className="review-grid">
        <div className="review-main">
          <Card className="mb-6 chart-card">
            <div className="card-header">
              <h2><Activity size={18} className="inline mr-2 text-teal" /> ECG Monitor (Lead II)</h2>
            </div>
            <div className="chart-container">
              {signal.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={signal}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" vertical={false} />
                    <XAxis dataKey="time" hide />
                    <YAxis domain={['auto', 'auto']} hide />
                    <Tooltip 
                      labelFormatter={() => ''} 
                      formatter={(val: any) => [`${Number(val).toFixed(2)} mV`, 'Amplitude']}
                      contentStyle={{ backgroundColor: 'var(--navy-dark)', color: 'white', border: 'none', borderRadius: '4px' }}
                    />
                    <Line type="monotone" dataKey="mv" stroke={isCritical && !isSigned ? "var(--status-critical)" : "var(--mint-dark)"} dot={false} strokeWidth={1.5} isAnimationActive={false} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-full text-tertiary">Loading signal data...</div>
              )}
            </div>
          </Card>

          <Card className="mb-6">
            <div className="card-header">
              <h2>Automated Clinical Summary</h2>
            </div>
            <div className="draft-text">
              {report.draft_text.split('\n').map((line, i) => (
                <p key={i}>{line}</p>
              ))}
            </div>
          </Card>
        </div>

        <div className="review-sidebar">
          <Card className="mb-6">
            <div className="card-header">
              <h2><Edit3 size={18} className="inline mr-2 text-teal" /> Physician Notes</h2>
            </div>
            <div className="card-body p-0">
              <textarea
                className="notes-textarea"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Enter clinical impression and final conclusion..."
                disabled={isSigned}
                rows={10}
              />
              {!isSigned && (
                <div className="notes-actions">
                  <Button variant="ghost" size="sm" onClick={handleSaveNotes}>Save Draft</Button>
                </div>
              )}
            </div>
          </Card>

          <Card className="actions-card">
            <div className="card-body">
              {!isSigned ? (
                <Button size="lg" variant={isCritical ? "danger" : "primary"} className="w-full mb-4" onClick={handleSign} isLoading={isSigning}>
                  Sign & Lock Record
                </Button>
              ) : (
                <div className="signed-info mb-4">
                  <CheckCircle size={24} className="text-success mb-2 mx-auto" />
                  <p className="text-sm font-medium">Digitally Signed</p>
                  <p className="text-xs text-tertiary mt-1">
                    {report.signed_by_user?.first_name} {report.signed_by_user?.last_name}
                  </p>
                  <p className="text-xs text-mono text-tertiary mt-1">
                    {new Date(report.signed_at!).toLocaleString()}
                  </p>
                </div>
              )}
              
              <Button
                variant="secondary"
                className="w-full"
                onClick={handleExportFHIR}
                disabled={!isSigned}
              >
                <Download size={16} className="inline mr-2" /> Export HL7 FHIR
              </Button>
            </div>
          </Card>
        </div>
      </div>

      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
    </div>
  );
};
