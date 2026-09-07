"""
Coded tool: ActionRecommenderTool
Turns the evaluator's verdict + blockers into a concrete, ordered
remediation checklist ("next actions") so the output is actionable, not
just a yes/no. Also emits the full audit trail collected in sly_data for
traceability, which is valuable for the hackathon's evaluation criteria.
"""

from typing import Any, Dict, List, Union

from neuro_san.interfaces.coded_tool import CodedTool

from .dra_utils import append_audit

# Maps a blocker keyword to a concrete owner + recommended action.
_ACTION_PLAYBOOK = [
    ("Missing approvals", "Change Manager", "Chase the outstanding approver(s) and obtain sign-off in the CHG record."),
    ("objection", "Requesting Team", "Engage the objecting team to resolve or formally withdraw the objection before proceeding."),
    ("load balancer", "Network Team", "Remove the server from the load balancer pool and confirm no live traffic."),
    ("Backup jobs", "Backup/Storage Team", "Disable and remove scheduled backup jobs for the server."),
    ("DNS PTR", "Directory Services Team", "Remove the DNS A/PTR records and confirm resolution is cleared."),
    ("Monitoring alerts", "Monitoring Team", "Disable and delete monitoring alerts/agents for the server."),
    ("open incident", "Service Desk", "Close or reassign the open incident(s) linked to the server."),
]


class ActionRecommenderTool(CodedTool):
    """Produces an ordered remediation plan from the verdict + blockers."""

    def invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Union[Dict[str, Any], str]:
        verdict = args.get("verdict", "UNKNOWN")
        blockers: List[str] = args.get("blockers") or []

        actions: List[Dict[str, str]] = []
        for blocker in blockers:
            for keyword, owner, action in _ACTION_PLAYBOOK:
                if keyword.lower() in blocker.lower():
                    actions.append({"blocker": blocker, "owner": owner, "recommended_action": action})
                    break
            else:
                actions.append({"blocker": blocker, "owner": "Change Manager", "recommended_action": "Review and resolve this blocker."})

        if verdict == "GO":
            next_actions_summary = "No remediation required. Proceed with the scheduled decommission."
        elif verdict == "CONDITIONAL-GO":
            next_actions_summary = "Complete the technical cleanup actions below, then re-run the readiness check."
        else:
            next_actions_summary = "Resolve the blocking actions below before this server can be decommissioned."

        audit_trail = (sly_data or {}).get("dra_audit_trail", [])

        result = {
            "verdict": verdict,
            "next_actions_summary": next_actions_summary,
            "remediation_plan": actions,
            "audit_trail": audit_trail,
        }
        append_audit(sly_data, "action_recommender", {"num_actions": len(actions)})
        return result

    async def async_invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Union[Dict[str, Any], str]:
        return self.invoke(args, sly_data)
