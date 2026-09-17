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
│  │  Quality Check → Pan-Tompkins & NeuroKit2 Delineation →          │  │
│  │  Intervals (RR, PR, QRS, QT, QTc) → Rule Engine & ICD-10         │  │
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

Raw ECG files (`.csv`, `.dat`/`.hea`, `.edf`) are processed deterministically:

1. **Format Loading & Calibration:** Multi-lead parsing with sampling frequency verification (`fs`).
2. **Quality & Receivability (`quality.py`):**
   - Flatline detection, baseline wander checking, and high-frequency noise ratio.
   - Lead check: ensures essential leads (`I`, `II`, `V1`, `V5`) are valid.
   - Automatic rejection (`REJECTED`) if signal is non-receivable.
3. **Delineation (`delineation.py`):**
   - Primary evaluation on Lead II using NeuroKit2 wavelet/derivative delineation.
   - Detection of P-onset, P-peak, Q-peak, R-peak, S-peak, T-peak, and T-offset.
   - Fallback to Lead V5 and Pan-Tompkins QRS detection if Lead II is degraded.
4. **Clinical Interval Measurement (`intervals.py`):**
   - Heart Rate (HR bpm) from median RR interval.
   - PR interval ($P_{onset} \to Q_{peak}$).
   - QRS duration ($Q_{peak} \to S_{peak}$).
   - QT interval ($Q_{peak} \to T_{offset}$).
   - Corrected QT (QTc) via **Bazett** ($QT / \sqrt{RR}$) and **Fridericia** ($QT / \sqrt[3]{RR}$).
   - Heart Rate Variability metrics: $pNN50$ and $RMSSD$.

---

## Clinical Rule Engine & ICD-10 Codification

| Finding Code | Condition | Severity | ICD-10 / CIM-10 | Clinical Source |
|--------------|-----------|----------|-----------------|-----------------|
| `BRADYCARDIA` | HR < 60 bpm | URGENT (ORANGE) | `R00.1` | AHA/ACC 2009 Standardisation |
| `TACHYCARDIA` | HR > 100 bpm | URGENT (ORANGE) | `R00.0` | AHA/ACC 2009 Standardisation |
| `SHORT_PR` | PR < 120 ms | ROUTINE (GREEN) | `I45.6` | Wolff-Parkinson-White / Pre-excitation |
| `LONG_PR` | PR > 200 ms | URGENT (ORANGE) | `I44.0` | Bloc AV du 1er degré (BAV 1) |
| `WIDE_QRS` | QRS ≥ 120 ms | URGENT (ORANGE) | `I45.9` | Troubles de conduction intraventriculaire |
| `QTC_MODERATE` | QTc ≥ 450 ms (♂) / ≥ 460 ms (♀) | URGENT (ORANGE) | `I45.81` | Rautaharju et al., JACC 1992 |
| `QTC_CRITICAL` | QTc ≥ 500 ms | CRITICAL (RED) | `I45.81` | ESC 2022 Ventricular Arrhythmias |
| `NORMAL_SINUS`| All measurements within normal limits | ROUTINE (GREEN) | `Z01.810` | AHA/ACC Guidelines |

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
