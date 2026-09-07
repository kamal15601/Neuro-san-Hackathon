# Decommission Readiness Agent (DRA) — Enhanced v2

Cognizant AI Lab Agentic AI Hackathon · Track 2 (Neuro SAN Studio)

A production-minded multi-agent network that decides whether a server is
safe to decommission — now with reliability engineering, weighted risk
scoring, a 3-state verdict, confidence scoring, a remediation planner, an
audit trail, and a passing unit-test suite.

---

## What's new vs. v1 (enhancements)

| Area | v1 | v2 (this) |
|---|---|---|
| Agents | 4 | **6** (added Intake/Resolver + Action Recommender) |
| Input handling | exact match only | **normalization + fuzzy matching** (typos like `app-db-04` resolve) |
| Error handling | basic | **graceful structured errors** everywhere, never raises |
| Verdict | GO / NO-GO | **GO / CONDITIONAL-GO / NO-GO** |
| Risk | flat pass/fail | **weighted 0–100 risk score + band** (LB > backups > DNS > monitoring) |
| Reliability | — | **confidence score + self-check for missing evidence** |
| Output | verdict only | **verdict + ordered remediation plan with owners** |
| Traceability | — | **audit trail via sly_data** (every step recorded) |
| Testing | — | **23 unit tests, all passing** |

---

## File layout

```
registries/
  decommission_readiness.hocon          # 6-agent network definition
coded_tools/decommission_readiness/
  __init__.py
  dra_utils.py                          # shared reliability helpers (load/normalize/fuzzy/audit)
  intake_resolver.py                    # agent 1 tool
  ticket_lookup.py                      # agent 2 tool
  comm_scanner.py                       # agent 3 tool
  risk_analyzer.py                      # agent 4 tool (weighted scoring)
  readiness_evaluator.py                # agent 5 tool (deterministic eval loop)
  action_recommender.py                 # agent 6 tool (remediation plan + audit)
  data/
    tickets.json                        # synthetic
    emails.json                         # synthetic
    dependencies.json                   # synthetic
tests/
  test_dra_logic.py                     # 23 unit tests (no server needed)
```

## Install into your project

```bash
cp registries/decommission_readiness.hocon  ~/neuro-san-hackathon/registries/
cp -r coded_tools/decommission_readiness    ~/neuro-san-hackathon/coded_tools/
cp -r tests                                 ~/neuro-san-hackathon/        # optional
```

Then register it in `registries/manifest.hocon` (mirror the `music_nerd`
entry):

```hocon
{
    "music_nerd.hocon": true,
    "decommission_readiness.hocon": true
}
```

Restart:

```bash
ns run
```

`DecommissionReadinessAgent` will appear in the nsflow "Available Agents"
list.

## Run the tests (great to show judges)

From the project root:

```bash
python tests/test_dra_logic.py
# expected: ==== RESULTS: 23 passed, 0 failed ====
```

## Demo script — 4 verdicts + reliability

| Input | Verdict | Why |
|---|---|---|
| `Check decommission readiness for CHG0012345` | **NO-GO** | Missing DBA approval + DNS/monitoring active |
| `Check decommission readiness for WEB-FE-017` | **NO-GO** | Unresolved scream-test objection |
| `Check decommission readiness for BATCH-JOB-009` | **CONDITIONAL-GO** | Approved, but backups/monitoring/incident cleanup pending (risk 55) |
| `Check decommission readiness for CHG0012500` | **GO** | Fully clean end-to-end |
| `Check decommission readiness for app-db-04` | **NO-GO** | **Fuzzy match** resolves typo → APP-DB-042 |
| `Check decommission readiness for nonsense-xyz` | *(no verdict)* | Gracefully asks user to confirm the id |

## The 6-agent workflow

```
User input (server or ticket, typos ok)
        │
        ▼
DecommissionReadinessAgent (FrontMan, Gemini reasoning + AAOSA delegation)
   │
   ├─1─▶ IntakeResolverAgent    → normalize + fuzzy-resolve → canonical ticket_id + server
   │
   ├─2─▶ TicketLookupAgent      → approvals / missing approvals / criticality
   ├─3─▶ CommScannerAgent       → scream-test sent? window elapsed? objections?
   ├─4─▶ RiskAnalyzerAgent      → weighted risk score (0–100) + outstanding deps
   │
   ├─5─▶ ReadinessEvaluatorAgent → deterministic checklist → GO/CONDITIONAL-GO/NO-GO
   │                               + confidence + missing-evidence self-check
   │
   └─6─▶ ActionRecommenderAgent → ordered remediation plan w/ owners + audit trail
        │
        ▼
FrontMan composes structured final report (verdict, evidence, plan)
```

## How this maps to the judging criteria

- **Multi-agent coordination** — 6 agents, hierarchical AAOSA delegation.
- **Tool usage** — every non-frontman agent wraps a real Python CodedTool.
- **Task planning** — FrontMan enforces resolve → investigate(×3) → evaluate → recommend.
- **Evaluation loop** — `ReadinessEvaluatorTool` is deterministic code that
  re-checks evidence AND validates its own input completeness (confidence
  drops if any investigator's data is missing).
- **Reliability** — normalization, fuzzy matching, graceful errors, weighted
  scoring, confidence, audit trail, and a green unit-test suite.
- **Impact / real-world** — mirrors a genuine enterprise change-management
  workflow that is manual and error-prone today.

## Extending to production (talking point for your write-up)

Swap the `load_dataset(...)` calls in each tool for real integrations:
ServiceNow API (tickets), Microsoft Graph / Exchange (scream-test emails),
and a CMDB / monitoring API (dependencies). The agent logic, scoring, and
evaluation loop stay identical — only the data source changes.

## Don't forget
⭐ Star https://github.com/cognizant-ai-lab/neuro-san-studio before submitting.
