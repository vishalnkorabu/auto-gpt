from __future__ import annotations

from abc import ABC, abstractmethod

import requests
from bs4 import BeautifulSoup

from .models import SourceDocument


class WebSearchProvider(ABC):
    @abstractmethod
    def search(self, query: str, limit: int) -> list[SourceDocument]:
        raise NotImplementedError


class TavilySearchProvider(WebSearchProvider):
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def search(self, query: str, limit: int) -> list[SourceDocument]:
        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": self.api_key,
                "query": query,
                "max_results": limit,
                "include_raw_content": True,
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results", [])

        documents: list[SourceDocument] = []
        for item in results:
            documents.append(
                SourceDocument(
                    title=item.get("title", "Untitled"),
                    url=item.get("url", ""),
                    snippet=item.get("content", "")[:500],
                    content=item.get("raw_content") or item.get("content", ""),
                    source_type="web",
                )
            )
        return documents


class SerpApiSearchProvider(WebSearchProvider):
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def search(self, query: str, limit: int) -> list[SourceDocument]:
        response = requests.get(
            "https://serpapi.com/search.json",
            params={"q": query, "engine": "google", "api_key": self.api_key, "num": limit},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        results = payload.get("organic_results", [])

        documents: list[SourceDocument] = []
        for item in results[:limit]:
            url = item.get("link", "")
            documents.append(
                SourceDocument(
                    title=item.get("title", "Untitled"),
                    url=url,
                    snippet=item.get("snippet", ""),
                    content=_extract_article_text(url),
                    source_type="web",
                )
            )
        return documents


class SemanticScholarSearchProvider:
    def search(self, query: str, limit: int) -> list[SourceDocument]:
        response = requests.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params={"query": query, "limit": limit, "fields": "title,url,abstract"},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        papers = payload.get("data", [])

        documents: list[SourceDocument] = []
        for item in papers:
            title = item.get("title", "Untitled")
            url = item.get("url", "")
            abstract = item.get("abstract", "")
            documents.append(
                SourceDocument(
                    title=title,
                    url=url,
                    snippet=abstract[:500],
                    content=abstract,
                    source_type="paper",
                )
            )
        return documents


def _extract_article_text(url: str) -> str:
    if not url:
        return ""
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
    except requests.RequestException:
        return ""

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = " ".join(soup.stripped_strings)
    return text[:8000]
