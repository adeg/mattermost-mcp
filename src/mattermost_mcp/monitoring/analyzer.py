"""Message analyzer with LLM support for topic detection."""

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from anthropic import Anthropic

from mattermost_mcp.clients.mattermost import MattermostClient
from mattermost_mcp.config import LlmConfig
from mattermost_mcp.logging import get_logger
from mattermost_mcp.models.mattermost import Post
from mattermost_mcp.monitoring.persistence import StateManager

logger = get_logger(__name__)


@dataclass
class AnalysisResult:
    """Result of analyzing messages in a channel."""

    channel_id: str
    channel_name: str
    posts: list[Post]
    relevant_topics: list[str]


@dataclass
class LlmAnalysisResult:
    """Result of LLM-based analysis."""

    relevant_posts: list[Post]
    relevant_topics: list[str]
    post_topics: dict[str, list[str]] = field(default_factory=dict)  # post_id -> list of topics


class MessageAnalyzer:
    """Analyzes messages for relevant topics using LLM or keyword matching."""

    def __init__(
        self,
        client: MattermostClient,
        state_manager: StateManager,
        topics: list[str],
        message_limit: int,
        llm_config: LlmConfig | None = None,
    ) -> None:
        """Initialize the message analyzer.

        Args:
            client: Mattermost client
            state_manager: State persistence manager
            topics: List of topics to search for
            message_limit: Maximum messages to analyze per channel
            llm_config: Optional LLM configuration for semantic analysis
        """
        self._client = client
        self._state_manager = state_manager
        self._topics = topics
        self._message_limit = message_limit
        self._llm_config = llm_config

    async def analyze_channel(
        self,
        channel_name: str,
        first_run: bool = False,
        first_run_limit: int | None = None,
    ) -> AnalysisResult | None:
        """Analyze messages in a channel for relevant topics.

        Args:
            channel_name: Name of the channel to analyze
            first_run: Whether this is the first run
            first_run_limit: Message limit for first run

        Returns:
            AnalysisResult if relevant posts found, None otherwise
        """
        try:
            logger.info("Analyzing channel", channel=channel_name)

            # Get channels to find the one we want
            channels_response = await self._client.get_channels(limit=200)
            channel = next((c for c in channels_response.channels if c.name == channel_name), None)

            if not channel:
                logger.warning("Channel not found", channel=channel_name)
                return None

            # Get posts for the channel
            limit = first_run_limit if first_run and first_run_limit else self._message_limit
            posts_response = await self._client.get_posts_for_channel(channel.id, limit=limit)

            # Filter out already processed posts
            processed_ids = set(self._state_manager.get_processed_post_ids(channel.id))
            unprocessed_posts = [
                posts_response.posts[pid]
                for pid in posts_response.order
                if pid in posts_response.posts and pid not in processed_ids
            ]

            if not unprocessed_posts:
                logger.debug("No new posts to analyze", channel=channel_name)
                return None

            # Enrich posts with user information
            enriched_posts = await self._enrich_posts_with_user_info(unprocessed_posts)

            # Analyze posts
            analysis_result = await self._analyze_posts_with_llm(enriched_posts, channel_name)

            # Mark all posts as processed
            for post in unprocessed_posts:
                self._state_manager.mark_post_processed(channel.id, post.id)
            self._state_manager.save_state()

            if not analysis_result.relevant_posts:
                logger.debug("No relevant posts found", channel=channel_name)
                return None

            return AnalysisResult(
                channel_id=channel.id,
                channel_name=channel.name,
                posts=analysis_result.relevant_posts,
                relevant_topics=analysis_result.relevant_topics,
            )

        except Exception as e:
            logger.error("Error analyzing channel", channel=channel_name, error=str(e))
            return None

    async def _enrich_posts_with_user_info(self, posts: list[Post]) -> list[dict[str, Any]]:
        """Add user information to posts.

        Args:
            posts: List of posts to enrich

        Returns:
            List of enriched post dictionaries
        """
        user_cache: dict[str, dict[str, str]] = {}
        enriched = []

        for post in posts:
            post_dict = post.model_dump()

            try:
                if post.user_id not in user_cache:
                    user_profile = await self._client.get_user_profile(post.user_id)
                    user_cache[post.user_id] = {
                        "username": user_profile.username,
                        "first_name": user_profile.first_name,
                        "last_name": user_profile.last_name,
                    }

                post_dict["user_info"] = user_cache[post.user_id]
            except Exception:
                pass

            enriched.append(post_dict)

        return enriched

    async def _analyze_posts_with_llm(
        self,
        posts: list[dict[str, Any]],
        channel_name: str,
    ) -> LlmAnalysisResult:
        """Analyze posts using LLM for semantic topic matching.

        Args:
            posts: List of enriched post dictionaries
            channel_name: Name of the channel

        Returns:
            LlmAnalysisResult with relevant posts and topics
        """
        if not self._llm_config or not self._llm_config.api_key or not posts:
            logger.debug("Using fallback analysis (no LLM config or empty posts)")
            return self._fallback_analysis(posts)

        try:
            # Format posts for the prompt
            formatted_posts = "\n\n".join(
                f"[ID: {p['id']}] [{datetime.fromtimestamp(p['create_at'] / 1000, tz=UTC).isoformat()}] "
                f'{p.get("user_info", {}).get("username", p["user_id"])}: "{p["message"]}"'
                for p in posts
            )

            # Create Anthropic client
            anthropic = Anthropic(api_key=self._llm_config.api_key)

            prompt = f"""You are analyzing messages from a Mattermost channel named "{channel_name}".

Your task is to determine which messages are related to any of these topics: {", ".join(self._topics)}

Here are the messages:
{formatted_posts}

For each topic, list the IDs of messages that are relevant to that topic.
Format your response as JSON:
{{
  "topics": {{
    "topic1": ["post_id1", "post_id2"],
    "topic2": ["post_id3"]
  }}
}}

Only include topics that have at least one relevant message.
If no messages are relevant to any topic, return {{"topics": {{}}}}.

Be semantic in your analysis. For example, if the topic is "table tennis" and a message mentions "ping pong equipment" or "butterfly rackets", it should be considered relevant.
"""

            logger.debug("Sending request to Anthropic API")

            response = anthropic.messages.create(
                model=self._llm_config.model,
                max_tokens=self._llm_config.max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )

            # Parse response
            content = response.content[0].text if response.content else "{}"

            # Extract JSON from response
            json_match = re.search(r"\{[\s\S]*\}", content)
            if not json_match:
                logger.warning("Could not parse LLM response, using fallback")
                return self._fallback_analysis(posts)

            import json

            try:
                result = json.loads(json_match.group())
            except json.JSONDecodeError:
                logger.warning("Invalid JSON in LLM response, using fallback")
                return self._fallback_analysis(posts)

            # Extract relevant posts and topics
            relevant_post_ids: set[str] = set()
            relevant_topics: set[str] = set()
            post_topics: dict[str, list[str]] = {}

            topics_data = result.get("topics", {})
            for topic, post_ids in topics_data.items():
                if isinstance(post_ids, list) and post_ids:
                    relevant_topics.add(topic)
                    for pid in post_ids:
                        relevant_post_ids.add(pid)
                        if pid not in post_topics:
                            post_topics[pid] = []
                        post_topics[pid].append(topic)

            # Convert back to Post objects
            relevant_posts = [Post(**p) for p in posts if p["id"] in relevant_post_ids]

            logger.info(
                "LLM analysis complete",
                relevant_count=len(relevant_posts),
                topics=list(relevant_topics),
            )

            return LlmAnalysisResult(
                relevant_posts=relevant_posts,
                relevant_topics=list(relevant_topics),
                post_topics=post_topics,
            )

        except Exception as e:
            logger.error("Error calling Anthropic API", error=str(e))
            return self._fallback_analysis(posts)

    def _fallback_analysis(self, posts: list[dict[str, Any]]) -> LlmAnalysisResult:
        """Fallback analysis using simple keyword matching.

        Args:
            posts: List of enriched post dictionaries

        Returns:
            LlmAnalysisResult with keyword-matched posts
        """
        logger.debug("Using fallback keyword matching")

        relevant_posts: list[Post] = []
        relevant_topics: set[str] = set()
        post_topics: dict[str, list[str]] = {}

        for post_dict in posts:
            message = post_dict.get("message", "").lower()

            for topic in self._topics:
                if topic.lower() in message:
                    post = Post(**post_dict)
                    if post not in relevant_posts:
                        relevant_posts.append(post)
                    relevant_topics.add(topic)

                    if post.id not in post_topics:
                        post_topics[post.id] = []
                    post_topics[post.id].append(topic)

        return LlmAnalysisResult(
            relevant_posts=relevant_posts,
            relevant_topics=list(relevant_topics),
            post_topics=post_topics,
        )
