# Qalb قلب — First-Line ECG Interpretation Platform

> *Future Health Connectathon · Défi 2.2*  
> *Every heartbeat explained. Every decision traceable. Every physician in the loop.*

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Signal Processing Pipeline](#signal-processing-pipeline)
4. [Clinical Rule Engine](#clinical-rule-engine)
5. [Admin Dashboard & Traceability](#admin-dashboard--traceability)
6. [Audit Log](#audit-log)
7. [FHIR Export](#fhir-export)
8. [Dataset Provenance](#dataset-provenance)
9. [Getting Started](#getting-started)
10. [API Reference](#api-reference)
11. [CI/CD](#cicd)
12. [Security & Privacy](#security--privacy)
13. [Integration Point for ML Layer](#integration-point-for-ml-layer)
14. [Ethical Constraints](#ethical-constraints)

---

## Overview

**Qalb قلب** (Arabic: *heart*) is a web platform enabling first-line ECG interpretation at primary care facilities. A field team acquires a 12-lead ECG, uploads it with minimal patient metadata, and a deterministic signal-processing pipeline computes clinical intervals and applies a transparent rule engine to produce a pre-filled triage report. A remote physician reviews the waveform, reads the annotated flags (each traceable to a measured value and a cited clinical threshold), adds notes, and electronically signs the report. Only signed reports are released to the field team and exported as HL7 FHIR R4 bundles.

### What this system is NOT
- ❌ No trained ML model (Person B adds that layer separately on a feature branch)
- ❌ No opaque scores — every flag exposes `measured_value`, `threshold`, `citation`
- ❌ No PII stored server-side — pseudonymized UUIDs only
- ❌ No unsupervised clinical decisions — physician sign-off is mandatory and non-bypassable

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         React Frontend                          │
│  LandingPage · UploadPage · PhysicianDashboard · ReviewPage     │
│  FieldTeamView · AdminDashboard (/admin — separate app)         │
│  Fixed KPI Bar (live counts: uploads, pending, CRITICAL today)  │
└─────────────┬───────────────────────────────────────────────────┘
              │ HTTPS / Axios
┌─────────────▼───────────────────────────────────────────────────┐
│                   Django REST Framework                          │
│  /api/patients/   /api/ecg/   /api/reports/   /api/fhir/        │
│  /api/admin/      (KPIs, audit log, traceability)               │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              ECG Processing Pipeline (Celery)              │ │
│  │  loader → preprocess → delineate → intervals → rule_engine │ │
│  │  (NeuroKit2 · SciPy · WFDB — deterministic only)          │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  Audit Log  │  │ FHIR Builder │  │  Admin Dashboard App │   │
│  │  (every     │  │ (R4 Obs +    │  │  (separate Django    │   │
│  │   action)   │  │  DiagReport) │  │   app, /admin path)  │   │
│  └─────────────┘  └──────────────┘  └──────────────────────┘   │
└──────────────────────────────┬──────────────────────────────────┘
                               │
              ┌────────────────┴────────────────┐
              │                                 │
    ┌─────────▼────────┐             ┌──────────▼────────┐
    │   PostgreSQL 15   │             │    Redis (Celery)  │
    │  (SSL, encrypted  │             │    task queue      │
    │   field storage)  │             └───────────────────┘
    └───────────────────┘
```

---

## Signal Processing Pipeline

All processing is **deterministic and explainable**. No trained model is used.

```
Raw ECG file (.mat / .csv / .edf)
        │
        ▼
  [loader.py]
  wfdb.rdsamp() / pd.read_csv() / mne.io.read_raw_edf()
  Output: signals (12 × N), fs (Hz), metadata (no PII)
        │
        ▼
  [preprocessing.py]
  Bandpass filter: 0.5–40 Hz (4th-order Butterworth, zero-phase)
  Per-lead z-score normalization
  Reference: Pan & Tompkins (1985); Sörnmo & Laguna (2005)
        │
        ▼
  [delineation.py]
  Primary: Lead II → nk.ecg_process(signal, sampling_rate=fs)
  Extracts: P onsets, Q peaks, R peaks, S peaks, T offsets
  Fallback: Lead V5 if Lead II delineation < 50% complete
  Partial mode: R-peaks only (Pan-Tompkins) if both leads fail
  Library: NeuroKit2 (Makowski et al., 2021, Journal of Open Source Software)
        │
        ▼
  [intervals.py]
  Per-beat computation, then median ± IQR reported:
  • PR interval  = P_onset → Q_peak  (ms)
  • QRS duration = Q_peak  → S_peak  (ms)
  • QT interval  = Q_peak  → T_offset (ms)
  • QTc (Bazett) = QT / √(RR in s)  — Bazett (1920)
  • QTc (Fridericia) = QT / RR^(1/3) — Fridericia (1920)
  • Heart rate   = 60 000 / median_RR (ms)
        │
        ▼
  [rule_engine.py]
  8 deterministic rules, each Flag carries:
    code · label · measured_value · unit · threshold · direction · severity · citation
  Severity: ROUTINE → URGENT → CRITICAL
```

---

## Clinical Rule Engine

| Rule Code | Condition | Severity | Clinical Source |
|-----------|-----------|----------|----------------|
| `BRADYCARDIA` | HR < 60 bpm | WARNING | AHA/ACC 2009 ECG Standardisation |
| `TACHYCARDIA` | HR > 100 bpm | WARNING | AHA/ACC 2009 |
| `SHORT_PR` | PR < 120 ms | WARNING | AHA/ACC 2009 (possible pre-excitation) |
| `LONG_PR` | PR > 200 ms | WARNING | AHA/ACC 2009 (possible 1° AV block) |
| `WIDE_QRS` | QRS > 120 ms | WARNING | AHA/ACC 2009 (possible bundle branch block) |
| `QTC_MODERATE` | QTc ≥ 450 ms (♂) / ≥ 460 ms (♀) | WARNING | Rautaharju et al., JACC 1992 |
| `QTC_CRITICAL` | QTc ≥ 500 ms | CRITICAL | ESC 2022 Channelopathy Guideline |
| `NORMAL_SINUS` | All within range | INFO | — |

Every flag is stored verbatim in the database and included in the FHIR export. No flag is ever removed or suppressed by the system.

---

## Admin Dashboard & Traceability

The admin dashboard is a **separate React page at `/admin`** served by the same Vite app, with its own Django app (`backend/admin_dashboard/`) serving dedicated API endpoints at `/api/admin/`.

### KPI Bar (fixed, always visible)
The top navbar shows live KPIs that refresh every 30 seconds:

| KPI | Source endpoint |
|-----|----------------|
| Total ECGs uploaded (today) | `/api/admin/kpis/` |
| Pending physician reviews | `/api/admin/kpis/` |
| Signed reports (today) | `/api/admin/kpis/` |
| CRITICAL flags (active) | `/api/admin/kpis/` |
| Avg processing time (ms) | `/api/admin/kpis/` |

### Admin Dashboard Features
- **Full pipeline traceability**: Every ECG record links to its processing result, flags, report, physician sign-off, and FHIR export.
- **Audit log viewer**: Filterable by user, action type, target entity, date range.
- **Report lifecycle view**: Timeline from upload → PENDING → REVIEWED → SIGNED → FHIR_EXPORTED.
- **Flag statistics**: Count by severity and rule code; trend over time.
- **User activity**: Physician sign-off rates, review latency.

---

## Audit Log

Every action in the system is recorded in the `AuditLog` table:

```python
class AuditLog(models.Model):
    timestamp     # when it happened
    actor         # which user performed the action (or "SYSTEM" for pipeline)
    action        # CREATE / UPDATE / SIGN / EXPORT_FHIR / PROCESS / ERROR
    target_type   # "Patient" / "ECGRecord" / "Report" / "ProcessingResult"
    target_id     # UUID or int PK of the affected object
    old_value     # JSON snapshot before change (null for CREATE)
    new_value     # JSON snapshot after change
    ip_address    # request IP (hashed for privacy)
    user_agent    # browser UA string
    extra         # arbitrary JSON context (e.g., flag codes triggered)
```

Audit logs are **append-only** — no update or delete is possible via the API. Only a superuser can query them. The admin dashboard exposes a read-only, filterable, exportable view.

---

## FHIR Export

Signed reports are exportable as an HL7 FHIR R4 Bundle:

```json
{
  "resourceType": "Bundle",
  "type": "collection",
  "entry": [
    {
      "resource": {
        "resourceType": "Observation",
        "status": "final",
        "code": { "coding": [{ "system": "http://loinc.org", "code": "11524-6" }] },
        "component": [
          { "code": { "coding": [{ "system": "http://loinc.org", "code": "8867-4" }] },
            "valueQuantity": { "value": 72, "unit": "/min", "system": "http://unitsofmeasure.org" }
          }
        ]
      }
    },
    {
      "resource": {
        "resourceType": "DiagnosticReport",
        "status": "final",
        "conclusion": "Physician notes here",
        "extension": [
          {
            "url": "https://qalb.health/fhir/extensions/ecg-flag",
            "extension": [
              { "url": "code",            "valueString": "QTC_CRITICAL" },
              { "url": "measured_value",  "valueDecimal": 512 },
              { "url": "threshold",       "valueDecimal": 500 },
              { "url": "unit",            "valueString": "ms" },
              { "url": "citation",        "valueString": "ESC 2022 Channelopathy Guideline" }
            ]
          }
        ]
      }
    }
  ]
}
```

**Endpoint**: `GET /api/reports/{id}/fhir/`  
**Auth**: Physician or field team token  
**Precondition**: `status = SIGNED` (403 otherwise)  
**Content-Type**: `application/fhir+json`

---

## Dataset Provenance

See [`backend/provenance/DATASET_PROVENANCE.md`](backend/provenance/DATASET_PROVENANCE.md) for full provenance of all datasets used in testing and validation.

| Dataset | DOI | License | Use |
|---------|-----|---------|-----|
| PTB-XL | 10.13026/cmsy-5161 | CC-BY 4.0 | Pipeline tests, demo records |
| QT Database | 10.13026/C24K53 | ODC-BY 1.0 | QTc accuracy validation |
| LUDB | 10.13026/qwde-4j96 | CC-BY 4.0 | Delineation accuracy |

No synthetic ECG data is used anywhere in this system.

---

## Getting Started

### Prerequisites
- Docker + Docker Compose v2
- Node.js ≥ 18
- Python ≥ 3.10 (for local dev without Docker)

### 1. Clone & configure

```bash
git clone https://github.com/your-org/qalb-ecg.git
cd qalb-ecg
cp .env.example .env
# Edit .env — set SECRET_KEY, FIELD_ENCRYPTION_KEY, DATABASE_URL
```

### 2. Start with Docker

```bash
docker-compose up --build
```

Services:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000/api/
- Admin Dashboard: http://localhost:5173/admin
- Django Admin (superuser): http://localhost:8000/django-admin/

### 3. Local backend dev (without Docker)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
# In a second terminal:
celery -A config worker -l info
```

### 4. Local frontend dev

```bash
cd frontend
npm install
npm run dev
```

### 5. Run tests

```bash
# Backend
cd backend && pytest --cov --cov-report=term-missing

# Frontend
cd frontend && npm test
```

---

## API Reference

### Patients
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/patients/` | Register pseudonymized patient |
| GET | `/api/patients/{pseudo_id}/` | Get patient info |

### ECG
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/ecg/upload/` | Upload ECG file → returns job_id |
| GET | `/api/ecg/{job_id}/status/` | Poll processing status |
| GET | `/api/ecg/{job_id}/signal/` | Downsampled signal for chart |

### Reports
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/reports/` | List reports (filterable by status) |
| GET | `/api/reports/{id}/` | Get full report |
| PATCH | `/api/reports/{id}/` | Update physician notes |
| POST | `/api/reports/{id}/sign/` | Physician sign-off (irreversible) |
| GET | `/api/reports/{id}/fhir/` | Export FHIR R4 Bundle |

### Admin
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/kpis/` | Live KPI counts |
| GET | `/api/admin/audit-logs/` | Paginated audit log (filterable) |
| GET | `/api/admin/traceability/{ecg_id}/` | Full lifecycle of one ECG |
| GET | `/api/admin/flag-stats/` | Flag frequency + severity breakdown |
| GET | `/api/admin/user-activity/` | Physician review latency stats |

---

## CI/CD

GitHub Actions pipeline (`.github/workflows/ci.yml`):

```
push / pull_request → main
        │
        ├── lint-backend    (flake8)
        ├── lint-frontend   (eslint)
        ├── test-backend    (pytest --cov-fail-under=65)
        ├── build-frontend  (vite build)
        ├── docker-check    (docker-compose up + manage.py check)
        └── provenance-guard (fail if DATASET_PROVENANCE.md missing)
```

All 6 jobs are **required status checks** — no merge to `main` without green CI.

---

## Security & Privacy

| Control | Implementation |
|---------|---------------|
| No PII stored | `pseudo_id` (UUID) + `dob_year` + `sex` only |
| Encrypted fields | `django-encrypted-model-fields` (AES-256) |
| Audit trail | Append-only `AuditLog` table; every state change logged |
| Role-based access | `IsPhysician` / `IsFieldTeam` / `IsAdmin` permission classes |
| Field team gate | 403 on any unsigned report, enforced at DRF permission level |
| HTTPS | Enforced in production (`SECURE_SSL_REDIRECT=True`) |
| CORS | Whitelist only (frontend origin) |
| File storage | Encrypted at rest; only SHA-256 hash stored in DB |

---

## Integration Point for ML Layer

Person B adds the ML model as a separate function with an identical `Flag` interface:

```python
# backend/ecg/pipeline/rule_engine.py

def apply_ml_flags(signals_clean: np.ndarray, intervals: IntervalResult) -> list[Flag]:
    """
    Person B implements this function.
    Contract:
      - Must return list[Flag] with the same Flag dataclass
      - Each Flag MUST have: measured_value, threshold, citation
      - No opaque scores — ML confidence must map to an explainable threshold
      - Must NOT modify any existing function in this file
    """
    raise NotImplementedError("Awaiting Person B ML integration")
```

The Celery task merges `apply_rules()` + `apply_ml_flags()` results. The feature branch adds only this function and a new `IS_ML_ENABLED` setting.

---

## Ethical Constraints

1. **No trained model** in this codebase (deterministic algorithms only).
2. **No synthetic ECG data** used as evidence — only PhysioNet public datasets with documented provenance.
3. **Every flag is traceable** to `measured_value + threshold + citation`.
4. **Physician sign-off is mandatory** and technically enforced (not just UI-level).
5. **Audit log is append-only** — no retroactive modification of any clinical record.
6. **Dataset provenance sheet is a CI gate** — CI fails if it is missing.

---

*Built for Future Health Connectathon · Défi 2.2 · 2026*
