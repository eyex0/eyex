from __future__ import annotations

import asyncio
import logging
import os

from langchain_core.tools import tool

logger = logging.getLogger("pix.tools.web")

_SEARCH_PROVIDER: str | None = None
_SEARCH_API_KEY: str | None = None


def _configure_search() -> None:
    global _SEARCH_PROVIDER, _SEARCH_API_KEY
    if _SEARCH_PROVIDER is None:
        _SEARCH_PROVIDER = os.environ.get("SEARCH_PROVIDER", "duckduckgo")
    if _SEARCH_API_KEY is None:
        _SEARCH_API_KEY = os.environ.get("SEARCH_API_KEY") or os.environ.get("SERPER_API_KEY")


async def _search_duckduckgo(query: str, num_results: int) -> list[dict[str, str]]:
    import httpx
    results: list[dict[str, str]] = []
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
            resp = await client.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            )
            resp.raise_for_status()

            from html.parser import HTMLParser

            class DDGResultParser(HTMLParser):
                def __init__(self) -> None:
                    super().__init__()
                    self._results: list[dict[str, str]] = []
                    self._current: dict[str, str] = {}
                    self._in_result = False
                    self._in_link = False
                    self._in_snippet = False
                    self._skip_next_a = False

                def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
                    attrs_dict = dict(attrs)
                    cls = attrs_dict.get("class", "")
                    if "result__a" in cls:
                        self._in_link = True
                        self._current["link"] = attrs_dict.get("href", "")
                        self._current["title"] = ""
                    elif "result__snippet" in cls:
                        self._in_snippet = True
                        self._current["snippet"] = ""

                def handle_data(self, data: str) -> None:
                    if self._in_link:
                        self._current["title"] = (self._current.get("title", "") + data).strip()
                    elif self._in_snippet:
                        self._current["snippet"] = (self._current.get("snippet", "") + data).strip()

                def handle_endtag(self, tag: str) -> None:
                    if tag == "a" and self._in_link:
                        self._in_link = False
                        if self._current.get("title"):
                            self._results.append(self._current.copy())
                        self._current = {}
                    elif tag == "a" and self._in_snippet:
                        self._in_snippet = False

                @property
                def results(self) -> list[dict[str, str]]:
                    return self._results[:num_results]

            parser = DDGResultParser()
            await asyncio.to_thread(parser.feed, resp.text)
            return parser.results
    except Exception as exc:
        logger.warning("DuckDuckGo search failed: %s", exc)
        return results


async def _search_serper(query: str, num_results: int) -> list[dict[str, str]]:
    import httpx
    key = _SEARCH_API_KEY or ""
    if not key:
        logger.warning("No SERPER_API_KEY set — cannot use Serper search")
        return []
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": key, "Content-Type": "application/json"},
                json={"q": query, "num": num_results},
            )
            resp.raise_for_status()
            data = resp.json()
            return [
                {"title": r.get("title", ""), "link": r.get("link", ""), "snippet": r.get("snippet", "")}
                for r in data.get("organic", [])[:num_results]
            ]
    except Exception as exc:
        logger.warning("Serper search failed: %s", exc)
        return []


@tool
async def web_search(query: str, num_results: int = 8) -> str:
    """Search the web for information. Returns title, URL, and snippet for each result."""
    provider = _SEARCH_PROVIDER or "duckduckgo"
    results: list[dict[str, str]] = []

    if provider == "serper":
        results = await _search_serper(query, num_results)
    else:
        results = await _search_duckduckgo(query, num_results)

    if not results:
        return f"No search results found for '{query}'"

    lines = [f"Search results for '{query}':\n"]
    for i, r in enumerate(results, 1):
        title = r.get("title", "").strip()
        link = r.get("link", "").strip()
        snippet = r.get("snippet", "").strip()
        lines.append(f"{i}. {title}")
        lines.append(f"   URL: {link}")
        if snippet:
            lines.append(f"   {snippet[:300]}")
        lines.append("")

    return "\n".join(lines).strip()


@tool
async def web_fetch(url: str, format: str = "markdown") -> str:
    """Fetch and extract content from a URL. Format options: 'markdown' (default), 'text', 'html'."""
    import httpx
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            resp = await client.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            )
            resp.raise_for_status()

            if format == "html":
                return f"URL: {url}\nContent-Type: {resp.headers.get('content-type', 'N/A')}\n\n{resp.text[:10000]}"

            from html.parser import HTMLParser

            class ContentExtractor(HTMLParser):
                def __init__(self) -> None:
                    super().__init__()
                    self._text_parts: list[str] = []
                    self._skip_tags = {"script", "style", "nav", "footer", "header", "noscript"}
                    self._in_skip = 0

                def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
                    if tag in self._skip_tags:
                        self._in_skip += 1

                def handle_endtag(self, tag: str) -> None:
                    if tag in self._skip_tags and self._in_skip > 0:
                        self._in_skip -= 1

                def handle_data(self, data: str) -> None:
                    if self._in_skip == 0:
                        stripped = data.strip()
                        if stripped:
                            self._text_parts.append(stripped)

                @property
                def text(self) -> str:
                    return "\n".join(self._text_part for self._text_part in self._text_parts)

            extractor = ContentExtractor()
            await asyncio.to_thread(extractor.feed, resp.text)
            text = extractor.text

            if format == "text":
                return f"URL: {url}\n\n{text[:8000]}"

            words = text.split()
            markdown = []
            para: list[str] = []
            for w in words:
                para.append(w)
                if len(" ".join(para)) > 100 and w.endswith((".", "!", "?")):
                    markdown.append(" ".join(para))
                    para = []
            if para:
                markdown.append(" ".join(para))

            result = f"# Content from {url}\n\n" + "\n\n".join(markdown)
            return result[:8000]

    except httpx.HTTPStatusError as exc:
        return f"Error fetching {url}: HTTP {exc.response.status_code} {exc.response.reason_phrase}"
    except httpx.TimeoutException:
        return f"Error: Timeout fetching {url} (15s)"
    except Exception as exc:
        logger.error("Failed to fetch %s: %s", url, exc)
        return f"Error fetching {url}: {exc}"
