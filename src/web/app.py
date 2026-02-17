from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from pathlib import Path
import contextlib
import logging
import os

from src.core.database import engine, Base
from src.web.dependencies import get_current_username

logger = logging.getLogger(__name__)


app = FastAPI(
    title="RADAR Market Intel",
    description="API for Real-time Automated Discovery & Analysis for Returns",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "Market Intel", "description": "General market intelligence and feed items"},
        {"name": "Universe", "description": "Company universe and discovery"},
        {"name": "Search", "description": "Global search functionality"},
        {"name": "Dashboard", "description": "Dashboard statistics and activity feed"},
        {"name": "Competitive", "description": "Competitive announcements and threats"},
        {"name": "Carveout", "description": "Carveout opportunities and probabilities"},
        {"name": "Capital Flows", "description": "PE firm investments and flows"},
        {"name": "Deal Intelligence", "description": "Deal comparables and valuation analysis"},
        {"name": "Reporting", "description": "Report generation and export"},
        {"name": "Target Tracker", "description": "Manage and analyze target watchlist"},
        {"name": "Alerts", "description": "Real-time notifications"},
    ]
)

from src.web.routers import register_routers
from src.web.scheduler import start_scheduler, stop_scheduler

register_routers(app)

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Database Tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Start Scheduler
    start_scheduler()
    
    yield
    
    # Stop Scheduler
    await stop_scheduler()

app.router.lifespan_context = lifespan

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], # Vite Dev Server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth imported from src.web.dependencies

# Mounting static files (for production build later)
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/dashboard")

@app.get("/dashboard", include_in_schema=False)
async def dashboard_view(username: str = Depends(get_current_username)):
    """Serve the dashboard HTML. Requires Auth."""
    # Use absolute path relative to this file
    file_path = Path(__file__).parent / "dashboard.html"
    return FileResponse(file_path)

@app.get("/DASHBOARD", include_in_schema=False)
async def dashboard_view_caps(username: str = Depends(get_current_username)):
    """Handle uppercase /DASHBOARD as some users might type it that way."""
    return RedirectResponse(url="/dashboard")

@app.get("/state.json", include_in_schema=False)
async def get_state_json(username: str = Depends(get_current_username)):
    """Serve the state.json file for dashboard polling. Requires Auth."""
    file_path = Path(__file__).parent / "state.json"
    if not file_path.exists():
        # Return default idle state if file doesn't exist yet
        return {"status": "idle", "current_zone": 0, "logs": [], "stats": {}}
    return FileResponse(file_path)
