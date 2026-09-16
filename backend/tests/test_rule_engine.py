from ecg.pipeline.intervals import IntervalResult, Measurement
from ecg.pipeline.rule_engine import apply_rules, severity_summary


def _meas(val, unit="ms"):
    return Measurement(median=val, iqr=0.0, unit=unit, formula_ref="", n_valid=10)


def _intervals(hr=70, pr=150, qrs=90, qt=400, qtc=410, partial=False):
    return IntervalResult(
        hr_bpm=_meas(hr, "bpm") if hr else None,
        pr_ms=_meas(pr) if pr else None,
        qrs_ms=_meas(qrs) if qrs else None,
        qt_ms=_meas(qt) if qt else None,
        qtc_bazett=_meas(qtc) if qtc else None,
        qtc_fridericia=_meas(qtc) if qtc else None,
        n_beats=10,
        partial=partial,
        lead_used="II",
        delineation_rate=1.0,
    )


def test_normal_sinus():
    intervals = _intervals()
    flags = apply_rules(intervals, sex="M")
    assert len(flags) == 1
    assert flags[0].code == "NORMAL_SINUS"
    assert flags[0].severity == "INFO"


def test_critical_qtc():
    intervals = _intervals(qtc=510)
    flags = apply_rules(intervals, sex="F")
    # Should flag critical QTC
    assert len(flags) == 1
    assert flags[0].code == "QTC_CRITICAL"
    assert flags[0].severity == "CRITICAL"


def test_severity_summary():
    flags = [
        apply_rules(_intervals(hr=40), "M")[0],  # BRADYCARDIA (WARNING)
    ]
    assert severity_summary(flags) == "URGENT"

    flags.append(apply_rules(_intervals(qtc=550), "M")[0])  # QTC_CRITICAL (CRITICAL)
    assert severity_summary(flags) == "CRITICAL"
