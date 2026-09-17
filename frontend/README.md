# Qalb قلب — Frontend Web Application

Modern, accessible, and high-performance React application for first-line ECG tele-expertise and clinical decision support.

---

## Technology Stack

* **Framework:** React 18 with TypeScript
* **Build Tool:** Vite 5
* **Routing:** React Router v6 (Role-protected routes)
* **Styling:** Custom Vanilla CSS design system with HSL tokens, glassmorphism, responsive grid layouts, and dark sidebar
* **Icons:** Lucide React
* **Charts & Waveforms:** Native SVG / Canvas 12-lead interactive waveform renderer with grid calibration (25 mm/s, 10 mm/mV) and NeuroKit2 wave boundary markers

---

## User Roles & Navigation

The interface automatically adapts based on the authenticated user's role:

### 1. Praticien de terrain (`FIELD_AGENT`)
* **Acquisition ECG (`/upload`):** Ingestion of 12-lead records (.csv, .edf, .dat), patient pseudonymization, sampling rate detection.
* **File d'attente ECG (`/doctor`):** Real-time monitoring of active dossiers in the tele-expertise pool.
* **Consultation des résultats (`/review/:id`):** Full read-only view of the 12-lead ECG, computed interval metrics, and AI rule flags.
* *Security guardrail:* The practitioner is shown an informative notice and is restricted from taking over, validating, or signing the study.

### 2. Médecin Télé-expert (`PHYSICIAN`)
* **Portail Télé-Interprétation (`/doctor`):** Prioritized worklist sorted by clinical triage (P1 Critical/Red, P2 Urgent/Orange, P3 Routine/Green).
* **Poste de lecture & signature (`/review/:id`):** 
  * Full 12-lead interactive signal viewer.
  * Side-by-side display of the immutable automated analysis report and a blank clinical conclusion field.
  * Certified electronic signature modal to validate and lock the record.
  * Reacquisition request trigger with medical justification.

### 3. Administrateur Système (`ADMIN`)
* **Audit Clinique de la Boucle Médicale (`/admin`):** Real-time dashboard measuring acquisition-to-delivery turnaround times, step chronometry, and triage volumes.
* **Journal d'audit (`/admin`):** Append-only forensic log viewer.
* **Gestion des utilisateurs (`/admin/users`):** Account provisioning, invitations, role modification, and account suspension.

---

## Directory Structure

```
frontend/src/
├── api/                  # Axios HTTP clients & API services
│   ├── admin.ts          # Audit logs, loop audit metrics, user management
│   ├── auth.ts           # Login, logout, JWT tokens
│   ├── client.ts         # Axios instance with auth interceptors
│   ├── ecg.ts            # Studies, worklist, waveform, signature, delivery
│   ├── patients.ts       # Patient registration & lookup
│   └── reports.ts        # Legacy report endpoints
├── components/
│   ├── auth/             # ProtectedRoute guards with allowedRoles
│   ├── ecg/              # Waveform viewer, clinical limits banner, audit viewer
│   ├── layout/           # Sidebar, Topbar with live KPI polling
│   └── ui/               # Badge, Button, Card, Skeleton, Toast, Modal
├── contexts/             # AuthContext (user, role, tokens, session state)
├── pages/
│   ├── admin/            # UserManagementPage, InviteModal
│   ├── doctor/           # DoctorPortalPage (prioritized worklist)
│   ├── AdminDashboard.tsx# Audit Clinique de la Boucle Médicale & logs
│   ├── ChangePasswordPage.tsx
│   ├── DashboardPage.tsx # Field agent study tracking
│   ├── ForbiddenPage.tsx # 403 error page
│   ├── LandingPage.tsx   # Platform overview & entry points
│   ├── LoginPage.tsx     # Authentication interface
│   ├── ReviewPage.tsx    # Interactive reading station & signature
│   └── UploadPage.tsx    # 12-lead ECG file ingestion
└── styles/               # Global CSS tokens, reset, typography
```

---

## Development

```bash
# Install dependencies
npm install

# Start Vite development server
npm run dev

# Run TypeScript type check
npx tsc --noEmit

# Production build
npm run build
```
