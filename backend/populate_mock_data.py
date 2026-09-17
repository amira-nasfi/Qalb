"""
populate_mock_data.py
Populates the database with realistic mock data for the practitioner dashboard:
- Pseudonymized Patients with full FHIR compliance (IPP, Nom, Prénom, DDN, Sexe)
- 12-lead ECG CSV files with simulated signals (for instant chart rendering)
- ProcessingResults with clinical intervals & flags
- Reports (both PENDING_REVIEW and SIGNED)
- AuditLog entries
"""

import os
import sys
import django
import uuid
import hashlib
import datetime
import numpy as np
import pandas as pd
from datetime import timedelta
from django.utils import timezone
from django.core.files.base import ContentFile

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

import neurokit2 as nk
from patients.models import Patient
from ecg.models import ECGRecord, ProcessingResult
from reports.models import Report
from reports.utils import generate_draft
from audit.models import AuditLog, AuditAction
from accounts.models import User, Role

STANDARD_LEADS = ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"]

def get_or_create_physician():
    physician = User.objects.filter(role=Role.PHYSICIAN).first()
    if not physician:
        physician = User.objects.create_user(
            username="88889999",
            first_name="Dr. Sarah",
            last_name="Mansour",
            email="sarah.mansour@qalb.health",
            password="TemporaryPassword123!",
            role=Role.PHYSICIAN,
            force_password_change=False
        )
    return physician

def generate_ecg_csv_content(hr: int = 75, duration: int = 10, fs: int = 500) -> str:
    lead_II = nk.ecg_simulate(duration=duration, sampling_rate=fs, heart_rate=hr)
    data = {}
    for i, lead in enumerate(STANDARD_LEADS):
        gain = 1.0 if lead == "II" else (0.7 + 0.1 * (i % 5))
        noise = np.random.normal(0, 0.02, len(lead_II))
        data[lead] = np.round((lead_II * gain + noise).astype(np.float32), 4)
    df = pd.DataFrame(data)
    df.insert(0, "fs", fs)
    return df.to_csv(index=False)

def create_case(case_def, physician):
    # 1. Create Patient with full demographic data
    patient = Patient.objects.create(
        pseudo_id=uuid.uuid4(),
        patient_identifier=case_def["patient_identifier"],
        first_name=case_def["first_name"],
        last_name=case_def["last_name"],
        birth_date=datetime.date.fromisoformat(case_def["birth_date"]),
        dob_year=int(case_def["birth_date"].split("-")[0]),
        sex=case_def["sex"],
        gender="male" if case_def["sex"] == "M" else "female",
        facility_id=case_def["facility_id"]
    )

    # 2. Generate Simulated CSV File
    csv_content = generate_ecg_csv_content(hr=case_def["hr"], duration=10, fs=500)
    file_bytes = csv_content.encode("utf-8")
    sha256 = hashlib.sha256(file_bytes).hexdigest()
    filename = f"sim_{case_def['code'].lower()}_{uuid.uuid4().hex[:8]}.csv"

    record = ECGRecord(
        patient=patient,
        fmt=ECGRecord.Format.CSV,
        status=ECGRecord.Status.DONE,
        file_hash=sha256,
        fs=500,
        lead_count=12,
    )
    record.file.save(filename, ContentFile(file_bytes), save=True)

    # 3. Create ProcessingResult
    intervals = case_def["intervals"]
    flags = case_def["flags"]

    result = ProcessingResult.objects.create(
        record=record,
        intervals_json=intervals,
        flags_json=flags,
        severity=case_def["severity"],
        lead_used="II",
        partial=False
    )

    # 4. Create Report
    draft = generate_draft(flags)
    report = Report.objects.create(
        result=result,
        draft_text=draft,
        severity=case_def["severity"],
        status=case_def["status"],
        physician_notes=case_def.get("physician_notes", ""),
        signed_by=physician if case_def["status"] == Report.Status.SIGNED else None,
        signed_at=timezone.now() - timedelta(hours=case_def.get("hours_ago", 1)) if case_def["status"] == Report.Status.SIGNED else None,
    )

    # 5. Audit Log
    AuditLog.log(
        action=AuditAction.PROCESS_DONE,
        target_type="ECGRecord",
        target_id=record.id,
        extra={"severity": case_def["severity"], "flag_codes": [f["code"] for f in flags]}
    )
    if report.status == Report.Status.SIGNED:
        AuditLog.log(
            action=AuditAction.SIGN,
            target_type="Report",
            target_id=report.id,
            actor=physician,
            extra={"signed_by": physician.username}
        )

    print(f"Created Case #{report.id} - Status: {report.status} - Severity: {report.severity} - Patient: {patient.full_name} ({patient.patient_identifier})")
    return report

def run():
    print("=== Cleaning previous reports and records ===")
    Report.objects.all().delete()
    ECGRecord.objects.all().delete()
    Patient.objects.all().delete()

    physician = get_or_create_physician()
    print(f"Assigning signed reports to physician: {physician.get_full_name() or physician.username}")

    cases = [
        # Case 1: CRITICAL
        {
            "code": "CRIT_QTC",
            "patient_identifier": "IPP-2026-00841",
            "first_name": "Mohamed",
            "last_name": "Ben Salem",
            "birth_date": "1968-04-12",
            "sex": "M",
            "facility_id": "DISP-TUNIS-SUD-01",
            "hr": 78,
            "severity": "CRITICAL",
            "status": Report.Status.PENDING_REVIEW,
            "intervals": {
                "hr_bpm": {"median": 78.4, "iqr": 2.1, "unit": "bpm", "formula_ref": "60000/RR", "n_valid": 13},
                "pr_ms": {"median": 168.0, "iqr": 6.2, "unit": "ms", "formula_ref": "P_onset to Q_peak", "n_valid": 12},
                "qrs_ms": {"median": 98.4, "iqr": 4.1, "unit": "ms", "formula_ref": "Q_peak to S_peak", "n_valid": 13},
                "qt_ms": {"median": 458.0, "iqr": 8.0, "unit": "ms", "formula_ref": "Q_peak to T_offset", "n_valid": 12},
                "qtc_bazett": {"median": 524.6, "iqr": 9.2, "unit": "ms", "formula_ref": "Bazett (1920)", "n_valid": 12},
                "qtc_fridericia": {"median": 501.2, "iqr": 8.5, "unit": "ms", "formula_ref": "Fridericia (1920)", "n_valid": 12},
                "n_beats": 13,
                "partial": False,
                "lead_used": "II",
                "delineation_rate": 0.96
            },
            "flags": [
                {
                    "code": "QTC_CRITICAL",
                    "label": "Allongement critique du QTc (524.6 ms >= 500 ms) - RISQUE MAJEUR DE TORSADES DE POINTES",
                    "measured_value": 524.6,
                    "unit": "ms",
                    "threshold": 500.0,
                    "direction": "above",
                    "severity": "CRITICAL",
                    "citation": "ESC (2022) Ventricular Arrhythmias Guidelines. Eur Heart J 43(40):3997-4126."
                }
            ]
        },
        # Case 2: URGENT (Tachycardia + Short PR)
        {
            "code": "URG_TACHY",
            "patient_identifier": "IPP-2026-01205",
            "first_name": "Sonia",
            "last_name": "Trabelsi",
            "birth_date": "1985-09-23",
            "sex": "F",
            "facility_id": "DISP-BIZERTE-03",
            "hr": 118,
            "severity": "URGENT",
            "status": Report.Status.PENDING_REVIEW,
            "intervals": {
                "hr_bpm": {"median": 118.2, "iqr": 3.4, "unit": "bpm", "formula_ref": "60000/RR", "n_valid": 19},
                "pr_ms": {"median": 108.0, "iqr": 4.5, "unit": "ms", "formula_ref": "P_onset to Q_peak", "n_valid": 18},
                "qrs_ms": {"median": 86.2, "iqr": 3.0, "unit": "ms", "formula_ref": "Q_peak to S_peak", "n_valid": 19},
                "qt_ms": {"median": 312.0, "iqr": 6.0, "unit": "ms", "formula_ref": "Q_peak to T_offset", "n_valid": 18},
                "qtc_bazett": {"median": 438.2, "iqr": 7.0, "unit": "ms", "formula_ref": "Bazett (1920)", "n_valid": 18},
                "qtc_fridericia": {"median": 412.0, "iqr": 6.5, "unit": "ms", "formula_ref": "Fridericia (1920)", "n_valid": 18},
                "n_beats": 19,
                "partial": False,
                "lead_used": "II",
                "delineation_rate": 0.95
            },
            "flags": [
                {
                    "code": "TACHYCARDIA",
                    "label": "Fréquence cardiaque au-dessus de la normale (118.2 bpm > 100 bpm)",
                    "measured_value": 118.2,
                    "unit": "bpm",
                    "threshold": 100.0,
                    "direction": "above",
                    "severity": "WARNING",
                    "citation": "AHA/ACC (2009) ECG Standardisation. JACC 53(11):976-981."
                },
                {
                    "code": "SHORT_PR",
                    "label": "Intervalle PR court (108.0 ms < 120 ms) - suspicion de pré-excitation",
                    "measured_value": 108.0,
                    "unit": "ms",
                    "threshold": 120.0,
                    "direction": "below",
                    "severity": "WARNING",
                    "citation": "AHA/ACC (2009) ECG Standardisation. JACC 53(11):976-981."
                }
            ]
        },
        # Case 3: URGENT (Wide QRS)
        {
            "code": "URG_QRS",
            "patient_identifier": "IPP-2026-00319",
            "first_name": "Habib",
            "last_name": "Gharbi",
            "birth_date": "1954-11-05",
            "sex": "M",
            "facility_id": "DISP-SFAX-OUEST-02",
            "hr": 66,
            "severity": "URGENT",
            "status": Report.Status.PENDING_REVIEW,
            "intervals": {
                "hr_bpm": {"median": 65.8, "iqr": 1.8, "unit": "bpm", "formula_ref": "60000/RR", "n_valid": 11},
                "pr_ms": {"median": 172.0, "iqr": 5.0, "unit": "ms", "formula_ref": "P_onset to Q_peak", "n_valid": 10},
                "qrs_ms": {"median": 134.5, "iqr": 6.2, "unit": "ms", "formula_ref": "Q_peak to S_peak", "n_valid": 11},
                "qt_ms": {"median": 412.0, "iqr": 7.5, "unit": "ms", "formula_ref": "Q_peak to T_offset", "n_valid": 11},
                "qtc_bazett": {"median": 432.0, "iqr": 7.0, "unit": "ms", "formula_ref": "Bazett (1920)", "n_valid": 11},
                "qtc_fridericia": {"median": 420.0, "iqr": 6.8, "unit": "ms", "formula_ref": "Fridericia (1920)", "n_valid": 11},
                "n_beats": 11,
                "partial": False,
                "lead_used": "II",
                "delineation_rate": 0.94
            },
            "flags": [
                {
                    "code": "WIDE_QRS",
                    "label": "Durée QRS élargie (134.5 ms > 120 ms) - suspicion de bloc de branche",
                    "measured_value": 134.5,
                    "unit": "ms",
                    "threshold": 120.0,
                    "direction": "above",
                    "severity": "WARNING",
                    "citation": "AHA/ACC (2009) ECG Standardisation. JACC 53(11):976-981."
                }
            ]
        },
        # Case 4: ROUTINE (Normal Sinus - Pending)
        {
            "code": "ROUT_NORMAL",
            "patient_identifier": "IPP-2026-02488",
            "first_name": "Nour",
            "last_name": "Ayari",
            "birth_date": "1996-02-17",
            "sex": "F",
            "facility_id": "DISP-TUNIS-NORD-02",
            "hr": 72,
            "severity": "ROUTINE",
            "status": Report.Status.PENDING_REVIEW,
            "intervals": {
                "hr_bpm": {"median": 72.0, "iqr": 2.0, "unit": "bpm", "formula_ref": "60000/RR", "n_valid": 12},
                "pr_ms": {"median": 154.0, "iqr": 4.8, "unit": "ms", "formula_ref": "P_onset to Q_peak", "n_valid": 12},
                "qrs_ms": {"median": 86.0, "iqr": 3.2, "unit": "ms", "formula_ref": "Q_peak to S_peak", "n_valid": 12},
                "qt_ms": {"median": 382.0, "iqr": 6.0, "unit": "ms", "formula_ref": "Q_peak to T_offset", "n_valid": 12},
                "qtc_bazett": {"median": 418.0, "iqr": 6.5, "unit": "ms", "formula_ref": "Bazett (1920)", "n_valid": 12},
                "qtc_fridericia": {"median": 402.0, "iqr": 6.2, "unit": "ms", "formula_ref": "Fridericia (1920)", "n_valid": 12},
                "n_beats": 12,
                "partial": False,
                "lead_used": "II",
                "delineation_rate": 0.98
            },
            "flags": [
                {
                    "code": "NORMAL_SINUS",
                    "label": "Rythme sinusal normal - tous les intervalles mesurés sont physiologiques",
                    "measured_value": 72.0,
                    "unit": "bpm",
                    "threshold": 0.0,
                    "direction": "none",
                    "severity": "INFO",
                    "citation": "AHA/ACC 2009 Guidelines"
                }
            ]
        },
        # Case 5: SIGNED (Bradycardia)
        {
            "code": "SIGN_BRADY",
            "patient_identifier": "IPP-2026-00672",
            "first_name": "Karim",
            "last_name": "Mejri",
            "birth_date": "1974-07-30",
            "sex": "M",
            "facility_id": "DISP-SOUSSE-LITTORAL-01",
            "hr": 54,
            "severity": "URGENT",
            "status": Report.Status.SIGNED,
            "hours_ago": 2,
            "physician_notes": "Bradycardie sinusale modérée (53.8 bpm). Patient asymptomatique, activité sportive régulière. Pas de signe de bloc auriculo-ventriculaire ni d'ischémie. Contrôle de routine dans 12 mois.",
            "intervals": {
                "hr_bpm": {"median": 53.8, "iqr": 1.5, "unit": "bpm", "formula_ref": "60000/RR", "n_valid": 9},
                "pr_ms": {"median": 182.0, "iqr": 5.2, "unit": "ms", "formula_ref": "P_onset to Q_peak", "n_valid": 9},
                "qrs_ms": {"median": 92.0, "iqr": 3.8, "unit": "ms", "formula_ref": "Q_peak to S_peak", "n_valid": 9},
                "qt_ms": {"median": 440.0, "iqr": 7.0, "unit": "ms", "formula_ref": "Q_peak to T_offset", "n_valid": 9},
                "qtc_bazett": {"median": 417.0, "iqr": 6.8, "unit": "ms", "formula_ref": "Bazett (1920)", "n_valid": 9},
                "qtc_fridericia": {"median": 421.0, "iqr": 6.5, "unit": "ms", "formula_ref": "Fridericia (1920)", "n_valid": 9},
                "n_beats": 9,
                "partial": False,
                "lead_used": "II",
                "delineation_rate": 0.97
            },
            "flags": [
                {
                    "code": "BRADYCARDIA",
                    "label": "Fréquence cardiaque sous la normale (53.8 bpm < 60 bpm)",
                    "measured_value": 53.8,
                    "unit": "bpm",
                    "threshold": 60.0,
                    "direction": "below",
                    "severity": "WARNING",
                    "citation": "AHA/ACC (2009) ECG Standardisation. JACC 53(11):976-981."
                }
            ]
        },
        # Case 6: SIGNED (Normal Sinus)
        {
            "code": "SIGN_NORMAL",
            "patient_identifier": "IPP-2026-01893",
            "first_name": "Ines",
            "last_name": "Khmiri",
            "birth_date": "1991-05-14",
            "sex": "F",
            "facility_id": "DISP-TUNIS-CENTRE-04",
            "hr": 70,
            "severity": "ROUTINE",
            "status": Report.Status.SIGNED,
            "hours_ago": 5,
            "physician_notes": "Tracé électrocardiographique strictement physiologique. Repolarisation homogène, pas de trouble du rythme ni de la conduction. Rapport validé pour consultation de médecine préventive.",
            "intervals": {
                "hr_bpm": {"median": 69.5, "iqr": 2.2, "unit": "bpm", "formula_ref": "60000/RR", "n_valid": 11},
                "pr_ms": {"median": 148.0, "iqr": 4.0, "unit": "ms", "formula_ref": "P_onset to Q_peak", "n_valid": 11},
                "qrs_ms": {"median": 84.0, "iqr": 3.0, "unit": "ms", "formula_ref": "Q_peak to S_peak", "n_valid": 11},
                "qt_ms": {"median": 390.0, "iqr": 5.5, "unit": "ms", "formula_ref": "Q_peak to T_offset", "n_valid": 11},
                "qtc_bazett": {"median": 420.0, "iqr": 6.0, "unit": "ms", "formula_ref": "Bazett (1920)", "n_valid": 11},
                "qtc_fridericia": {"median": 408.0, "iqr": 5.8, "unit": "ms", "formula_ref": "Fridericia (1920)", "n_valid": 11},
                "n_beats": 11,
                "partial": False,
                "lead_used": "II",
                "delineation_rate": 0.98
            },
            "flags": [
                {
                    "code": "NORMAL_SINUS",
                    "label": "Rythme sinusal normal - tous les intervalles mesurés sont physiologiques",
                    "measured_value": 69.5,
                    "unit": "bpm",
                    "threshold": 0.0,
                    "direction": "none",
                    "severity": "INFO",
                    "citation": "AHA/ACC 2009 Guidelines"
                }
            ]
        }
    ]

    for c in cases:
        create_case(c, physician)

    print("=== Mock data successfully created! ===")

if __name__ == "__main__":
    run()
