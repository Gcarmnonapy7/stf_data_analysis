"""FastAPI Application Entrypoint for STF Transparency Platform."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.analytics import router as analytics_router
from api.routes.decisions import router as decisions_router
from api.routes.lineage import router as lineage_router
from api.routes.processes import router as processes_router

app = FastAPI(
    title="STF Transparency Platform API",
    description="""
    Open-source data engineering and analytical API over public judicial data 
    from the Brazilian Supreme Federal Court (*Supremo Tribunal Federal* - STF / *Corte Aberta*).
    
    Provides queryable endpoints, aggregations, and full data lineage traceability.
    """,
    version="0.1.0",
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
app.include_router(lineage_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
def healthcheck():
    """Healthcheck endpoint for container orchestration and uptime monitoring."""
    return {
        "status": "healthy",
        "service": "stf-transparency-platform-api",
        "version": "0.1.0",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
