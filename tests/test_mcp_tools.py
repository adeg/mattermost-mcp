"""Tests for MCP tools."""

import pytest

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


class TestModels:
    """Tests for Pydantic models."""

    def test_channel_model(self, sample_channel: dict) -> None:
        """Test Channel model creation."""
        channel = Channel(**sample_channel)
        assert channel.id == "channel123"
        assert channel.name == "test-channel"
        assert channel.display_name == "Test Channel"
        assert channel.type == "O"

    def test_post_model(self, sample_post: dict) -> None:
        """Test Post model creation."""
        post = Post(**sample_post)
        assert post.id == "post123"
        assert post.message == "Test message"
        assert post.user_id == "user123"
        assert post.channel_id == "channel123"

    def test_user_model(self, sample_user: dict) -> None:
        """Test User model creation."""
        user = User(**sample_user)
        assert user.id == "user123"
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.is_bot is False

    def test_user_profile_model(self, sample_user: dict) -> None:
        """Test UserProfile model creation with extended fields."""
        profile_data = {
            **sample_user,
            "last_picture_update": 1704067200000,
            "auth_service": "",
            "email_verified": True,
            "notify_props": {},
            "props": {},
        }
        profile = UserProfile(**profile_data)
        assert profile.id == "user123"
        assert profile.email_verified is True

    def test_channels_response(self, sample_channel: dict) -> None:
        """Test ChannelsResponse model."""
        response = ChannelsResponse(
            channels=[Channel(**sample_channel)],
            total_count=1,
        )
        assert len(response.channels) == 1
        assert response.total_count == 1

    def test_posts_response(self, sample_post: dict) -> None:
        """Test PostsResponse model."""
        post = Post(**sample_post)
        response = PostsResponse(
            posts={post.id: post},
            order=[post.id],
            next_post_id="",
            prev_post_id="",
        )
        assert len(response.posts) == 1
        assert response.order == ["post123"]

    def test_users_response(self, sample_user: dict) -> None:
        """Test UsersResponse model."""
        response = UsersResponse(
            users=[User(**sample_user)],
            total_count=1,
        )
        assert len(response.users) == 1
        assert response.total_count == 1

    def test_reaction_model(self) -> None:
        """Test Reaction model."""
        reaction = Reaction(
            user_id="user123",
            post_id="post123",
            emoji_name="thumbsup",
            create_at=1704067200000,
        )
        assert reaction.emoji_name == "thumbsup"
        assert reaction.user_id == "user123"


class TestConfig:
    """Tests for configuration."""

    def test_settings_from_env(self) -> None:
        """Test that settings can be loaded from environment."""
        from mattermost_mcp.config import get_settings

        settings = get_settings()
        assert settings.mattermost_url == "https://mattermost.test.com"
        assert settings.mattermost_token == "test-token"
        assert settings.mattermost_team_id == "test-team-id"

    def test_monitoring_config_defaults(self) -> None:
        """Test monitoring config defaults."""
        from mattermost_mcp.config import MonitoringConfig

        config = MonitoringConfig()
        assert config.enabled is False
        assert config.schedule == "*/5 * * * *"
        assert config.message_limit == 50

    def test_llm_config_defaults(self) -> None:
        """Test LLM config defaults."""
        from mattermost_mcp.config import LlmConfig

        config = LlmConfig()
        assert config.model == "claude-sonnet-4-20250514"
        assert config.max_tokens == 1000


class TestStateManager:
    """Tests for state persistence."""

    def test_state_manager_init(self, tmp_path) -> None:
        """Test StateManager initialization."""
        from mattermost_mcp.monitoring.persistence import StateManager

        state_file = tmp_path / "test-state.json"
        manager = StateManager(str(state_file))

        assert not manager.is_post_processed("channel1", "post1")

    def test_mark_post_processed(self, tmp_path) -> None:
        """Test marking posts as processed."""
        from mattermost_mcp.monitoring.persistence import StateManager

        state_file = tmp_path / "test-state.json"
        manager = StateManager(str(state_file))

        manager.mark_post_processed("channel1", "post1")
        assert manager.is_post_processed("channel1", "post1")
        assert not manager.is_post_processed("channel1", "post2")

    def test_save_and_load_state(self, tmp_path) -> None:
        """Test state persistence."""
        from mattermost_mcp.monitoring.persistence import StateManager

        state_file = tmp_path / "test-state.json"

        # Create and save state
        manager1 = StateManager(str(state_file))
        manager1.mark_post_processed("channel1", "post1")
        manager1.mark_post_processed("channel1", "post2")
        manager1.save_state()

        # Load state in new manager
        manager2 = StateManager(str(state_file))
        assert manager2.is_post_processed("channel1", "post1")
        assert manager2.is_post_processed("channel1", "post2")


class TestScheduler:
    """Tests for the monitoring scheduler."""

    def test_cron_parsing(self) -> None:
        """Test cron expression parsing."""
        from mattermost_mcp.monitoring.scheduler import MonitoringScheduler

        async def dummy_callback():
            pass

        scheduler = MonitoringScheduler("*/5 * * * *", dummy_callback)
        cron_args = scheduler._parse_cron("*/5 * * * *")

        assert cron_args["minute"] == "*/5"
        assert cron_args["hour"] == "*"
        assert cron_args["day"] == "*"
        assert cron_args["month"] == "*"
        assert cron_args["day_of_week"] == "*"

    def test_invalid_cron_expression(self) -> None:
        """Test invalid cron expression handling."""
        from mattermost_mcp.monitoring.scheduler import MonitoringScheduler

        async def dummy_callback():
            pass

        scheduler = MonitoringScheduler("invalid", dummy_callback)

        with pytest.raises(ValueError):
            scheduler._parse_cron("invalid")
