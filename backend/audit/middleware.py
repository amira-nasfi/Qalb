"""
Audit middleware — automatically logs every significant API request.

Logs are created for:
  - POST requests (CREATE actions)
  - PATCH / PUT requests (UPDATE actions)
  - DELETE requests (if ever permitted)
  - 403 / 404 responses (PERMISSION_DENY)

GET requests to sensitive resources (reports, ECG results) are logged as VIEW.
GET requests to public/static endpoints are not logged.
"""

import logging

logger = logging.getLogger("audit")

# Paths where GET requests should be logged as VIEW events
AUDITED_GET_PATHS = [
    "/api/reports/",
    "/api/ecg/",
    "/api/fhir/",
]

# Path prefixes to completely skip logging (health checks, static files, etc.)
SKIP_PATH_PREFIXES = [
    "/django-admin/",
    "/static/",
    "/media/",
    "/api/admin/kpis",   # polled every 30 s — too noisy to log every time
]


class AuditMiddleware:
    """
    Lightweight middleware that creates AuditLog entries after the response
    is generated. Uses lazy import to avoid circular dependencies.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        self._log(request, response)
        return response

    def _log(self, request, response):
        path = request.path

        # Skip noisy / non-clinical paths
        for prefix in SKIP_PATH_PREFIXES:
            if path.startswith(prefix):
                return

        method = request.method
        status = response.status_code

        # Determine what to log
        action = None

        if method == "POST":
            action = "CREATE"
        elif method in ("PATCH", "PUT"):
            action = "UPDATE"
        elif method == "DELETE":
            action = "DELETE"
        elif method == "GET" and any(path.startswith(p) for p in AUDITED_GET_PATHS):
            action = "VIEW"
        elif status == 403:
            action = "PERMISSION_DENY"

        if action is None:
            return

        try:
            from audit.models import AuditLog, AuditAction

            action_map = {
                "CREATE": AuditAction.CREATE,
                "UPDATE": AuditAction.UPDATE,
                "VIEW": AuditAction.VIEW,
                "PERMISSION_DENY": AuditAction.PERMISSION_DENY,
            }

            actor = getattr(request, "user", None)

            AuditLog.log(
                action=action_map.get(
                    action,
                    action),
                target_type=self._infer_target_type(path),
                target_id=self._infer_target_id(path),
                actor=actor if (
                    actor and hasattr(
                        actor,
                        "is_authenticated") and actor.is_authenticated) else None,
                request=request,
                extra={
                    "http_method": method,
                    "path": path,
                    "status_code": status,
                },
            )
        except Exception as exc:  # never let audit failures break the request
            logger.error("AuditMiddleware failed: %s", exc, exc_info=True)

    @staticmethod
    def _infer_target_type(path: str) -> str:
        """Derive a target_type label from the URL path."""
        if "/reports/" in path:
            return "Report"
        if "/ecg/" in path:
            return "ECGRecord"
        if "/patients/" in path:
            return "Patient"
        if "/fhir/" in path:
            return "FHIRExport"
        return "Unknown"

    @staticmethod
    def _infer_target_id(path: str) -> str:
        """
        Extract the resource ID from the URL path.
        e.g. /api/reports/42/sign/ → "42"
        """
        parts = [
            p for p in path.split("/") if p and p not in (
                "api",
                "reports",
                "ecg",
                "patients",
                "fhir",
                "sign",
                "status",
                "signal",
                "fhir")]
        return parts[-1] if parts else "list"
