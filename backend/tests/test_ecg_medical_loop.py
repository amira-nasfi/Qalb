import os
import time
import tempfile
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from ecg.models import EcgStudy
from accounts.models import Role

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def ecg_csv_bytes():
    sample_path = os.path.join(settings.MEDIA_ROOT, "ecg_uploads", "sim_sign_normal_69909464.csv")
    if os.path.exists(sample_path):
        with open(sample_path, "rb") as f:
            return f.read()
    else:
        from scripts.smoke_ecg import make_synthetic_csv
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tf:
            tmp_p = tf.name
        make_synthetic_csv(tmp_p, duration_s=10, fs=500)
        with open(tmp_p, "rb") as f:
            data = f.read()
        os.unlink(tmp_p)
        return data


@pytest.mark.django_db
def test_full_medical_loop(api_client, ecg_csv_bytes):
    """
    Test the entire 7-stage medical loop:
    1. Acquisition (upload + verified identity)
    2. Synchronous Automated Analysis & QC
    3. Transmission to physician
    4. Physician opens study (recorded in audit)
    5. Waveform retrieval (250 Hz downsampled raw signals + overlay_scale_factor)
    6. Physician signs report (locks report, turnaround_s computed)
    7. Simulated HIS delivery failure (locked state, error in audit)
    8. Successful HIS delivery (FHIR DiagnosticReport)
    9. Complete loop audit trail validation
    """
    # Create actors
    field_agent = User.objects.create_user(
        username="agent_loop",
        email="agent_loop@example.com",
        password="password123",
        role=Role.FIELD_AGENT,
    )
    physician = User.objects.create_user(
        username="doc_loop",
        email="doc_loop@example.com",
        password="password123",
        role=Role.PHYSICIAN,
    )

    # 1. Acquisition + Automated Analysis
    api_client.force_authenticate(user=field_agent)
    f = SimpleUploadedFile("loop_trace.csv", ecg_csv_bytes, content_type="text/csv")
    upload_resp = api_client.post(
        "/api/ecg/studies/",
        {
            "file": f,
            "identity_verified": "true",
            "identity_method": "CIN",
            "patient_id": "PAT-LOOP-001",
            "patient_name": "Tahar Haddad",
            "patient_sex": "M",
            "age": "45",
            "fs": "500",
        },
        format="multipart",
    )
    assert upload_resp.status_code in (200, 201), f"Upload failed: {upload_resp.data}"
    study_id = upload_resp.data["study_id"]
    study = EcgStudy.objects.get(pk=study_id)
    assert study.state in (EcgStudy.State.ANALYSED, EcgStudy.State.REJECTED)
    assert study.events.filter(action="acquisition").exists()
    assert study.events.filter(action="analyse_automatique").exists()

    # Ensure study is in ANALYSED state for transmission
    if study.state != EcgStudy.State.ANALYSED:
        study.state = EcgStudy.State.ANALYSED
        study.save()

    # Small delay to ensure positive timedelta for timestamps
    time.sleep(0.05)

    # 2. Transmission to physician
    trans_resp = api_client.post(f"/api/ecg/studies/{study_id}/transmit/")
    assert trans_resp.status_code == 200
    assert trans_resp.data["state"] == EcgStudy.State.TRANSMITTED
    study.refresh_from_db()
    assert study.state == EcgStudy.State.TRANSMITTED
    assert study.transmitted_at is not None

    time.sleep(0.05)

    # 3. Physician opens study
    api_client.force_authenticate(user=physician)
    open_resp = api_client.get(f"/api/ecg/studies/{study_id}/open/")
    assert open_resp.status_code == 200
    assert open_resp.data["state"] == EcgStudy.State.REVIEWING
    study.refresh_from_db()
    assert study.state == EcgStudy.State.REVIEWING
    assert study.reader == physician
    assert study.opened_at is not None

    # 4. Waveform endpoint
    wave_resp = api_client.get(f"/api/ecg/studies/{study_id}/waveform/")
    assert wave_resp.status_code == 200
    assert wave_resp.data["raw"] is True
    assert round(wave_resp.data["fs"]) == 250
    assert "II" in wave_resp.data["samples"]
    assert "overlay_scale_factor" in wave_resp.data

    time.sleep(0.05)

    # 5. Physician signs report
    sign_resp = api_client.post(
        f"/api/ecg/studies/{study_id}/sign/",
        {
            "report": "Rythme sinusal régulier, pas d'anomalie de repolarisation.",
            "signature": "Dr. Loop MD — Cardiologue",
        },
    )
    assert sign_resp.status_code == 200
    assert sign_resp.data["state"] == EcgStudy.State.SIGNED
    study.refresh_from_db()
    assert study.state == EcgStudy.State.SIGNED
    assert study.signed_at is not None
    assert study.turnaround_s is not None
    assert study.turnaround_s >= 0

    # 6. Simulated HIS delivery failure (settings.ECG_DEMO_MODE=True)
    fail_resp = api_client.post(f"/api/ecg/studies/{study_id}/deliver/?simulate_failure=1")
    assert fail_resp.status_code == 502
    study.refresh_from_db()
    assert study.state == EcgStudy.State.SIGNED  # Locked at SIGNED
    assert study.events.filter(action="erreur_transmission").exists()

    # 7. Successful delivery to HIS
    ok_resp = api_client.post(f"/api/ecg/studies/{study_id}/deliver/")
    assert ok_resp.status_code == 200
    assert ok_resp.data["state"] == EcgStudy.State.DELIVERED
    study.refresh_from_db()
    assert study.state == EcgStudy.State.DELIVERED
    assert study.delivered_at is not None
    assert ok_resp.data["payload"]["resourceType"] == "DiagnosticReport"

    # 8. Complete audit verification
    audit_resp = api_client.get(f"/api/ecg/studies/{study_id}/audit/")
    assert audit_resp.status_code == 200
    audit_data = audit_resp.data
    assert audit_data["state"] == EcgStudy.State.DELIVERED
    assert audit_data["turnaround_s"] is not None
    assert audit_data["turnaround_s"] >= 0

    actions = [e["action"] for e in audit_data["events"]]
    expected_actions = [
        "acquisition",
        "analyse_automatique",
        "transmission",
        "ouverture",
        "signature",
        "erreur_transmission",
        "restitution_sih",
    ]
    for exp in expected_actions:
        assert exp in actions, f"Missing audit action: {exp}"

    # Loop timings contain measured delays for each leg
    timings = audit_data["loop_timings"]
    assert len(timings) >= 4
