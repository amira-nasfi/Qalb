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
