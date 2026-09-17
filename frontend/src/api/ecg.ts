import apiClient from "./client";
import type {
  ProcessingResult,
  EcgStudy,
  WaveformData,
  StudyAuditResponse,
} from "../types";

export interface ECGUploadResponse {
  job_id: number;
  status_url: string;
  status: string;
}

export interface ECGStatusResponse {
  id: number;
  status: "PENDING" | "PROCESSING" | "DONE" | "ERROR";
  error_message: string;
  uploaded_at: string;
  result_url: string | null;
}

export interface ECGSignalResponse {
  samples: number[];
  r_peaks: number[];
  fs_display: number;
  unit: string;
}

/* ─── Unified EcgStudy API ──────────────────────────────────────────────── */

export interface UnifiedUploadParams {
  file: File;
  patient_id: string;
  patient_name: string;
  patient_birth?: string;
  patient_sex?: string;
  identity_verified: boolean;
  identity_method: string;
  fs?: number;
  age?: number;
  paced?: boolean;
}

export const uploadAndAnalyseECG = async (
  params: UnifiedUploadParams,
  onUploadProgress?: (progressEvent: any) => void
): Promise<EcgStudy> => {
  const formData = new FormData();
  formData.append("file", params.file);
  formData.append("patient_id", params.patient_id);
  formData.append("patient_name", params.patient_name);
  if (params.patient_birth) formData.append("patient_birth", params.patient_birth);
  if (params.patient_sex) formData.append("patient_sex", params.patient_sex);
  formData.append("identity_verified", params.identity_verified ? "true" : "false");
  formData.append("identity_method", params.identity_method);
  if (params.fs) formData.append("fs", params.fs.toString());
  if (params.age) formData.append("age", params.age.toString());
  if (params.paced !== undefined) formData.append("paced", params.paced ? "true" : "false");

  const response = await apiClient.post<EcgStudy>("/api/ecg/studies/", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
    onUploadProgress,
  });
  return response.data;
};

export const getStudy = async (studyId: number | string): Promise<EcgStudy> => {
  const response = await apiClient.get<EcgStudy>(`/api/ecg/studies/${studyId}/`);
  return response.data;
};

export const getWaveform = async (studyId: number | string, fs?: number): Promise<WaveformData> => {
  const url = fs ? `/api/ecg/studies/${studyId}/waveform/?fs=${fs}` : `/api/ecg/studies/${studyId}/waveform/`;
  const response = await apiClient.get<WaveformData>(url);
  return response.data;
};

export const transmitStudy = async (studyId: number | string): Promise<{ state: string; transmitted_at: string }> => {
  const response = await apiClient.post(`/api/ecg/studies/${studyId}/transmit/`);
  return response.data;
};

export const openStudy = async (studyId: number | string): Promise<EcgStudy> => {
  const response = await apiClient.get<EcgStudy>(`/api/ecg/studies/${studyId}/open/`);
  return response.data;
};

export const signStudy = async (
  studyId: number | string,
  report: string,
  signature: string
): Promise<{ state: string; signed_at: string; turnaround_s: number }> => {
  const response = await apiClient.post(`/api/ecg/studies/${studyId}/sign/`, {
    report,
    signature,
  });
  return response.data;
};

export const deliverStudy = async (
  studyId: number | string,
  simulateFailure: boolean = false
): Promise<{ state: string; payload: any; turnaround_s: number }> => {
  const url = simulateFailure
    ? `/api/ecg/studies/${studyId}/deliver/?simulate_failure=1`
    : `/api/ecg/studies/${studyId}/deliver/`;
  const response = await apiClient.post(url);
  return response.data;
};

export const getStudyAudit = async (studyId: number | string): Promise<StudyAuditResponse> => {
  const response = await apiClient.get<StudyAuditResponse>(`/api/ecg/studies/${studyId}/audit/`);
  return response.data;
};

export const getWorklist = async (): Promise<EcgStudy[]> => {
  const response = await apiClient.get<EcgStudy[]>("/api/ecg/studies/worklist/");
  return response.data;
};

/* ─── Legacy compatibility helpers ───────────────────────────────────────── */

export const uploadECG = async (
  file: File,
  pseudo_id: string,
  _fmt: string,
  onUploadProgress?: (progressEvent: any) => void
): Promise<ECGUploadResponse> => {
  // Direct to unified upload
  const res = await uploadAndAnalyseECG(
    {
      file,
      patient_id: pseudo_id,
      patient_name: `Patient ${pseudo_id.slice(0, 8)}`,
      identity_verified: true,
      identity_method: "Dossier National",
    },
    onUploadProgress
  );
  return {
    job_id: res.study_id,
    status_url: `/api/ecg/studies/${res.study_id}/`,
    status: res.state,
  };
};

export const getECGStatus = async (jobId: number | string): Promise<ECGStatusResponse> => {
  const study = await getStudy(jobId);
  return {
    id: Number(jobId),
    status: study.state === "rejected" ? "ERROR" : study.state === "acquired" ? "PROCESSING" : "DONE",
    error_message: study.state === "rejected" ? "Tracé rejeté au contrôle qualité" : "",
    uploaded_at: study.acquired_at || new Date().toISOString(),
    result_url: `/api/ecg/studies/${jobId}/`,
  };
};

export const getECGResult = async (jobId: number | string): Promise<ProcessingResult> => {
  const study = await getStudy(jobId);
  const analysis = study.analysis || {};
  return {
    id: Number(jobId),
    record_id: Number(jobId),
    intervals_json: analysis.measurements || {},
    flags_json: (analysis.findings || []).map((f: any) => ({
      code: f.component,
      label: f.finding,
      measured_value: f.value || 0,
      unit: "",
      threshold: 0,
      direction: "none",
      severity: f.severity === "RED" ? "CRITICAL" : f.severity === "ORANGE" ? "WARNING" : "INFO",
      citation: f.citation || "",
    })),
    severity: (study.triage_level === "RED" || study.triage_level === "CRITICAL")
      ? "CRITICAL"
      : study.triage_level === "ORANGE"
      ? "URGENT"
      : "ROUTINE",
    lead_used: "II",
    partial: false,
    processed_at: study.analysed_at || "",
  };
};

export const getECGSignal = async (
  jobId: number | string,
  lead: string = "II",
  _downsample: number = 500
): Promise<ECGSignalResponse> => {
  const wave = await getWaveform(jobId);
  const samples = wave.samples[lead] || wave.samples["II"] || Object.values(wave.samples)[0] || [];
  return {
    samples,
    r_peaks: [],
    fs_display: wave.fs,
    unit: "mV",
  };
};
