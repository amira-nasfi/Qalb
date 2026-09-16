"""
Utility functions for reports.
"""

def generate_draft(flags: list) -> str:
    """
    Generate a human-readable draft clinical summary based on the raised flags.
    Expects a list of dictionaries with at least 'code', 'label', 'severity'.
    """
    if not flags:
        return "No flags detected. ECG appears normal."

    # Check for NORMAL_SINUS
    if any(f.get("code") == "NORMAL_SINUS" for f in flags):
        return "Normal sinus rhythm. All computed intervals are within normal limits."

    lines = ["Automated ECG analysis detected the following:"]

    criticals = [f for f in flags if f.get("severity") == "CRITICAL"]
    warnings = [f for f in flags if f.get("severity") == "WARNING"]
    infos = [f for f in flags if f.get("severity") == "INFO" and f.get("code") != "NORMAL_SINUS"]

    if criticals:
        lines.append("\n** CRITICAL FINDINGS **")
        for f in criticals:
            lines.append(f"- {f.get('label')}")

    if warnings:
        lines.append("\n* Warnings *")
        for f in warnings:
            lines.append(f"- {f.get('label')}")

    if infos:
        lines.append("\n* Informational *")
        for f in infos:
            lines.append(f"- {f.get('label')}")

    return "\n".join(lines)
