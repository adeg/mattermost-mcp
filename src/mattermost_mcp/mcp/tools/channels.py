"""Channel-related MCP tools for Mattermost."""

from datetime import UTC, datetime

from mattermost_mcp.clients.mattermost import get_mattermost_client
from mattermost_mcp.logging import get_logger
from mattermost_mcp.mcp.server import mcp

logger = get_logger(__name__)


@mcp.tool
async def mattermost_list_channels(limit: int = 100, page: int = 0) -> dict:
    """List public channels in the Mattermost workspace with pagination.

    Args:
        limit: Maximum number of channels to return (default 100, max 200)
        page: Page number for pagination (starting from 0)

    Returns:
        Dictionary containing channels list, total count, and pagination info
    """
    client = get_mattermost_client()

    try:
        response = await client.get_channels(limit=limit, page=page)

        formatted_channels = [
            {
                "id": c.id,
                "name": c.name,
                "display_name": c.display_name,
                "type": c.type,
                "purpose": c.purpose,
                "header": c.header,
                "total_msg_count": c.total_msg_count,
            }
            for c in response.channels
        ]

        return {
            "channels": formatted_channels,
            "total_count": response.total_count,
            "page": page,
            "per_page": limit,
        }
    except Exception as e:
        logger.error("Error listing channels", error=str(e))
        return {"error": str(e)}


@mcp.tool
async def mattermost_get_channel_history(channel_id: str, limit: int = 30, page: int = 0) -> dict:
    """Get recent messages from a Mattermost channel.

    Args:
        channel_id: The ID of the channel
        limit: Number of messages to retrieve (default 30)
        page: Page number for pagination (starting from 0)

    Returns:
        Dictionary containing posts list and pagination info
    """
    client = get_mattermost_client()

    try:
        response = await client.get_posts_for_channel(channel_id, limit=limit, page=page)

        formatted_posts = [
            {
                "id": response.posts[post_id].id,
                "user_id": response.posts[post_id].user_id,
                "message": response.posts[post_id].message,
                "create_at": datetime.fromtimestamp(response.posts[post_id].create_at / 1000, tz=UTC).isoformat(),
                "reply_count": response.posts[post_id].reply_count,
                "root_id": response.posts[post_id].root_id or None,
            }
            for post_id in response.order
            if post_id in response.posts
        ]

        return {
            "posts": formatted_posts,
            "has_next": bool(response.next_post_id),
            "has_prev": bool(response.prev_post_id),
            "page": page,
            "per_page": limit,
        }
    except Exception as e:
        logger.error("Error getting channel history", error=str(e), channel_id=channel_id)
        return {"error": str(e)}
