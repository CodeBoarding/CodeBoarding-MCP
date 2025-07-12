import re
from collections import defaultdict

def replace_mermaid_blocks(markdown: str) -> str:
    """
    Detects mermaid code blocks and replaces them with LLM-friendly summaries.
    """
    mermaid_block_pattern = re.compile(r"```mermaid\n(.*?)```", re.DOTALL)

    def convert_mermaid(match):
        mermaid_code = match.group(1)
        return format_mermaid_to_llm_markdown_no_links(mermaid_code)

    return mermaid_block_pattern.sub(convert_mermaid, markdown)

def format_mermaid_to_llm_markdown_no_links(mermaid_str: str) -> str:

    node_pattern = re.compile(r'(\w+)\["(.+?)"\]')
    nodes = dict(node_pattern.findall(mermaid_str))

    edge_pattern = re.compile(r'(\w+)\s+--\s+"(.+?)"\s+-->\s+(\w+)')
    edges = edge_pattern.findall(mermaid_str)

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
            src_name = nodes.get(src, src)
            if key not in [d for _, d in forward.get(src, [])]:
                lines.append(f"  {label} by:")
                lines.append(f"  - {src_name}")
        lines.append("")

    return "\n".join(lines)


def format_github_html_links_to_plaintext(markdown: str) -> str:
    """
    Converts GitHub HTML <a> links with line ranges to LLM-friendly plaintext.
    Example:
    <a href="...">`symbol` (10:20)</a> --> symbol  (path/to/file.py: lines 10–20)
    """
    pattern = re.compile(
        r'<a href="https://github\.com/[^/]+/[^/]+/blob/[^/]+/(?P<path>[^#]+)#L(?P<start>\d+)-L(?P<end>\d+)"[^>]*>`(?P<symbol>[^`]+)` \(\d+:\d+\)</a>'
    )

    def replacer(match):
        symbol = match.group("symbol")
        path = match.group("path")
        start = match.group("start")
        end = match.group("end")
        return f"{symbol}  ({path}: lines {start}–{end})"

    return pattern.sub(replacer, markdown)