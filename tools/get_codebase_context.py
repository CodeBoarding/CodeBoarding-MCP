from server import mcp
from utils.read_repo import get_markdown

@mcp.tool()
def get_context_with_code(repo: str, subdir_prefix: str) -> str:
    """
    Load onboarding markdown content with GitHub code links replaced by code blocks.
    """
    return get_markdown(repo, subdir_prefix, inline_code=True, cache=True)

@mcp.tool()
def get_context_without_code(repo: str, subdir_prefix: str) -> str:
    """
    Load onboarding markdown content without replacing GitHub code links.
    """
    return get_markdown(repo, subdir_prefix, inline_code=False, cache=True)