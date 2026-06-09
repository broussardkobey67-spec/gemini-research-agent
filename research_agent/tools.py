"""Web tools the agent uses to ground its answers in real sources.

Uses DuckDuckGo's HTML endpoint for search (no API key required) and a small,
polite fetcher for pulling readable text out of a page.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlparse

import requests

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}
_TIMEOUT = 15


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str


class _ResultParser(HTMLParser):
    """Extracts result titles/links/snippets from DuckDuckGo HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.results: list[SearchResult] = []
        self._mode: str | None = None
        self._href = ""
        self._title_parts: list[str] = []
        self._snippet_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        cls = a.get("class") or ""
        if tag == "a" and "result__a" in cls:
            self._mode = "title"
            self._href = a.get("href") or ""
            self._title_parts = []
        elif tag == "a" and "result__snippet" in cls:
            self._mode = "snippet"
            self._snippet_parts = []

    def handle_data(self, data: str) -> None:
        if self._mode == "title":
            self._title_parts.append(data)
        elif self._mode == "snippet":
            self._snippet_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._mode == "title":
            self.results.append(
                SearchResult(
                    title="".join(self._title_parts).strip(),
                    url=_clean_url(self._href),
                    snippet="",
                )
            )
            self._mode = None
        elif tag == "a" and self._mode == "snippet" and self.results:
            last = self.results[-1]
            self.results[-1] = SearchResult(
                last.title, last.url, "".join(self._snippet_parts).strip()
            )
            self._mode = None


def _clean_url(href: str) -> str:
    """DuckDuckGo wraps links as ``/l/?uddg=<encoded>``; unwrap to the target."""
    parsed = urlparse(href)
    if parsed.path.startswith("/l/"):
        target = parse_qs(parsed.query).get("uddg")
        if target:
            return target[0]
    return href


def web_search(query: str, max_results: int = 5) -> list[SearchResult]:
    """Return the top organic results for ``query``."""
    resp = requests.post(
        "https://html.duckduckgo.com/html/",
        data={"q": query},
        headers=_HEADERS,
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    parser = _ResultParser()
    parser.feed(resp.text)
    return [r for r in parser.results if r.url.startswith("http")][:max_results]


class _TextExtractor(HTMLParser):
    _SKIP = {"script", "style", "noscript", "header", "footer", "nav"}

    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs  # tag name is all we need here
        if tag in self._SKIP:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0 and data.strip():
            self._chunks.append(data.strip())

    @property
    def text(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self._chunks))


def fetch_text(url: str, max_chars: int = 4000) -> str:
    """Fetch ``url`` and return readable plain text, truncated to ``max_chars``."""
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException:
        return ""
    extractor = _TextExtractor()
    extractor.feed(resp.text)
    return extractor.text[:max_chars]
