"""FastMCP server setup and configuration."""

from fastmcp import FastMCP

# Create the FastMCP server instance
mcp = FastMCP(
    "mattermost-mcp",
    instructions="""Mattermost MCP Server - Interact with Mattermost workspaces.

Available operations:
- List and browse channels
- Read channel message history
- Post messages and reply to threads
- Add emoji reactions
- List users and view profiles
- Monitor channels for specific topics

All channel and user IDs are Mattermost internal IDs.
""",
)


def get_mcp() -> FastMCP:
    """Get the FastMCP server instance."""
    return mcp
