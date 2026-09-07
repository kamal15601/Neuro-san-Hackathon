"""
Coded tool: IntakeResolverTool
The reliability pre-step of the DRA workflow. Takes ANY user identifier
(server name or ticket id, possibly messy/typo'd) and resolves it to the
canonical ticket_id AND server name before any investigation begins.

This prevents the three investigator agents from each independently
mis-parsing the input, and guarantees they all operate on the same
canonical server name.
"""

from typing import Any, Dict, Union

from neuro_san.interfaces.coded_tool import CodedTool

from .dra_utils import append_audit, resolve_server_and_ticket


class IntakeResolverTool(CodedTool):
    """Resolves a raw identifier into canonical {ticket_id, server}."""

    def invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Union[Dict[str, Any], str]:
        identifier = args.get("identifier") or args.get("server_or_ticket") or ""
        ticket_id, server, notes = resolve_server_and_ticket(identifier)

        resolved = ticket_id is not None and server is not None
        result = {
            "input": identifier,
            "resolved": resolved,
            "ticket_id": ticket_id,
            "server": server,
            "resolution_notes": notes,
        }
        append_audit(sly_data, "intake_resolver", result)
        if not resolved:
            result["error"] = (
                f"Could not resolve '{identifier}' to a known server or ticket. "
                "Ask the user to confirm the server name or CHG ticket id."
            )
        return result

    async def async_invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Union[Dict[str, Any], str]:
        return self.invoke(args, sly_data)
