from fastapi import FastAPI

from src.web.routers.alerts import router as alerts_router
from src.web.routers.capital import router as capital_router
from src.web.routers.deals import router as deals_router
from src.web.routers.carveout import router as carveout_router
from src.web.routers.relationships import router as relationships_router
from src.web.routers.tracker import router as tracker_router
from src.web.routers.intelligence import router as intelligence_router
from src.web.routers.competitive import router as competitive_router
from src.web.routers.dashboard import router as dashboard_routes_router
from src.web.routers.universe import router as universe_router
from src.web.routers.search import router as search_router
from src.web.routers.reports import router as reports_router
from src.web.routers.intel import router as intel_router
from src.web.routers.config import router as config_router

def register_routers(app: FastAPI):
    """Register all routers with the application."""
    app.include_router(alerts_router)
    app.include_router(capital_router)
    app.include_router(deals_router)
    app.include_router(carveout_router)
    app.include_router(relationships_router)
    app.include_router(tracker_router)
    app.include_router(intelligence_router)
    app.include_router(competitive_router)
    app.include_router(dashboard_routes_router)
    app.include_router(universe_router)
    app.include_router(search_router)
    app.include_router(reports_router)
    app.include_router(intel_router)
    app.include_router(config_router)
