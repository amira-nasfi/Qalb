import os
import tempfile
from django.test import TestCase, override_settings
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from ecg.models import EcgStudy
from accounts.models import Role

User = get_user_model()


class EcgStudyWorkflowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.field_agent = User.objects.create_user(
            username="agent1",
            email="agent1@example.com",
            password="password123",
            role=Role.FIELD_AGENT,
        )
        self.physician = User.objects.create_user(
            username="doc1",
            email="doc1@example.com",
            password="password123",
            role=Role.PHYSICIAN,
        )
        self.admin = User.objects.create_superuser(
            username="admin1",
            email="admin1@example.com",
            password="password123",
            role=Role.ADMIN,
        )

        # Use existing valid simulated CSV file or generate with neurokit2
        sample_path = os.path.join(settings.MEDIA_ROOT, "ecg_uploads", "sim_sign_normal_69909464.csv")
        if os.path.exists(sample_path):
            with open(sample_path, "rb") as f:
                self.csv_content = f.read()
        else:
            from scripts.smoke_ecg import make_synthetic_csv
            with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tf:
                tmp_p = tf.name
            make_synthetic_csv(tmp_p, duration_s=10, fs=500)
            with open(tmp_p, "rb") as f:
                self.csv_content = f.read()
            os.unlink(tmp_p)

    def test_1_upload_unverified_identity_rejected(self):
        """Uploading without verified patient identity must fail with HTTP 400."""
        self.client.force_authenticate(user=self.field_agent)
        f = SimpleUploadedFile("test_ecg.csv", self.csv_content, content_type="text/csv")
        resp = self.client.post(
            "/api/ecg/studies/",
            {"file": f, "identity_verified": "false", "patient_id": "P-101"},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("identite", resp.data["detail"])

    def test_2_upload_and_analyse_valid_ecg(self):
        """Valid upload runs analysis synchronously and records audit trail."""
        self.client.force_authenticate(user=self.field_agent)
        f = SimpleUploadedFile("test_ecg.csv", self.csv_content, content_type="text/csv")
        resp = self.client.post(
            "/api/ecg/studies/",
            {
                "file": f,
                "identity_verified": "true",
                "patient_id": "P-101",
                "patient_name": "Test Patient",
                "fs": "500",
                "identity_method": "CIN",
            },
            format="multipart",
        )
        self.assertIn(resp.status_code, (200, 201))
        study_id = resp.data["study_id"]
        study = EcgStudy.objects.get(pk=study_id)
        self.assertIn(study.state, (EcgStudy.State.ANALYSED, EcgStudy.State.REJECTED))
        self.assertTrue(study.events.filter(action="analyse_automatique").exists())

    def test_3_waveform_endpoint_raw_samples(self):
        """Waveform endpoint returns raw samples downsampled to 250 Hz with metadata."""
        self.client.force_authenticate(user=self.field_agent)
        f = SimpleUploadedFile("test_ecg.csv", self.csv_content, content_type="text/csv")
        upload_resp = self.client.post(
            "/api/ecg/studies/",
            {"file": f, "identity_verified": "true", "patient_id": "P-102", "fs": "500"},
            format="multipart",
        )
        study_id = upload_resp.data["study_id"]

        self.client.force_authenticate(user=self.physician)
        study = EcgStudy.objects.get(pk=study_id)
        study.state = EcgStudy.State.TRANSMITTED
        study.save()

        wave_resp = self.client.get(f"/api/ecg/studies/{study_id}/waveform/")
        self.assertEqual(wave_resp.status_code, 200, getattr(wave_resp, "data", None))
        self.assertTrue(wave_resp.data["raw"])
        self.assertEqual(wave_resp.data["fs"], 250.0)
        self.assertIn("II", wave_resp.data["samples"])
        self.assertIn("overlay_scale_factor", wave_resp.data)

    def test_4_transmission_and_open_study(self):
        """Transmitting advances state to TRANSMITTED, physician opening advances to REVIEWING."""
        study = EcgStudy.objects.create(
            patient_id="P-103",
            patient_name="Patient Transmit",
            identity_verified=True,
            state=EcgStudy.State.ANALYSED,
            file=SimpleUploadedFile("dummy.csv", self.csv_content),
        )
        self.client.force_authenticate(user=self.admin)
        trans_resp = self.client.post(f"/api/ecg/studies/{study.pk}/transmit/")
        self.assertEqual(trans_resp.status_code, 200)
        study.refresh_from_db()
        self.assertEqual(study.state, EcgStudy.State.TRANSMITTED)
        self.assertIsNotNone(study.transmitted_at)

        # Physician opens
        self.client.force_authenticate(user=self.physician)
        open_resp = self.client.get(f"/api/ecg/studies/{study.pk}/open/")
        self.assertEqual(open_resp.status_code, 200)
        study.refresh_from_db()
        self.assertEqual(study.state, EcgStudy.State.REVIEWING)
        self.assertEqual(study.reader, self.physician)

    def test_5_sign_study_validations(self):
        """Signature locks report and records turnaround_s metric."""
        study = EcgStudy.objects.create(
            patient_id="P-104",
            patient_name="Patient Sign",
            identity_verified=True,
            state=EcgStudy.State.REVIEWING,
            reader=self.physician,
            report_text="Initial Draft",
            file=SimpleUploadedFile("dummy.csv", self.csv_content),
        )
        self.client.force_authenticate(user=self.physician)

        # Missing signature
        bad_resp = self.client.post(f"/api/ecg/studies/{study.pk}/sign/", {"report": "Final text"})
        self.assertEqual(bad_resp.status_code, 400)

        # Valid signature
        good_resp = self.client.post(
            f"/api/ecg/studies/{study.pk}/sign/",
            {"report": "ECG Normal validé", "signature": "Dr. House MD"},
        )
        self.assertEqual(good_resp.status_code, 200)
        study.refresh_from_db()
        self.assertEqual(study.state, EcgStudy.State.SIGNED)
        self.assertIsNotNone(study.signed_at)
        self.assertGreaterEqual(study.turnaround_s, 0)

    @override_settings(ECG_DEMO_MODE=True)
    def test_6_deliver_simulation_and_success(self):
        """Simulated failure logs erreur_transmission and returns 502; real delivery returns 200 DELIVERED."""
        study = EcgStudy.objects.create(
            patient_id="P-105",
            patient_name="Patient Deliver",
            identity_verified=True,
            state=EcgStudy.State.SIGNED,
            reader=self.physician,
            physician_report="Confirmed Normal",
            signature="Dr. House MD",
            file=SimpleUploadedFile("dummy.csv", self.csv_content),
        )
        self.client.force_authenticate(user=self.admin)

        # Simulated failure
        fail_resp = self.client.post(f"/api/ecg/studies/{study.pk}/deliver/?simulate_failure=1")
        self.assertEqual(fail_resp.status_code, 502)
        study.refresh_from_db()
        self.assertEqual(study.state, EcgStudy.State.SIGNED)  # state stays locked
        self.assertTrue(study.events.filter(action="erreur_transmission").exists())

        # Successful delivery
        ok_resp = self.client.post(f"/api/ecg/studies/{study.pk}/deliver/")
        self.assertEqual(ok_resp.status_code, 200)
        study.refresh_from_db()
        self.assertEqual(study.state, EcgStudy.State.DELIVERED)
        self.assertEqual(ok_resp.data["payload"]["resourceType"], "DiagnosticReport")
        self.assertTrue(study.events.filter(action="restitution_sih").exists())
