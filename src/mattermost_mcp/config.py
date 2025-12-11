"""Configuration management using Pydantic Settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LlmConfig(BaseSettings):
    """LLM configuration for message analysis."""

    model_config = SettingsConfigDict(env_prefix="ANTHROPIC_", extra="ignore")

    api_key: str = ""
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 1000


class MonitoringConfig(BaseSettings):
    """Monitoring system configuration."""

    model_config = SettingsConfigDict(env_prefix="MONITORING_", extra="ignore")

    enabled: bool = False
    schedule: str = "*/5 * * * *"
    channels: str = ""  # Comma-separated channel names
    topics: str = ""  # Comma-separated topic keywords
    message_limit: int = 50
    state_path: str = "./monitor-state.json"
    process_existing_on_first_run: bool = Field(default=False, validation_alias="MONITORING_PROCESS_EXISTING")
    first_run_limit: int = 10

    def get_channels(self) -> list[str]:
        """Parse comma-separated channels into list."""
        if not self.channels:
            return []
        return [c.strip() for c in self.channels.split(",") if c.strip()]

    def get_topics(self) -> list[str]:
        """Parse comma-separated topics into list."""
        if not self.topics:
            return []
        return [t.strip() for t in self.topics.split(",") if t.strip()]


class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Mattermost connection (required)
    mattermost_url: str
    mattermost_token: str
    mattermost_team_id: str

    # Server settings (optional with defaults)
    http_port: int = 8000
    log_level: str = "INFO"
    log_format: str = "json"

    @property
    def mattermost_base_url(self) -> str:
        """Get the base URL without /api/v4 suffix."""
        url = self.mattermost_url.rstrip("/")
        if url.endswith("/api/v4"):
            url = url[:-7]
        return url


# Global settings instance
_settings: Settings | None = None
_monitoring_config: MonitoringConfig | None = None
_llm_config: LlmConfig | None = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def get_monitoring_config() -> MonitoringConfig:
    """Get the global monitoring config instance."""
    global _monitoring_config
    if _monitoring_config is None:
        _monitoring_config = MonitoringConfig()
    return _monitoring_config


def get_llm_config() -> LlmConfig:
    """Get the global LLM config instance."""
    global _llm_config
    if _llm_config is None:
        _llm_config = LlmConfig()
    return _llm_config
