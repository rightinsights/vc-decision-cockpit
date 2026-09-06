"""
Brave Search API client. The app calls Brave directly (cheap, deterministic) and never asks
OpenClaw to run searches for it. Docs: https://api-dashboard.search.brave.com/app/documentation
"""

from __future__ import annotations

from typing import TypedDict
from urllib.parse import urlparse

import httpx
from fastapi import Depends

from ..config import Settings, get_settings

BRAVE_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"


class ResearchError(RuntimeError):
    pass


class BraveResult(TypedDict):
    title: str
    url: str
    description: str
    age: str | None
    query: str


def normalize_url(url: str) -> str:
    return url.strip().rstrip("/").lower()


def domain_of(url: str | None) -> str:
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        return (urlparse(url).hostname or "").removeprefix("www.")
    except ValueError:
        return ""


class BraveClient:
    name = "brave"

    def __init__(self, api_key: str | None, count: int = 8, timeout_seconds: int = 20,
                 transport: httpx.AsyncBaseTransport | None = None):
        if not api_key:
            raise ResearchError("BRAVE_API_KEY is not set.")
        self.api_key = api_key
        self.count = max(1, min(count, 20))
        self.timeout_seconds = timeout_seconds
        self._transport = transport

    async def search(self, query: str) -> list[BraveResult]:
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key,
        }
        params = {"q": query, "count": self.count, "text_decorations": "false", "safesearch": "off"}
        async with httpx.AsyncClient(timeout=self.timeout_seconds, transport=self._transport) as client:
            try:
                response = await client.get(BRAVE_ENDPOINT, params=params, headers=headers)
            except httpx.HTTPError as exc:
                raise ResearchError(f"Brave search failed: {exc}") from exc
        if response.status_code == 401:
            raise ResearchError("Brave rejected the API key (401).")
        if response.status_code == 429:
            raise ResearchError("Brave rate limit hit (429). Wait a moment and retry.")
        if response.status_code >= 400:
            raise ResearchError(f"Brave returned {response.status_code}: {response.text[:200]}")
        try:
            items = response.json().get("web", {}).get("results", [])
        except ValueError as exc:
            raise ResearchError("Brave returned a non-JSON body.") from exc
        results: list[BraveResult] = []
        for item in items:
            url = item.get("url")
            if not url:
                continue
            results.append({
                "title": (item.get("title") or "").strip(),
                "url": url,
                "description": (item.get("description") or "").strip(),
                "age": item.get("age") or item.get("page_age"),
                "query": query,
            })
        return results


def build_queries(name: str, website: str | None, brief: str) -> list[str]:
    """Two or three focused queries. The brief contributes keywords, not a sentence."""
    domain = domain_of(website)
    queries = [f'"{name}" {domain}'.strip() if domain else f'"{name}" startup']
    queries.append(f'"{name}" funding OR customers OR pilot OR partnership OR launch')
    words = [w for w in brief.replace(",", " ").split() if len(w) > 3][:6]
    if words:
        queries.append(f'"{name}" {" ".join(words)}')
    return queries


async def gather_results(client: BraveClient, queries: list[str]) -> list[BraveResult]:
    seen: set[str] = set()
    merged: list[BraveResult] = []
    for query in queries:
        for item in await client.search(query):
            key = normalize_url(item["url"])
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return merged


def get_brave(settings: Settings = Depends(get_settings)) -> BraveClient | None:
    """None when no key is configured; the route turns that into a 400 rather than a crash."""
    if settings.llm_provider == "canned":
        from .canned_brave import CannedBrave

        return CannedBrave()  # type: ignore[return-value]
    if not settings.brave_api_key:
        return None
    return BraveClient(settings.brave_api_key, settings.brave_result_count, settings.brave_timeout_seconds)
