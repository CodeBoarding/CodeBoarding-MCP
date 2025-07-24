import requests
import logging
import re
import os

from format import replace_mermaid_blocks, format_github_html_links_to_plaintext
from transformers import GPT2TokenizerFast

# initialize the GPT-2 BPE tokenizer
tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")

GITHUB_API_HEADERS = {"Accept": "application/vnd.github.v3+json"}

# pattern to capture inline code references: module, filepath, start, end
REF_PATTERN = re.compile(
    r"-\s*([A-Za-z0-9_\.]+)\s*"
    r"\(\s*([^:]+):\s*lines\s*(\d+)[–-](\d+)\s*\)"
)

# regex for GitHub blob links with line numbers
LINK_PATTERN = re.compile(
    r"https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/blob/"
    r"(?P<branch>[^/]+)/(?P<filepath>[^#]+)#L(?P<start>\d+)-L(?P<end>\d+)"
)


def extract_code_from_github_url(link: str) -> str:
    """
    Given a GitHub blob URL with line numbers, fetch the raw code snippet.
    """
    m = LINK_PATTERN.search(link)
    if not m:
        return ""
    gd = m.groupdict()
    raw_url = (
        f"https://raw.githubusercontent.com/{gd['owner']}/{gd['repo']}/"
        f"{gd['branch']}/{gd['filepath']}"
    )
    start, end = int(gd['start']), int(gd['end'])
    try:
        resp = requests.get(raw_url, headers=GITHUB_API_HEADERS, timeout=5)
        resp.raise_for_status()
        lines = resp.text.splitlines()
    except Exception:
        return ""
    snippet = lines[max(0, start-1): min(len(lines), end)]
    return "\n".join(snippet)


def count_tokens(text: str) -> int:
    """Count tokens using GPT-2 BPE tokenizer."""
    return len(tokenizer.encode(text))


def add_num_tokens_per_inline(combined_md: str, code_repo: str) -> str:
    """
    Annotate each '- Module.path (file:lines)' line with token count.
    Fetches snippet from code_repo via extract_code_from_github_url.
    """
    def annotate(m):
        module_ref, file_path, start_s, end_s = m.groups()
        link = (
            f"https://github.com/{code_repo}/blob/master/{file_path}#L{start_s}-L{end_s}"
        )
        snippet = extract_code_from_github_url(link)
        tok_count = count_tokens(snippet) if snippet else 0
        orig_line = m.group(0)
        return f"{orig_line} [{tok_count} tokens]"

    return REF_PATTERN.sub(annotate, combined_md)


def aggregate_markdown(
    docs_repo: str,
    subdir_prefix: str,
    inline_code: bool,
    token_budget: int,
    code_repo: str = None
) -> str:
    """
    Aggregate markdown from docs_repo under subdir_prefix.
    If inline_code=False, annotate inline refs with token counts from code_repo.

    Args:
        docs_repo: GitHub repo with docs (owner/name)
        subdir_prefix: path prefix to include .md files
        inline_code: True to inline code blocks, False to annotate tokens
        code_repo: GitHub repo with actual code; defaults to docs_repo
    """
    if code_repo is None:
        code_repo = docs_repo

    tree_url = f"https://api.github.com/repos/{docs_repo}/git/trees/main?recursive=1"
    tree = requests.get(tree_url, headers=GITHUB_API_HEADERS).json().get("tree", [])
    md_files = [
        item['path'] for item in tree
        if item['type']=="blob"
        and item['path'].endswith(".md")
        and item['path'].startswith(subdir_prefix)
    ]
    # prioritize onboarding
    for i, path in enumerate(md_files):
        if 'on_boarding.md' in path:
            md_files.insert(0, md_files.pop(i))
            break

    logging.info(f"Found {len(md_files)} .md files under {subdir_prefix}")
    # build combined
    repo_name = subdir_prefix.rstrip('/').split('/')[-1]
    header = f"\n\n# {repo_name} Architecture Overview\n\n"
    parts = [header]
    for md_path in md_files:
        raw_url = f"https://raw.githubusercontent.com/{docs_repo}/main/{md_path}"
        resp = requests.get(raw_url, headers=GITHUB_API_HEADERS)
        if resp.ok:
            content = resp.text
            if inline_code:
                content = replace_mermaid_blocks(content)
            comp = md_path.split('/')[-1].rsplit('.md',1)[0]
            hdr = (
                "## System Architecture of the Whole Project:" 
                if comp=='on_boarding' 
                else f"## System Architecture Overview of Component: {comp}\n\n"
            )
            parts.append(hdr + format_github_html_links_to_plaintext(content, inline_code))
        else:
            parts.append(f"\n\n# {md_path} (Failed fetch)\n\n")

    combined = '\n\n'.join(parts)
    combined = re.sub(r"### \[FAQ\].*", "", combined)
    combined = re.sub(r'(?:\[!\[[^\]]+\]\([^)]+\)\]\([^)]+\)\s*)+', '', combined)
    if not inline_code:
        combined = add_num_tokens_per_inline(combined, code_repo)
    
    all_tokens = tokenizer.encode(combined)
    if len(all_tokens) > token_budget:
        truncated = tokenizer.decode(all_tokens[:token_budget])
        combined = truncated

    return combined.strip()

    


def cached_aggregate_markdown(
    docs_repo: str,
    subdir_prefix: str,
    inline_code: bool = True,
    code_repo: str = None
) -> str:
    """
    Cached version of aggregate_markdown.
    """
    if code_repo is None:
        code_repo = docs_repo
    os.makedirs('.cache', exist_ok=True)
    safe_docs = docs_repo.replace('/','__')
    safe_sub = subdir_prefix.strip('/').replace('/','__')
    safe_code = code_repo.replace('/','__')
    cache_file = f".cache/{safe_docs}__{safe_sub}__{safe_code}__{'inline' if inline_code else 'raw'}.md"
    if os.path.exists(cache_file):
        logging.info(f"Loading cached at {cache_file}")
        return open(cache_file,'r',encoding='utf-8').read()
    content = aggregate_markdown(docs_repo, subdir_prefix, inline_code, code_repo)
    with open(cache_file,'w',encoding='utf-8') as f:
        f.write(content)
    return content


def get_markdown(
    repo_name: str,
    docs_repo: str = 'CodeBoarding/GeneratedOnBoardings',
    inline_code: bool = False,
    cache: bool = False,
    token_budget: int = 10_000,
    code_repo: str = None
) -> str:
    """
    Main entry: returns aggregated markdown, optionally cached, with inline code or token annotations.
    """
    if code_repo is None:
        code_repo = docs_repo
    if cache:
        return cached_aggregate_markdown(docs_repo, repo_name, inline_code, code_repo)
    return aggregate_markdown(docs_repo, repo_name, inline_code, token_budget, code_repo)

# Usage example
if __name__ == '__main__':
    print(get_markdown(
        repo_name='Alien/',
        inline_code=False,
        cache=False,
        code_repo='Sanofi-Public/Alien'
    ))
