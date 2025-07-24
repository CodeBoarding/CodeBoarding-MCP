# tools/get_context_with_code.py

from utils.read_repo import get_markdown
from server import server
@server.tool()
def get_context_with_code(repo_name: str, token_budget: int) -> str:
    """
    Load onboarding markdown content with GitHub code links replaced by code blocks.
    """
    return get_markdown(repo_name=repo_name, inline_code=True, cache=False, token_budget=token_budget)

