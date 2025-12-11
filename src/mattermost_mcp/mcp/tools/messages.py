"""Message-related MCP tools for Mattermost."""

from datetime import UTC, datetime

from mattermost_mcp.clients.mattermost import get_mattermost_client
from mattermost_mcp.logging import get_logger
from mattermost_mcp.mcp.server import mcp

logger = get_logger(__name__)


@mcp.tool
async def mattermost_post_message(channel_id: str, message: str) -> dict:
    """Post a new message to a Mattermost channel.

    Args:
        channel_id: The ID of the channel to post to
        message: The message text to post

    Returns:
        Dictionary containing the posted message details
    """
    client = get_mattermost_client()

    try:
        post = await client.create_post(channel_id, message)

        return {
            "id": post.id,
            "channel_id": post.channel_id,
            "message": post.message,
            "create_at": datetime.fromtimestamp(post.create_at / 1000, tz=UTC).isoformat(),
        }
    except Exception as e:
        logger.error("Error posting message", error=str(e), channel_id=channel_id)
        return {"error": str(e)}


@mcp.tool
async def mattermost_reply_to_thread(channel_id: str, post_id: str, message: str) -> dict:
    """Reply to a specific message thread in Mattermost.

    Args:
        channel_id: The ID of the channel containing the thread
        post_id: The ID of the parent message to reply to
        message: The reply text

    Returns:
        Dictionary containing the reply message details
    """
    client = get_mattermost_client()

    try:
        post = await client.create_post(channel_id, message, root_id=post_id)

        return {
            "id": post.id,
            "channel_id": post.channel_id,
            "root_id": post.root_id,
            "message": post.message,
            "create_at": datetime.fromtimestamp(post.create_at / 1000, tz=UTC).isoformat(),
        }
    except Exception as e:
        logger.error("Error replying to thread", error=str(e), channel_id=channel_id, post_id=post_id)
        return {"error": str(e)}


@mcp.tool
async def mattermost_add_reaction(channel_id: str, post_id: str, emoji_name: str) -> dict:
    """Add a reaction emoji to a message.

    Args:
        channel_id: The ID of the channel containing the message
        post_id: The ID of the message to react to
        emoji_name: The name of the emoji reaction (without colons)

    Returns:
        Dictionary containing the reaction details
    """
    client = get_mattermost_client()

    try:
        reaction = await client.add_reaction(post_id, emoji_name)

        return {
            "post_id": reaction.post_id,
            "user_id": reaction.user_id,
            "emoji_name": reaction.emoji_name,
            "create_at": datetime.fromtimestamp(reaction.create_at / 1000, tz=UTC).isoformat(),
        }
    except Exception as e:
        logger.error("Error adding reaction", error=str(e), post_id=post_id, emoji_name=emoji_name)
        return {"error": str(e)}


@mcp.tool
async def mattermost_get_thread_replies(channel_id: str, post_id: str) -> dict:
    """Get all replies in a message thread.

    Args:
        channel_id: The ID of the channel containing the thread
        post_id: The ID of the parent message

    Returns:
        Dictionary containing the thread posts
    """
    client = get_mattermost_client()

    try:
        response = await client.get_post_thread(post_id)

        formatted_posts = [
            {
                "id": response.posts[pid].id,
                "user_id": response.posts[pid].user_id,
                "message": response.posts[pid].message,
                "create_at": datetime.fromtimestamp(response.posts[pid].create_at / 1000, tz=UTC).isoformat(),
                "root_id": response.posts[pid].root_id or None,
            }
            for pid in response.order
            if pid in response.posts
        ]

        root_post = None
        if post_id in response.posts:
            rp = response.posts[post_id]
            root_post = {
                "id": rp.id,
                "user_id": rp.user_id,
                "message": rp.message,
                "create_at": datetime.fromtimestamp(rp.create_at / 1000, tz=UTC).isoformat(),
            }

        return {
            "posts": formatted_posts,
            "root_post": root_post,
        }
    except Exception as e:
        logger.error("Error getting thread replies", error=str(e), post_id=post_id)
        return {"error": str(e)}
