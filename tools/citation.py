"""Citation lookup: CrossRef and Semantic Scholar API queries.

Returns metadata for the LLM to inspect and judge — does not make
verification decisions itself.

Usage:
  uv run python -m tools.citation search-crossref '<title>'
  uv run python -m tools.citation search-s2 '<title>'
  uv run python -m tools.citation lookup-doi '<doi>'
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from urllib.parse import quote

from tools.utils import retry_on_rate_limit

logger = logging.getLogger(__name__)

_CROSSREF_BASE = "https://api.crossref.org/works"
_SEMANTIC_SCHOLAR_BASE = "https://api.semanticscholar.org/graph/v1/paper/search"
_HTTP_TIMEOUT = 10


def lookup_doi(doi: str) -> dict | None:
    """Fetch metadata for a DOI from the CrossRef API."""
    url = f"{_CROSSREF_BASE}/{quote(doi, safe='')}"
    try:
        def _fetch():
            req = urllib.request.Request(url, method="GET")
            req.add_header("User-Agent", "research-tools/0.1 (citation-check)")
            with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as resp:
                return json.loads(resp.read().decode())

        data = retry_on_rate_limit(_fetch)
        message = data.get("message", {})
        titles = message.get("title", [])
        authors_raw = message.get("author", [])
        authors = [
            " ".join(filter(None, [a.get("given", ""), a.get("family", "")]))
            for a in authors_raw
        ]
        return {
            "doi": doi,
            "title": titles[0] if titles else "",
            "authors": authors,
            "url": message.get("URL", f"https://doi.org/{doi}"),
        }
    except (urllib.error.HTTPError, urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        logger.debug("DOI lookup failed for %s: %s", doi, exc)
        return None


def search_crossref(title: str, rows: int = 3) -> list[dict]:
    """Search CrossRef by title and return candidate papers."""
    query = quote(title)
    url = f"{_CROSSREF_BASE}?query.bibliographic={query}&rows={rows}"
    try:
        def _fetch():
            req = urllib.request.Request(url, method="GET")
            req.add_header("User-Agent", "research-tools/0.1 (citation-check)")
            with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as resp:
                return json.loads(resp.read().decode())

        data = retry_on_rate_limit(_fetch)
        items = data.get("message", {}).get("items", [])
        results = []
        for item in items:
            titles = item.get("title", [])
            authors_raw = item.get("author", [])
            authors = [
                " ".join(filter(None, [a.get("given", ""), a.get("family", "")]))
                for a in authors_raw
            ]
            results.append({
                "doi": item.get("DOI", ""),
                "title": titles[0] if titles else "",
                "authors": authors,
                "url": item.get("URL", ""),
            })
        return results
    except (urllib.error.HTTPError, urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        logger.debug("CrossRef search failed for %r: %s", title, exc)
        return []


def search_semantic_scholar(title: str, limit: int = 3) -> list[dict]:
    """Search Semantic Scholar by title and return candidate papers."""
    query = quote(title)
    url = f"{_SEMANTIC_SCHOLAR_BASE}?query={query}&limit={limit}"
    try:
        s2_key = os.environ.get("S2_API_KEY")

        def _fetch():
            req = urllib.request.Request(url, method="GET")
            req.add_header("User-Agent", "research-tools/0.1 (citation-check)")
            if s2_key:
                req.add_header("x-api-key", s2_key)
            with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as resp:
                return json.loads(resp.read().decode())

        data = retry_on_rate_limit(_fetch)
        papers = data.get("data", [])
        return [
            {
                "paperId": p.get("paperId", ""),
                "title": p.get("title", ""),
                "url": p.get("url", ""),
            }
            for p in papers
        ]
    except (urllib.error.HTTPError, urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        logger.debug("Semantic Scholar search failed for %r: %s", title, exc)
        return []


def main() -> None:
    import sys

    if len(sys.argv) < 2:
        print("Usage: uv run python -m tools.citation <command> [args]")
        print("Commands:")
        print("  lookup-doi <doi>        — fetch metadata for a DOI")
        print("  search-crossref <title> — search CrossRef by title")
        print("  search-s2 <title>       — search Semantic Scholar by title")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "lookup-doi":
        result = lookup_doi(sys.argv[2])
        print(json.dumps(result, default=str))
    elif cmd == "search-crossref":
        results = search_crossref(sys.argv[2])
        print(json.dumps(results, default=str))
    elif cmd == "search-s2":
        results = search_semantic_scholar(sys.argv[2])
        print(json.dumps(results, default=str))
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
