"""Health check endpoints for the Mattermost MCP server."""

from fastapi import APIRouter
from pydantic import BaseModel

from mattermost_mcp import __version__

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    version: str


class ReadinessResponse(BaseModel):
    """Readiness check response model."""

    status: str
    version: str
    mattermost_connected: bool


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check endpoint.

    Returns:
        HealthResponse indicating the service is running
    """
    return HealthResponse(status="healthy", version=__version__)


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check() -> ReadinessResponse:
    """Readiness check that verifies Mattermost connectivity.

    Returns:
        ReadinessResponse with connection status
    """
    from mattermost_mcp.clients.mattermost import get_mattermost_client

    mattermost_connected = False

    try:
        client = get_mattermost_client()
        await client.login()
        mattermost_connected = True
    except Exception:
        pass

    return ReadinessResponse(
        status="ready" if mattermost_connected else "not_ready",
        version=__version__,
        mattermost_connected=mattermost_connected,
    )
