"""Main FastAPI application for Web Tool Set."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
import uvicorn

from app.api.network import router as network_router
from app.config import (
    APP_DESCRIPTION,
    APP_NAME,
    APP_VERSION,
    BASE_DIR,
    LOG_CONFIG_FILE,
    RATE_LIMIT_PER_MINUTE,
    STATIC_DIR,
    TEMPLATES_DIR,
)

# Configure logging
logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    application_limits=[f"{RATE_LIMIT_PER_MINUTE}/minute"],
)


def rate_limit_response() -> HTMLResponse:
    """Return the standard rate limit response."""
    return HTMLResponse(
        content="<html><body><h1>429 - Too Many Requests</h1><p>Please try again later.</p></body></html>",
        status_code=429,
    )


def global_rate_limit_endpoint():
    """Synthetic endpoint used for application-wide rate limiting."""


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events handler."""
    logger.info(f"Starting {APP_NAME} v{APP_VERSION}")
    yield
    logger.info(f"Shutting down {APP_NAME}")


# Create FastAPI application
app = FastAPI(
    title=APP_NAME,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter


@app.middleware("http")
async def global_rate_limit_middleware(request: Request, call_next):
    """Apply application-wide rate limiting to every HTTP request."""
    try:
        limiter._check_request_limit(request, global_rate_limit_endpoint, True)
    except RateLimitExceeded:
        return rate_limit_response()

    return await call_next(request)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Mount static files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Include routers
app.include_router(network_router)


# Rate limit exception handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded errors."""
    return rate_limit_response()


# Root endpoint - serve frontend
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the main frontend page."""
    return templates.TemplateResponse(request, "index.html")


# Legacy API endpoints (for backward compatibility)
@app.get("/ping")
@app.get("/ping/{address}")
async def ping_legacy(request: Request, address: str | None = None):
    """Legacy ping endpoint - redirects to new API."""
    from app.services.network import PingService
    from app.utils.iputils import get_real_ip

    if not address:
        address = get_real_ip(request) or "127.0.0.1"

    delay, error = PingService.ping(address)
    return {"delay": delay, "error": error}


@app.get("/tcping")
@app.get("/tcping/{address}")
async def tcping_legacy(
    request: Request, address: str = "", port: int = 80, timeout: int = 2
):
    """Legacy tcping endpoint - redirects to new API."""
    from app.services.network import TcpPingService
    from app.utils.iputils import get_real_ip

    if not address:
        address = get_real_ip(request) or "127.0.0.1"

    delay, error = TcpPingService.tcping(address, port=port, timeout=timeout)
    return {"delay": delay, "error": error}


@app.get("/myip")
async def myip_legacy(request: Request):
    """Legacy myip endpoint - redirects to new API."""
    from app.utils.iputils import get_real_ip

    ip = get_real_ip(request) or "unknown"
    return ip


@app.get("/wol/{mac_addr}")
async def wol_legacy(mac_addr: str):
    """Legacy wake on lan endpoint - redirects to new API."""
    from app.services.network import WakeOnLanService

    success, error = WakeOnLanService.wake(mac_addr)
    return {"rst": "success" if success else "failed", "error": error}


if __name__ == "__main__":
    # Use absolute path for log config
    log_config_path = LOG_CONFIG_FILE if LOG_CONFIG_FILE.exists() else None
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_config=str(log_config_path) if log_config_path else None,
    )


def main():
    """Entry point for the application."""
    import os

    os.chdir(BASE_DIR)
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_config=str(LOG_CONFIG_FILE) if LOG_CONFIG_FILE.exists() else None,
    )
