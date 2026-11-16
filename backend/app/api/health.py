from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database.session import check_db_connection, get_db

router = APIRouter(tags=["Health"])


class ProviderStatus(BaseModel):
    configured: bool
    model: str
    target: str | None = None


class DatabaseStatus(BaseModel):
    connected: bool
    type: str


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str
    timestamp: str
    database: DatabaseStatus
    ai_providers: dict[str, ProviderStatus]


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="System Health & Readiness",
    description="Returns backend health, database connectivity status, and AI provider readiness.",
)
async def get_health(
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> HealthResponse:
    db_connected = check_db_connection()

    gemini_configured = bool(settings.GEMINI_API_KEY and len(settings.GEMINI_API_KEY.strip()) > 0)
    ollama_configured = bool(settings.OLLAMA_BASE_URL and len(settings.OLLAMA_BASE_URL.strip()) > 0)

    overall_status = "healthy" if db_connected else "degraded"

    return HealthResponse(
        status=overall_status,
        service=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc).isoformat(),
        database=DatabaseStatus(
            connected=db_connected,
            type="sqlite",
        ),
        ai_providers={
            "gemini": ProviderStatus(
                configured=gemini_configured,
                model=settings.GEMINI_MODEL,
                target="Google AI",
            ),
            "ollama": ProviderStatus(
                configured=ollama_configured,
                model=settings.OLLAMA_MODEL,
                target=settings.OLLAMA_BASE_URL,
            ),
        },
    )
