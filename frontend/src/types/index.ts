export interface Patient {
  pseudo_id: string;
  patient_identifier?: string;
  first_name?: string;
  last_name?: string;
  full_name?: string;
  birth_date?: string;
  dob_year?: number;
  age?: number;
  sex?: "M" | "F" | "O";
  gender?: "male" | "female" | "other" | "unknown";
  facility_id?: string;
  created_at?: string;
}

export interface Measurement {
  median: number;
  iqr: number;
  unit: string;
  formula_ref: string;
  n_valid: number;
}

export interface Intervals {
  hr_bpm?: Measurement;
  pr_ms?: Measurement;
  qrs_ms?: Measurement;
  qt_ms?: Measurement;
  qtc_bazett?: Measurement;
  qtc_fridericia?: Measurement;
  n_beats: number;
  partial: boolean;
  lead_used: string;
  delineation_rate: number;
}

export interface Flag {
  code: string;
  label: string;
  measured_value: number;
  unit: string;
  threshold: number;
  direction: "above" | "below" | "none";
  severity: "INFO" | "WARNING" | "CRITICAL";
  citation: string;
}

export interface ProcessingResult {
  id: number;
  record_id: number;
  intervals_json: Intervals;
  flags_json: Flag[];
  severity: "ROUTINE" | "URGENT" | "CRITICAL";
  lead_used: string;
  partial: boolean;
  processed_at: string;
}

export interface QualityReport {
  acceptable: boolean;
  failed_leads: string[];
  missing_leads: string[];
  per_lead?: Record<string, string[]>;
}

export interface TriageReport {
  level: "RED" | "ORANGE" | "GREEN" | "REJET" | string;
  priority: number;
  escalate: boolean;
  reasons?: string[];
}

export interface Finding {
  component: string;
  finding: string;
  severity: "RED" | "ORANGE" | "GREEN" | string;
  citation?: string;
  value?: number;
  measured?: string;
  threshold?: string;
  meaning?: string;
  code?: string;
  diagnosis?: {
    label: string | null;
    icd10: string | null;
  } | null;
}

export interface MeasurementItem {
  label: string;
  value: number | null;
  unit: string;
  ref: string;
  na?: boolean;
}

export interface ReportBlocks {
  ok: boolean;
  header?: {
    patient: any;
    acquisition: any;
    analysed_at: string;
    total_ms: number;
  };
  quality?: QualityReport;
  measurements?: MeasurementItem[];
  findings?: Finding[];
  triage?: TriageReport;
  timings?: Array<{ step: string; duration_ms: number }>;
  limits?: string[];
  segmentation?: {
    labels?: number[];
    boundaries?: any;
    label_lead?: string;
  };
  error?: any;
}

export interface EcgStudy {
  study_id: number;
  id?: number;
  patient_id: string;
  patient_name: string;
  patient_birth?: string;
  patient_sex?: string;
  identity_verified: boolean;
  identity_method: string;
  file_format?: string;
  paced?: boolean;
  state: "acquired" | "analysed" | "rejected" | "transmitted" | "reviewing" | "signed" | "delivered" | string;
  triage?: string | TriageReport;
  triage_level?: string;
  triage_priority?: number;
  priority?: number;
  escalated?: boolean;
  analysis?: any;
  report_text?: string;
  physician_report?: string;
  signature?: string;
  turnaround_s?: number | null;
  loop_timings?: Array<{ leg: string; seconds: number }>;
  acquired_at?: string;
  analysed_at?: string;
  transmitted_at?: string;
  opened_at?: string;
  signed_at?: string;
  delivered_at?: string;
  waiting_s?: number;
  blocks?: ReportBlocks;
}

export interface AuditEventItem {
  at: string;
  actor: string | null;
  action: string;
  from: string;
  to: string;
  detail: any;
}

export interface StudyAuditResponse {
  study_id: number;
  patient_id: string;
  patient_name: string;
  state: string;
  identity_verified: boolean;
  triage: { level: string; priority: number; escalated: boolean };
  turnaround_s: number | null;
  loop_timings: Array<{ leg: string; seconds: number }>;
  analysis_timings: { steps: Array<{ step: string; duration_ms: number }>; total_ms: number };
  events: AuditEventItem[];
}

export interface WaveformData {
  study_id: number;
  fs: number;
  leads: string[];
  samples: Record<string, number[]>;
  n_samples: number;
  overlay_scale_factor: number;
  raw: boolean;
}

export interface PhysicianSummary {
  id: number;
  first_name: string;
  last_name: string;
  username: string;
}

export interface Report {
  id: number;
  job_id: number;
  pseudo_id: string;
  patient?: Patient;
  patient_identifier?: string;
  patient_name?: string;
  patient_age?: number;
  patient_gender?: string;
  result: ProcessingResult;
  draft_text: string;
  physician_notes: string;
  severity: "ROUTINE" | "URGENT" | "CRITICAL";
  status:
    | "PENDING_REVIEW"
    | "IN_REVIEW"
    | "SIGNED"
    | "RETAKE_REQUESTED"
    | "EMERGENCY_TRANSFER";
  // Tele-interpretation: claiming
  claimed_by_user?: PhysicianSummary;
  claimed_at?: string;
  // Tele-interpretation: retake & emergency
  retake_reason?: string;
  emergency_notes?: string;
  // Signing
  signed_by_user?: PhysicianSummary;
  signed_at?: string;
  created_at: string;
  updated_at: string;
}

