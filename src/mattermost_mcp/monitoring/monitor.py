"""Topic monitoring orchestrator."""

from datetime import UTC, datetime

from mattermost_mcp.clients.mattermost import MattermostClient
from mattermost_mcp.config import LlmConfig, MonitoringConfig, get_settings
from mattermost_mcp.logging import get_logger
from mattermost_mcp.monitoring.analyzer import AnalysisResult, MessageAnalyzer
from mattermost_mcp.monitoring.persistence import StateManager
from mattermost_mcp.monitoring.scheduler import MonitoringScheduler

logger = get_logger(__name__)


class TopicMonitor:
    """Monitors Mattermost channels for messages related to configured topics."""

    def __init__(
        self,
        client: MattermostClient,
        config: MonitoringConfig,
        llm_config: LlmConfig | None = None,
    ) -> None:
        """Initialize the topic monitor.

        Args:
            client: Mattermost client
            config: Monitoring configuration
            llm_config: Optional LLM configuration
        """
        self._client = client
        self._config = config
        self._state_manager = StateManager(config.state_path)
        self._analyzer = MessageAnalyzer(
            client=client,
            state_manager=self._state_manager,
            topics=config.topics,
            message_limit=config.message_limit,
            llm_config=llm_config,
        )
        self._scheduler = MonitoringScheduler(config.schedule, self._run_monitoring)
        self._target_user_id: str | None = None
        self._notification_channel_id: str | None = None

    async def start(self) -> bool:
        """Start the monitoring process.

        Returns:
            True if started successfully
        """
        try:
            # Find a user for notifications
            await self._find_target_user()

            # Set up notification channel
            await self._setup_notification_channel()

            # Start the scheduler
            return self._scheduler.start()
        except Exception as e:
            logger.error("Error starting topic monitor", error=str(e))
            return False

    def stop(self) -> bool:
        """Stop the monitoring process.

        Returns:
            True if stopped successfully
        """
        return self._scheduler.stop()

    async def run_now(self) -> None:
        """Run the monitoring process immediately."""
        await self._scheduler.run_now()

    def is_running(self) -> bool:
        """Check if a monitoring task is currently running.

        Returns:
            True if running
        """
        return self._scheduler.is_task_running()

    def is_enabled(self) -> bool:
        """Check if the scheduler is active.

        Returns:
            True if the scheduler is running
        """
        return self._scheduler.is_scheduler_running()

    async def _find_target_user(self) -> None:
        """Find a suitable user for notifications."""
        try:
            users_response = await self._client.get_users(limit=100)
            users = users_response.users

            if not users:
                raise ValueError("No users found in Mattermost")

            # Try to find an admin user
            target = next((u for u in users if "system_admin" in u.roles), None)

            # Fall back to regular user
            if not target:
                target = next((u for u in users if not u.is_bot and "system_user" in u.roles), None)

            # Fall back to any non-bot user
            if not target:
                target = next((u for u in users if not u.is_bot), None)

            # Fall back to first user
            if not target and users:
                target = users[0]

            if target:
                self._target_user_id = target.id
                logger.info("Found notification target user", username=target.username)
            else:
                raise ValueError("No suitable user found for notifications")

        except Exception as e:
            logger.error("Error finding target user", error=str(e))
            raise

    async def _setup_notification_channel(self) -> None:
        """Set up a channel for notifications (DM or fallback to public)."""
        if not self._target_user_id:
            raise ValueError("No target user found for notifications")

        try:
            # Get the bot's user ID
            me = await self._client.get_me()
            logger.info("Running as user", username=me.username)

            # Try to create a DM channel
            try:
                dm_channel = await self._client.create_direct_channel(me.id, self._target_user_id)
                self._notification_channel_id = dm_channel.id
                logger.info("Created DM channel for notifications")
                return
            except Exception as e:
                logger.warning("Could not create DM channel, using fallback", error=str(e))

            # Fall back to town-square or first public channel
            channels_response = await self._client.get_channels(limit=200)
            channels = channels_response.channels

            fallback = next((c for c in channels if c.name == "town-square"), None)
            if not fallback:
                fallback = next((c for c in channels if c.type == "O"), None)
            if not fallback and channels:
                fallback = channels[0]

            if fallback:
                self._notification_channel_id = fallback.id
                logger.info("Using fallback channel for notifications", channel=fallback.name)
            else:
                raise ValueError("No suitable channel found for notifications")

        except Exception as e:
            logger.error("Error setting up notification channel", error=str(e))
            raise

    async def _run_monitoring(self) -> None:
        """Run the monitoring process."""
        try:
            results: list[AnalysisResult] = []

            # Check if this is the first run
            is_first_run = not self._config.process_existing_on_first_run

            # Analyze each configured channel
            for channel_name in self._config.channels:
                result = await self._analyzer.analyze_channel(
                    channel_name=channel_name,
                    first_run=is_first_run,
                    first_run_limit=self._config.first_run_limit,
                )
                if result:
                    results.append(result)

            # Send notifications for relevant results
            for result in results:
                await self._send_notification(result)

        except Exception as e:
            logger.error("Error running monitoring", error=str(e))

    async def _send_notification(self, result: AnalysisResult) -> None:
        """Send a notification for relevant messages.

        Args:
            result: Analysis result containing relevant posts
        """
        if not self._notification_channel_id:
            logger.warning("No notification channel configured")
            return

        try:
            # Get target username for mention
            username = "user"
            if self._target_user_id:
                try:
                    profile = await self._client.get_user_profile(self._target_user_id)
                    username = profile.username
                except Exception:
                    pass

            # Build the Mattermost base URL
            settings = get_settings()
            base_url = settings.mattermost_base_url

            # Build notification message
            message = f"@{username} **Topic Monitor Alert**\n\n"
            message += f"Found {len(result.posts)} relevant posts in channel: **{result.channel_name}**\n\n"
            message += "**Recent Messages:**\n"

            for post in result.posts[:5]:  # Limit to 5 posts
                # Get post author username
                author = post.user_id
                try:
                    author_profile = await self._client.get_user_profile(post.user_id)
                    author = author_profile.username
                except Exception:
                    pass

                # Format timestamp
                timestamp = datetime.fromtimestamp(post.create_at / 1000, tz=UTC).strftime("%Y-%m-%d %H:%M")

                # Create message link
                team_id = settings.mattermost_team_id
                message_link = f"{base_url}/{team_id}/pl/{post.id}"

                topics_str = ", ".join(result.relevant_topics)
                message += f'- [{timestamp} ({author})]({message_link}): "{post.message[:100]}{"..." if len(post.message) > 100 else ""}"\n'
                message += f"  Topics: **{topics_str}**\n\n"

            if len(result.posts) > 5:
                message += f"... and {len(result.posts) - 5} more\n"

            # Send the notification
            await self._client.create_post(self._notification_channel_id, message)
            logger.info("Sent notification", channel=result.channel_name, posts=len(result.posts))

        except Exception as e:
            logger.error("Error sending notification", error=str(e))


# Global monitor instance
_monitor: TopicMonitor | None = None


def get_monitor() -> TopicMonitor | None:
    """Get the global monitor instance.

    Returns:
        TopicMonitor instance or None if not initialized
    """
    return _monitor


async def init_monitor(
    client: MattermostClient,
    config: MonitoringConfig,
    llm_config: LlmConfig | None = None,
) -> TopicMonitor:
    """Initialize and start the topic monitor.

    Args:
        client: Mattermost client
        config: Monitoring configuration
        llm_config: Optional LLM configuration

    Returns:
        Initialized TopicMonitor
    """
    global _monitor

    _monitor = TopicMonitor(client, config, llm_config)
    await _monitor.start()
    return _monitor


def stop_monitor() -> None:
    """Stop the global monitor."""
    global _monitor

    if _monitor:
        _monitor.stop()
        _monitor = None
