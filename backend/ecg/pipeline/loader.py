"""
ECG loader — multi-format ingestion.

Supported formats:
  - "wfdb"  : PTB-XL .mat + .hea via wfdb.rdsamp()
  - "csv"   : raw CSV, columns = leads, header = lead names
  - "edf"   : EDF/EDF+ via MNE

Returns:
  signals  : np.ndarray shape (n_leads, n_samples) in mV
  fs       : int — sampling frequency in Hz
  metadata : dict — source_format, filename_hash (SHA-256), lead_names
             (NO PII — original filename is hashed, never stored)

References:
  - Goldberger et al., PhysioBank / PhysioNet (2000)
  - WFDB Python package: https://github.com/MIT-LCP/wfdb-python
  - MNE-Python: https://mne.tools
"""

import hashlib
import logging
import os

import numpy as np

logger = logging.getLogger("ecg.pipeline")

# Standard 12-lead order (AHA/ACC 2009)
STANDARD_LEADS = ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"]

MIN_FS = 250    # Hz — below this, delineation quality degrades unacceptably
MAX_FS = 1000   # Hz


def load_ecg(path: str, fmt: str) -> tuple[np.ndarray, int, dict]:
    """
    Load a multi-lead ECG from disk.

    Args:
        path: Absolute path to the ECG file (or record name for WFDB).
        fmt:  One of "wfdb", "csv", "edf".

    Returns:
        (signals, fs, metadata)
        signals: np.ndarray of shape (n_leads, n_samples), values in mV.
        fs: sampling frequency in Hz.
        metadata: dict with keys source_format, filename_hash, lead_names,
                  n_leads, n_samples, duration_sec, warnings.
    """
    fmt = fmt.lower().strip()

    if fmt == "wfdb":
        signals, fs, lead_names = _load_wfdb(path)
    elif fmt == "csv":
        signals, fs, lead_names = _load_csv(path)
    elif fmt == "edf":
        signals, fs, lead_names = _load_edf(path)
    else:
        raise ValueError(f"Unsupported format: {fmt!r}. Use 'wfdb', 'csv', or 'edf'.")

    warnings = []

    # Validate sampling frequency
    if fs < MIN_FS:
        warnings.append(f"fs={fs} Hz is below minimum {MIN_FS} Hz — delineation may be unreliable.")
    if fs > MAX_FS:
        warnings.append(f"fs={fs} Hz is above maximum {MAX_FS} Hz — signals will be downsampled.")

    # Validate lead count
    n_leads, n_samples = signals.shape
    if n_leads < 12:
        warnings.append(f"Only {n_leads} leads found; expected 12. Some intervals may not be computed.")
    if n_leads > 12:
        logger.debug("Truncating %d leads to 12.", n_leads)
        signals = signals[:12, :]
        lead_names = lead_names[:12]
        n_leads = 12

    # Hash the file path (never store original filename)
    filename_hash = hashlib.sha256(os.path.basename(path).encode()).hexdigest()

    metadata = {
        "source_format": fmt,
        "filename_hash": filename_hash,
        "lead_names": lead_names,
        "n_leads": n_leads,
        "n_samples": n_samples,
        "duration_sec": round(n_samples / fs, 2),
        "warnings": warnings,
    }

    if warnings:
        for w in warnings:
            logger.warning("ECG loader warning: %s", w)

    logger.info(
        "Loaded ECG: fmt=%s, leads=%d, samples=%d, fs=%d Hz, duration=%.1f s",
        fmt, n_leads, n_samples, fs, metadata["duration_sec"],
    )
    return signals, fs, metadata


def _load_wfdb(path: str) -> tuple[np.ndarray, int, list[str]]:
    """Load a WFDB record (.hea + .dat or .mat)."""
    import wfdb

    # Support both full path and record name
    record_path = path.replace(".hea", "").replace(".mat", "")
    record = wfdb.rdsamp(record_path)
    # wfdb returns (signals, fields); signals shape is (N, n_leads)
    signals_raw, fields = record
    signals = signals_raw.T.astype(np.float32)  # → (n_leads, N)
    fs = int(fields["fs"])
    lead_names = fields.get("sig_name", STANDARD_LEADS[: signals.shape[0]])
    return signals, fs, list(lead_names)


def _load_csv(path: str) -> tuple[np.ndarray, int, list[str]]:
    """
    Load a CSV file.
    Expected format: first row = lead names, subsequent rows = samples.
    A column named 'fs' in the first row encodes the sampling frequency.
    """
    import pandas as pd

    df = pd.read_csv(path)

    # Try to parse fs from column names or a dedicated column
    fs = 500  # default
    if "fs" in df.columns:
        fs = int(df["fs"].iloc[0])
        df = df.drop(columns=["fs"])

    lead_names = list(df.columns)
    signals = df.values.T.astype(np.float32)  # → (n_leads, N)
    return signals, fs, lead_names


def _load_edf(path: str) -> tuple[np.ndarray, int, list[str]]:
    """Load an EDF/EDF+ file via MNE."""
    import mne

    raw = mne.io.read_raw_edf(path, preload=True, verbose=False)
    fs = int(raw.info["sfreq"])
    signals = raw.get_data(units="V") * 1000  # convert V → mV
    lead_names = raw.ch_names
    return signals.astype(np.float32), fs, lead_names
