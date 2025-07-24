import re
import requests
from collections import defaultdict

try:
    import tiktoken
    TOKEN_ENCODER = tiktoken.get_encoding("cl100k_base")
except ImportError:
    TOKEN_ENCODER = None  # Token counting unavailable without tiktoken


def replace_mermaid_blocks(markdown: str) -> str:
    """
    Detects mermaid code blocks and replaces them with LLM-friendly summaries.
    Strips out graph LR definitions and any `click ... href` links first.
    """
    mermaid_block_pattern = re.compile(
        r"```mermaid\s*\n(.*?)```",
        re.DOTALL | re.IGNORECASE
    )

    def convert_mermaid(match):
        code = match.group(1)
        # Remove 'graph LR' lines
        code = re.sub(r'^\s*graph\s+LR.*$', '', code, flags=re.MULTILINE)
        # Remove any 'click <id> href "url" "label"' lines
        code = re.sub(
            r'^\s*click\s+\w+\s+href\s+"[^"]+"\s+"[^"]+"',
            '', code, flags=re.MULTILINE
        )
        return format_mermaid_to_llm_markdown_no_links(code)

    return mermaid_block_pattern.sub(convert_mermaid, markdown)


def format_mermaid_to_llm_markdown_no_links(mermaid_str: str) -> str:
    """
    Parses node and edge definitions out of a (cleaned) mermaid graph
    and turns them into a simple bullet-list summary.
    """
    node_pat = re.compile(r'(\w+)\["(.+?)"\]')
    nodes = dict(node_pat.findall(mermaid_str))

    edge_pat = re.compile(r'(\w+)\s+--\s+"(.+?)"\s+-->\s+(\w+)')
    edges = edge_pat.findall(mermaid_str)

    forward = defaultdict(list)
    reverse = defaultdict(list)
    for src, label, dst in edges:
        forward[src].append((label, dst))
        reverse[dst].append((label, src))

    lines = ["**Core Components:**", ""]
    for key, name in nodes.items():
        lines.append(f"- {name}")
        for label, dst in forward.get(key, []):
            dst_name = nodes.get(dst, dst)
            lines.append(f"  {label}:")
            lines.append(f"  - {dst_name}")
        for label, src in reverse.get(key, []):
            if key not in [d for _, d in forward.get(src, [])]:
                src_name = nodes.get(src, src)
                lines.append(f"  {label} by:")
                lines.append(f"  - {src_name}")
        lines.append("")
    return "\n".join(lines)

def format_github_html_links_to_plaintext(
    markdown: str,
    inline_code: bool,
) -> str:
    """
    Converts GitHub HTML <a> links with line ranges into plaintext summaries,
    optionally embedding the code and token counts.

    Args:
      markdown: input markdown containing GitHub blob links.
      inline_code: if True, fetch & include the code snippet in a fenced block
                   (with optional token count). If False, only plaintext.

    Example:
      <a href="https://github.com/owner/repo/blob/main/path/to.py#L10-L20">`symbol` (10:20)</a>
    -->
      symbol (path/to.py: lines 10–20)
      ```python
      # code lines...
      ```
      [Token count: X]
    or, with inline_code=False:
      symbol (path/to.py: lines 10–20)
    """
    pattern = re.compile(
        r'<a href="https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/blob/'
        r'(?P<branch>[^/]+)/(?P<path>[^#]+)#L(?P<start>\d+)-L(?P<end>\d+)"[^>]*>'
        r'`(?P<symbol>[^`]+)` \(\d+:\d+\)</a>'
    )

    def replacer(match):
        owner = match.group('owner')
        repo = match.group('repo')
        branch = match.group('branch')
        path = match.group('path')
        start = int(match.group('start'))
        end = int(match.group('end'))
        symbol = match.group('symbol')
        base_text = f"{symbol} ({path}: lines {start}–{end})"

        if not inline_code:
            # Return only plaintext summary
            return base_text

        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
        snippet = None
        token_info = ''

        try:
            resp = requests.get(raw_url, timeout=5)
            resp.raise_for_status()
            lines = resp.text.splitlines()
            snippet_lines = lines[start-1:end]
            snippet = '\n'.join(snippet_lines)
            if TOKEN_ENCODER and snippet:
                token_count = len(TOKEN_ENCODER.encode(snippet))
                token_info = f"\n[Token count: {token_count}]"
        except Exception:
            snippet = None  # fallback

        if snippet:
            return f"{base_text}\n```python\n{snippet}\n```{token_info}"
        return base_text

    return pattern.sub(replacer, markdown)