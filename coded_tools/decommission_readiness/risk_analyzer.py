"""
Coded tool: RiskAnalyzerTool  (enhanced)
Checks technical dependency risks for a server and computes a WEIGHTED
risk score (0-100) rather than a flat pass/fail, so higher-impact
dependencies (e.g. still in a load balancer pool) count more heavily.
Includes normalization, fuzzy resolution, graceful errors, and audit.
"""

from typing import Any, Dict, List, Union

from neuro_san.interfaces.coded_tool import CodedTool

from .dra_utils import append_audit, load_dataset, resolve_server_and_ticket

# Weighted risk model: each active dependency contributes points toward a
# 0-100 risk score. Higher weight = more dangerous to decommission.
_RISK_WEIGHTS = {
    "load_balancer_member": (40, "Still a member of a load balancer pool (live traffic risk)"),
    "backup_jobs_active": (25, "Backup jobs still scheduled"),
    "dns_ptr_record_active": (20, "DNS PTR record still active"),
    "monitoring_alerts_active": (15, "Monitoring alerts still active"),
}


class RiskAnalyzerTool(CodedTool):
    """Reports outstanding technical dependencies and a weighted risk score."""

    def invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Union[Dict[str, Any], str]:
        identifier = args.get("server") or args.get("identifier") or ""
        _ticket, server, notes = resolve_server_and_ticket(identifier)

        deps = load_dataset("dependencies")
        if server is None or server not in deps:
            result = {
                "resolved": False,
                "error": f"No dependency record for '{identifier}'.",
                "resolution_notes": notes,
                "available_servers": list(deps.keys()),
            }
            append_audit(sly_data, "risk_analyzer", result)
            return result

        record = dict(deps[server])
        outstanding: List[str] = []
        risk_score = 0
        for field, (weight, label) in _RISK_WEIGHTS.items():
            if record.get(field):
                outstanding.append(label)
                risk_score += weight

        open_incidents = int(record.get("open_incidents", 0) or 0)
        if open_incidents > 0:
            outstanding.append(f"{open_incidents} open incident(s) linked to server")
            risk_score += min(30, 15 * open_incidents)

        risk_score = min(100, risk_score)
        if risk_score == 0:
            risk_band = "None"
        elif risk_score <= 30:
            risk_band = "Low"
        elif risk_score <= 60:
            risk_band = "Medium"
        else:
            risk_band = "High"

        result = {
            "resolved": True,
            "server": server,
            "outstanding_risks": outstanding,
            "risk_score": risk_score,
            "risk_band": risk_band,
            "is_clean": len(outstanding) == 0,
            "resolution_notes": notes,
            "notes": record.get("notes"),
        }
        append_audit(sly_data, "risk_analyzer", result)
        return result

    async def async_invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Union[Dict[str, Any], str]:
        return self.invoke(args, sly_data)
