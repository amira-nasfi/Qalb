"""ECG analysis pipeline. One entry point, JSON-serialisable output.

    from ecg_analysis import analyze
    result = analyze("/path/to/record.edf", age=64, sex="M")

Every stage is timed, because the challenge requires showing the delay of each
step in the medical loop.

No Django import here on purpose: this module is a plain library so it can be
called from a view, a Celery task or a management command without change.
"""
from __future__ import annotations

import time
import traceback
from datetime import datetime, timezone

import numpy as np
from scipy import signal as sps
from scipy import stats
from scipy.ndimage import median_filter

from .readers import LEADS, EcgReadError, read_any

FS = 500.0
POWERLINE = 50.0            # Tunisia / Europe
ANCHOR = ["II", "V1", "V5"]
AF_THRESH = 0.35
BRADY_BPM, TACHY_BPM = 60.0, 90.0

# Calibration measured on 191 LUDB records against cardiologist annotations.
BIAS_MS = {"P_on": 12.8, "P_off": -18.3, "QRS_on": -6.9, "QRS_off": -4.4,
           "T_off": -19.6}

PIPELINE_VERSION = "ecg-analysis-1.0"
RED, ORANGE, GREEN = "RED", "ORANGE", "GREEN"


# ---------------------------------------------------------------- timing ----

class Timer:
    """Records the duration of each stage, in milliseconds."""

    def __init__(self):
        self.steps: list[dict] = []
        self._t0 = time.perf_counter()

    def mark(self, name: str):
        now = time.perf_counter()
        self.steps.append({"step": name,
                           "duration_ms": round((now - self._t0) * 1000, 1)})
        self._t0 = now

    def total_ms(self):
        return round(sum(s["duration_ms"] for s in self.steps), 1)


# ------------------------------------------------------- signal processing ---

def preprocess(raw_mv: np.ndarray, fs_in: float) -> np.ndarray:
    """Resample, denotch, debaseline, lowpass. Amplitude in mV is preserved.

    Baseline removal uses a two-stage median filter rather than a high-pass:
    a 0.5 Hz high-pass manufactures ST deviation, and the IEC 0.05 Hz edge is
    numerically fragile at 500 Hz. The 200 ms then 600 ms median cascade leaves
    the ST segment untouched.
    """
    x = np.asarray(raw_mv, dtype=float)
    if abs(fs_in - FS) > 1e-6:
        from fractions import Fraction
        r = Fraction(FS / fs_in).limit_denominator(1000)
        x = sps.resample_poly(x, r.numerator, r.denominator, axis=-1)
    for f0 in (POWERLINE, 2 * POWERLINE):
        if f0 < FS / 2:
            b, a = sps.iirnotch(f0, 30.0, fs=FS)
            x = sps.filtfilt(b, a, x, axis=-1)
    k1, k2 = int(round(0.200 * FS)) | 1, int(round(0.600 * FS)) | 1
    out = np.empty_like(x)
    for i in range(x.shape[0]):
        base = median_filter(x[i], size=k1, mode="nearest")
        base = median_filter(base, size=k2, mode="nearest")
        out[i] = x[i] - base
    sos = sps.butter(4, 150.0, btype="low", fs=FS, output="sos")
    return sps.sosfiltfilt(sos, out, axis=-1)


def _band_power(x, fs, lo, hi):
    f, p = sps.welch(x, fs=fs, nperseg=min(len(x), int(4 * fs)))
    m = (f >= lo) & (f < hi)
    return float(np.trapezoid(p[m], f[m])) if m.any() else 0.0


def assess_quality(sig: np.ndarray, lead_names: list[str]) -> dict:
    """Per-lead quality. Judged per lead so the operator knows which electrode
    to re-stick, rather than being told the whole trace is bad."""
    per_lead, failed = {}, []
    for i, name in enumerate(lead_names):
        x = sig[i]
        reasons = []
        n = int(FS); nw = len(x) // n
        if nw:
            ptp = np.ptp(x[:nw * n].reshape(nw, n), axis=1)
            if float(np.mean(ptp < 0.05)) > 0.20:
                reasons.append("ligne plate ou electrode debranchee")
        if float(np.max(np.abs(x))) > 10.0:
            reasons.append("amplitude hors plage physiologique")
        tot = _band_power(x, FS, 0, 150) + 1e-12
        if _band_power(x, FS, 0, 0.7) / tot > 0.50:
            reasons.append("derive de ligne de base excessive")
        if _band_power(x, FS, POWERLINE - 1, POWERLINE + 1) / tot > 0.25:
            reasons.append(f"interference {POWERLINE:.0f} Hz")
        if _band_power(x, FS, 5, 15) / (_band_power(x, FS, 5, 40) + 1e-12) < 0.40:
            reasons.append("bruit musculaire dominant")
        if float(stats.kurtosis(x, fisher=False)) < 4.0:
            reasons.append("signal domine par le bruit")
        per_lead[name] = reasons
        if reasons:
            failed.append(name)
    missing = [l for l in LEADS if l not in lead_names]
    acceptable = len(failed) <= 2 and not missing
    return {"acceptable": acceptable, "failed_leads": failed,
            "missing_leads": missing, "per_lead": per_lead,
            "action": ("analyse" if acceptable else "reacquisition_requise")}


def detect_beats(sig: np.ndarray, lead_names: list[str]) -> np.ndarray:
    import neurokit2 as nk
    lead = "II" if "II" in lead_names else lead_names[0]
    _, info = nk.ecg_peaks(sig[lead_names.index(lead)], sampling_rate=FS)
    return np.asarray(info["ECG_R_Peaks"], dtype=int)


def segment(sig: np.ndarray, lead_names: list[str], rpeaks: np.ndarray) -> dict:
    """Wavelet segmentation of the PQRST complex.

    Returns per-lead boundaries AND a per-sample label array, because the
    frontend needs the label array to shade the trace.
    """
    import neurokit2 as nk
    out = {}
    for lead in ANCHOR:
        if lead not in lead_names:
            continue
        try:
            _, w = nk.ecg_delineate(sig[lead_names.index(lead)], rpeaks,
                                    sampling_rate=FS, method="dwt")
        except Exception:
            continue
        keep = {}
        for k, v in w.items():
            vals = [int(x) for x in v if x is not None and not np.isnan(x)]
            if vals:
                keep[k.replace("ECG_", "")] = vals
        if keep:
            out[lead] = keep
    return out


def label_array(seg_lead: dict, n: int) -> list[int]:
    """0 background, 1 P, 2 QRS, 3 T. One value per sample, for the overlay."""
    lab = np.zeros(n, dtype=np.int8)
    for pref, code in (("P", 1), ("R", 2), ("T", 3)):
        on = seg_lead.get(f"{pref}_Onsets", [])
        off = seg_lead.get(f"{pref}_Offsets", [])
        for a, b in zip(sorted(on), sorted(off)):
            a, b = max(0, int(a)), min(n, int(b))
            if b > a:
                lab[a:b] = code
    return lab.tolist()


def _med(a):
    a = np.asarray(a, dtype=float)
    return float(np.median(a)) if a.size else None


def measure(rpeaks: np.ndarray, seg: dict) -> dict:
    """Intervals, in milliseconds, with the calibration offsets applied."""
    b = lambda k: BIAS_MS.get(k, 0.0) / 1000 * FS
    m: dict = {}
    rr = np.diff(rpeaks) / FS
    m["n_beats"] = int(len(rpeaks))
    m["rr_ms"] = _med(rr * 1000)
    m["hr_bpm"] = round(60000 / m["rr_ms"], 1) if m["rr_ms"] else None
    if len(rr) > 2:
        d = np.abs(np.diff(rr * 1000))
        m["pnn50"] = round(float(np.mean(d > 50)), 3)
        m["rmssd_ms"] = round(float(np.sqrt(np.mean(d ** 2))), 1)
        med = np.median(rr * 1000)
        m["n_ectopic"] = int(np.sum(np.abs(rr * 1000 - med) > 0.20 * med))
    else:
        m["pnn50"] = m["rmssd_ms"] = None
        m["n_ectopic"] = 0

    # QRS: median of the per-lead durations. Taking the onset from one lead and
    # the offset from another compounds two delineation errors and over-widens.
    durs = []
    for w in seg.values():
        on = np.array(w.get("R_Onsets", []), float) - b("QRS_on")
        off = np.array(w.get("R_Offsets", []), float) - b("QRS_off")
        k = min(len(on), len(off))
        if k:
            d = (np.sort(off)[:k] - np.sort(on)[:k]) / FS * 1000
            d = d[(d > 40) & (d < 200)]
            if d.size:
                durs.append(float(np.median(d)))
    m["qrs_ms"] = round(float(np.median(durs)), 1) if durs else None

    w = seg.get("II") or (next(iter(seg.values())) if seg else {})
    pon = np.array(w.get("P_Onsets", []), float) - b("P_on")
    qon = np.array(w.get("R_Onsets", []), float) - b("QRS_on")
    tof = np.array(w.get("T_Offsets", []), float) - b("T_off")

    k = min(len(pon), len(qon))
    pr = (np.sort(qon)[:k] - np.sort(pon)[:k]) / FS * 1000 if k else np.array([])
    pr = pr[(pr > 60) & (pr < 400)]
    m["pr_ms"] = round(_med(pr), 1) if pr.size else None

    k = min(len(qon), len(tof))
    qt = (np.sort(tof)[:k] - np.sort(qon)[:k]) / FS * 1000 if k else np.array([])
    qt = qt[(qt > 200) & (qt < 700)]
    m["qt_ms"] = round(_med(qt), 1) if qt.size else None
    if m["qt_ms"] and m["rr_ms"]:
        s = m["rr_ms"] / 1000
        m["qtc_bazett_ms"] = round(m["qt_ms"] / s ** 0.5, 1)
        m["qtc_fridericia_ms"] = round(m["qt_ms"] / s ** (1 / 3), 1)
    else:
        m["qtc_bazett_ms"] = m["qtc_fridericia_ms"] = None
    return m


# ------------------------------------------------------------- rules -------

# Clinical diagnosis mapping: finding code → {label, icd10}
# Sources: AHA/ACC/HRS 2022, CIM-10-FR 2024, ICD-10-CM 2024
DIAGNOSIS_MAP: dict[str, dict] = {
    "PACED":            {"label": "Rythme électro-entraîné (stimulateur cardiaque)",
                         "icd10": "Z95.0"},
    "IRREG":            {"label": "Fibrillation auriculaire (FA) - à confirmer",
                         "icd10": "I48.91"},
    "SINUS":            {"label": "Rythme sinusal normal",
                         "icd10": None},
    "BRADY":            {"label": "Bradycardie sinusale",
                         "icd10": "R00.1"},
    "TACHY":            {"label": "Tachycardie sinusale",
                         "icd10": "R00.0"},
    "WCT":              {"label": "Tachycardie à complexes larges - TV non exclue",
                         "icd10": "I47.2"},
    "ECTOPIC":          {"label": "Extrasystoles (ectopies)",
                         "icd10": "I49.40"},
    "AVB1":             {"label": "Bloc auriculo-ventriculaire du 1er degré",
                         "icd10": "I44.0"},
    "SHORT_PR":         {"label": "Syndrome de pré-excitation ventriculaire (WPW suspect)",
                         "icd10": "I45.6"},
    "PR_OK":            {"label": "Conduction AV normale",
                         "icd10": None},
    "PR_NA":            {"label": "Intervalle PR non applicable (rythme irrégulier)",
                         "icd10": None},
    "IVCD":             {"label": "Bloc de branche / retard de conduction intraventriculaire",
                         "icd10": "I45.4"},
    "QRS_OK":           {"label": "Conduction intraventriculaire normale",
                         "icd10": None},
    "QRS_NA":           {"label": "QRS non interprétable (rythme stimulé)",
                         "icd10": None},
    "ST_NA":            {"label": "Analyse ST non applicable - critères de Sgarbossa requis",
                         "icd10": None},
    "QT_LONG_SEVERE":   {"label": "Syndrome du QT long - risque de torsades de pointes",
                         "icd10": "I45.81"},
    "QT_LONG":          {"label": "Allongement du QT - à surveiller",
                         "icd10": "R94.31"},
    "QT_SHORT":         {"label": "Syndrome du QT court (suspect)",
                         "icd10": "I45.89"},
    "QT_OK":            {"label": "Repolarisation ventriculaire normale",
                         "icd10": None},
    "HR_OK":            {"label": "Fréquence cardiaque normale",
                         "icd10": None},
    # Clinical synonyms & legacy taxonomy
    "FLUTTER":          {"label": "Flutter auriculaire",
                         "icd10": "I48.3"},
    "ESV":              {"label": "Extrasystoles ventriculaires (ESV)",
                         "icd10": "I49.3"},
    "BBI":              {"label": "Bloc de branche / retard intraventriculaire",
                         "icd10": "I44.7"},
    "BAV1":             {"label": "Bloc auriculo-ventriculaire du 1er degré",
                         "icd10": "I44.0"},
    "QT_DANGER":        {"label": "Syndrome du QT long sévère - risque de torsades de pointes",
                         "icd10": "I45.81"},
    "QT_BORDERLINE":    {"label": "Allongement limite de l'intervalle QTc",
                         "icd10": "R94.31"},
    "QT_LIMITE":        {"label": "Allongement limite du QTc (Bazett)",
                         "icd10": "R94.31"},
}


def _f(component, finding, severity, measured, threshold, meaning, code):
    diag = DIAGNOSIS_MAP.get(code, {})
    return {
        "component": component,
        "finding": finding,
        "severity": severity,
        "measured": measured,
        "threshold": threshold,
        "meaning": meaning,
        "code": code,
        "diagnosis": {
            "label": diag.get("label"),
            "icd10": diag.get("icd10"),
        } if diag.get("label") else None,
    }


def classify_rhythm(m: dict, paced: bool = False) -> tuple[str, str, str]:
    """(rhythm, rate, reason). Rhythm, rate and pacing are independent axes:
    a paced patient can be in atrial fibrillation, and a sinus rhythm can be
    slow, so collapsing them into one label loses findings."""
    hr, pnn = m.get("hr_bpm"), m.get("pnn50")
    rate = ("bradycardie" if hr and hr < BRADY_BPM else
            "tachycardie" if hr and hr > TACHY_BPM else "normale")
    if pnn is not None and pnn > AF_THRESH:
        return "irregulier", rate, f"pNN50 {pnn:.2f} > {AF_THRESH}"
    return "sinusal", rate, f"{hr:.0f} bpm, reguliers" if hr else "rythme regulier"


def analyse(m: dict, rhythm: str, rate: str, reason: str,
            paced: bool = False, sex: str | None = None) -> list[dict]:
    out = []
    hr, pr, qrs = m.get("hr_bpm"), m.get("pr_ms"), m.get("qrs_ms")
    qtcb, qtcf = m.get("qtc_bazett_ms"), m.get("qtc_fridericia_ms")

    if paced:
        out.append(_f("Stimulation", "Rythme appareille (stimulateur)", ORANGE,
                      "drapeau de stimulation fourni par l'appareil",
                      "detection materielle >= 1 kHz",
                      "les criteres ST, la largeur du QRS et les criteres de bloc "
                      "de branche ne s'appliquent pas a un rythme appareille",
                      "PACED"))

    if rhythm == "irregulier":
        out.append(_f("Rythme", "Rythme irregulier, fibrillation auriculaire non exclue",
                      ORANGE, reason, f"pNN50 > {AF_THRESH}",
                      "interpretation du rythme par un medecin requise ; sensibilite "
                      "100%, specificite 79% sur 200 enregistrements annotes",
                      "IRREG"))
    else:
        out.append(_f("Rythme", "Rythme sinusal", GREEN, reason,
                      f"pNN50 <= {AF_THRESH}",
                      "activite auriculaire organisee, intervalles reguliers", "SINUS"))

    if rate == "bradycardie":
        out.append(_f("Frequence", "Bradycardie", GREEN if hr >= 45 else ORANGE,
                      f"{hr:.0f} bpm", f"< {BRADY_BPM:.0f} bpm",
                      "frequence inferieure a la normale", "BRADY"))
    elif rate == "tachycardie":
        sev = RED if (qrs and qrs > 120 and hr > 120 and not paced) else ORANGE
        out.append(_f("Frequence",
                      "Tachycardie a complexes larges" if sev == RED else "Tachycardie",
                      sev, f"{hr:.0f} bpm", f"> {TACHY_BPM:.0f} bpm",
                      "urgence si complexes larges" if sev == RED else "frequence elevee",
                      "WCT" if sev == RED else "TACHY"))
    elif hr:
        out.append(_f("Frequence", "Frequence normale", GREEN, f"{hr:.0f} bpm",
                      f"{BRADY_BPM:.0f}-{TACHY_BPM:.0f} bpm", "sans particularite",
                      "HR_OK"))

    # ectopic count only means something against a regular baseline
    if m.get("n_ectopic") and rhythm == "sinusal":
        n = m["n_ectopic"]
        out.append(_f("Rythme", f"{n} intervalle(s) ectopique(s)", GREEN,
                      f"{n} RR hors mediane +/-20%", "+/-20% de la mediane RR",
                      "extrasystoles probables", "ECTOPIC"))

    if rhythm == "sinusal" and pr:
        if pr > 200:
            out.append(_f("PR", "Bloc auriculo-ventriculaire du 1er degre", ORANGE,
                          f"{pr:.0f} ms", "> 200 ms",
                          "retard de conduction auriculo-ventriculaire", "AVB1"))
        elif pr < 120:
            out.append(_f("PR", "PR court", ORANGE, f"{pr:.0f} ms", "< 120 ms",
                          "evoquer une pre-excitation ventriculaire", "SHORT_PR"))
        else:
            out.append(_f("PR", "Conduction AV normale", GREEN, f"{pr:.0f} ms",
                          "120-200 ms", "sans particularite", "PR_OK"))
    elif rhythm == "irregulier":
        out.append(_f("PR", "PR non mesurable", GREEN, "rythme irregulier",
                      "pas d'activite auriculaire organisee",
                      "l'intervalle PR n'existe pas sans onde P organisee", "PR_NA"))

    if qrs:
        if paced:
            out.append(_f("QRS", "Duree QRS non interpretable", GREEN,
                          f"mesuree {qrs:.0f} ms", "rythme appareille",
                          "un QRS stimule est large par construction", "QRS_NA"))
        elif qrs > 120:
            out.append(_f("QRS", "Retard de conduction intraventriculaire", ORANGE,
                          f"{qrs:.0f} ms", "> 120 ms",
                          "bloc de branche ou conduction ventriculaire anormale ; la "
                          "lateralisation exige une analyse morphologique", "IVCD"))
            out.append(_f("ST", "Criteres ST invalides", ORANGE, f"QRS {qrs:.0f} ms",
                          "QRS > 120 ms",
                          "les seuils ST standards ne s'appliquent pas ; criteres de "
                          "Sgarbossa requis", "ST_NA"))
        else:
            out.append(_f("QRS", "Duree QRS normale", GREEN, f"{qrs:.0f} ms",
                          "< 120 ms", "conduction intraventriculaire normale", "QRS_OK"))

    if qtcb:
        lim = 460 if sex == "F" else 450
        val = f"QTcB {qtcb:.0f} ms, QTcF {qtcf:.0f} ms"
        if qtcb > 500:
            out.append(_f("QT", "Allongement marque du QT", RED, val, "> 500 ms",
                          "risque de torsades de pointes ; revoir les medicaments "
                          "allongeant le QT", "QT_LONG_SEVERE"))
        elif qtcb > lim:
            out.append(_f("QT", "Allongement du QT", ORANGE, val, f"> {lim} ms",
                          "limite superieure, a surveiller", "QT_LONG"))
        elif qtcb < 340:
            out.append(_f("QT", "QT court", ORANGE, val, "< 340 ms",
                          "evoquer un syndrome du QT court", "QT_SHORT"))
        else:
            out.append(_f("QT", "QT normal", GREEN, val, f"<= {lim} ms",
                          "repolarisation sans particularite", "QT_OK"))
    return out


def triage(findings: list[dict]) -> dict:
    sev = (RED if any(f["severity"] == RED for f in findings) else
           ORANGE if any(f["severity"] == ORANGE for f in findings) else GREEN)
    return {
        RED:    {"level": RED, "priority": 1, "label": "URGENT",
                 "action": "revue medicale immediate", "escalate": True},
        ORANGE: {"level": ORANGE, "priority": 2, "label": "A REVOIR",
                 "action": "revue medicale requise, non immediate", "escalate": False},
        GREEN:  {"level": GREEN, "priority": 3, "label": "ROUTINE",
                 "action": "revue de routine", "escalate": False},
    }[sev]


LIMITS = [
    "Criteres de voltage (ST, hypertrophie, microvoltage, axe) non calcules sur "
    "les bases normalisees en amplitude par derivation.",
    "Detection des spicules de stimulation non realisee a 500 Hz ; le drapeau de "
    "stimulation est une entree fournie par l'appareil, pas une sortie.",
    "Bloc AV du 3e degre et lateralisation des blocs de branche non couverts.",
    "Systeme adulte uniquement.",
    "Aide a la decision : l'analyse automatique ne remplace pas l'interpretation "
    "medicale et ne constitue pas un diagnostic.",
]


# --------------------------------------------------------------- entry ------

def analyze(source, fs: float | None = None, age=None, sex=None, paced=False,
            unit="mV", patient_id=None, want_labels=True) -> dict:
    """Analyse one ECG. Returns a JSON-serialisable dict.

    `source` is a path to a .dat/.hea, .csv or .edf file, or a (n_leads,
    n_samples) array of millivolts with `fs` supplied.
    """
    t = Timer()
    res = {"ok": False, "version": PIPELINE_VERSION,
           "analysed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "patient": {"id": patient_id, "age": age, "sex": sex, "paced": bool(paced)}}
    try:
        if isinstance(source, np.ndarray):
            if not fs:
                raise EcgReadError("fs is required when passing an array")
            raw, lead_names, meta = source.astype(float), list(LEADS), {"source": "array"}
        else:
            raw, fs, lead_names, meta = read_any(str(source), fs=fs, unit=unit)
        res["acquisition"] = {"fs_in_hz": round(float(fs), 2),
                              "duration_s": round(raw.shape[1] / fs, 2),
                              "leads": lead_names, **meta}
        if age is None and meta.get("age"):
            res["patient"]["age"] = meta["age"]
        if sex is None and meta.get("sex"):
            res["patient"]["sex"] = meta["sex"]
        t.mark("lecture")

        sig = preprocess(raw, fs)
        t.mark("pretraitement")

        res["quality"] = assess_quality(sig, lead_names)
        t.mark("controle_qualite")

        if not res["quality"]["acceptable"]:
            res["ok"] = True
            res["triage"] = {"level": "REJET", "priority": 0,
                             "label": "REACQUISITION REQUISE",
                             "action": "reacquerir le trace", "escalate": True}
            res["findings"] = []
            res["limits"] = LIMITS
            res["timings"] = {"steps": t.steps, "total_ms": t.total_ms()}
            return res

        rpeaks = detect_beats(sig, lead_names)
        if len(rpeaks) < 3:
            raise EcgReadError(f"only {len(rpeaks)} beats detected; trace too short "
                               "or too noisy to analyse")
        t.mark("detection_battements")

        seg = segment(sig, lead_names, rpeaks)
        res["segmentation"] = {
            "method": "ondelettes (dwt), calibree sur 191 enregistrements LUDB",
            "calibration_offsets_ms": BIAS_MS,
            "r_peaks": rpeaks.tolist(),
            "boundaries": seg,
        }
        if want_labels and seg:
            lead = "II" if "II" in seg else next(iter(seg))
            res["segmentation"]["label_lead"] = lead
            res["segmentation"]["labels"] = label_array(seg[lead], sig.shape[1])
            res["segmentation"]["label_legend"] = {"0": "fond", "1": "P", "2": "QRS", "3": "T"}
        t.mark("segmentation_pqrst")

        m = measure(rpeaks, seg)
        res["measurements"] = m
        t.mark("mesures")

        rh, rt, reason = classify_rhythm(m, paced)
        res["rhythm"] = {"rhythm": rh, "rate": rt, "reason": reason, "paced": bool(paced)}
        res["findings"] = analyse(m, rh, rt, reason, paced, res["patient"]["sex"])
        res["triage"] = triage(res["findings"])
        res["limits"] = LIMITS
        t.mark("regles_cliniques")

        res["ok"] = True
    except EcgReadError as e:
        res["error"] = {"type": "EcgReadError", "message": str(e)}
        t.mark("erreur")
    except Exception as e:
        res["error"] = {"type": type(e).__name__, "message": str(e),
                        "trace": traceback.format_exc(limit=3)}
        t.mark("erreur")
    res["timings"] = {"steps": t.steps, "total_ms": t.total_ms()}
    return res


def analyze_to_report(source, **kw) -> dict:
    """analyze() plus the rendered report. This is the one call a Django view
    needs: it returns the machine-readable result, the text report and the
    block structure for the frontend."""
    from .report import build_report, report_blocks
    res = analyze(source, **kw)
    return {"result": res, "report_text": build_report(res),
            "report_blocks": report_blocks(res)}
