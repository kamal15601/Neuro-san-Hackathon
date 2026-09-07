"""
Coded tool: TicketLookupTool  (enhanced)
Looks up a change/decommission ticket and reports approval status,
with input normalization, fuzzy matching, graceful errors, and an
audit-trail entry.
"""

from typing import Any, Dict, List, Union

from neuro_san.interfaces.coded_tool import CodedTool

from .dra_utils import append_audit, load_dataset, resolve_server_and_ticket


class TicketLookupTool(CodedTool):
    """Returns approval/status info for a change ticket."""

    def invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Union[Dict[str, Any], str]:
        identifier = args.get("ticket_id") or args.get("server") or args.get("identifier") or ""
        ticket_id, server, notes = resolve_server_and_ticket(identifier)

        tickets = load_dataset("tickets")
        if ticket_id is None or ticket_id not in tickets:
            result = {
                "resolved": False,
                "error": f"No matching ticket for '{identifier}'.",
                "resolution_notes": notes,
                "available_tickets": list(tickets.keys()),
            }
            append_audit(sly_data, "ticket_lookup", result)
            return result

        record = dict(tickets[ticket_id])
        required: List[str] = record.get("required_approvers", [])
        received: List[str] = record.get("approvals_received", [])
        missing = [a for a in required if a not in received]

        result = {
            "resolved": True,
            "ticket_id": ticket_id,
            "server": server,
            "status": record.get("status"),
            "business_criticality": record.get("business_criticality", "Unknown"),
            "required_approvers": required,
            "approvals_received": received,
            "missing_approvals": missing,
            "all_approvals_received": len(missing) == 0,
            "scheduled_decommission_date": record.get("scheduled_decommission_date"),
            "resolution_notes": notes,
            "notes": record.get("notes"),
        }
        append_audit(sly_data, "ticket_lookup", result)
        return result

    async def async_invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Union[Dict[str, Any], str]:
        return self.invoke(args, sly_data)
