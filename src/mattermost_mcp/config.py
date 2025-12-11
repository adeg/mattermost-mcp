"""Configuration management using Pydantic Settings."""

import os

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LlmConfig(BaseSettings):
    """LLM configuration for message analysis."""

    model_config = SettingsConfigDict(env_prefix="ANTHROPIC_", extra="ignore")

    api_key: str = Field(default="")
    model: str = Field(default="claude-sonnet-4-20250514")
    max_tokens: int = Field(default=1000)


class MonitoringConfig(BaseSettings):
    """Monitoring system configuration."""

    model_config = SettingsConfigDict(env_prefix="MONITORING_", extra="ignore")

    enabled: bool = Field(default=False)
    schedule: str = Field(default="*/5 * * * *")
    channels: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    message_limit: int = Field(default=50)
    state_path: str = Field(default="./monitor-state.json")
    process_existing_on_first_run: bool = Field(default=False, validation_alias="MONITORING_PROCESS_EXISTING")
    first_run_limit: int = Field(default=10)

    @field_validator("channels", "topics", mode="before")
    @classmethod
    def parse_comma_separated(cls, v: str | list[str]) -> list[str]:
        """Parse comma-separated string into list."""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @classmethod
    def from_env(cls) -> MonitoringConfig:
        """Create config from environment variables."""
        return cls(
            _env_file=None,
            enabled=os.getenv("MONITORING_ENABLED", "false").lower() == "true",
            schedule=os.getenv("MONITORING_SCHEDULE", "*/5 * * * *"),
            channels=os.getenv("MONITORING_CHANNELS", ""),
            topics=os.getenv("MONITORING_TOPICS", ""),
            message_limit=int(os.getenv("MONITORING_MESSAGE_LIMIT", "50")),
            state_path=os.getenv("MONITORING_STATE_PATH", "./monitor-state.json"),
            process_existing_on_first_run=os.getenv("MONITORING_PROCESS_EXISTING", "false").lower() == "true",
            first_run_limit=int(os.getenv("MONITORING_FIRST_RUN_LIMIT", "10")),
        )


class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Mattermost connection
    mattermost_url: str = Field(alias="MATTERMOST_URL")
    mattermost_token: str = Field(alias="MATTERMOST_TOKEN")
    mattermost_team_id: str = Field(alias="MATTERMOST_TEAM_ID")

    # Server settings
    http_port: int = Field(default=8000, alias="HTTP_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")

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
        _monitoring_config = MonitoringConfig.from_env()
    return _monitoring_config


def get_llm_config() -> LlmConfig:
    """Get the global LLM config instance."""
    global _llm_config
    if _llm_config is None:
        _llm_config = LlmConfig()
    return _llm_config
