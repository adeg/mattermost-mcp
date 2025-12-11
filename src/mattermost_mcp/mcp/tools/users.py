"""User-related MCP tools for Mattermost."""

from datetime import UTC, datetime

from mattermost_mcp.clients.mattermost import get_mattermost_client
from mattermost_mcp.logging import get_logger
from mattermost_mcp.mcp.server import mcp

logger = get_logger(__name__)


@mcp.tool
async def mattermost_get_users(limit: int = 100, page: int = 0) -> dict:
    """Get a list of users in the Mattermost workspace with pagination.

    Args:
        limit: Maximum number of users to return (default 100, max 200)
        page: Page number for pagination (starting from 0)

    Returns:
        Dictionary containing users list, total count, and pagination info
    """
    client = get_mattermost_client()

    try:
        response = await client.get_users(limit=limit, page=page)

        formatted_users = [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "nickname": u.nickname,
                "position": u.position,
                "roles": u.roles,
                "is_bot": u.is_bot,
            }
            for u in response.users
        ]

        return {
            "users": formatted_users,
            "total_count": response.total_count,
            "page": page,
            "per_page": limit,
        }
    except Exception as e:
        logger.error("Error getting users", error=str(e))
        return {"error": str(e)}


@mcp.tool
async def mattermost_get_user_profile(user_id: str) -> dict:
    """Get detailed profile information for a specific user.

    Args:
        user_id: The ID of the user

    Returns:
        Dictionary containing the user's profile information
    """
    client = get_mattermost_client()

    try:
        user = await client.get_user_profile(user_id)

        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "nickname": user.nickname,
            "position": user.position,
            "roles": user.roles,
            "locale": user.locale,
            "timezone": user.timezone,
            "is_bot": user.is_bot,
            "bot_description": user.bot_description,
            "last_picture_update": user.last_picture_update,
            "create_at": datetime.fromtimestamp(user.create_at / 1000, tz=UTC).isoformat() if user.create_at else None,
            "update_at": datetime.fromtimestamp(user.update_at / 1000, tz=UTC).isoformat() if user.update_at else None,
        }
    except Exception as e:
        logger.error("Error getting user profile", error=str(e), user_id=user_id)
        return {"error": str(e)}
