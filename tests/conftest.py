"""Pytest configuration and fixtures."""

import os
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest

# Set test environment variables before importing application modules
os.environ.setdefault("MATTERMOST_URL", "https://mattermost.test.com")
os.environ.setdefault("MATTERMOST_TOKEN", "test-token")
os.environ.setdefault("MATTERMOST_TEAM_ID", "test-team-id")


@pytest.fixture
def mock_mattermost_client() -> MagicMock:
    """Create a mock Mattermost client."""
    client = MagicMock()
    client.login = AsyncMock()
    client.logout = AsyncMock()
    client.get_channels = AsyncMock()
    client.get_posts_for_channel = AsyncMock()
    client.create_post = AsyncMock()
    client.get_post_thread = AsyncMock()
    client.add_reaction = AsyncMock()
    client.get_users = AsyncMock()
    client.get_user_profile = AsyncMock()
    client.get_me = AsyncMock()
    return client


@pytest.fixture
def sample_channel() -> dict:
    """Sample channel data."""
    return {
        "id": "channel123",
        "team_id": "team123",
        "display_name": "Test Channel",
        "name": "test-channel",
        "type": "O",
        "header": "Test header",
        "purpose": "Test purpose",
        "create_at": 1704067200000,
        "update_at": 1704067200000,
        "delete_at": 0,
        "total_msg_count": 100,
        "creator_id": "user123",
    }


@pytest.fixture
def sample_post() -> dict:
    """Sample post data."""
    return {
        "id": "post123",
        "create_at": 1704067200000,
        "update_at": 1704067200000,
        "delete_at": 0,
        "edit_at": 0,
        "user_id": "user123",
        "channel_id": "channel123",
        "root_id": "",
        "original_id": "",
        "message": "Test message",
        "type": "",
        "props": {},
        "hashtags": "",
        "pending_post_id": "",
        "reply_count": 0,
        "metadata": {},
    }


@pytest.fixture
def sample_user() -> dict:
    """Sample user data."""
    return {
        "id": "user123",
        "username": "testuser",
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "nickname": "tester",
        "position": "Developer",
        "roles": "system_user",
        "locale": "en",
        "timezone": {"useAutomaticTimezone": True},
        "is_bot": False,
        "bot_description": "",
        "create_at": 1704067200000,
        "update_at": 1704067200000,
        "delete_at": 0,
    }
