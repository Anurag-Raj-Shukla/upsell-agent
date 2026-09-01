
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field


class CartItem(BaseModel):
    sku: str
    quantity: int = 1


class ChatRequest(BaseModel):
    session_id: str
    message: str
    cart: list[CartItem] = Field(default_factory=list)


class Suggestion(BaseModel):
    """A single upsell/cross-sell candidate proposed by the agent,
    BEFORE it has been checked by the policy engine."""
    sku: str
    name: str
    reason: str  # agent's natural-language justification
    suggested_discount_pct: float = 0.0


class PolicyDecision(BaseModel):
    """Output of the policy engine for one suggestion."""
    sku: str
    approved: bool
    final_discount_pct: float
    rejection_reason: Optional[str] = None
    rule_trail: list[str] = Field(default_factory=list)  # which rules were checked


class ExecutedAction(BaseModel):
    sku: str
    action_type: Literal["payment_link_update", "order_amount_update", "none"]
    razorpay_ref: Optional[str] = None
    status: Literal["success", "failed", "skipped"]
    detail: Optional[str] = None


class AuditEntry(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    session_id: str
    suggestion: Suggestion
    policy_decision: PolicyDecision
    executed_action: Optional[ExecutedAction] = None
    agent_reasoning: str = ""


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    audit_entries: list[AuditEntry] = Field(default_factory=list)
