from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .config import Settings
from .models import ResearchReport, SourceDocument
from .report_generator import ReportGenerator
from .search import (
    SemanticScholarSearchProvider,
    SerpApiSearchProvider,
    TavilySearchProvider,
    WebSearchProvider,
)
from .summarizer import LLMSummarizer
from .vector_store import SourceIndexer


class ResearchAgent:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.web_provider = self._build_web_provider(settings)
        self.paper_provider = SemanticScholarSearchProvider()
        self.summarizer = LLMSummarizer(settings.openai_api_key, settings.openai_model)
        self.report_generator = ReportGenerator(settings.openai_api_key, settings.openai_model)
        self.indexer = SourceIndexer(settings.openai_api_key)

    def run(self, query: str, output_dir: Path) -> ResearchReport:
        output_dir.mkdir(parents=True, exist_ok=True)
        web_docs = self.web_provider.search(query, self.settings.max_web_results)
        paper_docs = self.paper_provider.search(query, self.settings.max_paper_results)
        sources = _dedupe_sources(web_docs + paper_docs)

        summaries = [self.summarizer.summarize_source(i + 1, doc) for i, doc in enumerate(sources)]
        report_md = self.report_generator.generate(query, summaries, sources)

        self._save_sources(output_dir / "sources.json", sources)
        self._save_summaries(output_dir / "summaries.json", summaries)
        self._save_report(output_dir / "report.md", report_md)
        self.indexer.build(sources, output_dir / "faiss_index")

        return ResearchReport(topic=query, markdown=report_md, sources=sources, summaries=summaries)

    def _build_web_provider(self, settings: Settings) -> WebSearchProvider:
        if settings.tavily_api_key:
            return TavilySearchProvider(settings.tavily_api_key)
        if settings.serpapi_api_key:
            return SerpApiSearchProvider(settings.serpapi_api_key)
        raise ValueError("Set TAVILY_API_KEY or SERPAPI_API_KEY to enable web search.")

    @staticmethod
    def _save_sources(path: Path, sources: list[SourceDocument]) -> None:
        payload = [asdict(s) for s in sources]
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @staticmethod
    def _save_summaries(path: Path, summaries: list) -> None:
        payload = [asdict(s) for s in summaries]
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @staticmethod
    def _save_report(path: Path, report_md: str) -> None:
        path.write_text(report_md, encoding="utf-8")


def _dedupe_sources(sources: list[SourceDocument]) -> list[SourceDocument]:
    seen_urls: set[str] = set()
    deduped: list[SourceDocument] = []
    for source in sources:
        key = source.url.strip().lower()
        if not key or key in seen_urls:
            continue
        seen_urls.add(key)
        deduped.append(source)
    return deduped
