"""Report rendering. Deterministic slot filling: no text is generated, every
line is assembled from a measured value and the rule that produced it.

Two renderers from the same result dict: plain text for the signed PDF, and a
dict of blocks for the React view.
"""
from __future__ import annotations

SEV_ORDER = {"RED": 0, "ORANGE": 1, "GREEN": 2}
COMPONENT_ORDER = ["Stimulation", "Rythme", "Frequence", "PR", "QRS", "ST", "QT"]


def _n(v, unit="", ref=""):
    s = "non mesurable" if v is None else f"{v:g}{unit}"
    return f"{s}{('        ' + ref) if ref else ''}"


def build_report(res: dict, include_reference: str | None = None) -> str:
    """Plain-text report, ready for signature or PDF conversion."""
    if not res.get("ok"):
        e = res.get("error", {})
        return (f"ANALYSE IMPOSSIBLE\n{e.get('type','')}: {e.get('message','')}\n"
                "Le trace doit etre reacquis.")

    q, tri, pat = res["quality"], res["triage"], res["patient"]
    m = res.get("measurements", {})
    L = []
    A = L.append
    A("=" * 74)
    A("COMPTE RENDU ECG - ANALYSE AUTOMATISEE")
    A(f"Dossier : {pat.get('id') or 'non renseigne'}    "
      f"Age : {pat.get('age') or 'inconnu'}    Sexe : {pat.get('sex') or 'inconnu'}")
    A(f"Acquis  : {res['acquisition']['duration_s']} s, "
      f"{res['acquisition']['fs_in_hz']} Hz, "
      f"{len(res['acquisition']['leads'])} derivations")
    A(f"Analyse : {res['analysed_at']}   ({res['timings']['total_ms']} ms)")
    A("=" * 74)

    A("\n1. QUALITE ET RECEVABILITE")
    A(f"   Verdict               : "
      f"{'exploitable' if q['acceptable'] else 'NON EXPLOITABLE'}")
    A(f"   Derivations degradees : "
      f"{', '.join(q['failed_leads']) if q['failed_leads'] else 'aucune'}")
    A(f"   Derivations manquantes: "
      f"{', '.join(q['missing_leads']) if q['missing_leads'] else 'aucune'}")
    for lead, rs in q["per_lead"].items():
        for r in rs:
            A(f"      {lead}: {r}")

    if not q["acceptable"]:
        A("\n   ARRET : aucune interpretation produite. Reacquerir le trace.")
        A("-" * 74)
        return "\n".join(L)

    A("\n2. MESURES")
    A(f"   Battements analyses   : {m.get('n_beats')}")
    A(f"   Frequence cardiaque   : {_n(m.get('hr_bpm'),' bpm','[60-90]')}")
    A(f"   Intervalle RR         : {_n(m.get('rr_ms'),' ms')}")
    A(f"   pNN50                 : {_n(m.get('pnn50'),'','[<= 0.35]')}")
    pr = (_n(m.get("pr_ms"), " ms", "[120-200]")
          if res["rhythm"]["rhythm"] == "sinusal"
          else "non applicable (rythme irregulier)")
    A(f"   Intervalle PR         : {pr}")
    A(f"   Duree QRS             : {_n(m.get('qrs_ms'),' ms','[< 120]')}")
    A(f"   Intervalle QT         : {_n(m.get('qt_ms'),' ms')}")
    A(f"   QTc Bazett            : {_n(m.get('qtc_bazett_ms'),' ms')}")
    A(f"   QTc Fridericia        : {_n(m.get('qtc_fridericia_ms'),' ms')}")

    A("\n3. ANALYSE PAR COMPOSANTE DU COMPLEXE PQRST")
    for comp in COMPONENT_ORDER:
        for f in [x for x in res["findings"] if x["component"] == comp]:
            A(f"   {f['component']:<12} [{f['severity']}] {f['finding']}")
            A(f"   {'':<12}  mesure   : {f['measured']}")
            A(f"   {'':<12}  seuil    : {f['threshold']}")
            A(f"   {'':<12}  sens     : {f['meaning']}")
            diag = f.get("diagnosis")
            if diag and diag.get("label") and (f.get("severity") != "GREEN" or diag.get("icd10")):
                icd = f" [CIM-10: {diag['icd10']}]" if diag.get("icd10") else ""
                A(f"   {'':<12}  anomalie : {diag['label']}{icd}")

    A("\n4. CONCLUSION")
    flagged = [f for f in res["findings"] if f["severity"] != "GREEN"]
    if not flagged:
        A("   Trace sans anomalie detectee par les criteres appliques.")
    for f in sorted(flagged, key=lambda x: SEV_ORDER[x["severity"]]):
        diag = f.get("diagnosis")
        diag_txt = f" -> {diag['label']} (CIM-10: {diag['icd10']})" if (diag and diag.get("icd10")) else ""
        A(f"   - [{f['severity']:6s}] {f['finding']}   ({f['measured']}){diag_txt}")

    A("\n5. PRIORITE DE PRISE EN CHARGE")
    A(f"   PRIORITE {tri['priority']} - {tri['label']}")
    A(f"   {tri['action']}")
    if tri["escalate"]:
        A("   ESCALADE DECLENCHEE")

    A("\n6. DELAIS PAR ETAPE")
    for s in res["timings"]["steps"]:
        A(f"   {s['step']:<24} {s['duration_ms']:>8.1f} ms")
    A(f"   {'TOTAL':<24} {res['timings']['total_ms']:>8.1f} ms")

    A("\n7. LIMITES DECLAREES")
    for limit in res["limits"]:
        A(f"   - {limit}")

    if include_reference:
        A(f"\n8. REFERENCE (annotation existante)\n   {include_reference}")

    A("\n" + "-" * 74)
    A("GARDE-FOU : document d'aide a la decision. L'IA signale, elle n'interprete")
    A("pas. Seul un professionnel habilite interprete, signe et engage la conduite")
    A("a tenir.")
    A(f"Version du moteur : {res['version']}")
    A("Medecin interprete : ____________________  Signature : ______________")
    A("Date et heure      : ____________________")
    A("-" * 74)
    return "\n".join(L)


def report_blocks(res: dict) -> dict:
    """Same content as a dict of blocks, for the React view to render."""
    if not res.get("ok"):
        return {"ok": False, "error": res.get("error")}
    m = res.get("measurements", {})
    return {
        "ok": True,
        "header": {"patient": res["patient"], "acquisition": res["acquisition"],
                   "analysed_at": res["analysed_at"],
                   "total_ms": res["timings"]["total_ms"]},
        "quality": res["quality"],
        "measurements": [
            {"label": "Frequence cardiaque", "value": m.get("hr_bpm"), "unit": "bpm",
             "ref": "60-90"},
            {"label": "Intervalle RR", "value": m.get("rr_ms"), "unit": "ms", "ref": ""},
            {"label": "pNN50", "value": m.get("pnn50"), "unit": "", "ref": "<= 0.35"},
            {"label": "Intervalle PR", "value": m.get("pr_ms"), "unit": "ms",
             "ref": "120-200",
             "na": res["rhythm"]["rhythm"] != "sinusal"},
            {"label": "Duree QRS", "value": m.get("qrs_ms"), "unit": "ms", "ref": "< 120"},
            {"label": "Intervalle QT", "value": m.get("qt_ms"), "unit": "ms", "ref": ""},
            {"label": "QTc Bazett", "value": m.get("qtc_bazett_ms"), "unit": "ms",
             "ref": "<= 450 H / 460 F"},
            {"label": "QTc Fridericia", "value": m.get("qtc_fridericia_ms"),
             "unit": "ms", "ref": ""},
        ],
        "findings": sorted(res["findings"], key=lambda x: SEV_ORDER[x["severity"]]),
        "triage": res["triage"],
        "timings": res["timings"]["steps"],
        "limits": res["limits"],
        "segmentation": res.get("segmentation", {}),
    }
