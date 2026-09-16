export interface Patient {
  pseudo_id: string;
  dob_year: number;
  sex: "M" | "F" | "O";
  facility_id: string;
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

export interface Report {
  id: number;
  job_id: number;
  pseudo_id: string;
  result: ProcessingResult;
  draft_text: string;
  physician_notes: string;
  severity: "ROUTINE" | "URGENT" | "CRITICAL";
  status: "PENDING_REVIEW" | "REVIEWED" | "SIGNED";
  signed_by_user?: {
    id: number;
    first_name: string;
    last_name: string;
    username: string;
  };
  signed_at?: string;
  created_at: string;
  updated_at: string;
}
