"""
FastAPI entry point.

Run locally:
    uvicorn app.main:app --reload

Endpoints:
    POST /chat            -> run the agent for one turn
    GET  /audit            -> full audit log (JSON, for the dashboard)
    GET  /audit/{session}  -> audit log filtered to one session
    GET  /dashboard        -> simple HTML dashboard (static/dashboard.html)
"""
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()  # must run before app.razorpay_client reads env vars at import time

from app import audit, catalog, db
from app.agent import run_agent
from app.models import ChatRequest, ChatResponse

app = FastAPI(title="Merchant Upsell Agent", version="0.1.0")

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
def on_startup():
    db.init_db()


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    return run_agent(req)


@app.get("/catalog")
def get_catalog():
    """Used by the chat UI to populate a cart picker."""
    return catalog.load_catalog()


@app.get("/audit")
def get_audit():
    return audit.all_entries()


@app.get("/audit/{session_id}")
def get_audit_for_session(session_id: str):
    return audit.entries_for_session(session_id)


@app.get("/dashboard")
def dashboard():
    return FileResponse("static/dashboard.html")


@app.get("/chat-ui")
def chat_ui():
    return FileResponse("static/chat.html")


@app.get("/health")
def health():
    return {"status": "ok"}
