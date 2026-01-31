"""
Point d'entrée FastAPI pour SyncObsidian API.
"""
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from .core.config import settings
from .core.database import init_db
from .routers import auth, sync


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events : startup et shutdown."""
    # Startup
    await init_db()
    yield
    # Shutdown
    pass


app = FastAPI(
    title="SyncObsidian API",
    description="API de synchronisation Obsidian auto-hébergée",
    version="1.0.0",
    lifespan=lifespan
)


# ============ Middlewares ============

class TimeoutMiddleware(BaseHTTPMiddleware):
    """Timeout sur les requêtes (configurable via REQUEST_TIMEOUT_SECONDS)."""
    async def dispatch(self, request, call_next):
        try:
            async with asyncio.timeout(settings.request_timeout_seconds):
                return await call_next(request)
        except asyncio.TimeoutError:
            return JSONResponse(
                status_code=408,
                content={"detail": "Request timeout"}
            )

app.add_middleware(TimeoutMiddleware)

# Compression GZip pour réduire la bande passante (~80% sur du Markdown)
app.add_middleware(GZipMiddleware, minimum_size=500)

# CORS pour permettre les requêtes depuis Obsidian
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ Static Files ============

static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_path), name="static")


# ============ Routers ============

app.include_router(auth.router)
app.include_router(sync.router)


# ============ Root Endpoints ============

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "syncobsidian"}


@app.get("/sync-viewer", tags=["Health"])
async def sync_viewer():
    """Page HTML de visualisation des notes synchronisées."""
    return FileResponse(static_path / "sync-viewer.html")


# ============ Main ============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
