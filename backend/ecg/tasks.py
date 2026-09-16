"""Celery task: run the full ECG processing pipeline asynchronously."""

import logging
import time

from celery import shared_task
from django.utils import timezone

from audit.models import AuditLog, AuditAction

logger = logging.getLogger("ecg.pipeline")


@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def process_ecg_task(self, record_id: int) -> dict:
    """
    Full pipeline: load → preprocess → delineate → intervals → rules → save result.

    Args:
        record_id: PK of an ECGRecord with status=PENDING.

    Returns:
        dict with severity and flag count.
    """
    from ecg.models import ECGRecord, ProcessingResult
    from ecg.pipeline import (
        load_ecg, preprocess, delineate, compute_intervals,
        apply_rules, severity_summary,
    )
    from reports.models import Report
    from reports.utils import generate_draft

    start = time.monotonic()

    try:
        record = ECGRecord.objects.get(pk=record_id)
    except ECGRecord.DoesNotExist:
        logger.error("process_ecg_task: ECGRecord %d not found.", record_id)
        return {"error": "record not found"}

    # ── Mark as PROCESSING ────────────────────────────────────────────────────
    record.status = ECGRecord.Status.PROCESSING
    record.save(update_fields=["status", "updated_at"])

    AuditLog.log(
        action=AuditAction.PROCESS_START,
        target_type="ECGRecord",
        target_id=record_id,
        extra={"fmt": record.fmt},
    )

    try:
        # ── 1. Load ───────────────────────────────────────────────────────────
        signals, fs, metadata = load_ecg(record.file.path, record.fmt)

        record.fs = fs
        record.lead_count = signals.shape[0]
        record.save(update_fields=["fs", "lead_count", "updated_at"])

        # ── 2. Preprocess ─────────────────────────────────────────────────────
        signals_clean = preprocess(signals, fs)

        # ── 3. Delineate ──────────────────────────────────────────────────────
        delineation = delineate(signals_clean, fs)

        # ── 4. Intervals ──────────────────────────────────────────────────────
        intervals = compute_intervals(delineation, fs)

        # ── 5. Rule engine ────────────────────────────────────────────────────
        sex = record.patient.sex
        flags = apply_rules(intervals, sex)
        severity = severity_summary(flags)

        # ── 6. Save ProcessingResult ──────────────────────────────────────────
        result = ProcessingResult.objects.create(
            record=record,
            intervals_json=intervals.to_dict(),
            flags_json=[f.to_dict() for f in flags],
            severity=severity,
            lead_used=delineation["lead_used"],
            partial=delineation["partial"],
        )

        # ── 7. Create draft Report ────────────────────────────────────────────
        draft_text = generate_draft(flags)
        Report.objects.create(
            result=result,
            draft_text=draft_text,
            severity=severity,
            status=Report.Status.PENDING_REVIEW,
        )

        # ── 8. Mark as DONE ───────────────────────────────────────────────────
        record.status = ECGRecord.Status.DONE
        record.save(update_fields=["status", "updated_at"])

        elapsed_ms = round((time.monotonic() - start) * 1000)

        AuditLog.log(
            action=AuditAction.PROCESS_DONE,
            target_type="ECGRecord",
            target_id=record_id,
            extra={
                "severity": severity,
                "flag_codes": [f["code"] for f in result.flags_json],
                "n_beats": intervals.n_beats,
                "lead_used": delineation["lead_used"],
                "partial": delineation["partial"],
                "elapsed_ms": elapsed_ms,
            },
        )

        logger.info(
            "ECG %d processed in %d ms — severity=%s, flags=%d.",
            record_id, elapsed_ms, severity, len(flags),
        )
        return {"severity": severity, "flag_count": len(flags), "elapsed_ms": elapsed_ms}

    except Exception as exc:
        record.status = ECGRecord.Status.ERROR
        record.error_message = str(exc)[:2000]
        record.save(update_fields=["status", "error_message", "updated_at"])

        AuditLog.log(
            action=AuditAction.PROCESS_ERROR,
            target_type="ECGRecord",
            target_id=record_id,
            extra={"error": str(exc)[:500]},
        )

        logger.exception("ECG %d processing failed: %s", record_id, exc)

        # Retry up to max_retries
        raise self.retry(exc=exc)
