
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "app.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_conn():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Creates tables if they don't exist. Safe to call on every startup."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                session_id TEXT NOT NULL,
                suggestion_json TEXT NOT NULL,
                policy_decision_json TEXT NOT NULL,
                executed_action_json TEXT,
                agent_reasoning TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS session_counts (
                session_id TEXT PRIMARY KEY,
                count INTEGER NOT NULL DEFAULT 0
            )
        """)


# --- Audit entries --------------------------------------------------------

def insert_audit_entry(entry: dict) -> None:
    """entry keys: timestamp (datetime), session_id, suggestion (dict),
    policy_decision (dict), executed_action (dict|None), agent_reasoning (str)"""
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO audit_entries
               (timestamp, session_id, suggestion_json, policy_decision_json,
                executed_action_json, agent_reasoning)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                entry["timestamp"].isoformat() if isinstance(entry["timestamp"], datetime) else entry["timestamp"],
                entry["session_id"],
                json.dumps(entry["suggestion"]),
                json.dumps(entry["policy_decision"]),
                json.dumps(entry["executed_action"]) if entry.get("executed_action") else None,
                entry.get("agent_reasoning", ""),
            ),
        )


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "timestamp": row["timestamp"],
        "session_id": row["session_id"],
        "suggestion": json.loads(row["suggestion_json"]),
        "policy_decision": json.loads(row["policy_decision_json"]),
        "executed_action": json.loads(row["executed_action_json"]) if row["executed_action_json"] else None,
        "agent_reasoning": row["agent_reasoning"],
    }


def all_audit_entries() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM audit_entries ORDER BY id ASC").fetchall()
        return [_row_to_dict(r) for r in rows]


def audit_entries_for_session(session_id: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM audit_entries WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]


def clear_audit() -> None:
    """Utility for tests / demo resets."""
    with get_conn() as conn:
        conn.execute("DELETE FROM audit_entries")


# --- Session counters -------------------------------------------------------

def increment_session_count(session_id: str) -> int:
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO session_counts (session_id, count) VALUES (?, 1)
               ON CONFLICT(session_id) DO UPDATE SET count = count + 1""",
            (session_id,),
        )
        row = conn.execute(
            "SELECT count FROM session_counts WHERE session_id = ?", (session_id,)
        ).fetchone()
        return row["count"]


def reset_session_count(session_id: str) -> None:
    """Utility for tests / demo resets."""
    with get_conn() as conn:
        conn.execute("DELETE FROM session_counts WHERE session_id = ?", (session_id,))
