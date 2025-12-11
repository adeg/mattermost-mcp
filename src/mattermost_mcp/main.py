"""Main entry point for the Mattermost MCP server."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from mattermost_mcp import __version__
from mattermost_mcp.api.health import router as health_router
from mattermost_mcp.clients.mattermost import close_client, get_mattermost_client, init_client
from mattermost_mcp.config import get_llm_config, get_monitoring_config, get_settings
from mattermost_mcp.logging import get_logger, setup_logging
from mattermost_mcp.monitoring.monitor import init_monitor, stop_monitor

# Import tools to register them with the MCP server
from mattermost_mcp.mcp import tools as _tools  # noqa: F401
from mattermost_mcp.mcp.server import mcp

logger = get_logger(__name__)


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application lifecycle.

    Handles:
    - Logging setup
    - Mattermost client initialization
    - Graceful shutdown
    """
    settings = get_settings()

    # Setup logging
    setup_logging(
        log_level=settings.log_level,
        json_format=settings.log_format.lower() == "json",
    )

    logger.info(
        "Starting Mattermost MCP server",
        version=__version__,
        port=settings.http_port,
    )

    # Initialize Mattermost client
    try:
        await init_client()
        logger.info("Mattermost client initialized")
    except Exception as e:
        logger.error("Failed to initialize Mattermost client", error=str(e))
        # Continue startup - client can be initialized on first request

    # Initialize monitoring if enabled
    monitoring_config = get_monitoring_config()
    if monitoring_config.enabled:
        try:
            client = get_mattermost_client()
            llm_config = get_llm_config()
            await init_monitor(client, monitoring_config, llm_config)
            logger.info(
                "Monitoring system initialized",
                channels=monitoring_config.channels,
                topics=monitoring_config.topics,
                schedule=monitoring_config.schedule,
            )
        except Exception as e:
            logger.error("Failed to initialize monitoring", error=str(e))

    yield

    # Cleanup
    logger.info("Shutting down Mattermost MCP server")
    stop_monitor()
    await close_client()


# Create the MCP HTTP app
mcp_app = mcp.http_app(path="/mcp")


@asynccontextmanager
async def combined_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Combined lifespan manager for FastAPI and FastMCP."""
    async with app_lifespan(app):
        async with mcp_app.lifespan(app):
            yield


# Create the FastAPI application
app = FastAPI(
    title="Mattermost MCP Server",
    description="FastMCP server for Mattermost integration",
    version=__version__,
    lifespan=combined_lifespan,
)

# Mount the MCP app
app.mount("/llm", mcp_app)

# Include health check routes
app.include_router(health_router)


@app.get("/", tags=["root"])
async def root() -> dict:
    """Root endpoint with service information."""
    return {
        "service": "mattermost-mcp",
        "version": __version__,
        "mcp_endpoint": "/llm/mcp",
        "health_endpoint": "/health",
        "ready_endpoint": "/ready",
    }


def main() -> None:
    """Run the server using uvicorn."""
    import uvicorn

    settings = get_settings()

    uvicorn.run(
        "mattermost_mcp.main:app",
        host="0.0.0.0",
        port=settings.http_port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
