"""
P/QRS/T delineation via NeuroKit2.

Detects cardiac fiducial points for each beat:
  - P wave onset
  - Q peak (start of QRS)
  - R peak (maximum of QRS)
  - S peak (end of QRS)
  - T wave offset

Primary lead: Lead II (index 1 in standard 12-lead order)
Fallback lead: Lead V5 (index 10) if Lead II delineation rate < 50%
Partial mode: R-peaks only (Pan-Tompkins via nk.ecg_peaks) if both fail

References:
  - Makowski et al. (2021), NeuroKit2: A Python toolbox for neurophysiological
    signal processing. JOSS, doi:10.21105/joss.02621
  - Pan & Tompkins (1985), IEEE Trans. Biomed. Eng. 32(3):230-236
  - NeuroKit2 ECG delineation: https://neuropsychology.github.io/NeuroKit/
"""

import logging
import numpy as np

logger = logging.getLogger("ecg.pipeline")

# Lead indices in standard 12-lead order (AHA/ACC 2009)
LEAD_II_INDEX  = 1
LEAD_V5_INDEX  = 10

# Minimum fraction of beats that must be fully delineated (all 5 landmarks)
MIN_DELINEATION_RATE = 0.50


def delineate(signals_clean: np.ndarray, fs: int) -> dict:
    """
    Delineate P/QRS/T complexes in a preprocessed 12-lead ECG.

    Args:
        signals_clean : np.ndarray shape (n_leads, n_samples), z-scored.
        fs            : sampling frequency in Hz.

    Returns:
        dict with keys:
            p_onsets   : np.ndarray of sample indices (int)
            q_peaks    : np.ndarray of sample indices
            r_peaks    : np.ndarray of sample indices
            s_peaks    : np.ndarray of sample indices
            t_offsets  : np.ndarray of sample indices
            n_beats    : int — number of fully delineated beats
            partial    : bool — True if only R-peaks were obtained
            lead_used  : str — which lead was used ("II", "V5", or "R-only")
            delineation_rate : float — fraction of beats fully delineated
    """
    n_leads = signals_clean.shape[0]

    # Try Lead II first
    if n_leads > LEAD_II_INDEX:
        result = _try_delineate(signals_clean[LEAD_II_INDEX], fs, "II")
        if result is not None:
            return result

    # Fallback: Lead V5
    if n_leads > LEAD_V5_INDEX:
        logger.warning("Lead II delineation insufficient — falling back to Lead V5.")
        result = _try_delineate(signals_clean[LEAD_V5_INDEX], fs, "V5")
        if result is not None:
            return result

    # Partial mode: R-peaks only
    logger.warning("Full delineation failed on both leads — using R-peaks only (Pan-Tompkins).")
    return _rpeaks_only(signals_clean[min(LEAD_II_INDEX, n_leads - 1)], fs)


def _try_delineate(lead_signal: np.ndarray, fs: int, lead_name: str) -> dict | None:
    """
    Attempt full P/QRS/T delineation on a single lead.
    Returns None if delineation rate is below MIN_DELINEATION_RATE.
    """
    import neurokit2 as nk
    import pandas as pd

    try:
        ecg_df, _ = nk.ecg_process(lead_signal, sampling_rate=fs)
    except Exception as exc:
        logger.warning("NeuroKit2 ecg_process failed on Lead %s: %s", lead_name, exc)
        return None

    def _extract(col):
        """Extract non-NaN sample indices for a delineation column."""
        if col not in ecg_df.columns:
            return np.array([], dtype=int)
        mask = ecg_df[col].notna() & (ecg_df[col] > 0)
        return ecg_df.index[mask].to_numpy(dtype=int)

    r_peaks   = _extract("ECG_R_Peaks")
    p_onsets  = _extract("ECG_P_Onsets")
    q_peaks   = _extract("ECG_Q_Peaks")
    s_peaks   = _extract("ECG_S_Peaks")
    t_offsets = _extract("ECG_T_Offsets")

    n_beats = len(r_peaks)
    if n_beats == 0:
        logger.warning("No R-peaks found in Lead %s.", lead_name)
        return None

    # Delineation rate: fraction of R-peaks that have all 5 landmarks
    min_full = min(len(p_onsets), len(q_peaks), len(s_peaks), len(t_offsets))
    rate = min_full / n_beats

    logger.info(
        "Delineation Lead %s: %d R-peaks, rate=%.1f%%.",
        lead_name, n_beats, rate * 100,
    )

    if rate < MIN_DELINEATION_RATE:
        return None

    return {
        "p_onsets":         p_onsets,
        "q_peaks":          q_peaks,
        "r_peaks":          r_peaks,
        "s_peaks":          s_peaks,
        "t_offsets":        t_offsets,
        "n_beats":          n_beats,
        "partial":          False,
        "lead_used":        lead_name,
        "delineation_rate": round(rate, 4),
    }


def _rpeaks_only(lead_signal: np.ndarray, fs: int) -> dict:
    """Pan-Tompkins R-peak detection only (partial delineation mode)."""
    import neurokit2 as nk

    try:
        _, info = nk.ecg_peaks(lead_signal, sampling_rate=fs, method="pantompkins1985")
        r_peaks = info["ECG_R_Peaks"]
    except Exception as exc:
        logger.error("Pan-Tompkins R-peak detection also failed: %s", exc)
        r_peaks = np.array([], dtype=int)

    n_beats = len(r_peaks)
    logger.info("Partial mode: %d R-peaks detected.", n_beats)

    return {
        "p_onsets":         np.array([], dtype=int),
        "q_peaks":          np.array([], dtype=int),
        "r_peaks":          r_peaks,
        "s_peaks":          np.array([], dtype=int),
        "t_offsets":        np.array([], dtype=int),
        "n_beats":          n_beats,
        "partial":          True,
        "lead_used":        "R-only",
        "delineation_rate": 0.0,
    }
