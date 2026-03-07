from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .config import Settings
from .models import ResearchReport, SourceDocument, SourceSummary
from .multi_agent import MultiAgentOrchestrator
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
        self.web_provider: WebSearchProvider | None = None
        self.paper_provider: SemanticScholarSearchProvider | None = None
        self.summarizer: LLMSummarizer | None = None
        self.report_generator: ReportGenerator | None = None
        self.indexer: SourceIndexer | None = None
        self.multi_agent: MultiAgentOrchestrator | None = None

    def run(self, query: str, output_dir: Path, mode: str = "multi", dry_run: bool = False) -> ResearchReport:
        if dry_run:
            return self._run_dry(query=query, output_dir=output_dir, mode=mode)

        self._ensure_runtime()
        if mode == "single":
            return self._run_single(query=query, output_dir=output_dir)
        return self._run_multi(query=query, output_dir=output_dir)

    def _run_single(self, query: str, output_dir: Path) -> ResearchReport:
        output_dir.mkdir(parents=True, exist_ok=True)
        assert self.web_provider is not None
        assert self.paper_provider is not None
        assert self.summarizer is not None
        assert self.report_generator is not None
        assert self.indexer is not None

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

    def _run_multi(self, query: str, output_dir: Path) -> ResearchReport:
        output_dir.mkdir(parents=True, exist_ok=True)
        assert self.multi_agent is not None
        assert self.indexer is not None
        state = self.multi_agent.run(query)
        sources = state["sources"]
        summaries = state["summaries"]
        report_md = state["report_markdown"]

        self._save_sources(output_dir / "sources.json", sources)
        self._save_summaries(output_dir / "summaries.json", summaries)
        self._save_report(output_dir / "report.md", report_md)
        self._save_plan(output_dir / "plan.txt", state["plan"])
        self._save_analysis(output_dir / "analysis.txt", state["analysis"])
        self.indexer.build(sources, output_dir / "faiss_index")

        return ResearchReport(topic=query, markdown=report_md, sources=sources, summaries=summaries)

    def _run_dry(self, query: str, output_dir: Path, mode: str) -> ResearchReport:
        output_dir.mkdir(parents=True, exist_ok=True)
        sources = self._mock_sources(query)
        summaries = self._mock_summaries(sources)
        plan = (
            f"1) Define scope for '{query}'\n"
            "2) Collect business, technical, and risk angles\n"
            "3) Synthesize claims with source-backed citations"
        )
        analysis = (
            "Early signals indicate rapid adoption with uneven outcomes across segments. "
            "Main levers are cost reduction, speed, regulatory fit, and integration complexity."
        )
        report_md = self._mock_report(query, summaries, sources, plan, analysis)

        self._save_sources(output_dir / "sources.json", sources)
        self._save_summaries(output_dir / "summaries.json", summaries)
        self._save_report(output_dir / "report.md", report_md)
        if mode == "multi":
            self._save_plan(output_dir / "plan.txt", plan)
            self._save_analysis(output_dir / "analysis.txt", analysis)

        return ResearchReport(topic=query, markdown=report_md, sources=sources, summaries=summaries)

    def _ensure_runtime(self) -> None:
        if self.web_provider is None:
            self.web_provider = self._build_web_provider(self.settings)
        if self.paper_provider is None:
            self.paper_provider = SemanticScholarSearchProvider()
        if self.summarizer is None:
            self.summarizer = LLMSummarizer(
                api_key=self.settings.llm_api_key,
                model=self.settings.llm_model,
                base_url=self.settings.llm_base_url,
            )
        if self.report_generator is None:
            self.report_generator = ReportGenerator(
                api_key=self.settings.llm_api_key,
                model=self.settings.llm_model,
                base_url=self.settings.llm_base_url,
            )
        if self.indexer is None:
            self.indexer = SourceIndexer(self.settings.embedding_model)
        if self.multi_agent is None:
            assert self.web_provider is not None
            assert self.paper_provider is not None
            assert self.summarizer is not None
            assert self.report_generator is not None
            self.multi_agent = MultiAgentOrchestrator(
                settings=self.settings,
                web_provider=self.web_provider,
                paper_provider=self.paper_provider,
                summarizer=self.summarizer,
                report_generator=self.report_generator,
            )

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

    @staticmethod
    def _save_plan(path: Path, plan: str) -> None:
        path.write_text(plan, encoding="utf-8")

    @staticmethod
    def _save_analysis(path: Path, analysis: str) -> None:
        path.write_text(analysis, encoding="utf-8")

    @staticmethod
    def _mock_sources(query: str) -> list[SourceDocument]:
        return [
            SourceDocument(
                title=f"{query}: Industry Outlook",
                url="https://example.com/industry-outlook",
                snippet="Overview of trends and growth dynamics.",
                content="Synthetic dry-run source content for industry outlook.",
                source_type="web",
            ),
            SourceDocument(
                title=f"{query}: Academic Evidence",
                url="https://example.com/academic-evidence",
                snippet="Paper-style evidence on outcomes and limitations.",
                content="Synthetic dry-run source content for academic evidence.",
                source_type="paper",
            ),
            SourceDocument(
                title=f"{query}: Startup Case Studies",
                url="https://example.com/startup-cases",
                snippet="Examples of startup execution patterns.",
                content="Synthetic dry-run source content for startup cases.",
                source_type="web",
            ),
        ]

    @staticmethod
    def _mock_summaries(sources: list[SourceDocument]) -> list[SourceSummary]:
        summaries: list[SourceSummary] = []
        for i, src in enumerate(sources, start=1):
            summaries.append(
                SourceSummary(
                    source_id=i,
                    title=src.title,
                    url=src.url,
                    summary=(
                        f"This dry-run summary captures key claims from '{src.title}', "
                        "including opportunities, constraints, and implementation concerns."
                    ),
                    key_points=[
                        "Potential productivity gains",
                        "Execution depends on data and workflow quality",
                        "Risk and compliance require early design",
                    ],
                )
            )
        return summaries

    @staticmethod
    def _mock_report(
        topic: str,
        summaries: list[SourceSummary],
        sources: list[SourceDocument],
        plan: str,
        analysis: str,
    ) -> str:
        findings = "\n".join([f"- [{s.source_id}] {s.key_points[0]} and {s.key_points[1]}." for s in summaries])
        refs = "\n".join([f"{i}. {src.title} - {src.url}" for i, src in enumerate(sources, start=1)])
        return (
            f"# Research Report: {topic}\n\n"
            "## Executive Summary\n"
            "This is a deterministic dry-run report used to validate pipeline behavior.\n\n"
            "## Key Findings\n"
            f"{findings}\n\n"
            "## Market/Technical Analysis\n"
            f"{analysis}\n\n"
            "## Risks\n"
            "- Source quality variance can distort conclusions.\n"
            "- Domain-specific validation is still required before decisions.\n\n"
            "## Conclusion\n"
            "The workflow is operational and produces structured outputs with citations.\n\n"
            "## Planner Notes\n"
            f"{plan}\n\n"
            "## References\n"
            f"{refs}\n"
        )


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
