# Merchant Upsell / Cross-sell Agent

An agent that looks at a customer's cart, proposes relevant upsell/cross-sell
items from the catalog, and only ever acts on those suggestions **inside a
bounded policy engine** — every money-moving action is explainable, capped,
and logged before it ever touches Razorpay.

## Architecture

```
Chat interface  →  LangGraph agent  →  Policy engine  →  Razorpay test API
(customer/merchant)  (reasons over        (bounds every       (executes
                       cart + catalog)      money action)       bounded action)
                                                │                    │
                                                └────────► Audit log ┘
                                                                 │
                                                          Admin dashboard
                                                        (trace + outcomes)
```

- **Purple layer (reasoning):** chat interface + LangGraph agent. Free to
  suggest anything — has zero authority to execute money actions directly.
- **Coral layer (bounded execution):** policy engine, Razorpay test API,
  audit log. Every suggestion must pass policy before execution; every
  outcome (approved or rejected) is logged.
- **Gray layer (monitoring):** admin dashboard, read-only.

## Policy rules (the "bounded" part, made explicit)

| Rule | Constant | Behavior |
|---|---|---|
| Max discount ceiling | `MAX_DISCOUNT_PCT = 15%` | Clamps any suggested discount above this |
| Margin floor | `MARGIN_FLOOR_PCT = 10%` | Rejects or clamps discount if it would push margin below floor |
| Inventory check | — | Rejects suggestion if item is out of stock |
| Session frequency cap | `MAX_SUGGESTIONS_PER_SESSION = 3` | Rejects suggestions beyond this count per session |

See `app/policy.py` for the implementation and full rule trail logic.

## Project layout

```
app/
  main.py            FastAPI routes (/chat, /catalog, /audit, /dashboard, /chat-ui)
  agent.py           LangGraph graph: propose (LLM) → policy_check → execute → reply
  policy.py           Policy engine — the bounded execution layer
  catalog.py          Mock catalog loader
  razorpay_client.py  Razorpay test-mode wrapper (mocked until keys added)
  audit.py            Audit log (SQLite-backed via db.py)
  db.py                SQLite persistence: audit entries + session counters
  models.py            Shared Pydantic models
data/
  catalog.json        Mock product catalog
  app.db               SQLite file (created on first run, gitignored)
static/
  dashboard.html      Admin dashboard (trace + outcomes)
  chat.html            Customer-facing chat UI
tests/
  test_policy.py       Unit tests for every policy rule
```

## Setup

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in keys once you have them
uvicorn app.main:app --reload
```

- Chat UI: http://localhost:8000/chat-ui
- Admin dashboard: http://localhost:8000/dashboard
- Raw API: http://localhost:8000/chat

## Running tests

```bash
pytest tests/ -v
```

Each test targets exactly one policy rule (unknown SKU, out-of-stock,
discount ceiling, margin floor, session cap) so a failure tells you
precisely which "bounded" guarantee broke.

## Example request

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "demo-1",
    "message": "what should I add to my cart?",
    "cart": [{"sku": "sku_001", "quantity": 1}]
  }'
```

## Build plan (10 days)

- **Day 1-2:** Catalog + policy rules — done in this scaffold, tune as needed
- **Day 3-5:** Real LLM reasoning in `agent.py` (done — routes to Claude when
  `ANTHROPIC_API_KEY` is set, falls back to a rule-based stub otherwise),
  prompt-injection guard (done — see SYSTEM_PROMPT in agent.py)
- **Day 6-7:** Wire real Razorpay test keys into `razorpay_client.py`
- **Day 8:** Persist audit log to SQLite (done — see db.py), polish dashboard
- **Day 9:** Failure handling — out-of-stock mid-conversation (tested),
  Razorpay API failure (handled via try/except in razorpay_client.py),
  retry/session-cap loop guard (tested)
- **Day 10:** README polish, architecture diagram, 5-min pitch video

## Remaining gaps before submission

- `razorpay_client.py` runs in mock mode until `RAZORPAY_KEY_ID`/`SECRET` are set
- `agent.py` runs in rule-based fallback mode until `ANTHROPIC_API_KEY` is set
- No deployment yet — see hosting notes (Render recommended for the free tier)
- Chat UI (`static/chat.html`) is intentionally minimal — functional, not styled for production
