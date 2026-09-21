"""FastAPI Application Entrypoint for STF Transparency Platform."""

from __future__ import annotations

from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from api.routes.administrative import router as administrative_router
from api.routes.analytics import router as analytics_router
from api.routes.decisions import router as decisions_router
from api.routes.export import router as export_router
from api.routes.lineage import router as lineage_router
from api.routes.processes import router as processes_router

app = FastAPI(
    title="STF Transparency Platform API",
    description="""
    Open-source data engineering and analytical API over public judicial and administrative data 
    from the Brazilian Supreme Federal Court (*Supremo Tribunal Federal* - STF / *Corte Aberta*).
    
    Provides queryable endpoints, analytical aggregations, survival modeling, streaming exports,
    and full data lineage traceability.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS for dashboard and third-party researchers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API v1 Routers
app.include_router(processes_router, prefix="/api/v1")
app.include_router(decisions_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(administrative_router, prefix="/api/v1")
app.include_router(export_router, prefix="/api/v1")
app.include_router(lineage_router, prefix="/api/v1")


@app.get("/", tags=["Root"])
def root():
    """Root entrypoint with service metadata, documentation links, and endpoint index."""
    return {
        "title": "STF Transparency Platform API",
        "version": "1.0.0",
        "dashboard_url": "/dashboard",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "health_url": "/health",
        "endpoints": {
            "processes": "/api/v1/processes",
            "decisions": "/api/v1/decisions",
            "analytics_overview": "/api/v1/analytics/overview",
            "yearly_trends": "/api/v1/analytics/yearly-trends",
            "decisions_by_category": "/api/v1/analytics/decisions-by-category",
            "by_region": "/api/v1/analytics/by-region",
            "judges_caseload": "/api/v1/analytics/judges",
            "survival_analysis": "/api/v1/analytics/survival",
            "administrative_budget": "/api/v1/administrative/budget/summary",
            "administrative_remuneration": "/api/v1/administrative/remuneration/summary",
            "administrative_personnel": "/api/v1/administrative/personnel",
            "streaming_export": "/api/v1/export/{dataset}?format={csv|jsonl|parquet}",
            "lineage_trace": "/api/v1/lineage/{entity_name}",
        },
        "description": "Open-source data engineering and analytical platform for Brazilian Supreme Court (STF) public data.",
    }


@app.get("/dashboard", response_class=HTMLResponse, tags=["Dashboard"])
def get_dashboard():
    """Serves the interactive STF Analytics & Transparency Dashboard."""
    template_path = Path(__file__).resolve().parent / "templates" / "dashboard.html"
    if not template_path.exists():
        return HTMLResponse("<h1>Dashboard template not found</h1>", status_code=500)
    return HTMLResponse(content=template_path.read_text(encoding="utf-8"))


@app.get("/health", tags=["Health"])
def healthcheck():
    """Healthcheck endpoint for container orchestration and uptime monitoring."""
    return {
        "status": "healthy",
        "service": "stf-transparency-platform-api",
        "version": "1.0.0",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)

