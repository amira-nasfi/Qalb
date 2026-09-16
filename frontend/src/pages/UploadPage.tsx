import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Toast } from "../components/ui/Toast";
import { uploadECG } from "../api/ecg";
import "./UploadPage.css";
import { UploadCloud, File, X, ShieldAlert } from "lucide-react";

export const UploadPage: React.FC = () => {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [pseudoId, setPseudoId] = useState("");
  const [fmt, setFmt] = useState("wfdb");
  const [isUploading, setIsUploading] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !pseudoId) return;

    setIsUploading(true);
    try {
      const res = await uploadECG(file, pseudoId, fmt);
      setToast({ message: "Upload verified. Commencing signal processing.", type: "success" });
      setTimeout(() => {
        navigate(`/result/${res.job_id}`);
      }, 1500);
    } catch (err: any) {
      setToast({ message: err.response?.data?.error || "Upload rejected.", type: "error" });
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="upload-page">
      <div className="upload-header">
        <h1 className="page-title">Initiate ECG Upload</h1>
        <p className="page-subtitle">Field team acquisition & secure data transfer</p>
      </div>

      <div className="upload-container">
        <Card>
          <div className="clinical-notice">
            <ShieldAlert size={16} className="text-mint" />
            <span>Ensure all patient PII has been removed prior to upload. Only use the assigned Pseudo ID.</span>
          </div>
          
          <form onSubmit={handleSubmit} className="upload-form">
            <div className="form-row">
              <div className="form-group flex-1">
                <label htmlFor="pseudoId">Patient Pseudo ID</label>
                <input
                  id="pseudoId"
                  type="text"
                  value={pseudoId}
                  onChange={(e) => setPseudoId(e.target.value)}
                  placeholder="e.g. 550e8400-e29b..."
                  required
                  className="form-input text-mono"
                />
              </div>

              <div className="form-group flex-1">
                <label htmlFor="fmt">Signal Format</label>
                <select
                  id="fmt"
                  value={fmt}
                  onChange={(e) => setFmt(e.target.value)}
                  className="form-select"
                >
                  <option value="wfdb">WFDB (.mat / .dat)</option>
                  <option value="csv">CSV (time, leads...)</option>
                  <option value="edf">EDF/EDF+</option>
                </select>
              </div>
            </div>

            <div className="form-group">
              <label>ECG Acquisition File</label>
              {!file ? (
                <div
                  className="clinical-dropzone"
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={handleDrop}
                  onClick={() => document.getElementById("file-upload")?.click()}
                >
                  <UploadCloud size={32} className="dropzone-icon" />
                  <p className="dropzone-text">Click to browse or drag file here</p>
                  <input
                    id="file-upload"
                    type="file"
                    className="hidden-input"
                    onChange={(e) => e.target.files && setFile(e.target.files[0])}
                  />
                </div>
              ) : (
                <div className="file-selected-box">
                  <File size={20} className="file-icon" />
                  <div className="file-info">
                    <span className="file-name text-mono">{file.name}</span>
                    <span className="file-size text-mono">{(file.size / 1024).toFixed(1)} KB</span>
                  </div>
                  <button type="button" className="btn-remove-file" onClick={() => setFile(null)}>
                    <X size={16} />
                  </button>
                </div>
              )}
            </div>

            <div className="form-actions">
              <Button variant="secondary" type="button" onClick={() => { setFile(null); setPseudoId(''); }}>
                Reset
              </Button>
              <Button type="submit" disabled={!file || !pseudoId} isLoading={isUploading}>
                Upload & Process Signal
              </Button>
            </div>
          </form>
        </Card>
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
