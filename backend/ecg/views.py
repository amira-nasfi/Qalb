import os
import numpy as np
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from ecg_analysis import analyze_to_report, EcgReadError, read_any
from patients.models import Patient
from accounts.models import Role
from .models import EcgStudy, AuditEvent, ECGRecord, ProcessingResult
from .permissions import CanAccessEcgStudy


def _audit(study, actor, action, to_state=None, **detail):
    AuditEvent.objects.create(
        study=study,
        actor=actor if actor and actor.is_authenticated else None,
        action=action,
        from_state=study.state,
        to_state=to_state or study.state,
        detail=detail,
    )


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
@permission_classes([permissions.IsAuthenticated])
def upload_and_analyse(request):
    """
    Acquisition + quality control + automated analysis, in one synchronous call.
    Identity must be verified before the file is accepted: an unidentified
    trace cannot be routed to a physician or returned to the HIS.
    """
    identity_verified_val = request.data.get("identity_verified")
    if identity_verified_val not in ("true", "True", True, "1", 1):
        return Response({"detail": "identite patient non verifiee"}, status=status.HTTP_400_BAD_REQUEST)

    f = request.FILES.get("file")
    if not f:
        return Response({"detail": "aucun fichier"}, status=status.HTTP_400_BAD_REQUEST)

    patient_id = request.data.get("patient_id") or request.data.get("pseudo_id", "")
    patient_name = request.data.get("patient_name", "")
    patient_sex = (request.data.get("patient_sex") or request.data.get("sex") or "")[:1]

    # Resolve from patient database if exists
    if patient_id:
        try:
            pat = Patient.objects.filter(pseudo_id=patient_id).first()
            if not pat and str(patient_id).isdigit():
                pat = Patient.objects.filter(id=int(patient_id)).first()
            if pat:
                if not patient_name:
                    patient_name = f"{pat.first_name} {pat.last_name}".strip()
                if not patient_sex:
                    patient_sex = (pat.sex or "")[:1]
        except Exception:
            pass

    study = EcgStudy.objects.create(
        patient_id=str(patient_id),
        patient_name=patient_name or "Patient Inconnu",
        patient_sex=patient_sex,
        identity_verified=True,
        identity_method=request.data.get("identity_method", "Dossier National"),
        paced=request.data.get("paced") in ("true", "True", True, "1", 1),
        file=f,
        file_format=os.path.splitext(f.name)[1].lstrip(".").lower() or "csv",
        operator=request.user if request.user.is_authenticated else None,
    )
    _audit(
        study,
        request.user,
        "acquisition",
        EcgStudy.State.ACQUIRED,
        filename=f.name,
        identity_method=study.identity_method,
    )

    try:
        out = analyze_to_report(
            study.file.path,
            fs=float(request.data["fs"]) if request.data.get("fs") else None,
            age=float(request.data["age"]) if request.data.get("age") else None,
            sex=study.patient_sex or None,
            paced=study.paced,
            patient_id=study.patient_id,
        )
    except EcgReadError as e:
        _audit(study, request.user, "erreur_lecture", detail=str(e))
        return Response({"detail": f"fichier illisible: {e}"}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

    res = out["result"]
    with transaction.atomic():
        study.analysis = res
        study.report_text = out["report_text"]
        study.analysed_at = timezone.now()
        if not res.get("ok") or not res.get("quality", {}).get("acceptable"):
            study.state = EcgStudy.State.REJECTED
            study.escalated = True
            study.triage_level = "REJET"
            study.triage_priority = 0
        else:
            study.state = EcgStudy.State.ANALYSED
            study.triage_level = res["triage"]["level"]
            study.triage_priority = res["triage"]["priority"]
            study.escalated = res["triage"]["escalate"]
        study.save()
        _audit(
            study,
            request.user,
            "analyse_automatique",
            study.state,
            triage=study.triage_level,
            failed_leads=res.get("quality", {}).get("failed_leads", []),
            timings=res.get("timings", {}),
        )

    return Response(
        {
            "study_id": study.id,
            "state": study.state,
            "triage": res.get("triage"),
            "quality": res.get("quality"),
            "escalated": study.escalated,
            "blocks": out["report_blocks"],
        },
        status=status.HTTP_201_CREATED if study.state != EcgStudy.State.REJECTED else status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, CanAccessEcgStudy])
def study_detail(request, pk):
    study = get_object_or_404(EcgStudy, pk=pk)
    perm = CanAccessEcgStudy()
    if not perm.has_object_permission(request, None, study):
        return Response({"detail": "Permission refusee"}, status=status.HTTP_403_FORBIDDEN)
    return Response({
        "study_id": study.id,
        "patient_id": study.patient_id,
        "patient_name": study.patient_name,
        "patient_birth": study.patient_birth,
        "patient_sex": study.patient_sex,
        "identity_verified": study.identity_verified,
        "identity_method": study.identity_method,
        "file_format": study.file_format,
        "paced": study.paced,
        "state": study.state,
        "triage": {
            "level": study.triage_level,
            "priority": study.triage_priority,
            "escalated": study.escalated,
        },
        # Flat aliases — required by ReviewPage and DoctorPortalPage
        "triage_level": study.triage_level,
        "triage_priority": study.triage_priority,
        "escalated": study.escalated,
        "analysis": study.analysis,
        "report_text": study.report_text,
        "physician_report": study.physician_report,
        "signature": study.signature,
        "turnaround_s": study.turnaround_s,
        "loop_timings": study.loop_timings(),
        "acquired_at": study.acquired_at,
        "analysed_at": study.analysed_at,
        "transmitted_at": study.transmitted_at,
        "opened_at": study.opened_at,
        "signed_at": study.signed_at,
        "delivered_at": study.delivered_at,
    })


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, CanAccessEcgStudy])
def waveform(request, pk):
    """
    Serve raw 12-lead signal downsampled to 250 Hz with 3 decimal precision.
    Includes overlay_scale_factor for frontend PQRST mapping.
    """
    study = get_object_or_404(EcgStudy, pk=pk)
    perm = CanAccessEcgStudy()
    if not perm.has_object_permission(request, None, study):
        return Response({"detail": "Permission refusee"}, status=status.HTTP_403_FORBIDDEN)

    req_fs = None
    if request.query_params.get("fs"):
        try:
            req_fs = float(request.query_params["fs"])
        except Exception:
            pass
    elif study.analysis and isinstance(study.analysis, dict):
        req_fs = study.analysis.get("acquisition", {}).get("fs_in_hz")
    if not req_fs:
        req_fs = 500.0

    try:
        signal, fs, lead_names, _ = read_any(study.file.path, fs=req_fs, unit="mV")
    except Exception as exc:
        return Response({"detail": f"Erreur de lecture du signal: {exc}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    step = max(1, int(round(fs / 250.0)))
    out = {name: [round(float(v), 3) for v in signal[i, ::step]]
           for i, name in enumerate(lead_names)}
    effective_fs = fs / step

    return Response({
        "study_id": study.id,
        "fs": effective_fs,
        "leads": lead_names,
        "samples": out,
        "n_samples": len(next(iter(out.values()))) if out else 0,
        "overlay_scale_factor": 500.0 / effective_fs,
        "raw": True,
    })


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated, CanAccessEcgStudy])
def transmit(request, pk):
    """Secure handoff to the interpreting physician."""
    study = get_object_or_404(EcgStudy, pk=pk)
    perm = CanAccessEcgStudy()
    if not perm.has_object_permission(request, None, study):
        return Response({"detail": "Permission refusee"}, status=status.HTTP_403_FORBIDDEN)

    if study.state != EcgStudy.State.ANALYSED:
        return Response({"detail": f"etat invalide: {study.state}"}, status=status.HTTP_409_CONFLICT)

    study.transmitted_at = timezone.now()
    study.state = EcgStudy.State.TRANSMITTED
    study.save()
    _audit(study, request.user, "transmission", study.state)
    return Response({"state": study.state, "transmitted_at": study.transmitted_at})


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, CanAccessEcgStudy])
def open_study(request, pk):
    """Physician opens the trace. Records the read time for the audit."""
    study = get_object_or_404(EcgStudy, pk=pk)
    perm = CanAccessEcgStudy()
    if not perm.has_object_permission(request, None, study):
        return Response({"detail": "Permission refusee"}, status=status.HTTP_403_FORBIDDEN)

    is_physician = getattr(request.user, "role", None) == Role.PHYSICIAN or request.user.is_staff
    if not study.opened_at and is_physician:
        study.opened_at = timezone.now()
        study.state = EcgStudy.State.REVIEWING
        study.reader = request.user
        study.save()
        _audit(study, request.user, "ouverture", study.state)

    return Response({
        "study_id": study.id,
        "state": study.state,
        "analysis": study.analysis,
        "draft_report": study.report_text,
        "reader": str(study.reader) if study.reader else None,
    })


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated, CanAccessEcgStudy])
def sign(request, pk):
    """Physician signs. The draft is theirs to edit; the signature locks it."""
    if getattr(request.user, "role", None) != Role.PHYSICIAN and not request.user.is_staff and not request.user.is_superuser:
        return Response({"detail": "Seul un médecin télé-expert habilité peut valider et signer l'examen."}, status=status.HTTP_403_FORBIDDEN)

    study = get_object_or_404(EcgStudy, pk=pk)
    perm = CanAccessEcgStudy()
    if not perm.has_object_permission(request, None, study):
        return Response({"detail": "Permission refusee"}, status=status.HTTP_403_FORBIDDEN)

    if study.state not in (EcgStudy.State.REVIEWING, EcgStudy.State.TRANSMITTED):
        return Response({"detail": f"etat invalide pour signature: {study.state}"}, status=status.HTTP_409_CONFLICT)

    text = request.data.get("report") or ""
    sig = request.data.get("signature")
    if not sig:
        return Response({"detail": "signature requise"}, status=status.HTTP_400_BAD_REQUEST)

    study.physician_report = text
    study.signature = sig
    study.signed_at = timezone.now()
    study.state = EcgStudy.State.SIGNED
    if not study.reader and request.user.is_authenticated:
        study.reader = request.user
    study.save()
    _audit(
        study,
        request.user,
        "signature",
        study.state,
        turnaround_s=study.turnaround_s,
    )
    return Response({
        "state": study.state,
        "signed_at": study.signed_at,
        "turnaround_s": study.turnaround_s,
    })


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated, CanAccessEcgStudy])
def deliver_to_his(request, pk):
    """
    Restitution to the Hospital Information System (FHIR DiagnosticReport).
    Simulated failure is gated behind settings.ECG_DEMO_MODE.
    """
    study = get_object_or_404(EcgStudy, pk=pk)
    perm = CanAccessEcgStudy()
    if not perm.has_object_permission(request, None, study):
        return Response({"detail": "Permission refusee"}, status=status.HTTP_403_FORBIDDEN)

    if study.state != EcgStudy.State.SIGNED:
        return Response({"detail": "compte rendu non signe"}, status=status.HTTP_409_CONFLICT)

    simulate_failure = (
        request.query_params.get("simulate_failure") in ("1", "true", "True")
        or request.headers.get("X-Simulate-Error") in ("1", "true", "True")
    )

    demo_mode = getattr(settings, "ECG_DEMO_MODE", True)
    if simulate_failure and demo_mode:
        error_detail = {
            "phase": "restitution_sih",
            "endpoint": "https://his.hospital.local/fhir/DiagnosticReport",
            "http_status": 504,
            "error": "Gateway Timeout: Remote HIS server unreachable after 5000ms",
            "attempt": 1,
            "simulated": True,
        }
        _audit(study, request.user, "erreur_transmission", study.state, **error_detail)
        return Response(
            {"detail": "Échec de restitution SIH (504 Gateway Timeout)", "error": error_detail},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    payload = {
        "resourceType": "DiagnosticReport",
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "LP29708-2",
                        "display": "Cardiology",
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "11524-6",
                    "display": "EKG study",
                }
            ]
        },
        "subject": {"identifier": {"value": study.patient_id}},
        "effectiveDateTime": study.acquired_at.isoformat() if study.acquired_at else timezone.now().isoformat(),
        "issued": study.signed_at.isoformat() if study.signed_at else timezone.now().isoformat(),
        "performer": [{"display": str(study.reader) if study.reader else ""}],
        "conclusion": study.physician_report,
        "conclusionCode": [
            {"text": f["finding"]}
            for f in (study.analysis or {}).get("findings", [])
            if f.get("severity") != "GREEN"
        ],
    }

    study.delivered_at = timezone.now()
    study.state = EcgStudy.State.DELIVERED
    study.save()
    _audit(
        study,
        request.user,
        "restitution_sih",
        study.state,
        payload_bytes=len(str(payload)),
    )
    return Response({
        "state": study.state,
        "payload": payload,
        "turnaround_s": study.turnaround_s,
    })


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, CanAccessEcgStudy])
def audit(request, pk):
    """Full audit of the medical loop, with the delay of each leg."""
    study = get_object_or_404(EcgStudy, pk=pk)
    perm = CanAccessEcgStudy()
    if not perm.has_object_permission(request, None, study):
        return Response({"detail": "Permission refusee"}, status=status.HTTP_403_FORBIDDEN)

    return Response({
        "study_id": study.id,
        "patient_id": study.patient_id,
        "patient_name": study.patient_name,
        "state": study.state,
        "identity_verified": study.identity_verified,
        "triage": {
            "level": study.triage_level,
            "priority": study.triage_priority,
            "escalated": study.escalated,
        },
        "turnaround_s": study.turnaround_s,
        "loop_timings": study.loop_timings(),
        "analysis_timings": (study.analysis or {}).get("timings", {}),
        "events": [
            {
                "at": e.at.isoformat(),
                "actor": str(e.actor) if e.actor else None,
                "action": e.action,
                "from": e.from_state,
                "to": e.to_state,
                "detail": e.detail,
            }
            for e in study.events.all()
        ],
    })


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def loop_audit_summary(request):
    """
    Admin view: returns all studies with their medical loop timing summary.
    GET /api/ecg/studies/loop-audit/
    Restricted to admin and physician roles.
    """
    from accounts.models import Role
    role = getattr(request.user, "role", None)
    if not (getattr(request.user, "is_superuser", False) or role in (Role.ADMIN, Role.PHYSICIAN)):
        return Response({"detail": "Accès réservé aux administrateurs et médecins."}, status=status.HTTP_403_FORBIDDEN)

    qs = EcgStudy.objects.order_by("-acquired_at")[:100]
    results = []
    for s in qs:
        results.append({
            "study_id": s.id,
            "patient_id": s.patient_id,
            "patient_name": s.patient_name,
            "state": s.state,
            "triage_level": s.triage_level,
            "triage_priority": s.triage_priority,
            "escalated": s.escalated,
            "acquired_at": s.acquired_at.isoformat() if s.acquired_at else None,
            "analysed_at": s.analysed_at.isoformat() if s.analysed_at else None,
            "transmitted_at": s.transmitted_at.isoformat() if s.transmitted_at else None,
            "read_at": s.read_at.isoformat() if s.read_at else None,
            "signed_at": s.signed_at.isoformat() if s.signed_at else None,
            "turnaround_s": s.turnaround_s,
            "loop_timings": s.loop_timings(),
            "event_count": s.events.count(),
        })
    return Response(results)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def worklist(request):
    """Physician worklist, urgent first. This is the escalation surface."""
    qs = EcgStudy.objects.exclude(state=EcgStudy.State.DELIVERED).order_by("triage_priority", "-acquired_at")
    return Response([
        {
            "study_id": s.id,
            "patient_id": s.patient_id,
            "patient_name": s.patient_name,
            "state": s.state,
            "triage": s.triage_level,
            "priority": s.triage_priority,
            "escalated": s.escalated,
            "acquired_at": s.acquired_at.isoformat() if s.acquired_at else None,
            "waiting_s": round((timezone.now() - s.acquired_at).total_seconds(), 0) if s.acquired_at else 0,
        }
        for s in qs
    ])


# Deprecated legacy views kept for backward compatibility if needed
class ECGUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        return Response(
            {"detail": "Deprecated endpoint. Use /api/ecg/studies/ instead."},
            status=status.HTTP_410_GONE,
        )


class ECGStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return Response(
            {"detail": "Deprecated endpoint."},
            status=status.HTTP_410_GONE,
        )


class ECGResultView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return Response(
            {"detail": "Deprecated endpoint. Use /api/ecg/studies/<pk>/ instead."},
            status=status.HTTP_410_GONE,
        )


class ECGSignalView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, record_id):
        # Forward to waveform if record exists
        study = EcgStudy.objects.filter(pk=record_id).first()
        if study:
            return waveform(request._request, pk=record_id)
        return Response({"error": "Study not found"}, status=status.HTTP_404_NOT_FOUND)
