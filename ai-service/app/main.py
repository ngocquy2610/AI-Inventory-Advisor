"""FastAPI app entrypoint, router registration, and middleware setup."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_v1_router
from app.config import settings
from app.core.middleware import RequestLoggingMiddleware, InternalTokenMiddleware
from app.schemas.common import HealthResponse

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Inventory Advisor",
    description="AI-powered inventory management microservice",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(InternalTokenMiddleware)

# Register routers
app.include_router(api_v1_router)


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health_check():
    return HealthResponse()


@app.on_event("startup")
def on_startup():
    logger.info("AI Inventory Advisor service starting up")
    if settings.environment == "development":
        from app.db.session import init_db
        init_db()
        logger.info("Database tables initialized (dev mode)")