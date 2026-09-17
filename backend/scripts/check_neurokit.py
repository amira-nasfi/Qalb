"""
scripts/check_neurokit.py
=========================
Verify that the installed neurokit2 version exposes every key that
ecg_analysis/pipeline.py depends on for PQRST delineation.

Run from backend/:
    python scripts/check_neurokit.py

Exit 0  → all required keys present → safe to proceed with Phase 2.
Exit 1  → one or more keys missing  → stop and report; do not pin ecg_analysis.
"""

import sys
import importlib.metadata

REQUIRED_KEYS = {
    "ECG_P_Onsets",
    "ECG_P_Offsets",
    "ECG_R_Onsets",
    "ECG_R_Offsets",
    "ECG_T_Offsets",
}


def main() -> int:
    # ── 1. Report installed version ─────────────────────────────────────────
    try:
        version = importlib.metadata.version("neurokit2")
    except importlib.metadata.PackageNotFoundError:
        print("FAIL: neurokit2 is not installed")
        return 1
    print(f"neurokit2 version: {version}")

    # ── 2. Import and synthesise a 10-second signal ─────────────────────────
    try:
        import neurokit2 as nk
        import numpy as np
    except ImportError as exc:
        print(f"FAIL: import error — {exc}")
        return 1

    sig = nk.ecg_simulate(duration=10, sampling_rate=500, heart_rate=70,
                          noise=0.0)
    clean = nk.ecg_clean(sig, sampling_rate=500)

    # ── 3. Detect R-peaks ───────────────────────────────────────────────────
    _, rp_info = nk.ecg_peaks(clean, sampling_rate=500,
                               method="pantompkins1985")
    r_peaks = rp_info["ECG_R_Peaks"]
    print(f"R-peaks detected: {len(r_peaks)}")

    # ── 4. Delineate PQRST (DWT method — same as ecg_analysis/pipeline.py) ──
    _, waves = nk.ecg_delineate(clean, r_peaks, sampling_rate=500,
                                 method="dwt")
    found_keys = set(waves.keys())
    print(f"delineate keys: {sorted(found_keys)}")

    # ── 5. Assert required keys ─────────────────────────────────────────────
    missing = REQUIRED_KEYS - found_keys
    if missing:
        print(f"\nFAIL: missing keys — {sorted(missing)}")
        print("Action: stop Phase 2. Report to maintainer to evaluate "
              "whether to pin neurokit2>=0.2.13.")
        return 1

    print(f"\nSTEP_1_NEUROKIT_OK — all {len(REQUIRED_KEYS)} required keys "
          f"present in neurokit2=={version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
