"""Pydantic models for Mattermost API responses."""

from typing import Any

from pydantic import BaseModel, Field


class Channel(BaseModel):
    """Mattermost channel model."""

    id: str
    team_id: str = ""
    display_name: str = ""
    name: str = ""
    type: str = ""
    header: str = ""
    purpose: str = ""
    create_at: int = 0
    update_at: int = 0
    delete_at: int = 0
    total_msg_count: int = 0
    creator_id: str = ""


class Post(BaseModel):
    """Mattermost post/message model."""

    id: str
    create_at: int = 0
    update_at: int = 0
    delete_at: int = 0
    edit_at: int = 0
    user_id: str = ""
    channel_id: str = ""
    root_id: str = ""
    original_id: str = ""
    message: str = ""
    type: str = ""
    props: dict[str, Any] = Field(default_factory=dict)
    hashtags: str = ""
    pending_post_id: str = ""
    reply_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class User(BaseModel):
    """Mattermost user model."""

    id: str
    username: str = ""
    email: str = ""
    first_name: str = ""
    last_name: str = ""
    nickname: str = ""
    position: str = ""
    roles: str = ""
    locale: str = ""
    timezone: dict[str, Any] = Field(default_factory=dict)
    is_bot: bool = False
    bot_description: str = ""
    create_at: int = 0
    update_at: int = 0
    delete_at: int = 0


class UserProfile(User):
    """Extended user profile with additional fields."""

    last_picture_update: int = 0
    auth_service: str = ""
    email_verified: bool = False
    notify_props: dict[str, Any] = Field(default_factory=dict)
    props: dict[str, Any] = Field(default_factory=dict)
    terms_of_service_id: str = ""
    terms_of_service_create_at: int = 0


class Reaction(BaseModel):
    """Mattermost reaction model."""

    user_id: str
    post_id: str
    emoji_name: str
    create_at: int = 0


class PostsResponse(BaseModel):
    """Response model for posts listing."""

    posts: dict[str, Post] = Field(default_factory=dict)
    order: list[str] = Field(default_factory=list)
    next_post_id: str = ""
    prev_post_id: str = ""


class ChannelsResponse(BaseModel):
    """Response model for channels listing."""

    channels: list[Channel] = Field(default_factory=list)
    total_count: int = 0


class UsersResponse(BaseModel):
    """Response model for users listing."""

    users: list[User] = Field(default_factory=list)
    total_count: int = 0
