"""Placeholder search results for LLM_PROVIDER=canned. Clearly labelled; never for the demo."""

from __future__ import annotations

from .brave import BraveResult


class CannedBrave:
    name = "canned"

    async def search(self, query: str) -> list[BraveResult]:
        return [
            {"title": "[canned] Example company page", "url": "https://example.com/company",
             "description": "[canned] Placeholder search result. Set BRAVE_API_KEY for real research.", "age": None, "query": query},
            {"title": "[canned] Example press item", "url": "https://example.com/news/pilots",
             "description": "[canned] Placeholder press snippet about pilots.", "age": "2026-09-01", "query": query},
        ]
