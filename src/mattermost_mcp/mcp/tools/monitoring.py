"""Monitoring-related MCP tools for Mattermost."""

from mattermost_mcp.logging import get_logger
from mattermost_mcp.mcp.server import mcp
from mattermost_mcp.monitoring.monitor import get_monitor

logger = get_logger(__name__)


@mcp.tool
async def mattermost_run_monitoring() -> dict:
    """Run the topic monitoring process immediately.

    Analyzes configured channels for messages related to configured topics
    and sends notifications for relevant messages.

    Returns:
        Dictionary with success status and message
    """
    monitor = get_monitor()

    if not monitor:
        logger.warning("Monitoring not enabled or not initialized")
        return {
            "success": False,
            "message": "Monitoring is not enabled or not initialized",
        }

    try:
        await monitor.run_now()
        return {
            "success": True,
            "message": "Monitoring run completed successfully",
        }
    except Exception as e:
        logger.error("Error running monitoring", error=str(e))
        return {
            "success": False,
            "message": f"Error running monitoring: {e}",
        }


@mcp.tool
async def mattermost_get_monitoring_status() -> dict:
    """Get the current status of the monitoring system.

    Returns:
        Dictionary with enabled flag and running state
    """
    monitor = get_monitor()

    if not monitor:
        return {
            "enabled": False,
            "running": False,
            "message": "Monitoring is not enabled or not initialized",
        }

    return {
        "enabled": monitor.is_enabled(),
        "running": monitor.is_running(),
        "message": "Monitoring system is active" if monitor.is_enabled() else "Monitoring system is stopped",
    }
