"""
main.py  –  FastAPI backend for Keystroke Logging Demonstration System
========================================================================
Educational / ethical demo only.  DO NOT use for malicious purposes.

Endpoints
---------
POST /api/login            – authenticate & get session token
POST /api/logout           – revoke session token
POST /api/logger/start     – start keystroke capture
POST /api/logger/stop      – stop keystroke capture
POST /api/logger/reset     – stop + clear in-memory buffer + storage
GET  /api/logger/status    – current status (running, total, kpm)
GET  /api/keystrokes        – last N keystrokes from in-memory buffer
GET  /api/stats            – aggregate statistics from stored data
GET  /api/charts           – base64 chart images (bar, kpm, pie)
GET  /api/export/csv       – download full CSV report
POST /api/change-password  – change the app password

WS   /ws/live              – WebSocket: real-time keystroke stream
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from typing import Any, Dict, Optional

# Make sure backend modules are importable
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import (
    FastAPI, WebSocket, WebSocketDisconnect,
    HTTPException, Depends, Request, Query
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel

import auth
import logger as logger_module
import storage
import analysis

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Keystroke Logging Demonstration System",
    description=(
        "⚠️  FOR EDUCATIONAL & ETHICAL USE ONLY.  "
        "This API demonstrates how keystroke logging works "
        "and how to detect/prevent it."
    ),
    version="1.0.0",
)

# Allow the frontend (served from a different origin during dev) to talk to us
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Single shared logger instance
_logger = logger_module.KeystrokeLogger(persist=True)


# ---------------------------------------------------------------------------
# Session dependency
# ---------------------------------------------------------------------------
def get_session_token(request: Request) -> str:
    token = request.headers.get("X-Session-Token") or request.cookies.get("session_token")
    if not token or not auth.validate_session(token):
        raise HTTPException(status_code=401, detail="Invalid or expired session.")
    return token


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------
class LoginRequest(BaseModel):
    password: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------
@app.post("/api/login", tags=["Auth"])
def login(body: LoginRequest) -> Dict[str, Any]:
    """Validate password and return a session token."""
    token = auth.create_session(body.password)
    if not token:
        raise HTTPException(status_code=401, detail="Incorrect password.")
    return {"token": token, "message": "Login successful."}


@app.post("/api/logout", tags=["Auth"])
def logout(token: str = Depends(get_session_token)) -> Dict[str, str]:
    auth.revoke_session(token)
    return {"message": "Logged out successfully."}


@app.post("/api/change-password", tags=["Auth"])
def change_password(
    body: ChangePasswordRequest,
    _token: str = Depends(get_session_token),
) -> Dict[str, str]:
    success = auth.change_password(body.old_password, body.new_password)
    if not success:
        raise HTTPException(status_code=400, detail="Old password is incorrect.")
    return {"message": "Password changed successfully."}


# ---------------------------------------------------------------------------
# Logger control endpoints
# ---------------------------------------------------------------------------
@app.post("/api/logger/start", tags=["Logger"])
def start_logger(_token: str = Depends(get_session_token)) -> Dict[str, str]:
    """⚡ Begins capturing keystrokes (explicit user action required)."""
    _logger.start()
    return {"status": "running", "message": "Keystroke logging started."}


@app.post("/api/logger/stop", tags=["Logger"])
def stop_logger(_token: str = Depends(get_session_token)) -> Dict[str, str]:
    _logger.stop()
    return {"status": "stopped", "message": "Keystroke logging stopped."}


@app.post("/api/logger/reset", tags=["Logger"])
def reset_logger(_token: str = Depends(get_session_token)) -> Dict[str, str]:
    """Stop logging and wipe all in-memory data (NOT the encrypted file)."""
    _logger.reset()
    return {"status": "reset", "message": "Logger reset. In-memory data cleared."}


@app.post("/api/logger/clear-storage", tags=["Logger"])
def clear_storage(_token: str = Depends(get_session_token)) -> Dict[str, str]:
    """Permanently erase the encrypted keystroke log file."""
    _logger.reset()
    storage.clear_records()
    return {"message": "All stored data has been permanently deleted."}


@app.get("/api/logger/status", tags=["Logger"])
def logger_status(_token: str = Depends(get_session_token)) -> Dict[str, Any]:
    return {
        "running":     _logger.is_running,
        "total_live":  _logger.total_count,
        "kpm_live":    _logger.kpm,
        "stored_total":storage.get_stats().get("total", 0),
    }


# ---------------------------------------------------------------------------
# Data retrieval endpoints
# ---------------------------------------------------------------------------
@app.get("/api/keystrokes", tags=["Data"])
def get_keystrokes(
    n: int = Query(50, ge=1, le=500),
    _token: str = Depends(get_session_token),
) -> Dict[str, Any]:
    """Return the last *n* keystrokes from the in-memory live buffer."""
    buf = _logger.get_buffer()
    return {
        "keystrokes": buf[-n:],
        "total_live": _logger.total_count,
    }


@app.get("/api/stats", tags=["Data"])
def get_stats(_token: str = Depends(get_session_token)) -> Dict[str, Any]:
    """Return aggregate statistics over ALL stored (encrypted) records."""
    stats = storage.get_stats()
    stats["kpm_live"]   = _logger.kpm
    stats["is_running"] = _logger.is_running
    return stats


@app.get("/api/charts", tags=["Data"])
def get_charts(_token: str = Depends(get_session_token)) -> Dict[str, str]:
    """
    Generate and return all analysis charts as base64-encoded PNG strings.
    Frontend renders them as  <img src="data:image/png;base64,…">
    """
    records = storage.get_all_records()
    charts  = analysis.generate_all_charts(records)
    return charts


@app.get("/api/export/csv", tags=["Data"])
def export_csv(_token: str = Depends(get_session_token)) -> Response:
    """Download all stored keystrokes as a CSV file."""
    csv_data = storage.export_csv()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="keylog_report.csv"'},
    )


# ---------------------------------------------------------------------------
# WebSocket – real-time keystroke stream
# ---------------------------------------------------------------------------
@app.websocket("/ws/live")
async def websocket_live(ws: WebSocket, token: Optional[str] = Query(None)):
    """
    WebSocket endpoint for the live keystroke feed.

    Clients connect with ?token=<session_token>.
    Each keystroke captured by the logger is pushed as JSON.
    """
    if not token or not auth.validate_session(token):
        await ws.close(code=4001)
        return

    await ws.accept()
    queue: asyncio.Queue = asyncio.Queue()
    _logger.subscribe(queue)

    try:
        while True:
            record = await asyncio.wait_for(queue.get(), timeout=30.0)
            await ws.send_text(json.dumps(record))
    except asyncio.TimeoutError:
        # Send a heartbeat ping to keep the connection alive
        try:
            await ws.send_text(json.dumps({"heartbeat": True}))
        except Exception:
            pass
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        _logger.unsubscribe(queue)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/api/health", tags=["Meta"])
def health() -> Dict[str, str]:
    return {"status": "ok", "disclaimer": "FOR EDUCATIONAL USE ONLY"}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys, uvicorn
    # Force UTF-8 output so emoji prints correctly on Windows
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("\n" + "=" * 65)
    print("  [!] KEYSTROKE LOGGING DEMONSTRATION SYSTEM [!]")
    print("  FOR EDUCATIONAL & ETHICAL CYBERSECURITY USE ONLY")
    print("  Default login password: demo1234")
    print("  Open frontend/index.html in your browser")
    print("=" * 65 + "\n")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
