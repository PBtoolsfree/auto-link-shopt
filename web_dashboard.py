import os
import hashlib
import logging
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn

# Config and Bot Imports
from config import config_manager
import gplinks_bot

# Initialize FastAPI App
app = FastAPI(title="GPLinks Affiliate Bot Dashboard")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DashboardBackend")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Templates Config
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# =========================================================================
# SYSTEM BOOT AUTO-START HANDLER
# =========================================================================
@app.on_event("startup")
async def startup_event():
    """Tries to auto-start the poller bot service on boot if credentials exist."""
    logger.info("Server booting up: Checking if bot can auto-start...")
    success = await gplinks_bot.start_bot()
    if success:
        logger.info("Bot poller successfully auto-started on boot!")
    else:
        logger.info("Auto-start skipped: Bot credentials (token/source channel) not set in .env yet.")

@app.on_event("shutdown")
async def shutdown_event():
    """Gracefully shuts down the background poller before exit."""
    logger.info("Server shutting down: Stopping poller daemon...")
    await gplinks_bot.stop_bot()

# =========================================================================
# PASSWORD GATE & AUTHENTICATION SECURE COOKIES
# =========================================================================
def is_authenticated(request: Request) -> bool:
    """Checks if the request holds a valid hashed admin password session cookie."""
    saved_pwd = config_manager.configs.get("DASHBOARD_PASSWORD", "admin123")
    cookie_token = request.cookies.get("gplinks_admin_session")
    expected_token = hashlib.sha256(saved_pwd.encode("utf-8")).hexdigest()
    return cookie_token == expected_token

class LoginRequest(BaseModel):
    password: str

# =========================================================================
# WEB PAGES & SECURITY GATEWAY
# =========================================================================
@app.get("/", response_class=HTMLResponse)
async def get_dashboard_root(request: Request):
    """Serves the secure control center homepage if authorized, else gates with login page."""
    if not is_authenticated(request):
        return templates.TemplateResponse(request=request, name="login.html")
    return templates.TemplateResponse(request=request, name="dashboard.html")

@app.post("/api/login")
async def api_login(payload: LoginRequest, response: Response):
    """Authenticates the dashboard access password and sets a secure Lax cookie."""
    saved_pwd = config_manager.configs.get("DASHBOARD_PASSWORD", "admin123")
    if payload.password == saved_pwd:
        session_token = hashlib.sha256(saved_pwd.encode("utf-8")).hexdigest()
        response.set_cookie(
            key="gplinks_admin_session",
            value=session_token,
            max_age=30 * 24 * 60 * 60,  # 30-day session
            httponly=True,
            samesite="lax"
        )
        return {"status": "success", "message": "Successfully authenticated!"}
    raise HTTPException(status_code=401, detail="Incorrect password. Access denied.")

@app.post("/api/logout")
async def api_logout(response: Response):
    """Clears the session cookie, logging out the administrator."""
    response.delete_cookie("gplinks_admin_session")
    return {"status": "success", "message": "Successfully logged out."}

# =========================================================================
# CONFIGURATION SETTINGS GATEWAYS
# =========================================================================
@app.get("/api/config")
async def get_dashboard_config(request: Request):
    """Reads and returns the active env configuration variables."""
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized access.")
    return config_manager.configs

@app.post("/api/config")
async def update_dashboard_config(payload: Dict[str, str], request: Request):
    """Receives updated configs from UI, saves to env, and hot-reloads runtime states."""
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized access.")
    
    # Write to env and reload
    config_manager.save(payload)
    
    # If the bot is active, tell it to restart or reload config parameters
    if gplinks_bot.is_running:
        logger.info("Bot is active: Hot-reloading bot configuration parameters.")
        # If bot token changes, restarting poller ensures updates are pulled from new bot!
        await gplinks_bot.stop_bot()
        await gplinks_bot.start_bot()
        
    return {"status": "success", "message": "Configurations successfully updated!"}

# =========================================================================
# SYSTEM RUNTIME OPERATIONS & METRICS APIs
# =========================================================================
@app.get("/api/bot/status")
async def get_bot_operational_status(request: Request):
    """Returns active state (running/stopped) and real-time counter metrics."""
    # Allowed unauthenticated to allow client health checks to stay alive
    status_str = "running" if gplinks_bot.is_running else "stopped"
    return {
        "status": status_str,
        "stats": config_manager.stats
    }

@app.post("/api/bot/start")
async def start_bot_poller(request: Request):
    """Launches the automatic updates long-polling loop task thread."""
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized access.")
        
    if gplinks_bot.is_running:
        return {"status": "running", "message": "Bot is already running."}
        
    success = await gplinks_bot.start_bot()
    if success:
        return {"status": "running", "message": "Bot poller successfully launched!"}
    else:
        raise HTTPException(
            status_code=400,
            detail="Could not start bot: Ensure Telegram Bot Token & Source Channel username are configured in settings!"
        )

@app.post("/api/bot/stop")
async def stop_bot_poller(request: Request):
    """Safely halts the updates polling daemon thread loop."""
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized access.")
        
    await gplinks_bot.stop_bot()
    return {"status": "stopped", "message": "Bot poller stopped."}

# =========================================================================
# BOT SYSTEM LOG STREAMING API
# =========================================================================
@app.get("/api/logs")
async def stream_gplinks_bot_logs(request: Request, lines: int = 50):
    """Safely extracts and returns the last N records from the local log storage."""
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized access.")
        
    log_file = gplinks_bot.log_file_path
    if not os.path.exists(log_file):
        return [f"[INFO] Welcome! No log entries recorded yet in {os.path.basename(log_file)}."]
        
    try:
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            log_lines = f.readlines()
            return [line.strip() for line in log_lines[-lines:]]
    except Exception as e:
        return [f"[ERROR] Failed streaming log records: {e}"]

# =========================================================================
# CONSOLE RUN HOOK
# =========================================================================
if __name__ == '__main__':
    logger.info("Initializing GPLinks bot control systems...")
    uvicorn.run("web_dashboard:app", host="0.0.0.0", port=8000, reload=True)
