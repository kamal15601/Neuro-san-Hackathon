"""
Coded tool: ReadinessEvaluatorTool  (enhanced)
The deterministic evaluation loop. Applies a weighted readiness checklist
to the combined findings and returns a GO / CONDITIONAL-GO / NO-GO verdict
plus a confidence score and a completeness check on its own inputs.

Key reliability feature: it validates that it actually received all the
evidence it needs. If any investigator's data is missing, it lowers its
own confidence and flags the gap rather than silently issuing a verdict
on incomplete evidence.
"""

from typing import Any, Dict, List, Union

from neuro_san.interfaces.coded_tool import CodedTool

from .dra_utils import append_audit


class ReadinessEvaluatorTool(CodedTool):
    """Applies the readiness checklist and returns a verdict + confidence."""

    def invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Union[Dict[str, Any], str]:
        required_approvers: List[str] = args.get("required_approvers") or []
        approvals_received: List[str] = args.get("approvals_received") or []
        has_unresolved_objections = bool(args.get("has_unresolved_objections", False))
        outstanding_risks: List[str] = args.get("outstanding_risks") or []
        risk_score = int(args.get("risk_score", 0) or 0)

        # --- Input completeness check (self-validation) ------------------
        missing_inputs: List[str] = []
        if not required_approvers:
            missing_inputs.append("required_approvers (from TicketLookupAgent)")
        if args.get("has_unresolved_objections") is None:
            missing_inputs.append("has_unresolved_objections (from CommScannerAgent)")
        if args.get("risk_score") is None and not outstanding_risks:
            missing_inputs.append("risk data (from RiskAnalyzerAgent)")

        # Confidence starts high and is reduced for each missing evidence source.
        confidence = 1.0 - (0.25 * len(missing_inputs))
        confidence = max(0.0, round(confidence, 2))

        # --- Checklist ---------------------------------------------------
        missing_approvals = [a for a in required_approvers if a not in approvals_received]
        checklist = {
            "all_approvals_received": len(missing_approvals) == 0,
            "no_unresolved_scream_test_objections": not has_unresolved_objections,
            "no_outstanding_technical_risks": len(outstanding_risks) == 0,
        }

        blockers: List[str] = []
        if missing_approvals:
            blockers.append(f"Missing approvals from: {', '.join(missing_approvals)}")
        if has_unresolved_objections:
            blockers.append("Unresolved scream-test objection(s) present")
        if outstanding_risks:
            blockers.append(f"Outstanding technical risks: {', '.join(outstanding_risks)}")

        # --- Verdict logic ----------------------------------------------
        # Hard blockers (governance): missing approvals or objections => NO-GO.
        # Technical-only risk with all approvals + no objections => CONDITIONAL-GO
        #   (safe once the listed low/medium technical cleanup is completed).
        governance_blocked = bool(missing_approvals) or has_unresolved_objections
        if governance_blocked:
            verdict = "NO-GO"
        elif outstanding_risks:
            verdict = "CONDITIONAL-GO" if risk_score <= 60 else "NO-GO"
        else:
            verdict = "GO"

        if verdict == "GO":
            summary = "All readiness checks passed. Safe to proceed with decommission."
        elif verdict == "CONDITIONAL-GO":
            summary = (
                "Governance checks passed (approvals + scream test), but technical "
                "cleanup is still outstanding. Safe to proceed ONLY after the listed "
                "technical items are completed."
            )
        else:
            summary = "Decommission must be held until the listed blockers are resolved."

        result = {
            "verdict": verdict,
            "confidence": confidence,
            "checklist": checklist,
            "blockers": blockers,
            "risk_score": risk_score,
            "evidence_complete": len(missing_inputs) == 0,
            "missing_evidence": missing_inputs,
            "summary": summary,
        }
        append_audit(sly_data, "readiness_evaluator", result)
        return result

    async def async_invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Union[Dict[str, Any], str]:
        return self.invoke(args, sly_data)
