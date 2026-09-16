"""
ECG signal preprocessing.

Steps applied to every lead before delineation:
  1. Bandpass filter 0.5–40 Hz (4th-order Butterworth, zero-phase)
     — removes baseline wander (< 0.5 Hz) and high-freq noise (> 40 Hz)
  2. Per-lead z-score normalization
     — stabilises delineation regardless of gain/amplitude differences

References:
  - Pan & Tompkins (1985), IEEE Trans. Biomed. Eng. 32(3):230–236
  - Sörnmo & Laguna (2005), Bioelectrical Signal Processing, Elsevier
  - SciPy signal processing: https://docs.scipy.org/doc/scipy/reference/signal.html
"""

import logging
import numpy as np
from scipy.signal import butter, filtfilt

logger = logging.getLogger("ecg.pipeline")

# ── Filter constants ──────────────────────────────────────────────────────────
BANDPASS_LOW_HZ   = 0.5
BANDPASS_HIGH_HZ  = 40.0
FILTER_ORDER      = 4


def preprocess(signals: np.ndarray, fs: int) -> np.ndarray:
    """
    Apply bandpass filter and z-score normalisation to each lead.

    Args:
        signals : np.ndarray shape (n_leads, n_samples), values in mV.
        fs      : sampling frequency in Hz.

    Returns:
        signals_clean : same shape as input, filtered and normalised.
    """
    n_leads, n_samples = signals.shape
    signals_clean = np.zeros_like(signals, dtype=np.float32)

    b, a = _butter_bandpass(fs)

    for i in range(n_leads):
        lead = signals[i].astype(np.float64)

        # Step 1: zero-phase bandpass filter
        try:
            lead_filtered = filtfilt(b, a, lead)
        except ValueError as exc:
            logger.warning("Lead %d bandpass filter failed (%s) — using raw signal.", i, exc)
            lead_filtered = lead

        # Step 2: per-lead z-score normalisation
        std = np.std(lead_filtered)
        if std > 1e-9:
            lead_norm = (lead_filtered - np.mean(lead_filtered)) / std
        else:
            lead_norm = lead_filtered  # flat line — normalisation would cause NaN

        signals_clean[i] = lead_norm.astype(np.float32)

    logger.debug("Preprocessing done: %d leads, %d samples, fs=%d Hz.", n_leads, n_samples, fs)
    return signals_clean


def _butter_bandpass(fs: int):
    """Return (b, a) coefficients for a 4th-order Butterworth bandpass filter."""
    nyq = fs / 2.0
    low  = BANDPASS_LOW_HZ  / nyq
    high = BANDPASS_HIGH_HZ / nyq

    # Clamp to valid range
    low  = max(low,  1e-4)
    high = min(high, 0.9999)

    b, a = butter(FILTER_ORDER, [low, high], btype="band")
    return b, a
