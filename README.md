# Qalb قلب — First-Line ECG Interpretation Platform

> *Future Health Connectathon · Défi 2.2*  
> *Every heartbeat explained. Every decision traceable. Every physician in the loop.*

---

## Table of Contents

1. [Overview](#overview)
2. [Key Capabilities & Clinical Guardrails](#key-capabilities--clinical-guardrails)
3. [Architecture & Medical Loop](#architecture--medical-loop)
4. [Role-Based Access Control (RBAC)](#role-based-access-control-rbac)
5. [Demo Credentials](#demo-credentials)
6. [Signal Processing Pipeline & Engine](#signal-processing-pipeline--engine)
7. [Clinical Rule Engine & ICD-10 Codification](#clinical-rule-engine--icd-10-codification)
8. [Unified Medical Loop & State Machine](#unified-medical-loop--state-machine)
9. [Admin Dashboard & Audit Trail](#admin-dashboard--audit-trail)
10. [HL7 FHIR R4 Interoperability](#hl7-fhir-r4-interoperability)
11. [Dataset Provenance](#dataset-provenance)
12. [Getting Started](#getting-started)
13. [API Reference](#api-reference)
14. [Security, Privacy & Ethics](#security-privacy--ethics)

---

## Overview

**Qalb قلب** (Arabic: *heart*) is a tele-expertise and clinical decision-support web platform designed for first-line 12-lead ECG interpretation in primary care dispensaries and remote healthcare centers. 

A practitioner or field team acquires an ECG and uploads it along with minimal pseudonymized metadata. A deterministic, explainable signal processing engine immediately evaluates signal quality, computes P-Q-R-S-T intervals, and applies transparent clinical rules with cited medical thresholds and ICD-10 (CIM-10) classifications.

A remote specialist (tele-expert cardiologist) accesses a prioritized real-time worklist, reviews the high-resolution interactive 12-lead waveform, writes their independent clinical conclusion (kept completely blank on pending cases to prevent automation bias), and applies a certified electronic signature. The finalized report is then automatically transmitted back to the primary care facility and delivered to the Hospital Information System (HIS) as an HL7 FHIR R4 DiagnosticReport bundle.

---

## Key Capabilities & Clinical Guardrails

* **100% Explainable & Deterministic:** No opaque neural network black-boxes in the diagnostic loop. Every finding provides `measured_value`, `threshold`, clinical rationale, and authoritative medical citations (AHA/ACC, ESC).
* **Clear Separation of Automated Findings vs. Clinical Validation:**
  * **Automated Analysis Report:** Machine-measured metrics, lead quality, rhythm assessment, and ICD-10 findings.
  * **Physician Conclusion (Avis Spécialisé):** Blank on all pending/undone cases, requiring explicit, manual clinical validation and signature from the certified tele-expert.
* **Closed Medical Loop with Append-Only Audit:**
  * Every state transition (`ACQUIRED` → `ANALYSED` → `TRANSMITTED` → `REVIEWING` → `SIGNED` → `DELIVERED`) is recorded immutably in an append-only audit trail with sub-second timestamps.
* **Focused Tele-Expertise Workflow:** Tele-experts focus on validation, differential diagnosis, and reacquisition requests (deprecated emergency dispatch buttons removed in favor of structured clinical handoff).
* **Zero-PII Compliance:** No patient names or sensitive identifiers are stored in unencrypted form; patient identity is protected via pseudonymized identifiers and national health card verification mechanisms.

---

## Architecture & Medical Loop

```
┌────────────────────────────────────────────────────────────────────────┐
│                        React 18 + TypeScript                           │
│  Acquisition (UploadPage) · Real-Time Worklist (DoctorPortalPage)     │
│  Interactive 12-Lead Reviewer & Signature (ReviewPage)                │
│  Admin Audit & Clinical Loop Monitor (AdminDashboard)                 │
│  User Management & Invites (UserManagementPage)                        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTPS / JWT Auth
┌───────────────────────────────────▼────────────────────────────────────┐
│                    Django REST Framework Core API                      │
│                                                                        │
│  /api/auth/           Authentication, token refresh, password resets   │
│  /api/ecg/studies/    Unified EcgStudy loop, worklist, waveform, audit │
│  /api/admin/          Operational KPIs, user directory, system logs    │
│  /api/fhir/           HL7 FHIR R4 Bundle generation                    │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                   Deterministic ECG Engine                       │  │
│  │  Quality Check → NeuroKit2 DWT Delineation (II/V1/V5) →          │  │
│  │  Intervals (RR, PR, QRS, QT, QTc, pNN50, RMSSD) → Rule Engine   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌────────────────┐  │
│  │ EcgStudy & AuditLog │  │ FHIR R4 Exporter    │  │ User Directory │  │
│  │ Append-only events  │  │ LOINC / SNOMED-CT   │  │ RBAC / Roles   │  │
│  └─────────────────────┘  └─────────────────────┘  └────────────────┘  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                         ┌──────────┴──────────┐
                         │                     │
               ┌─────────▼────────┐  ┌─────────▼────────┐
               │  PostgreSQL /    │  │ Encrypted Media  │
               │  SQLite DB       │  │ Storage (Raw ECG)│
               └──────────────────┘  └──────────────────┘
```

---

## Role-Based Access Control (RBAC)

The platform enforces strict role differentiation across both the frontend navigation and backend API endpoints:

| Role | Intended User | Capabilities & Permissions |
|------|---------------|----------------------------|
| `FIELD_AGENT` | Praticien / Agent de dispensaire | • Upload & acquisition of 12-lead ECGs<br>• Access to real-time worklist & queue<br>• **Read-only** consultation of automated findings & waveforms<br>• *Cannot claim, validate, or electronically sign dossiers* |
| `PHYSICIAN` | Médecin Télé-expert (Cardiologue) | • Access to prioritized clinical worklist (P1/P2/P3)<br>• Dossier claiming and waveform exploration<br>• Manual conclusion drafting & electronic signature<br>• ECG reacquisition requests |
| `ADMIN` | Administrateur Médical / Système | • **Audit Clinique de la Boucle Médicale** (turnaround, SLAs)<br>• System audit log inspection with cryptographic hashes<br>• User provisioning, account suspension, and role assignment |

---

## Demo Credentials

All test accounts share the same default password: `Password123!`

| Role | Username / Identifier | Password | Description |
|------|-----------------------|----------|-------------|
| **Administrateur** | `admin` | `Password123!` | Full admin dashboard, clinical loop audit, user management |
| **Médecin Télé-expert** | `40218840` | `Password123!` | Tele-expertise portal, electronic signature station |
| **Praticien de terrain** | `71867777` | `Password123!` | Dispensary acquisition, read-only worklist consultation |

---

## Signal Processing Pipeline & Engine

Raw ECG files (`.csv`, `.dat`/`.hea`, `.edf`) are processed synchronously by the `ecg_analysis` library (`backend/ecg_analysis/`) on every upload. The pipeline runs in a single function call — `analyze_to_report()` — and produces a fully JSON-serialisable result in under 1 000 ms.

1. **Format Loading (`readers.py`):** Multi-format ingestion via `read_any()`. Supports WFDB (`.dat`/`.hea`) via `wfdb.rdsamp()`, CSV with lead-name headers, and EDF via `pyedflib`. Amplitude is normalized to millivolts; lead order is remapped to the canonical AHA/ACC 12-lead sequence.
2. **Preprocessing (`pipeline.py` — `preprocess()`):**
   - **Resampling** to 500 Hz (polyphase) if the source `fs` differs.
   - **Notch filters** at 50 Hz and 100 Hz (IIR, Q=30) to remove powerline interference.
   - **2-stage median baseline correction** (200 ms then 600 ms windows) — preserves ST segment morphology unlike a high-pass filter.
   - **150 Hz 4th-order Butterworth lowpass** applied zero-phase.
3. **Signal Quality Assessment (`assess_quality()`):**
   - Per-lead checks: flatline detection (peak-to-peak < 0.05 mV), amplitude range, baseline wander ratio, powerline noise ratio, and signal kurtosis.
   - Automatic rejection (`REJECTED` triage, `escalated=True`) if signal quality is unacceptable.
4. **Beat Detection & PQRST Segmentation (`detect_beats()`, `segment()`):**
   - R-peak detection via NeuroKit2 `ecg_peaks()` on Lead II.
   - DWT-based delineation via `ecg_delineate()` run on anchor leads **II, V1, V5**.
   - Calibration offsets applied (measured against 191 LUDB annotated records): P_on (+12.8 ms), P_off (−18.3 ms), QRS_on (−6.9 ms), QRS_off (−4.4 ms), T_off (−19.6 ms).
5. **Clinical Interval Measurement (`measure()`):**
   - Heart Rate (HR bpm) from median RR interval.
   - PR interval ($P_{onset} \to QRS_{onset}$), QRS duration, QT interval — all as per-beat medians.
   - Corrected QT via **Bazett** ($QT / \sqrt{RR}$) and **Fridericia** ($QT / RR^{1/3}$).
   - Heart Rate Variability: $pNN50$ and $RMSSD$.
   - Ectopic beat count (RR deviation > 20% from median).

---

## Clinical Rule Engine & ICD-10 Codification

The `analyse()` function in `ecg_analysis/pipeline.py` applies deterministic, fully cited rules. Every finding exposes `code`, `finding`, `severity`, `measured`, `threshold`, `meaning`, and a `diagnosis` block with ICD-10 / CIM-10 code.

| Finding Code | Condition | Severity | ICD-10 / CIM-10 | Clinical Source |
|--------------|-----------|----------|-----------------|-----------------|
| `PACED` | Paced rhythm flag supplied by device | ORANGE | `Z95.0` | AHA/ACC 2022 |
| `IRREG` | pNN50 > 0.35 → AF not excluded | ORANGE | `I48.91` | Sensitivity 100%, specificity 79% on 200 records |
| `SINUS` | pNN50 ≤ 0.35 → organised sinus activity | GREEN | — | AHA/ACC 2009 |
| `BRADY` | HR < 60 bpm | GREEN / ORANGE | `R00.1` | AHA/ACC 2009 Standardisation |
| `TACHY` | HR > 90 bpm | ORANGE | `R00.0` | AHA/ACC 2009 Standardisation |
| `WCT` | Tachycardia + QRS > 120 ms + HR > 120 bpm | RED | `I47.2` | Wide Complex Tachycardia — VT not excluded |
| `ECTOPIC` | n RR intervals deviating > 20% from median | GREEN | `I49.40` | AHA/ACC 2009 |
| `AVB1` | PR > 200 ms | ORANGE | `I44.0` | Bloc AV du 1er degré |
| `SHORT_PR` | PR < 120 ms | ORANGE | `I45.6` | WPW / pre-excitation |
| `PR_OK` | 120 ms ≤ PR ≤ 200 ms | GREEN | — | Normal AV conduction |
| `IVCD` | QRS > 120 ms | ORANGE | `I45.4` | Bundle branch block / intraventricular conduction delay |
| `ST_NA` | ST criteria invalid (IVCD or paced) | ORANGE | — | Sgarbossa criteria required |
| `QT_LONG_SEVERE` | QTc > 500 ms | RED | `I45.81` | ESC 2022 — high risk of Torsades de Pointes |
| `QT_LONG` | QTc > 450 ms (♂) / 460 ms (♀) | ORANGE | `R94.31` | Rautaharju et al., JACC 1992 |
| `QT_SHORT` | QTc < 340 ms | ORANGE | `I45.89` | Short QT syndrome (suspected) |
| `QT_OK` | QTc within normal limits | GREEN | — | Normal ventricular repolarisation |
| `SINUS` | All findings GREEN | GREEN | — | Normal tracing |

---

## Unified Medical Loop & State Machine

The entire patient journey is tracked under the unified `EcgStudy` state machine:

$$\text{ACQUIRED} \longrightarrow \text{ANALYSED} \longrightarrow \text{TRANSMITTED} \longrightarrow \text{REVIEWING} \longrightarrow \text{SIGNED} \longrightarrow \text{DELIVERED}$$

* **Acquired:** ECG raw data and verified patient metadata ingested.
* **Analysed:** Automated processing pipeline finishes in $< 1000\text{ ms}$; triage priority assigned.
* **Transmitted:** Study pushed to the tele-expertise pool.
* **Reviewing:** Cardiologist claims the record; reading timestamp recorded.
* **Signed:** Specialist writes manual conclusions and electronically signs; dossier locked.
* **Delivered:** Final DiagnosticReport bundle restituted to the local clinic and Hospital Information System (HIS).

---

## Admin Dashboard & Audit Trail

Accessible to administrators at `/admin`:

1. **System Audit Log:**
   * Append-only trail with actor usernames, timestamps, hashed IP addresses, and state changes.
   * Cryptographic integrity ensuring zero retroactive mutation of medical records.
2. **User Directory & Provisioning (`/admin/users`):**
   * Role management (`FIELD_AGENT`, `PHYSICIAN`, `ADMIN`), secure temporary password generation, and soft-suspension.
3. **Operational Metrics (Topbar):**
   * Live indicators refreshed every 30 seconds: 24h upload volume, pending reviews, active critical flags, and average processing latency.

---

## HL7 FHIR R4 Interoperability

Exportable via `GET /api/reports/{id}/fhir/` and `POST /api/ecg/studies/{id}/deliver/`:

* **`Observation` Resources:** Discrete LOINC-coded quantitative measurements (Heart Rate `8867-4`, PR interval `8625-6`, QRS duration `8633-0`, QT interval `8634-8`, QTc `8636-3`).
* **`DiagnosticReport` Resource:** Comprehensive clinical summary containing physician signature, conclusion, and extensions for deterministic rules triggered.

---

## Getting Started

### 1. Prerequisites
* Node.js ≥ 18
* Python ≥ 3.10
* SQLite (default for development) or PostgreSQL 15

### 2. Backend Setup
```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8000
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

The app will be running at `http://localhost:5173`.

---

## API Reference

### ECG & Medical Loop (`/api/ecg/studies/`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/ecg/studies/` | Upload ECG file, execute pipeline, and create `EcgStudy` |
| `GET` | `/api/ecg/studies/worklist/` | Prioritized clinical worklist (P1 Red, P2 Orange, P3 Green) |
| `GET` | `/api/ecg/studies/loop-audit/` | Audit metrics, pipeline steps & turnaround for Admin |
| `GET` | `/api/ecg/studies/{id}/` | Full details of a study including automated analysis |
| `GET` | `/api/ecg/studies/{id}/waveform/` | 12-lead signal sampled at 250 Hz with overlay calibration |
| `POST` | `/api/ecg/studies/{id}/open/` | Records physician opening timestamp |
| `POST` | `/api/ecg/studies/{id}/sign/` | Electronic signature submission & dossier locking |
| `POST` | `/api/ecg/studies/{id}/deliver/` | Restitution of signed report to Hospital Information System |

### Authentication & Users (`/api/`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/login/` | JWT token pair generation (`access`, `refresh`) |
| `GET` | `/api/auth/me/` | Current user profile and active role |
| `GET` | `/api/admin/users/` | List all system users (Admin only) |
| `POST` | `/api/admin/users/invite/` | Create and invite new practitioner or physician |
| `POST` | `/api/admin/users/{id}/suspend/`| Toggle soft-disable user account |

---

## Security, Privacy & Ethics

1. **Physician in the Loop:** The automated engine only assists and flags; formal medical diagnosis and therapeutic decisions require certified practitioner sign-off.
2. **Zero-PII Storage:** Patient files contain no unencrypted names; identifiers use standard format `IPP-YYYY-XXXXX`.
3. **No Retroactive Alterations:** Audit tables and clinical logs cannot be deleted or mutated via API.
4. **Guaranteed Explainability:** Every finding includes measured values, thresholds, and cited literature.
