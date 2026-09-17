"""Django integration. Copy the pieces you need into your own app.

This file is a reference, not an importable app: it has no models module and
no app config, so nothing here runs unless you copy it into your project.

Layout that works:

    yourproject/
      ecg_analysis/          <- this package, dropped in as-is
      ecg/                   <- your Django app
        models.py            <- EcgStudy below
        views.py             <- the views below
        urls.py              <- the routes below
"""

# --------------------------------------------------------------- models -----

MODELS = '''
from django.db import models
from django.contrib.auth import get_user_model


class EcgStudy(models.Model):
    """One trip round the medical loop. Every transition is timestamped,
    because the challenge requires showing the delay of each step."""

    class State(models.TextChoices):
        ACQUIRED   = "acquired",   "Acquis"
        ANALYSED   = "analysed",   "Analyse automatique faite"
        REJECTED   = "rejected",   "Rejete, reacquisition requise"
        TRANSMITTED= "transmitted","Transmis au medecin"
        REVIEWING  = "reviewing",  "En cours de lecture"
        SIGNED     = "signed",     "Compte rendu signe"
        DELIVERED  = "delivered",  "Restitue au SIH"

    # identity, verified at acquisition
    patient_id      = models.CharField(max_length=64, db_index=True)
    patient_name    = models.CharField(max_length=128)
    patient_birth   = models.DateField(null=True, blank=True)
    patient_sex     = models.CharField(max_length=1, blank=True)
    identity_verified = models.BooleanField(default=False)
    identity_method = models.CharField(max_length=32, blank=True)  # CIN, bracelet...

    # acquisition
    file            = models.FileField(upload_to="ecg/%Y/%m/")
    file_format     = models.CharField(max_length=8, blank=True)   # wfdb csv edf
    paced           = models.BooleanField(default=False)  # flag from the device
    operator        = models.ForeignKey(get_user_model(), null=True,
                                        on_delete=models.SET_NULL,
                                        related_name="ecg_acquired")

    # automated analysis
    state           = models.CharField(max_length=16, choices=State.choices,
                                       default=State.ACQUIRED, db_index=True)
    analysis        = models.JSONField(null=True, blank=True)   # analyze() output
    report_text     = models.TextField(blank=True)
    triage_level    = models.CharField(max_length=8, blank=True, db_index=True)
    triage_priority = models.IntegerField(null=True, db_index=True)
    escalated       = models.BooleanField(default=False, db_index=True)

    # physician
    reader          = models.ForeignKey(get_user_model(), null=True, blank=True,
                                        on_delete=models.SET_NULL,
                                        related_name="ecg_read")
    physician_report= models.TextField(blank=True)
    signature       = models.CharField(max_length=256, blank=True)

    # loop timestamps
    acquired_at     = models.DateTimeField(auto_now_add=True)
    analysed_at     = models.DateTimeField(null=True, blank=True)
    transmitted_at  = models.DateTimeField(null=True, blank=True)
    opened_at       = models.DateTimeField(null=True, blank=True)
    signed_at       = models.DateTimeField(null=True, blank=True)
    delivered_at    = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["triage_priority", "-acquired_at"]

    @property
    def turnaround_s(self):
        """Acquisition to signature. The metric the challenge is about."""
        if self.signed_at:
            return (self.signed_at - self.acquired_at).total_seconds()
        return None

    def loop_timings(self):
        """Elapsed seconds for each leg of the loop, for the audit view."""
        legs = [("acquisition -> analyse", self.acquired_at, self.analysed_at),
                ("analyse -> transmission", self.analysed_at, self.transmitted_at),
                ("transmission -> ouverture", self.transmitted_at, self.opened_at),
                ("ouverture -> signature", self.opened_at, self.signed_at),
                ("signature -> SIH", self.signed_at, self.delivered_at)]
        return [{"leg": n, "seconds": round((b - a).total_seconds(), 1)}
                for n, a, b in legs if a and b]


class AuditEvent(models.Model):
    """Append-only trail. One row per action, never updated or deleted."""
    study      = models.ForeignKey(EcgStudy, on_delete=models.CASCADE,
                                   related_name="events")
    at         = models.DateTimeField(auto_now_add=True, db_index=True)
    actor      = models.ForeignKey(get_user_model(), null=True,
                                   on_delete=models.SET_NULL)
    action     = models.CharField(max_length=40)
    from_state = models.CharField(max_length=16, blank=True)
    to_state   = models.CharField(max_length=16, blank=True)
    detail     = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["at"]
'''

# ---------------------------------------------------------------- views -----

VIEWS = '''
import os
from django.utils import timezone
from django.db import transaction
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from ecg_analysis import analyze_to_report, EcgReadError
from .models import EcgStudy, AuditEvent


def _audit(study, actor, action, to_state=None, **detail):
    AuditEvent.objects.create(study=study, actor=actor if actor and
                              actor.is_authenticated else None,
                              action=action, from_state=study.state,
                              to_state=to_state or study.state, detail=detail)


@api_view(["POST"])
@parser_classes([MultiPartParser])
def upload_and_analyse(request):
    """Acquisition + quality control + automated analysis, in one call.

    Identity must be verified before the file is accepted: an unidentified
    trace cannot be routed to a physician or returned to the HIS.
    """
    if request.data.get("identity_verified") not in ("true", "True", True, "1", 1):
        return Response({"detail": "identite patient non verifiee"}, status=400)

    f = request.FILES.get("file")
    if not f:
        return Response({"detail": "aucun fichier"}, status=400)

    study = EcgStudy.objects.create(
        patient_id=request.data.get("patient_id", ""),
        patient_name=request.data.get("patient_name", ""),
        patient_sex=(request.data.get("patient_sex") or "")[:1],
        identity_verified=True,
        identity_method=request.data.get("identity_method", ""),
        paced=request.data.get("paced") in ("true", "True", True, "1", 1),
        file=f,
        file_format=os.path.splitext(f.name)[1].lstrip(".").lower(),
        operator=request.user if request.user.is_authenticated else None,
    )
    _audit(study, request.user, "acquisition", EcgStudy.State.ACQUIRED,
           filename=f.name, identity_method=study.identity_method)

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
        return Response({"detail": f"fichier illisible: {e}"}, status=422)

    res = out["result"]
    with transaction.atomic():
        study.analysis = res
        study.report_text = out["report_text"]
        study.analysed_at = timezone.now()
        if not res["ok"] or not res["quality"]["acceptable"]:
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
        _audit(study, request.user, "analyse_automatique", study.state,
               triage=study.triage_level,
               failed_leads=res.get("quality", {}).get("failed_leads", []),
               timings=res["timings"])

    return Response({"study_id": study.id, "state": study.state,
                     "triage": res.get("triage"),
                     "quality": res.get("quality"),
                     "escalated": study.escalated,
                     "blocks": out["report_blocks"]},
                    status=201 if study.state != EcgStudy.State.REJECTED else 200)


@api_view(["POST"])
def transmit(request, pk):
    """Secure handoff to the interpreting physician."""
    study = EcgStudy.objects.get(pk=pk)
    if study.state != EcgStudy.State.ANALYSED:
        return Response({"detail": f"etat invalide: {study.state}"}, status=409)
    study.transmitted_at = timezone.now()
    study.state = EcgStudy.State.TRANSMITTED
    study.save()
    _audit(study, request.user, "transmission", study.state)
    return Response({"state": study.state, "transmitted_at": study.transmitted_at})


@api_view(["GET"])
def open_study(request, pk):
    """Physician opens the trace. Records the read time for the audit."""
    study = EcgStudy.objects.get(pk=pk)
    if not study.opened_at:
        study.opened_at = timezone.now()
        study.state = EcgStudy.State.REVIEWING
        study.reader = request.user if request.user.is_authenticated else None
        study.save()
        _audit(study, request.user, "ouverture", study.state)
    return Response({"study_id": study.id, "state": study.state,
                     "analysis": study.analysis,
                     "draft_report": study.report_text})


@api_view(["POST"])
def sign(request, pk):
    """Physician signs. The draft is theirs to edit; the signature locks it."""
    study = EcgStudy.objects.get(pk=pk)
    text = request.data.get("report") or study.report_text
    sig = request.data.get("signature")
    if not sig:
        return Response({"detail": "signature requise"}, status=400)
    study.physician_report = text
    study.signature = sig
    study.signed_at = timezone.now()
    study.state = EcgStudy.State.SIGNED
    study.save()
    _audit(study, request.user, "signature", study.state,
           turnaround_s=study.turnaround_s)
    return Response({"state": study.state, "signed_at": study.signed_at,
                     "turnaround_s": study.turnaround_s})


@api_view(["POST"])
def deliver_to_his(request, pk):
    """Restitution to the hospital information system.

    Replace the body with your real HL7/FHIR call. The payload below is the
    content a DiagnosticReport resource needs.
    """
    study = EcgStudy.objects.get(pk=pk)
    if study.state != EcgStudy.State.SIGNED:
        return Response({"detail": "compte rendu non signe"}, status=409)
    payload = {
        "resourceType": "DiagnosticReport",
        "status": "final",
        "category": [{"coding": [{"system": "http://loinc.org", "code": "LP29708-2",
                                  "display": "Cardiology"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "11524-6",
                             "display": "EKG study"}]},
        "subject": {"identifier": {"value": study.patient_id}},
        "effectiveDateTime": study.acquired_at.isoformat(),
        "issued": study.signed_at.isoformat(),
        "performer": [{"display": str(study.reader) if study.reader else ""}],
        "conclusion": study.physician_report,
        "conclusionCode": [{"text": f["finding"]}
                           for f in (study.analysis or {}).get("findings", [])
                           if f["severity"] != "GREEN"],
    }
    # ok, err = push_to_his(payload)
    study.delivered_at = timezone.now()
    study.state = EcgStudy.State.DELIVERED
    study.save()
    _audit(study, request.user, "restitution_sih", study.state,
           payload_bytes=len(str(payload)))
    return Response({"state": study.state, "payload": payload,
                     "turnaround_s": study.turnaround_s})


@api_view(["GET"])
def audit(request, pk):
    """Full audit of the medical loop, with the delay of each leg."""
    study = EcgStudy.objects.get(pk=pk)
    return Response({
        "study_id": study.id,
        "patient_id": study.patient_id,
        "state": study.state,
        "identity_verified": study.identity_verified,
        "triage": {"level": study.triage_level, "priority": study.triage_priority,
                   "escalated": study.escalated},
        "turnaround_s": study.turnaround_s,
        "loop_timings": study.loop_timings(),
        "analysis_timings": (study.analysis or {}).get("timings", {}),
        "events": [{"at": e.at, "actor": str(e.actor) if e.actor else None,
                    "action": e.action, "from": e.from_state, "to": e.to_state,
                    "detail": e.detail} for e in study.events.all()],
    })


@api_view(["GET"])
def worklist(request):
    """Physician worklist, urgent first. This is the escalation surface."""
    qs = EcgStudy.objects.exclude(state=EcgStudy.State.DELIVERED)
    return Response([{
        "study_id": s.id, "patient_id": s.patient_id, "state": s.state,
        "triage": s.triage_level, "priority": s.triage_priority,
        "escalated": s.escalated, "acquired_at": s.acquired_at,
        "waiting_s": round((timezone.now() - s.acquired_at).total_seconds(), 0),
    } for s in qs])
'''

URLS = '''
from django.urls import path
from . import views

urlpatterns = [
    path("ecg/",                     views.upload_and_analyse),
    path("ecg/worklist/",            views.worklist),
    path("ecg/<int:pk>/transmit/",   views.transmit),
    path("ecg/<int:pk>/open/",       views.open_study),
    path("ecg/<int:pk>/sign/",       views.sign),
    path("ecg/<int:pk>/deliver/",    views.deliver_to_his),
    path("ecg/<int:pk>/audit/",      views.audit),
]
'''

if __name__ == "__main__":
    import sys
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    for name, code in (("models", MODELS), ("views", VIEWS), ("urls", URLS)):
        if which in ("all", name):
            print(f"# ===== {name}.py " + "=" * 50)
            print(code)
