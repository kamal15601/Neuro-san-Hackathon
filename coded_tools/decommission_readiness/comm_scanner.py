"""
Coded tool: CommScannerTool  (enhanced)
Checks scream-test communication status for a server, with normalization,
fuzzy resolution, scream-test window validation, graceful errors, and an
audit-trail entry.
"""

from datetime import date, datetime
from typing import Any, Dict, Optional, Union

from neuro_san.interfaces.coded_tool import CodedTool

from .dra_utils import append_audit, load_dataset, resolve_server_and_ticket


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


class CommScannerTool(CodedTool):
    """Reports scream-test status and objections for a server."""

    def invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Union[Dict[str, Any], str]:
        identifier = args.get("server") or args.get("identifier") or ""
        _ticket, server, notes = resolve_server_and_ticket(identifier)

        emails = load_dataset("emails")
        if server is None or server not in emails:
            result = {
                "resolved": False,
                "error": f"No communication record for '{identifier}'.",
                "resolution_notes": notes,
                "available_servers": list(emails.keys()),
            }
            append_audit(sly_data, "comm_scanner", result)
            return result

        record = dict(emails[server])
        objections = record.get("objections_received", []) or []
        sent = bool(record.get("scream_test_sent"))

        # Validate the scream-test window has actually elapsed.
        window_elapsed = None
        sent_date = _parse_date(record.get("scream_test_sent_date"))
        window_days = record.get("scream_test_window_days", 0)
        if sent and sent_date is not None:
            window_elapsed = (date.today() - sent_date).days >= window_days

        result = {
            "resolved": True,
            "server": server,
            "scream_test_sent": sent,
            "scream_test_window_elapsed": window_elapsed,
            "objections_received": objections,
            "has_unresolved_objections": len(objections) > 0,
            "resolution_notes": notes,
            "notes": record.get("notes"),
        }
        append_audit(sly_data, "comm_scanner", result)
        return result

    async def async_invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Union[Dict[str, Any], str]:
        return self.invoke(args, sly_data)
