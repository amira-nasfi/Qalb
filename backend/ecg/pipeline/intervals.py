"""
Clinical interval computation from delineated ECG landmarks.

Computes per-beat measurements then reports median ± IQR:
  - Heart Rate (HR)  : 60 000 / median_RR  [bpm]
  - PR interval      : P_onset → Q_peak    [ms]
  - QRS duration     : Q_peak  → S_peak    [ms]
  - QT interval      : Q_peak  → T_offset  [ms]
  - QTc (Bazett)     : QT / sqrt(RR_sec)   [ms]  — Bazett (1920)
  - QTc (Fridericia) : QT / RR_sec^(1/3)   [ms]  — Fridericia (1920)

In partial mode (R-peaks only), only HR is computed.

References:
  - Bazett HC (1920). An analysis of the time-relations of electrocardiograms.
    Heart, 7, 353–370.
  - Fridericia LS (1920). Die Systolendauer im Elektrokardiogramm bei normalen
    Menschen und bei Herzkranken. Acta Med. Scand., 53, 469–486.
  - Rautaharju PM et al. (1992). Normal standards for duration and amplitude
    of QT and QTc intervals. JACC, 20(6), 1371–1377.
  - AHA/ACC (2009). Recommendations for the Standardization and Interpretation
    of the Electrocardiogram.
"""

import logging
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger("ecg.pipeline")


@dataclass
class Measurement:
    """A single interval measurement with statistics and provenance."""
    median: float           # median value across beats
    iqr: float              # interquartile range (Q75 - Q25)
    unit: str               # "ms" or "bpm"
    formula_ref: str        # citation string
    n_valid: int            # number of beats contributing to this measurement


@dataclass
class IntervalResult:
    """All computed intervals for one ECG record."""
    hr_bpm: Measurement
    pr_ms: Measurement | None    # None in partial mode
    qrs_ms: Measurement | None
    qt_ms: Measurement | None
    qtc_bazett: Measurement | None
    qtc_fridericia: Measurement | None
    n_beats: int
    partial: bool
    lead_used: str
    delineation_rate: float

    def to_dict(self) -> dict:
        """Serialisable dict for JSON storage."""
        def _m(m):
            if m is None:
                return None
            return {
                "median": round(m.median, 2),
                "iqr": round(m.iqr, 2),
                "unit": m.unit,
                "formula_ref": m.formula_ref,
                "n_valid": m.n_valid,
            }
        return {
            "hr_bpm": _m(self.hr_bpm),
            "pr_ms": _m(self.pr_ms),
            "qrs_ms": _m(self.qrs_ms),
            "qt_ms": _m(self.qt_ms),
            "qtc_bazett": _m(self.qtc_bazett),
            "qtc_fridericia": _m(self.qtc_fridericia),
            "n_beats": self.n_beats,
            "partial": self.partial,
            "lead_used": self.lead_used,
            "delineation_rate": self.delineation_rate,
        }


def compute_intervals(delineation: dict, fs: int) -> IntervalResult:
    """
    Compute clinical intervals from delineation landmarks.

    Args:
        delineation : dict from delineation.delineate()
        fs          : sampling frequency in Hz

    Returns:
        IntervalResult dataclass
    """
    r_peaks = delineation["r_peaks"]
    p_onsets = delineation["p_onsets"]
    q_peaks = delineation["q_peaks"]
    s_peaks = delineation["s_peaks"]
    t_offsets = delineation["t_offsets"]
    partial = delineation["partial"]
    n_beats = delineation["n_beats"]

    # ── Heart Rate ──────────────────────────────────────────────────────────
    hr = _compute_hr(r_peaks, fs)

    if partial or n_beats < 2:
        # R-peaks only mode — compute HR only
        return IntervalResult(
            hr_bpm=hr,
            pr_ms=None,
            qrs_ms=None,
            qt_ms=None,
            qtc_bazett=None,
            qtc_fridericia=None,
            n_beats=n_beats,
            partial=True,
            lead_used=delineation["lead_used"],
            delineation_rate=delineation["delineation_rate"],
        )

    # RR intervals in seconds (for QTc formulas)
    rr_ms = np.diff(r_peaks) / fs * 1000.0   # ms
    rr_sec = rr_ms / 1000.0

    # ── PR interval ──────────────────────────────────────────────────────────
    pr_ms = _paired_diff(p_onsets, q_peaks, fs)

    # ── QRS duration ─────────────────────────────────────────────────────────
    qrs_ms = _paired_diff(q_peaks, s_peaks, fs)

    # ── QT interval ──────────────────────────────────────────────────────────
    qt_ms = _paired_diff(q_peaks, t_offsets, fs)

    # ── QTc (Bazett) ─────────────────────────────────────────────────────────
    qtc_b = _compute_qtc_bazett(qt_ms, rr_sec)

    # ── QTc (Fridericia) ─────────────────────────────────────────────────────
    qtc_f = _compute_qtc_fridericia(qt_ms, rr_sec)

    result = IntervalResult(
        hr_bpm=hr,
        pr_ms=pr_ms,
        qrs_ms=qrs_ms,
        qt_ms=qt_ms,
        qtc_bazett=qtc_b,
        qtc_fridericia=qtc_f,
        n_beats=n_beats,
        partial=False,
        lead_used=delineation["lead_used"],
        delineation_rate=delineation["delineation_rate"],
    )

    logger.info(
        "Intervals: HR=%.1f bpm, PR=%.1f ms, QRS=%.1f ms, QTc(Baz)=%.1f ms [n=%d beats]",
        hr.median,
        pr_ms.median if pr_ms else float("nan"),
        qrs_ms.median if qrs_ms else float("nan"),
        qtc_b.median if qtc_b else float("nan"),
        n_beats,
    )
    return result


# ── Private helpers ─────────────────────────────────────────────────────

def _compute_hr(r_peaks: np.ndarray, fs: int) -> Measurement:
    if len(r_peaks) < 2:
        return Measurement(
            median=float("nan"), iqr=0.0, unit="bpm",
            formula_ref="HR = 60000 / RR_ms", n_valid=0,
        )
    rr_ms = np.diff(r_peaks) / fs * 1000.0
    hr_values = 60_000.0 / rr_ms
    return Measurement(
        median=float(np.median(hr_values)),
        iqr=float(np.percentile(hr_values, 75) - np.percentile(hr_values, 25)),
        unit="bpm",
        formula_ref="HR = 60000 / RR_ms (standard)",
        n_valid=len(hr_values),
    )


def _paired_diff(
    start_indices: np.ndarray,
    end_indices: np.ndarray,
    fs: int,
) -> Measurement | None:
    """
    Compute per-beat duration between matched pairs of landmark arrays.
    Uses nearest-neighbour matching; pairs with negative duration are discarded.
    """
    if len(start_indices) == 0 or len(end_indices) == 0:
        return None

    # Match each start to the nearest end
    diffs_ms = []
    for s in start_indices:
        diffs = end_indices.astype(int) - int(s)
        pos = diffs[diffs > 0]
        if len(pos) == 0:
            continue
        nearest = pos.min()
        diffs_ms.append(nearest / fs * 1000.0)

    if not diffs_ms:
        return None

    arr = np.array(diffs_ms)
    return Measurement(
        median=float(np.median(arr)),
        iqr=float(np.percentile(arr, 75) - np.percentile(arr, 25)),
        unit="ms",
        formula_ref="landmark_diff / fs * 1000",
        n_valid=len(arr),
    )


def _compute_qtc_bazett(
    qt_measurement: Measurement | None,
    rr_sec: np.ndarray,
) -> Measurement | None:
    """QTc = QT / sqrt(RR_sec). Bazett HC (1920)."""
    if qt_measurement is None or len(rr_sec) == 0:
        return None
    median_rr = float(np.median(rr_sec))
    if median_rr <= 0:
        return None
    qtc = qt_measurement.median / np.sqrt(median_rr)
    return Measurement(
        median=round(
            qtc,
            2),
        iqr=qt_measurement.iqr,
        unit="ms",
        formula_ref="Bazett (1920): QTc = QT / sqrt(RR_sec). Heart, 7:353–370.",
        n_valid=qt_measurement.n_valid,
    )


def _compute_qtc_fridericia(
    qt_measurement: Measurement | None,
    rr_sec: np.ndarray,
) -> Measurement | None:
    """QTc = QT / RR_sec^(1/3). Fridericia LS (1920)."""
    if qt_measurement is None or len(rr_sec) == 0:
        return None
    median_rr = float(np.median(rr_sec))
    if median_rr <= 0:
        return None
    qtc = qt_measurement.median / (median_rr ** (1.0 / 3.0))
    return Measurement(
        median=round(
            qtc,
            2),
        iqr=qt_measurement.iqr,
        unit="ms",
        formula_ref="Fridericia (1920): QTc = QT / RR^(1/3). Acta Med. Scand., 53:469–486.",
        n_valid=qt_measurement.n_valid,
    )
