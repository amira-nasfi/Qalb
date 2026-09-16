"""
HL7 FHIR R4 Bundle builder for ECG reports.
"""

from reports.models import Report

LOINC_ECG_STUDY = "11524-6"
LOINC_PR = "8625-6"
LOINC_QRS = "8633-2"
LOINC_QTC = "8634-0"
LOINC_HR = "8867-4"

EXTENSION_URL = "https://qalb.health/fhir/extensions/ecg-flag"


def build_observation(report: Report) -> dict:
    """FHIR R4 Observation resource with one component per interval."""
    intervals = report.result.intervals_json

    components = []
    
    # HR
    if intervals.get("hr_bpm") and intervals["hr_bpm"].get("median") is not None:
        components.append({
            "code": {"coding": [{"system": "http://loinc.org", "code": LOINC_HR}]},
            "valueQuantity": {
                "value": intervals["hr_bpm"]["median"],
                "unit": "/min",
                "system": "http://unitsofmeasure.org"
            }
        })
        
    # PR
    if intervals.get("pr_ms") and intervals["pr_ms"].get("median") is not None:
        components.append({
            "code": {"coding": [{"system": "http://loinc.org", "code": LOINC_PR}]},
            "valueQuantity": {
                "value": intervals["pr_ms"]["median"],
                "unit": "ms",
                "system": "http://unitsofmeasure.org"
            }
        })
        
    # QRS
    if intervals.get("qrs_ms") and intervals["qrs_ms"].get("median") is not None:
        components.append({
            "code": {"coding": [{"system": "http://loinc.org", "code": LOINC_QRS}]},
            "valueQuantity": {
                "value": intervals["qrs_ms"]["median"],
                "unit": "ms",
                "system": "http://unitsofmeasure.org"
            }
        })

    # QTc (Bazett)
    if intervals.get("qtc_bazett") and intervals["qtc_bazett"].get("median") is not None:
        components.append({
            "code": {"coding": [{"system": "http://loinc.org", "code": LOINC_QTC}]},
            "valueQuantity": {
                "value": intervals["qtc_bazett"]["median"],
                "unit": "ms",
                "system": "http://unitsofmeasure.org"
            }
        })

    pseudo_id = str(report.result.record.patient.pseudo_id)
    
    return {
        "resourceType": "Observation",
        "id": f"obs-{report.id}",
        "status": "final",
        "code": {
            "coding": [{"system": "http://loinc.org", "code": LOINC_ECG_STUDY}]
        },
        "subject": {
            "reference": f"Patient/{pseudo_id}"
        },
        "effectiveDateTime": report.result.record.uploaded_at.isoformat(),
        "component": components
    }


def build_diagnostic_report(report: Report, obs_id: str) -> dict:
    """FHIR R4 DiagnosticReport with flags as extensions."""
    flags = report.result.flags_json

    extensions = []
    for f in flags:
        extensions.append({
            "url": EXTENSION_URL,
            "extension": [
                {"url": "code", "valueString": f.get("code")},
                {"url": "measured_value", "valueDecimal": f.get("measured_value")},
                {"url": "threshold", "valueDecimal": f.get("threshold")},
                {"url": "unit", "valueString": f.get("unit")},
                {"url": "severity", "valueString": f.get("severity")},
                {"url": "citation", "valueString": f.get("citation")},
            ]
        })
        
    pseudo_id = str(report.result.record.patient.pseudo_id)

    return {
        "resourceType": "DiagnosticReport",
        "id": f"dr-{report.id}",
        "status": "final",
        "code": {
            "coding": [{"system": "http://loinc.org", "code": LOINC_ECG_STUDY}]
        },
        "subject": {
            "reference": f"Patient/{pseudo_id}"
        },
        "effectiveDateTime": report.result.record.uploaded_at.isoformat(),
        "issued": report.signed_at.isoformat() if report.signed_at else None,
        "performer": [
            {
                "display": report.signed_by.get_full_name() if report.signed_by else "Unknown"
            }
        ],
        "result": [
            {"reference": f"Observation/{obs_id}"}
        ],
        "conclusion": report.physician_notes,
        "extension": extensions
    }


def build_bundle(report: Report) -> dict:
    """FHIR Bundle wrapping both resources."""
    obs = build_observation(report)
    dr = build_diagnostic_report(report, obs["id"])

    return {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {"resource": obs},
            {"resource": dr}
        ]
    }
