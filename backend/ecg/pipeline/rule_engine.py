"""
Deterministic ECG rule engine — Qalb قلب.

Every Flag produced by this engine carries:
  - code            : machine-readable rule identifier
  - label           : human-readable description
  - measured_value  : the actual computed value (never hidden)
  - unit            : "ms" or "bpm"
  - threshold       : the clinical threshold crossed
  - direction       : "above" or "below"
  - severity        : "INFO" / "WARNING" / "CRITICAL"
  - citation        : primary literature or guideline reference

NO rule may produce a flag without a measured_value and a citation.
NO rule uses a model weight, an opaque score, or a trained classifier.

References:
  - AHA/ACC (2009): Recommendations for the Standardization and Interpretation
    of the Electrocardiogram. JACC, 53(11):976–981.
  - Rautaharju PM et al. (1992): Normal standards for duration and amplitude of
    QT and QTc intervals. JACC, 20(6):1371–1377.
  - ESC (2022): 2022 ESC Guidelines for the management of patients with
    ventricular arrhythmias and the prevention of sudden cardiac death.
    Eur Heart J, 43(40):3997–4126.
"""

import logging
from dataclasses import dataclass, asdict
from typing import Literal

from .intervals import IntervalResult

logger = logging.getLogger("ecg.pipeline")

# ── Clinical threshold constants (all sourced) ──────────────────────────

# AHA/ACC 2009
HR_LOW_BPM = 60
HR_HIGH_BPM = 100
PR_SHORT_MS = 120
PR_LONG_MS = 200
QRS_WIDE_MS = 120

# Rautaharju et al. (1992), JACC — sex-specific QTc (Bazett)
QTC_WARN_MALE_MS = 450
QTC_WARN_FEMALE_MS = 460

# ESC 2022 Channelopathy Guideline — high-risk QTc threshold
QTC_CRITICAL_MS = 500

CITATION_AHA = "AHA/ACC (2009) ECG Standardisation. JACC 53(11):976–981."
CITATION_RAUTAHARJU = "Rautaharju et al. (1992) QT/QTc normal standards. JACC 20(6):1371–1377."
CITATION_ESC_2022 = "ESC (2022) Ventricular Arrhythmias Guidelines. Eur Heart J 43(40):3997–4126."


@dataclass
class Flag:
    """
    A single clinical flag raised by the rule engine.
    All fields are mandatory — no opaque or hidden values allowed.
    """
    code: str
    label: str
    measured_value: float
    unit: str
    threshold: float
    direction: Literal["above", "below", "none"]
    severity: Literal["INFO", "WARNING", "CRITICAL"]
    citation: str
    rule_version: str = "1.0.0"

    def to_dict(self) -> dict:
        return asdict(self)


def apply_rules(intervals: IntervalResult, sex: str) -> list[Flag]:
    """
    Apply all deterministic rules to a computed IntervalResult.

    Args:
        intervals : IntervalResult from compute_intervals()
        sex       : "M", "F", or "O" — used for sex-specific QTc thresholds

    Returns:
        list[Flag] — never empty (at minimum contains NORMAL_SINUS or a partial-mode notice)
    """
    flags: list[Flag] = []

    # ── 1. Heart rate ───────────────────────────────────────────────────────
    if intervals.hr_bpm and not _is_nan(intervals.hr_bpm.median):
        hr = intervals.hr_bpm.median

        if hr < HR_LOW_BPM:
            flags.append(
                Flag(
                    code="BRADYCARDIA",
                    label=f"Heart rate below normal ({hr:.1f} bpm < {HR_LOW_BPM} bpm)",
                    measured_value=round(
                        hr,
                        1),
                    unit="bpm",
                    threshold=float(HR_LOW_BPM),
                    direction="below",
                    severity="WARNING",
                    citation=CITATION_AHA,
                ))

        elif hr > HR_HIGH_BPM:
            flags.append(
                Flag(
                    code="TACHYCARDIA",
                    label=f"Heart rate above normal ({hr:.1f} bpm > {HR_HIGH_BPM} bpm)",
                    measured_value=round(
                        hr,
                        1),
                    unit="bpm",
                    threshold=float(HR_HIGH_BPM),
                    direction="above",
                    severity="WARNING",
                    citation=CITATION_AHA,
                ))

    # ── 2. PR interval ──────────────────────────────────────────────────────
    if intervals.pr_ms and not _is_nan(intervals.pr_ms.median):
        pr = intervals.pr_ms.median

        if pr < PR_SHORT_MS:
            flags.append(
                Flag(
                    code="SHORT_PR",
                    label=f"PR interval short ({pr:.1f} ms < {PR_SHORT_MS} ms) — possible pre-excitation",
                    measured_value=round(
                        pr,
                        1),
                    unit="ms",
                    threshold=float(PR_SHORT_MS),
                    direction="below",
                    severity="WARNING",
                    citation=CITATION_AHA,
                ))

        elif pr > PR_LONG_MS:
            flags.append(
                Flag(
                    code="LONG_PR",
                    label=f"PR interval prolonged ({pr:.1f} ms > {PR_LONG_MS} ms) — possible 1° AV block",
                    measured_value=round(
                        pr,
                        1),
                    unit="ms",
                    threshold=float(PR_LONG_MS),
                    direction="above",
                    severity="WARNING",
                    citation=CITATION_AHA,
                ))

    # ── 3. QRS duration ─────────────────────────────────────────────────────
    if intervals.qrs_ms and not _is_nan(intervals.qrs_ms.median):
        qrs = intervals.qrs_ms.median

        if qrs > QRS_WIDE_MS:
            flags.append(
                Flag(
                    code="WIDE_QRS",
                    label=f"QRS duration wide ({qrs:.1f} ms > {QRS_WIDE_MS} ms) — possible bundle branch block",
                    measured_value=round(
                        qrs,
                        1),
                    unit="ms",
                    threshold=float(QRS_WIDE_MS),
                    direction="above",
                    severity="WARNING",
                    citation=CITATION_AHA,
                ))

    # ── 4. QTc — sex-specific thresholds ─────────────────────────────────────
    qtc_meas = intervals.qtc_bazett
    if qtc_meas and not _is_nan(qtc_meas.median):
        qtc = qtc_meas.median
        qtc_warn = QTC_WARN_FEMALE_MS if sex == "F" else QTC_WARN_MALE_MS

        if qtc >= QTC_CRITICAL_MS:
            flags.append(
                Flag(
                    code="QTC_CRITICAL",
                    label=f"QTc critically prolonged ({qtc:.1f} ms ≥ {QTC_CRITICAL_MS} ms) — HIGH RISK",
                    measured_value=round(
                        qtc,
                        1),
                    unit="ms",
                    threshold=float(QTC_CRITICAL_MS),
                    direction="above",
                    severity="CRITICAL",
                    citation=CITATION_ESC_2022,
                ))

        elif qtc >= qtc_warn:
            flags.append(
                Flag(
                    code="QTC_MODERATE",
                    label=f"QTc prolonged ({qtc:.1f} ms ≥ {qtc_warn} ms for sex={sex})",
                    measured_value=round(
                        qtc,
                        1),
                    unit="ms",
                    threshold=float(qtc_warn),
                    direction="above",
                    severity="WARNING",
                    citation=CITATION_RAUTAHARJU,
                ))

    # ── 5. Partial mode notice ──────────────────────────────────────────────
    if intervals.partial:
        flags.append(
            Flag(
                code="PARTIAL_DELINEATION",
                label="Full P/QRS/T delineation was not possible — only HR computed from R-peaks",
                measured_value=float(
                    intervals.delineation_rate),
                unit="rate",
                threshold=0.50,
                direction="below",
                severity="WARNING",
                citation="NeuroKit2 delineation (Makowski et al., JOSS 2021)",
            ))

    # ── 6. All normal ───────────────────────────────────────────────────────
    if not flags:
        flags.append(Flag(
            code="NORMAL_SINUS",
            label="All computed intervals within normal reference ranges",
            measured_value=0.0,
            unit="none",
            threshold=0.0,
            direction="none",
            severity="INFO",
            citation=CITATION_AHA,
        ))

    _log_flags(flags)
    return flags


def severity_summary(
        flags: list[Flag]) -> Literal["ROUTINE", "URGENT", "CRITICAL"]:
    """
    Derive overall report priority from the set of flags.

    CRITICAL  ← at least one flag with severity="CRITICAL"
    URGENT    ← at least one flag with severity="WARNING"
    ROUTINE   ← all flags are INFO
    """
    severities = {f.severity for f in flags}
    if "CRITICAL" in severities:
        return "CRITICAL"
    if "WARNING" in severities:
        return "URGENT"
    return "ROUTINE"


# ── Integration point for Person B (ML layer) ───────────────────────────

def apply_ml_flags(signals_clean, intervals: IntervalResult) -> list[Flag]:
    """
    RESERVED for Person B — ML model integration.

    Contract (do not change):
      - Must return list[Flag] using the same Flag dataclass.
      - Every Flag MUST have a non-empty citation.
      - ML confidence must map to measured_value + threshold (no opaque score).
      - Must not modify any other function in this file.
      - Enable with settings.IS_ML_ENABLED = True.
    """
    raise NotImplementedError(
        "ML layer not yet integrated. "
        "Person B should implement apply_ml_flags() on a feature branch."
    )


# ── Helpers ─────────────────────────────────────────────────────────────

def _is_nan(value: float) -> bool:
    import math
    try:
        return math.isnan(value)
    except (TypeError, ValueError):
        return True


def _log_flags(flags: list[Flag]) -> None:
    for f in flags:
        logger.info(
            "Flag raised: [%s] %s | measured=%.1f %s | threshold=%.1f | severity=%s",
            f.code,
            f.label,
            f.measured_value,
            f.unit,
            f.threshold,
            f.severity,
        )
