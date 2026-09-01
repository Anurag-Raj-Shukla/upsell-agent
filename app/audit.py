
from app import db
from app.models import AuditEntry


def record(entry: AuditEntry) -> None:
    db.insert_audit_entry({
        "timestamp": entry.timestamp,
        "session_id": entry.session_id,
        "suggestion": entry.suggestion.model_dump(),
        "policy_decision": entry.policy_decision.model_dump(),
        "executed_action": entry.executed_action.model_dump() if entry.executed_action else None,
        "agent_reasoning": entry.agent_reasoning,
    })


def all_entries() -> list[dict]:
    """Returns raw dicts (already JSON-serializable) — used directly by the
    /audit API route, no need to round-trip through AuditEntry again."""
    return db.all_audit_entries()


def entries_for_session(session_id: str) -> list[dict]:
    return db.audit_entries_for_session(session_id)


def clear() -> None:
    """Utility for tests / demo resets."""
    db.clear_audit()
