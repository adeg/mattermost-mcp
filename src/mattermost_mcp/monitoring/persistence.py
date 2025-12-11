"""State persistence for the monitoring system."""

import json
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from mattermost_mcp.logging import get_logger

logger = get_logger(__name__)


class MonitorState(BaseModel):
    """State data for the monitoring system."""

    last_run: str = Field(default_factory=lambda: datetime.now().isoformat())
    processed_posts: dict[str, list[str]] = Field(default_factory=dict)  # channel_id -> list of post_ids


class StateManager:
    """Manages persistent state for the monitoring system."""

    def __init__(self, state_file_path: str) -> None:
        """Initialize the state manager.

        Args:
            state_file_path: Path to the JSON state file
        """
        self._state_file_path = Path(state_file_path).resolve()
        self._state = self._load_state()

    def _load_state(self) -> MonitorState:
        """Load state from file or create default state."""
        try:
            if self._state_file_path.exists():
                data = json.loads(self._state_file_path.read_text())
                return MonitorState(**data)
        except Exception as e:
            logger.error("Error loading state", error=str(e), path=str(self._state_file_path))

        return MonitorState()

    def save_state(self) -> None:
        """Save state to file."""
        try:
            # Ensure directory exists
            self._state_file_path.parent.mkdir(parents=True, exist_ok=True)

            # Update last run timestamp
            self._state.last_run = datetime.now().isoformat()

            # Write state to file
            self._state_file_path.write_text(self._state.model_dump_json(indent=2))
            logger.debug("State saved", path=str(self._state_file_path))
        except Exception as e:
            logger.error("Error saving state", error=str(e), path=str(self._state_file_path))

    def is_post_processed(self, channel_id: str, post_id: str) -> bool:
        """Check if a post has been processed.

        Args:
            channel_id: The channel ID
            post_id: The post ID

        Returns:
            True if the post has been processed
        """
        channel_posts = self._state.processed_posts.get(channel_id, [])
        return post_id in channel_posts

    def mark_post_processed(self, channel_id: str, post_id: str) -> None:
        """Mark a post as processed.

        Args:
            channel_id: The channel ID
            post_id: The post ID
        """
        if channel_id not in self._state.processed_posts:
            self._state.processed_posts[channel_id] = []

        if not self.is_post_processed(channel_id, post_id):
            self._state.processed_posts[channel_id].append(post_id)

    def mark_posts_processed(self, channel_id: str, post_ids: list[str]) -> None:
        """Mark multiple posts as processed.

        Args:
            channel_id: The channel ID
            post_ids: List of post IDs
        """
        for post_id in post_ids:
            self.mark_post_processed(channel_id, post_id)

    def get_last_run(self) -> datetime:
        """Get the last run timestamp.

        Returns:
            Last run datetime
        """
        return datetime.fromisoformat(self._state.last_run)

    def get_processed_post_ids(self, channel_id: str) -> list[str]:
        """Get all processed post IDs for a channel.

        Args:
            channel_id: The channel ID

        Returns:
            List of processed post IDs
        """
        return self._state.processed_posts.get(channel_id, [])

    def get_all_processed_posts(self) -> dict[str, list[str]]:
        """Get all processed posts.

        Returns:
            Dictionary mapping channel IDs to processed post IDs
        """
        return dict(self._state.processed_posts)
