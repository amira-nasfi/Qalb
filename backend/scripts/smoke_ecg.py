"""
scripts/smoke_ecg.py
====================
Smoke-test the ecg_analysis library against a synthetic 12-lead signal.

Validates:
  1. analyze_to_report returns result["ok"] == True
  2. segmentation.labels contains all four classes {0, 1, 2, 3}
  3. result["timings"]["steps"] contains the expected analysis stages
  4. read_any returns signal, fs, lead_names, meta in the correct contract

Run from backend/:
    python scripts/smoke_ecg.py

Exit 0  → SMOKE_ECG_PASSED — safe to proceed to Step 3 (models).
Exit 1  → assertion failed   — stop and report.
"""

from __future__ import annotations
import csv
import os
import sys
import tempfile

# ── Make sure ecg_analysis is importable from backend/ ───────────────────────
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ECG_PKG_DIR = os.path.join(BACKEND_DIR, "ecg_analysis")
if ECG_PKG_DIR not in sys.path:
    sys.path.insert(0, ECG_PKG_DIR)

from ecg_analysis import analyze_to_report, read_any, LEADS  # noqa: E402


def make_synthetic_csv(path: str, duration_s: int = 10, fs: int = 500) -> None:
    """
    Write a 12-lead ECG CSV at the given path.
    Each lead is a neurokit2-simulated ECG signal to ensure physiologically
    plausible PQRST morphology (which the pipeline's wavelet delineator needs).
    """
    import neurokit2 as nk
    import numpy as np

    n = duration_s * fs
    t = [i / fs for i in range(n)]

    # Simulate 12 channels; vary heart rate slightly to avoid exact alignment
    signals = {}
    for i, lead in enumerate(LEADS):
        hr = 70 + (i % 3) * 2       # 70, 72, 74 bpm cycling
        raw = nk.ecg_simulate(duration=duration_s, sampling_rate=fs,
                               heart_rate=hr, noise=0.02)
        # crude polarity adjustment for limb leads
        if lead in ("aVR",):
            raw = -raw
        signals[lead] = np.round(raw.astype(float), 6).tolist()

    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["time"] + LEADS)
        for j in range(n):
            writer.writerow(
                [round(t[j], 6)] + [signals[ld][j] for ld in LEADS]
            )


def main() -> int:
    print("smoke_ecg: generating synthetic 12-lead CSV…")

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tf:
        csv_path = tf.name

    try:
        make_synthetic_csv(csv_path, duration_s=10, fs=500)
        print(f"smoke_ecg: CSV written  ({os.path.getsize(csv_path)//1024} KB)")

        # ── 1. read_any contract check ────────────────────────────────────────
        print("smoke_ecg: testing read_any…")
        sig, fs, lead_names, meta = read_any(csv_path)
        assert sig.ndim == 2,                  f"signal must be 2D, got shape {sig.shape}"
        assert sig.shape[0] == len(lead_names), "row count must equal lead count"
        assert len(lead_names) == 12,          f"expected 12 leads, got {len(lead_names)}"
        assert round(fs) == 500,               f"expected fs≈500, got {fs}"
        print(f"  read_any OK — shape {sig.shape}, fs={fs}, leads={lead_names}")

        # ── 2. Full analysis pipeline ─────────────────────────────────────────
        print("smoke_ecg: running analyze_to_report…")
        out = analyze_to_report(
            csv_path,
            fs=500,
            age=45,
            sex="M",
            paced=False,
            patient_id="SMOKE-TEST-001",
        )
        result = out["result"]

        # ok
        assert result["ok"] is True, f"result['ok'] is False: {result.get('error')}"

        # quality
        qc = result["quality"]
        assert qc["acceptable"] is True, f"quality not acceptable: {qc}"
        print(f"  quality OK — acceptable=True, "
              f"failed_leads={qc.get('failed_leads', [])}, "
              f"missing_leads={qc.get('missing_leads', [])}")

        # segmentation labels: must contain {0, 1, 2, 3}
        labels = result["segmentation"]["labels"]
        classes = sorted(set(labels))
        assert set(classes) == {0, 1, 2, 3}, \
            f"segmentation classes should be {{0,1,2,3}}, got {classes}"
        print(f"  segmentation OK — classes={classes}, "
              f"n_labels={len(labels)}, "
              f"label_lead={result['segmentation']['label_lead']}")

        # timings
        steps = result["timings"]["steps"]
        n_steps = len(steps)
        assert n_steps >= 4, f"expected ≥4 timing steps, got {n_steps}: {steps}"
        print(f"  timings OK — {n_steps} steps, "
              f"total={result['timings']['total_ms']} ms")
        for s in steps:
            print(f"    {s['step']}: {s['duration_ms']} ms")

        # triage
        triage = result["triage"]
        assert triage["priority"] in (1, 2, 3), \
            f"unexpected triage priority: {triage}"
        print(f"  triage OK — level={triage['level']}, "
              f"priority={triage['priority']}, "
              f"escalate={triage['escalate']}")

        # report_text and report_blocks
        assert isinstance(out["report_text"], str) and out["report_text"], \
            "report_text is empty"
        assert isinstance(out["report_blocks"], dict), \
            "report_blocks must be a dict"
        print(f"  report OK — {len(out['report_text'])} chars, "
              f"{len(out['report_blocks'])} keys in report_blocks")

        # limits
        limits = result["limits"]
        assert isinstance(limits, list) and limits, \
            "result['limits'] must be a non-empty list"
        print(f"  limits OK — {len(limits)} entries")

    finally:
        os.unlink(csv_path)

    print(f"\nSMOKE_ECG_PASSED: ok=True, classes={classes}, "
          f"timings_steps={n_steps}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
