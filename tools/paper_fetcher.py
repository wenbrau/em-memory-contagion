"""Paper content fetcher for targeted deep reading during novelty assessment.

Supports:
- ArXiv papers: section extraction (discussion, limitations, future work, etc.)
- LessWrong / Alignment Forum: GraphQL API (no auth required)
- Blog posts and arbitrary URLs: trafilatura extraction

Usage:
  uv run python -m tools.paper_fetcher fetch '<url>'
  uv run python -m tools.paper_fetcher fetch-batch '<json_array_of_urls>'
"""

from __future__ import annotations

import io
import logging
import re
from urllib.parse import urlparse

import arxiv
import httpx
import pypdf
import trafilatura

logger = logging.getLogger(__name__)

# Limits
_SECTION_LIMIT = 3000   # max chars per extracted section
_CONTENT_LIMIT = 5000   # max chars for blog/LW content
_TIMEOUT = 15           # seconds per fetch

_ARXIV_HTML_BASE = "https://arxiv.org/html"
_KNOWN_BLOG_DOMAINS = [
    "alignmentforum.org",
    "lesswrong.com",
    "anthropic.com",
    "deepmind.google",
]

_TARGET_SECTIONS = [
    "discussion",
    "limitations",
    "future work",
    "conclusion",
    "related work",
]

_TAG_RE = re.compile(r"<[^>]+>")
_HEADING_RE = re.compile(r"<h([2-3])[^>]*>(.*?)</h\1>", re.IGNORECASE | re.DOTALL)
_PDF_SECTION_RE = re.compile(
    r"^(\d+\.?\s+)?(discussion|limitations|future work|conclusion|related work)\s*$",
    re.IGNORECASE | re.MULTILINE,
)

_GRAPHQL_ENDPOINTS = {
    "lesswrong.com": "https://www.lesswrong.com/graphql",
    "alignmentforum.org": "https://www.lesswrong.com/graphql",
}
_POST_QUERY = """
query PostById($id: String) {
  post(input: {selector: {_id: $id}}) {
    result { title htmlBody }
  }
}
"""
_LW_POST_ID_RE = re.compile(r"/posts/([^/]+)")
_BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _strip_tags(html: str) -> str:
    text = _TAG_RE.sub(" ", html)
    return re.sub(r"\s+", " ", text).strip()


def _extract_arxiv_id(url: str) -> str | None:
    parsed = urlparse(url)
    if not parsed.hostname or "arxiv.org" not in parsed.hostname:
        return None
    path = parsed.path.strip("/")
    for prefix in ("abs/", "html/", "pdf/"):
        if path.startswith(prefix):
            return path[len(prefix):]
    return None


def _get_lw_endpoint(url: str) -> str | None:
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    for domain, endpoint in _GRAPHQL_ENDPOINTS.items():
        if domain in hostname:
            return endpoint
    return None


def _extract_lw_post_id(url: str) -> str | None:
    match = _LW_POST_ID_RE.search(url)
    return match.group(1) if match else None


# --- ArXiv ---

def _parse_sections_from_html(html: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    headings = []
    for match in _HEADING_RE.finditer(html):
        level = int(match.group(1))
        text = re.sub(r"^\d+(\.\d+)*\s*", "", _strip_tags(match.group(2)).lower().strip())
        headings.append((match.start(), level, text, match.end()))

    for i, (pos, level, heading_text, content_start) in enumerate(headings):
        for target in _TARGET_SECTIONS:
            if target in heading_text and target not in sections:
                content_end = len(html)
                for j in range(i + 1, len(headings)):
                    if headings[j][1] <= level:
                        content_end = headings[j][0]
                        break
                clean = _strip_tags(html[content_start:content_end])
                if clean:
                    sections[target] = clean[:_SECTION_LIMIT]
                break
    return sections


def _extract_sections_from_text(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    matches = list(_PDF_SECTION_RE.finditer(text))
    for i, match in enumerate(matches):
        section_name = match.group(2).lower().strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        for target in _TARGET_SECTIONS:
            if target in section_name and target not in sections:
                if content:
                    sections[target] = content[:_SECTION_LIMIT]
                break
    return sections


def fetch_arxiv_sections(arxiv_id: str) -> dict | None:
    """Fetch an ArXiv paper and extract key sections. Tries HTML, then PDF, then abstract."""
    # Try HTML first
    try:
        url = f"{_ARXIV_HTML_BASE}/{arxiv_id}"
        resp = httpx.get(url, timeout=_TIMEOUT, follow_redirects=True)
        if resp.status_code == 200:
            sections = _parse_sections_from_html(resp.text)
            if sections:
                return {"url": url, "sections": sections}
    except httpx.HTTPError:
        pass

    # Try PDF
    try:
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
        resp = httpx.get(pdf_url, timeout=30, follow_redirects=True)
        if resp.status_code == 200:
            reader = pypdf.PdfReader(io.BytesIO(resp.content))
            full_text = "\n".join(page.extract_text() or "" for page in reader.pages)
            sections = _extract_sections_from_text(full_text)
            if sections:
                return {"url": pdf_url, "sections": sections}
    except Exception:
        pass

    # Fall back to abstract via API
    try:
        client = arxiv.Client()
        clean_id = re.sub(r"v\d+$", "", arxiv_id)
        results = list(client.results(arxiv.Search(id_list=[clean_id])))
        if results:
            paper = results[0]
            return {"url": paper.entry_id, "sections": {"abstract": paper.summary[:_SECTION_LIMIT]}}
    except Exception as e:
        logger.warning("ArXiv API failed for %s: %s", arxiv_id, e)

    return None


# --- LessWrong / Alignment Forum ---

def fetch_lw_content(url: str) -> dict | None:
    """Fetch post content from LessWrong or Alignment Forum via GraphQL."""
    endpoint = _get_lw_endpoint(url)
    post_id = _extract_lw_post_id(url)
    if not endpoint or not post_id:
        return None
    try:
        resp = httpx.post(
            endpoint,
            json={"query": _POST_QUERY, "variables": {"id": post_id}},
            timeout=_TIMEOUT,
            headers={"Content-Type": "application/json"},
        )
        if resp.status_code != 200:
            return None
        post = resp.json().get("data", {}).get("post", {}).get("result")
        if not post or not post.get("htmlBody"):
            return None
        return {"url": url, "content": _strip_tags(post["htmlBody"])[:_CONTENT_LIMIT]}
    except Exception as e:
        logger.warning("Failed to fetch LW/AF content from %s: %s", url, e)
        return None


# --- Blogs and general URLs ---

def fetch_blog_content(url: str) -> dict | None:
    """Fetch and extract clean text from a blog post or arbitrary URL."""
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded is None:
            resp = httpx.get(url, timeout=_TIMEOUT, follow_redirects=True,
                             headers={"User-Agent": _BROWSER_UA})
            downloaded = resp.text
        if not downloaded:
            return None
        content = trafilatura.extract(downloaded, include_tables=False, include_comments=False)
        if not content:
            return None
        return {"url": url, "content": content[:_CONTENT_LIMIT]}
    except Exception as e:
        logger.warning("Failed to extract content from %s: %s", url, e)
        return None


# --- Main dispatcher ---

def fetch_deep_content(url: str) -> dict | None:
    """Fetch deep content from a URL. Routes to the appropriate fetcher."""
    arxiv_id = _extract_arxiv_id(url)
    if arxiv_id:
        return fetch_arxiv_sections(arxiv_id)
    if _get_lw_endpoint(url):
        return fetch_lw_content(url)
    return fetch_blog_content(url)


def main() -> None:
    import json
    import sys

    if len(sys.argv) < 3:
        print("Usage: uv run python -m tools.paper_fetcher <command> <url_or_json>")
        print("Commands:")
        print("  fetch <url>             — fetch deep content from a single URL")
        print("  fetch-batch '<json>'    — fetch from a JSON array of URLs")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "fetch":
        result = fetch_deep_content(sys.argv[2])
        print(json.dumps(result, indent=2, default=str))
    elif cmd == "fetch-batch":
        urls = json.loads(sys.argv[2])
        results = [fetch_deep_content(u) for u in urls]
        print(json.dumps(results, indent=2, default=str))
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
