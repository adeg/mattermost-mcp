"""Async wrapper around mattermostautodriver for Mattermost API access."""

from asyncio import to_thread
from typing import Any

from mattermostautodriver import TypedDriver

from mattermost_mcp.config import get_settings
from mattermost_mcp.logging import get_logger
from mattermost_mcp.models.mattermost import (
    Channel,
    ChannelsResponse,
    Post,
    PostsResponse,
    Reaction,
    User,
    UserProfile,
    UsersResponse,
)

logger = get_logger(__name__)


class MattermostClient:
    """Async wrapper for Mattermost API using mattermostautodriver.

    All methods use asyncio.to_thread() to run the synchronous driver
    calls without blocking the event loop.
    """

    def __init__(self) -> None:
        """Initialize the Mattermost driver."""
        settings = get_settings()

        # Parse URL to extract scheme, host, and port
        url = settings.mattermost_base_url
        if url.startswith("https://"):
            scheme = "https"
            host = url[8:]
            port = 443
        elif url.startswith("http://"):
            scheme = "http"
            host = url[7:]
            port = 80
        else:
            scheme = "https"
            host = url
            port = 443

        # Handle port in URL
        if ":" in host:
            host, port_str = host.rsplit(":", 1)
            port = int(port_str)

        # TypedDriver requires options as a dict parameter
        self._driver = TypedDriver(
            options={
                "url": host,
                "token": settings.mattermost_token,
                "scheme": scheme,
                "port": port,
                "verify": True,
                "timeout": 30,
            }
        )
        self._team_id = settings.mattermost_team_id
        self._logged_in = False

    async def login(self) -> None:
        """Authenticate with Mattermost using the configured token."""
        if not self._logged_in:
            await to_thread(self._driver.login)
            self._logged_in = True
            logger.info("Connected to Mattermost")

    async def logout(self) -> None:
        """Disconnect from Mattermost."""
        if self._logged_in:
            await to_thread(self._driver.logout)
            self._logged_in = False
            logger.info("Disconnected from Mattermost")

    # Channel operations

    async def get_channels(self, limit: int = 100, page: int = 0) -> ChannelsResponse:
        """Get public channels for the team.

        Args:
            limit: Maximum number of channels to return
            page: Page number for pagination

        Returns:
            ChannelsResponse with list of channels
        """
        await self.login()
        channels_data = await to_thread(
            self._driver.channels.get_public_channels_for_team,
            self._team_id,
            page=page,
            per_page=limit,
        )

        channels = [Channel(**c) for c in channels_data]
        return ChannelsResponse(channels=channels, total_count=len(channels))

    async def get_channel(self, channel_id: str) -> Channel:
        """Get a specific channel by ID.

        Args:
            channel_id: The channel ID

        Returns:
            Channel object
        """
        await self.login()
        channel_data = await to_thread(self._driver.channels.get_channel, channel_id)
        return Channel(**channel_data)

    async def get_channel_by_name(self, channel_name: str) -> Channel:
        """Get a channel by name.

        Args:
            channel_name: The channel name

        Returns:
            Channel object
        """
        await self.login()
        channel_data = await to_thread(
            self._driver.channels.get_channel_by_name,
            self._team_id,
            channel_name,
        )
        return Channel(**channel_data)

    # Post operations

    async def get_posts_for_channel(self, channel_id: str, limit: int = 30, page: int = 0) -> PostsResponse:
        """Get posts from a channel.

        Args:
            channel_id: The channel ID
            limit: Number of posts to retrieve
            page: Page number for pagination

        Returns:
            PostsResponse with posts dict and order
        """
        await self.login()
        posts_data = await to_thread(
            self._driver.posts.get_posts_for_channel,
            channel_id,
            page=page,
            per_page=limit,
        )

        posts = {pid: Post(**pdata) for pid, pdata in posts_data.get("posts", {}).items()}
        return PostsResponse(
            posts=posts,
            order=posts_data.get("order", []),
            next_post_id=posts_data.get("next_post_id", ""),
            prev_post_id=posts_data.get("prev_post_id", ""),
        )

    async def create_post(self, channel_id: str, message: str, root_id: str = "") -> Post:
        """Create a new post in a channel.

        Args:
            channel_id: The channel ID
            message: The message content
            root_id: Optional root post ID for thread replies

        Returns:
            The created Post
        """
        await self.login()
        post_data: dict[str, Any] = {
            "channel_id": channel_id,
            "message": message,
        }
        if root_id:
            post_data["root_id"] = root_id

        result = await to_thread(self._driver.posts.create_post, options=post_data)
        return Post(**result)

    async def get_post(self, post_id: str) -> Post:
        """Get a specific post by ID.

        Args:
            post_id: The post ID

        Returns:
            Post object
        """
        await self.login()
        post_data = await to_thread(self._driver.posts.get_post, post_id)
        return Post(**post_data)

    async def get_post_thread(self, post_id: str) -> PostsResponse:
        """Get all posts in a thread.

        Args:
            post_id: The root post ID

        Returns:
            PostsResponse with all thread posts
        """
        await self.login()
        thread_data = await to_thread(self._driver.posts.get_post_thread, post_id)

        posts = {pid: Post(**pdata) for pid, pdata in thread_data.get("posts", {}).items()}
        return PostsResponse(
            posts=posts,
            order=thread_data.get("order", []),
            next_post_id=thread_data.get("next_post_id", ""),
            prev_post_id=thread_data.get("prev_post_id", ""),
        )

    # Reaction operations

    async def add_reaction(self, post_id: str, emoji_name: str) -> Reaction:
        """Add a reaction to a post.

        Args:
            post_id: The post ID
            emoji_name: The emoji name (without colons)

        Returns:
            The created Reaction
        """
        await self.login()
        me = await to_thread(self._driver.users.get_user, "me")
        user_id = me["id"]

        reaction_data = await to_thread(
            self._driver.reactions.save_reaction,
            options={
                "user_id": user_id,
                "post_id": post_id,
                "emoji_name": emoji_name,
            },
        )
        return Reaction(**reaction_data)

    # User operations

    async def get_users(self, limit: int = 100, page: int = 0) -> UsersResponse:
        """Get users with pagination.

        Args:
            limit: Maximum number of users to return
            page: Page number for pagination

        Returns:
            UsersResponse with list of users
        """
        await self.login()
        users_data = await to_thread(
            self._driver.users.get_users,
            page=page,
            per_page=limit,
        )

        users = [User(**u) for u in users_data]
        return UsersResponse(users=users, total_count=len(users))

    async def get_user_profile(self, user_id: str) -> UserProfile:
        """Get a user's profile.

        Args:
            user_id: The user ID

        Returns:
            UserProfile object
        """
        await self.login()
        user_data = await to_thread(self._driver.users.get_user, user_id)
        return UserProfile(**user_data)

    async def get_me(self) -> UserProfile:
        """Get the current authenticated user's profile.

        Returns:
            UserProfile of the bot/integration user
        """
        await self.login()
        user_data = await to_thread(self._driver.users.get_user, "me")
        return UserProfile(**user_data)

    async def create_direct_channel(self, user_id_1: str, user_id_2: str) -> Channel:
        """Create a direct message channel between two users.

        Args:
            user_id_1: First user ID
            user_id_2: Second user ID

        Returns:
            The created Channel
        """
        await self.login()
        channel_data = await to_thread(
            self._driver.channels.create_direct_channel,
            options=[user_id_1, user_id_2],
        )
        return Channel(**channel_data)


# Global client instance
_client: MattermostClient | None = None


def get_mattermost_client() -> MattermostClient:
    """Get the global Mattermost client instance."""
    global _client
    if _client is None:
        _client = MattermostClient()
    return _client


async def init_client() -> MattermostClient:
    """Initialize and return the Mattermost client."""
    client = get_mattermost_client()
    await client.login()
    return client


async def close_client() -> None:
    """Close the Mattermost client connection."""
    global _client
    if _client is not None:
        await _client.logout()
        _client = None
