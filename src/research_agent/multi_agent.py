from __future__ import annotations

import json
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from .config import Settings
from .llm import LLMClient
from .models import ProgressCallback, SourceDocument, SourceSummary
from .quality import filter_high_quality_sources
from .report_generator import ReportGenerator
from .search import SemanticScholarSearchProvider, WebSearchProvider
from .summarizer import LLMSummarizer


class AgentState(TypedDict):
    topic: str
    plan: str
    planned_queries: list[str]
    sources: list[SourceDocument]
    summaries: list[SourceSummary]
    analysis: str
    report_markdown: str


class MultiAgentOrchestrator:
    def __init__(
        self,
        settings: Settings,
        web_provider: WebSearchProvider,
        paper_provider: SemanticScholarSearchProvider,
        summarizer: LLMSummarizer,
        report_generator: ReportGenerator,
    ) -> None:
        self.settings = settings
        self.web_provider = web_provider
        self.paper_provider = paper_provider
        self.summarizer = summarizer
        self.report_generator = report_generator
        self.client = LLMClient(
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            base_url=settings.llm_base_url,
        )
        self.progress_callback: ProgressCallback | None = None

    def run(self, query: str, progress_callback: ProgressCallback | None = None) -> AgentState:
        self.progress_callback = progress_callback
        graph = self._build_graph()
        compiled = graph.compile()
        return compiled.invoke(
            {
                "topic": query,
                "plan": "",
                "planned_queries": [],
                "sources": [],
                "summaries": [],
                "analysis": "",
                "report_markdown": "",
            }
        )

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)
        workflow.add_node("planner", self._planner_node)
        workflow.add_node("researcher", self._researcher_node)
        workflow.add_node("analyst", self._analyst_node)
        workflow.add_node("writer", self._writer_node)
        workflow.add_edge(START, "planner")
        workflow.add_edge("planner", "researcher")
        workflow.add_edge("researcher", "analyst")
        workflow.add_edge("analyst", "writer")
        workflow.add_edge("writer", END)
        return workflow

    def _planner_node(self, state: AgentState) -> AgentState:
        self._emit("Breaking the question into research angles.")
        prompt = (
            "You are a research planner. For the given topic, create a concise plan and search queries.\n"
            "Return strict JSON with keys: plan (string), queries (array of strings).\n"
            f"Max queries: {self.settings.max_planned_queries}\n"
            f"Topic: {state['topic']}"
        )
        text = self.client.generate(prompt=prompt, temperature=0.1)
        parsed = _safe_parse_json(text)

        plan = ""
        queries: list[str] = []
        if isinstance(parsed, dict):
            plan = str(parsed.get("plan", "")).strip()
            raw_queries = parsed.get("queries", [])
            if isinstance(raw_queries, list):
                queries = [str(q).strip() for q in raw_queries if str(q).strip()]

        if not queries:
            queries = [state["topic"]]
        queries = queries[: self.settings.max_planned_queries]
        self._emit(f"Planned {len(queries)} search paths for the topic.")

        return {
            **state,
            "plan": plan or f"Research topic from multiple angles: {state['topic']}",
            "planned_queries": queries,
        }

    def _researcher_node(self, state: AgentState) -> AgentState:
        self._emit("Sourcing the web for answers.")
        all_sources: list[SourceDocument] = []

        query_count = max(1, len(state["planned_queries"]))
        per_query_web = max(0, self.settings.max_web_results // query_count)
        per_query_paper = max(0, self.settings.max_paper_results // query_count)

        if self.settings.max_web_results > 0 and per_query_web == 0:
            per_query_web = 1
        if self.settings.max_paper_results > 0 and per_query_paper == 0:
            per_query_paper = 1

        for q in state["planned_queries"]:
            self._emit(f"Searching for: {q}")
            if per_query_web > 0:
                web_results = self.web_provider.search(q, per_query_web)
                all_sources.extend(web_results)
                self._emit(_progress_from_sources(web_results, fallback="Reviewing web pages."))
            if per_query_paper > 0:
                paper_results = self.paper_provider.search(q, per_query_paper)
                all_sources.extend(paper_results)
                if paper_results:
                    self._emit(_progress_from_sources(paper_results, fallback="Reading published material."))

        deduped = _dedupe_sources(all_sources)
        deduped = filter_high_quality_sources(deduped)
        self._emit(f"Kept {len(deduped)} strong sources after filtering.")
        return {**state, "sources": deduped}

    def _analyst_node(self, state: AgentState) -> AgentState:
        self._emit("Summarizing the collected evidence.")
        summaries = [self.summarizer.summarize_source(i + 1, doc) for i, doc in enumerate(state["sources"])]

        synthesis_prompt = (
            "Synthesize the core findings into concise bullets for a research analyst handoff.\n"
            f"Topic: {state['topic']}\n"
            f"Plan: {state['plan']}\n"
            "Source summaries:\n"
            + "\n\n".join([f"[{s.source_id}] {s.title}\n{s.summary}" for s in summaries])
        )
        synthesis = self.client.generate(prompt=synthesis_prompt, temperature=0.2)
        self._emit("Connecting the evidence into a coherent review.")

        return {**state, "summaries": summaries, "analysis": synthesis}

    def _writer_node(self, state: AgentState) -> AgentState:
        self._emit("Generating the final response.")
        report_md = self.report_generator.generate(
            topic=state["topic"],
            summaries=state["summaries"],
            sources=state["sources"],
            plan=state["plan"],
            analysis=state["analysis"],
        )
        self._emit("Packaging charts, sections, and citations.")
        return {**state, "report_markdown": report_md}

    def _emit(self, message: str) -> None:
        if self.progress_callback is not None:
            self.progress_callback(message)


def _safe_parse_json(text: str) -> Any:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


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


def _progress_from_sources(sources: list[SourceDocument], fallback: str) -> str:
    if not sources:
        return fallback
    title = sources[0].title.strip()
    if len(title) > 72:
        title = title[:69] + "..."
    return f"Referring to {title}"
