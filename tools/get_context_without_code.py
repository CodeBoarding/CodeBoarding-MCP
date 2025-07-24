# tools/get_context_without_code.py

from utils.read_repo import get_markdown
from server import server
@server.tool()
def get_context_without_code(repo_name: str) -> str:
    """
    Load onboarding markdown content without replacing GitHub code links.
    """
    return get_markdown(repo_name=repo_name, inline_code=False, cache=False)