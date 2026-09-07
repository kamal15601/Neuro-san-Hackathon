"""
Shared reliability utilities for the Decommission Readiness Agent (DRA).

Centralizes:
  * safe, cached loading of the synthetic JSON datasets
  * input normalization (case / whitespace / common prefixes)
  * fuzzy matching so minor typos in server/ticket names still resolve
  * a small audit-trail helper for traceability

Keeping this logic in one place means every coded tool behaves
consistently and fails gracefully instead of throwing raw exceptions.
"""

import difflib
import json
import os
from typing import Any, Dict, List, Optional, Tuple

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# Simple in-process cache so we don't re-read files on every invocation.
_CACHE: Dict[str, Dict[str, Any]] = {}


def load_dataset(name: str) -> Dict[str, Any]:
    """
    Safely load a dataset by base name (e.g. "tickets", "emails",
    "dependencies"). Returns {} on any failure rather than raising, so a
    missing/corrupt file degrades gracefully.
    """
    if name in _CACHE:
        return _CACHE[name]
    path = os.path.join(_DATA_DIR, f"{name}.json")
    try:
        with open(path, "r", encoding="utf-8") as file_handle:
            data = json.load(file_handle)
        if not isinstance(data, dict):
            data = {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        data = {}
    _CACHE[name] = data
    return data


def normalize_key(raw: Optional[str]) -> str:
    """
    Normalize a user-supplied identifier: strip whitespace, collapse
    internal spaces, and uppercase (server names and CHG ids are
    conventionally uppercase). Returns "" for None/empty input.
    """
    if not raw:
        return ""
    return " ".join(str(raw).strip().split()).upper()


def looks_like_ticket_id(value: str) -> bool:
    """
    Heuristic: a change ticket id in this system starts with 'CHG'
    followed by digits. Used to decide lookup strategy.
    """
    v = normalize_key(value)
    return v.startswith("CHG") and any(ch.isdigit() for ch in v)


def fuzzy_match(candidate: str, choices: List[str], cutoff: float = 0.6) -> Optional[str]:
    """
    Return the single closest match for `candidate` among `choices`
    (case-insensitive), or None if nothing clears the similarity cutoff.
    Lets minor typos like 'APP-DB-04' or 'appdb042' still resolve.
    """
    candidate_n = normalize_key(candidate)
    if not candidate_n or not choices:
        return None

    # Exact (normalized) match first.
    norm_map = {normalize_key(c): c for c in choices}
    if candidate_n in norm_map:
        return norm_map[candidate_n]

    # Fall back to difflib similarity on normalized keys.
    best = difflib.get_close_matches(candidate_n, list(norm_map.keys()), n=1, cutoff=cutoff)
    if best:
        return norm_map[best[0]]
    return None


def resolve_server_and_ticket(
    identifier: str,
) -> Tuple[Optional[str], Optional[str], List[str]]:
    """
    Given any identifier (server name OR ticket id, possibly with typos),
    resolve BOTH the canonical ticket id and canonical server name.

    Returns (ticket_id, server, notes) where notes is a list of
    human-readable resolution notes (e.g. that a fuzzy match was used).
    Either ticket_id or server may be None if unresolved.
    """
    notes: List[str] = []
    tickets = load_dataset("tickets")
    ident_n = normalize_key(identifier)

    if not ident_n:
        notes.append("Empty identifier supplied.")
        return None, None, notes

    # Build lookup structures.
    ticket_ids = list(tickets.keys())
    server_to_ticket = {
        normalize_key(rec.get("server", "")): tid for tid, rec in tickets.items()
    }

    # Strategy 1: treat as a ticket id.
    if looks_like_ticket_id(ident_n):
        matched_ticket = fuzzy_match(ident_n, ticket_ids)
        if matched_ticket:
            if normalize_key(matched_ticket) != ident_n:
                notes.append(f"Interpreted '{identifier}' as ticket '{matched_ticket}' (fuzzy match).")
            server = tickets[matched_ticket].get("server")
            return matched_ticket, server, notes

    # Strategy 2: treat as a server name.
    matched_server_key = fuzzy_match(ident_n, list(server_to_ticket.keys()))
    if matched_server_key:
        tid = server_to_ticket[matched_server_key]
        server = tickets[tid].get("server")
        if matched_server_key != ident_n:
            notes.append(f"Interpreted '{identifier}' as server '{server}' (fuzzy match).")
        return tid, server, notes

    # Strategy 3: last-ditch, try ticket-id fuzzy even if it didn't look like one.
    matched_ticket = fuzzy_match(ident_n, ticket_ids)
    if matched_ticket:
        notes.append(f"Interpreted '{identifier}' as ticket '{matched_ticket}' (fuzzy match).")
        server = tickets[matched_ticket].get("server")
        return matched_ticket, server, notes

    notes.append(
        f"Could not resolve '{identifier}'. Known tickets: {ticket_ids}; "
        f"known servers: {[tickets[t].get('server') for t in ticket_ids]}."
    )
    return None, None, notes


def append_audit(sly_data: Dict[str, Any], step: str, detail: Any) -> None:
    """
    Append a structured entry to an audit trail stored in sly_data.
    sly_data travels privately between agents/tools, so this builds a
    traceable, citable record of every check performed without exposing
    it to the LLM prompt text.
    """
    if sly_data is None:
        return
    trail = sly_data.setdefault("dra_audit_trail", [])
    trail.append({"step": step, "detail": detail})
