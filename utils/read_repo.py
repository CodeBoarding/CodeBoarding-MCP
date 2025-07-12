import requests
import logging
import re
import os

from utils.format import replace_mermaid_blocks
from utils.format import format_github_html_links_to_plaintext

GITHUB_API_HEADERS = {
    "Accept": "application/vnd.github.v3+json"
}


def extract_code_from_github_url(link: str) -> str:
    """
    Extract code from a GitHub link that includes a line range.
    Example: https://github.com/user/repo/blob/branch/path/to/file.py#L10-L20
    """
    match = re.match(
        r"https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/blob/(?P<branch>[^/]+)/(?P<filepath>[^#]+)#L(?P<start>\d+)-L(?P<end>\d+)",
        link
    )
    if not match:
        return f"\n⚠️ Could not parse link: {link}\n"

    groups = match.groupdict()
    raw_url = f"https://raw.githubusercontent.com/{groups['owner']}/{groups['repo']}/{groups['branch']}/{groups['filepath']}"
    start_line = int(groups['start'])
    end_line = int(groups['end'])

    response = requests.get(raw_url)
    if response.status_code != 200:
        return f"\n⚠️ Failed to fetch: {raw_url}\n"

    lines = response.text.splitlines()
    extracted = lines[start_line - 1:end_line]
    return f"\n```python\n{chr(10).join(extracted)}\n```\n"


def replace_github_links_with_code(markdown: str) -> str:
    """
    Replace all GitHub blob links with line numbers in a markdown string with actual code blocks.
    """
    def replacer(match):
        url = match.group(1)
        return extract_code_from_github_url(url)

    pattern = r'<a href="(https://github\.com/[^"]+#L\d+-L\d+)"[^>]*>.*?</a>'
    return re.sub(pattern, replacer, markdown)

def aggregate_markdown(repo: str, subdir_prefix: str, inline_code: bool = True) -> str:
    base_url = f"https://api.github.com/repos/{repo}/git/trees/main?recursive=1"
    tree = requests.get(base_url, headers=GITHUB_API_HEADERS).json().get("tree", [])

    md_files = [
        item['path'] for item in tree
        if item['type'] == 'blob'
        and item['path'].endswith(".md")
        and item['path'].startswith(subdir_prefix)
    ]

    for i, f in enumerate(md_files): # set onboarding.md to be first
        if "on_boarding.md" in f:
            md_files.insert(0, md_files.pop(i))
            break


    logging.info(f"Found {len(md_files)} markdown files in {subdir_prefix}" if md_files else f"No markdown files found in {subdir_prefix}")

    repo_name = subdir_prefix.rstrip("/").split("/")[-1]
    header = (
        f"\n\n# Project Structure & Detailed Overview of Project : {repo_name}\n\n"
        "This text provides first a high-level overview of the whole project, "
        "listing and describing its components, and then goes into more detail "
        "presenting each component again and its subcomponents.\n\n"
    )
    parts = [header]

    for md_path in md_files:
        raw_url = f"https://raw.githubusercontent.com/{repo}/main/{md_path}"
        r = requests.get(raw_url)
        if r.ok:
            content = r.text
            if inline_code:
                content = replace_github_links_with_code(content)
            component_name = md_path.split("/")[-1].split(".md")[0]
            if component_name == "on_boarding":
                header = "## System Architecture of the Whole Project:"
            else: 
                header = f"## System Architecture Overview of Component: {component_name}\n\n"
            content = header + replace_mermaid_blocks(content)
            content = format_github_html_links_to_plaintext(content)  # 🆕 apply HTML <a> cleaner
            parts.append(content)
        else:
            parts.append(f"\n\n# {md_path} (Failed to fetch)\n\n")

    combined = "\n\n".join(parts)
    combined = re.sub(r"### \[FAQ\].*", "", combined)
    combined = re.sub(r'(?:\[\!\[[^\]]+\]\([^)]+\)\]\([^)]+\)\s*)+', '', combined)

    return combined.strip()



def cached_aggregate_markdown(repo: str, subdir_prefix: str, inline_code: bool = True) -> str:
    """
    Returns cached aggregated markdown if available, otherwise computes and stores it.

    Cache is stored in `.cache/{repo}__{subdir_prefix}__inline.md`
    """
    os.makedirs(".cache", exist_ok=True)

    safe_repo = repo.replace("/", "__")
    safe_subdir = subdir_prefix.strip("/").replace("/", "__")
    cache_file = f".cache/{safe_repo}__{safe_subdir}__{'inline' if inline_code else 'raw'}.md"

    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            logging.info(f"Loaded cached markdown from {cache_file}")
            return f.read()

    content = aggregate_markdown(repo, subdir_prefix, inline_code=inline_code)
    with open(cache_file, "w", encoding="utf-8") as f:
        f.write(content)
        logging.info(f"Saved aggregated markdown to cache at {cache_file}")
    return content


def get_markdown(repo: str, subdir_prefix: str, inline_code: bool = True, cache: bool = True) -> str:
    """
    High-level function to get aggregated markdown with optional caching and code inlining.

    Args:
        repo: GitHub repo like 'user/repo'
        subdir_prefix: Subdirectory to look under
        inline_code: Whether to replace GitHub links with actual code
        cache: Whether to use cached version if available

    Returns:
        Processed markdown content
    """
    if cache:
        return cached_aggregate_markdown(repo, subdir_prefix, inline_code=inline_code)
    else:
        return aggregate_markdown(repo, subdir_prefix, inline_code=inline_code)


# Usage
if __name__ == "__main__":
    print(get_markdown(
        repo="CodeBoarding/GeneratedOnBoardings",
        subdir_prefix="Alien/",
        inline_code=False,   # True = embed GitHub code links as code blocks
        cache=False          # True = use .cache folder if available
    ))