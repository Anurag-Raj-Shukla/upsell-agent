"""
Unit tests for the policy engine — this is the file that proves the
"bounded" claim in the architecture diagram, not just asserts it.

Run:
    pytest tests/test_policy.py -v

Each test targets exactly one rule so a failure tells you precisely which
policy guarantee broke.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from app import db, policy
from app.models import Suggestion


@pytest.fixture(autouse=True)
def clean_db(tmp_path, monkeypatch):
    """Point the db module at a throwaway sqlite file per test so tests
    never share session-count state with each other or with dev data."""
    test_db_path = tmp_path / "test.db"
    monkeypatch.setattr(db, "DB_PATH", test_db_path)
    db.init_db()
    yield
    if test_db_path.exists():
        test_db_path.unlink()


def make_suggestion(sku="sku_001", discount=10.0) -> Suggestion:
    return Suggestion(sku=sku, name="Wireless Mouse", reason="test", suggested_discount_pct=discount)


def test_unknown_sku_is_rejected():
    decision = policy.evaluate("s1", make_suggestion(sku="sku_does_not_exist"))
    assert not decision.approved
    assert decision.rejection_reason == "Unknown SKU"


def test_out_of_stock_item_is_rejected():
    # sku_003 (Laptop Stand) has stock: 0 in data/catalog.json
    decision = policy.evaluate("s1", make_suggestion(sku="sku_003", discount=5.0))
    assert not decision.approved
    assert "stock" in decision.rejection_reason.lower()


def test_discount_within_limit_is_approved_unchanged():
    # sku_001 margin_pct=35, so 10% discount is well within both caps
    decision = policy.evaluate("s1", make_suggestion(sku="sku_001", discount=10.0))
    assert decision.approved
    assert decision.final_discount_pct == 10.0


def test_discount_above_ceiling_is_clamped_not_rejected():
    # MAX_DISCOUNT_PCT = 15.0 — asking for 50% should clamp to 15%, not reject
    decision = policy.evaluate("s1", make_suggestion(sku="sku_001", discount=50.0))
    assert decision.approved
    assert decision.final_discount_pct == 15.0
    assert any("CLAMPED" in step for step in decision.rule_trail if "max_discount_cap" in step)


def test_discount_that_would_breach_margin_floor_is_clamped():
    # sku_006 (Webcam) margin_pct=18, MARGIN_FLOOR_PCT=10 -> max allowed discount is 8%
    decision = policy.evaluate("s1", make_suggestion(sku="sku_006", discount=15.0))
    assert decision.approved
    assert decision.final_discount_pct == pytest.approx(8.0)


def test_discount_rejected_when_margin_too_thin_for_any_discount():
    # sku_006 margin_pct=18; if MARGIN_FLOOR were higher than margin, no discount survives.
    # Simulate by requesting a product whose margin already sits at the floor via a tiny
    # discount ask of 0 -- covered by the "approved unchanged" test above instead; here we
    # directly test the reject branch using a monkeypatched floor.
    original_floor = policy.MARGIN_FLOOR_PCT
    policy.MARGIN_FLOOR_PCT = 100.0  # impossible floor forces rejection
    try:
        decision = policy.evaluate("s1", make_suggestion(sku="sku_006", discount=5.0))
        assert not decision.approved
        assert "margin" in decision.rejection_reason.lower()
    finally:
        policy.MARGIN_FLOOR_PCT = original_floor


def test_session_frequency_cap_blocks_after_limit():
    # MAX_SUGGESTIONS_PER_SESSION = 3
    session = "capped-session"
    for _ in range(policy.MAX_SUGGESTIONS_PER_SESSION):
        decision = policy.evaluate(session, make_suggestion())
        assert decision.approved

    fourth = policy.evaluate(session, make_suggestion())
    assert not fourth.approved
    assert "limit" in fourth.rejection_reason.lower()


def test_reset_session_clears_frequency_cap():
    session = "reset-session"
    for _ in range(policy.MAX_SUGGESTIONS_PER_SESSION):
        policy.evaluate(session, make_suggestion())

    policy.reset_session(session)
    decision = policy.evaluate(session, make_suggestion())
    assert decision.approved


def test_rule_trail_is_never_empty_on_approval():
    decision = policy.evaluate("s1", make_suggestion())
    assert len(decision.rule_trail) > 0


def test_rule_trail_is_never_empty_on_rejection():
    decision = policy.evaluate("s1", make_suggestion(sku="unknown"))
    assert len(decision.rule_trail) > 0
