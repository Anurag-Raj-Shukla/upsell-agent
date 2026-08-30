"""
Policy engine — this is the "coral box" from the architecture diagram.

Nothing the LangGraph agent proposes reaches Razorpay without passing
through here first. Every rule below should be independently testable
and independently loggable (rule_trail), so the audit dashboard can show
*why* a suggestion was approved or rejected — not just the outcome.

Day 3-6 TODO: tune thresholds, add real inventory/margin data source.
"""
from app.catalog import get_product, in_stock
from app import db
from app.models import PolicyDecision, Suggestion

# --- Tunable policy constants -------------------------------------------
MAX_DISCOUNT_PCT = 15.0        # hard ceiling on any single discount
MARGIN_FLOOR_PCT = 10.0        # never let (margin - discount) drop below this
MAX_SUGGESTIONS_PER_SESSION = 3  # session frequency cap
# -------------------------------------------------------------------------


def evaluate(session_id: str, suggestion: Suggestion) -> PolicyDecision:
    """Run a suggestion through every policy rule in sequence.
    Returns a PolicyDecision with a full rule_trail for auditability."""
    trail: list[str] = []

    product = get_product(suggestion.sku)
    if not product:
        trail.append("catalog_lookup: FAILED (unknown sku)")
        return PolicyDecision(
            sku=suggestion.sku, approved=False, final_discount_pct=0.0,
            rejection_reason="Unknown SKU", rule_trail=trail,
        )
    trail.append(f"catalog_lookup: OK ({product['name']})")

    # Rule 1: inventory check
    if not in_stock(suggestion.sku):
        trail.append("inventory_check: FAILED (out of stock)")
        return PolicyDecision(
            sku=suggestion.sku, approved=False, final_discount_pct=0.0,
            rejection_reason="Item out of stock", rule_trail=trail,
        )
    trail.append("inventory_check: OK")

    # Rule 2: session frequency cap
    count = db.increment_session_count(session_id)
    if count > MAX_SUGGESTIONS_PER_SESSION:
        trail.append(f"session_frequency_cap: FAILED ({count} > {MAX_SUGGESTIONS_PER_SESSION})")
        return PolicyDecision(
            sku=suggestion.sku, approved=False, final_discount_pct=0.0,
            rejection_reason="Session suggestion limit reached", rule_trail=trail,
        )
    trail.append(f"session_frequency_cap: OK ({count}/{MAX_SUGGESTIONS_PER_SESSION})")

    # Rule 3: max discount ceiling
    discount = min(suggestion.suggested_discount_pct, MAX_DISCOUNT_PCT)
    if suggestion.suggested_discount_pct > MAX_DISCOUNT_PCT:
        trail.append(
            f"max_discount_cap: CLAMPED ({suggestion.suggested_discount_pct}% -> {discount}%)"
        )
    else:
        trail.append(f"max_discount_cap: OK ({discount}%)")

    # Rule 4: margin floor — never discount below margin_floor_pct
    projected_margin = product["margin_pct"] - discount
    if projected_margin < MARGIN_FLOOR_PCT:
        # try to salvage by reducing the discount to the max allowed by margin floor
        max_allowed_discount = max(0.0, product["margin_pct"] - MARGIN_FLOOR_PCT)
        if max_allowed_discount <= 0:
            trail.append(
                f"margin_floor_check: FAILED (margin {product['margin_pct']}% too thin)"
            )
            return PolicyDecision(
                sku=suggestion.sku, approved=False, final_discount_pct=0.0,
                rejection_reason="Discount would breach margin floor", rule_trail=trail,
            )
        trail.append(
            f"margin_floor_check: CLAMPED ({discount}% -> {max_allowed_discount}%)"
        )
        discount = max_allowed_discount
    else:
        trail.append(f"margin_floor_check: OK (projected margin {projected_margin}%)")

    return PolicyDecision(
        sku=suggestion.sku, approved=True, final_discount_pct=round(discount, 2),
        rule_trail=trail,
    )


def reset_session(session_id: str) -> None:
    """Utility for tests / demo resets."""
    db.reset_session_count(session_id)
