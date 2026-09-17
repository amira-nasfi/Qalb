"""File readers. Every reader returns the same contract:
(signal in mV shaped (n_leads, n_samples), fs, lead_names, metadata dict).

Add a format by adding a reader here. Nothing downstream changes.
"""
from __future__ import annotations

import csv as _csv
import io
import os

import numpy as np

LEADS = ["I", "II", "III", "aVR", "aVL", "aVF",
         "V1", "V2", "V3", "V4", "V5", "V6"]


class EcgReadError(Exception):
    """Raised when a file cannot be read as a 12-lead ECG."""


def _reorder(sig: np.ndarray, names: list[str]) -> tuple[np.ndarray, list[str]]:
    """Map the file's lead order onto the canonical 12-lead order."""
    lut = {str(n).strip().lower().replace(" ", ""): i for i, n in enumerate(names)}
    # tolerate common spellings: "avr", "AVR", "aVR", "lead II", "ii"
    def find(lead: str):
        k = lead.lower()
        for cand in (k, "lead" + k, k.replace("v", "v")):
            if cand in lut:
                return lut[cand]
        for key, i in lut.items():
            if key.endswith(k):
                return i
        return None

    rows, kept = [], []
    for lead in LEADS:
        i = find(lead)
        if i is not None:
            rows.append(sig[i]); kept.append(lead)
    if not rows:
        raise EcgReadError(f"no recognisable 12-lead names in {names}")
    return np.asarray(rows, dtype=float), kept


def read_wfdb(path: str):
    """PhysioNet WFDB. Pass the path with or without extension."""
    import wfdb
    base = os.path.splitext(path)[0] if path.endswith((".dat", ".hea")) else path
    sig, meta = wfdb.rdsamp(base)
    units = [str(u).lower() for u in meta.get("units", [])]
    x = sig.T.astype(float)
    if units and units[0] in ("uv", "µv"):
        x = x / 1000.0
    x, kept = _reorder(x, list(meta["sig_name"]))
    md = {"source": "wfdb", "units": "mV"}
    for line in meta.get("comments", []):
        low = str(line).lower()
        if "<age>" in low:
            try: md["age"] = float(line.split(":", 1)[1].strip())
            except Exception: pass
        elif "<sex>" in low:
            md["sex"] = (line.split(":", 1)[1].strip().upper() or " ")[0]
        elif line.strip():
            md.setdefault("notes", []).append(line.strip().lstrip("#").strip())
    return x, float(meta["fs"]), kept, md


def read_csv(path_or_bytes, fs: float | None = None, unit: str = "mV"):
    """CSV with one column per lead and a header row naming the leads.

    fs must be supplied unless the file carries a 'time' or 'fs' column,
    because a CSV of samples has no inherent sampling rate.
    """
    if isinstance(path_or_bytes, (bytes, bytearray)):
        fh = io.StringIO(path_or_bytes.decode("utf-8", "ignore"))
    else:
        fh = open(path_or_bytes, newline="", encoding="utf-8", errors="ignore")
    with fh:
        rdr = _csv.reader(fh)
        header = next(rdr, None)
        if header is None:
            raise EcgReadError("empty CSV")
        rows = [r for r in rdr if any(c.strip() for c in r)]
    if not rows:
        raise EcgReadError("CSV has a header but no data rows")

    names = [h.strip() for h in header]
    arr = np.array([[float(c) if c.strip() else np.nan for c in r] for r in rows]).T

    # a time column lets us derive fs
    tcol = next((i for i, n in enumerate(names) if n.lower() in ("time", "t", "s")), None)
    if tcol is not None:
        t = arr[tcol]
        if len(t) > 2 and np.isfinite(t[:3]).all():
            dt = float(np.median(np.diff(t)))
            if dt > 0:
                fs = 1.0 / dt if dt < 1 else 1000.0 / dt   # seconds or ms
        arr = np.delete(arr, tcol, axis=0)
        names.pop(tcol)

    if not fs:
        raise EcgReadError("sampling rate unknown: pass fs, or include a time column")

    x, kept = _reorder(arr, names)
    if unit.lower() in ("uv", "µv"):
        x = x / 1000.0
    return x, float(fs), kept, {"source": "csv", "units": "mV"}


def read_edf(path: str):
    """European Data Format, the usual export from clinical recorders."""
    import pyedflib
    f = pyedflib.EdfReader(path)
    try:
        names = [f.getLabel(i) for i in range(f.signals_in_file)]
        fss = [f.getSampleFrequency(i) for i in range(f.signals_in_file)]
        dims = [str(f.getPhysicalDimension(i)).strip().lower()
                for i in range(f.signals_in_file)]
        n = min(f.getNSamples())
        rows = [f.readSignal(i)[:n] for i in range(f.signals_in_file)]
        x = np.asarray(rows, dtype=float)
        for i, d in enumerate(dims):
            if d in ("uv", "µv"):
                x[i] = x[i] / 1000.0
        x, kept = _reorder(x, names)
        md = {"source": "edf", "units": "mV"}
        try:
            md["age"] = float(f.getPatientAdditional() or "nan")
        except Exception:
            pass
        if len(set(fss)) > 1:
            md["warning"] = "channels have different sampling rates; using the first"
        return x, float(fss[0]), kept, md
    finally:
        f.close()


def read_any(path: str, fs: float | None = None, unit: str = "mV"):
    """Dispatch on extension. Raises EcgReadError with a usable message."""
    ext = os.path.splitext(str(path))[1].lower()
    if ext in (".dat", ".hea", ""):
        return read_wfdb(path)
    if ext == ".csv":
        return read_csv(path, fs=fs, unit=unit)
    if ext in (".edf", ".bdf"):
        return read_edf(path)
    raise EcgReadError(f"unsupported extension {ext!r}; expected .dat/.hea, .csv or .edf")
