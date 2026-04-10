from __future__ import annotations

from .llm import LLMClient
from .models import SourceDocument, SourceSummary


class ReportGenerator:
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
        provider: str = "openai",
        input_cost_per_million: float = 0.0,
        output_cost_per_million: float = 0.0,
    ) -> None:
        self.client = LLMClient(
            api_key=api_key,
            model=model,
            base_url=base_url,
            provider=provider,
            input_cost_per_million=input_cost_per_million,
            output_cost_per_million=output_cost_per_million,
        )

    def generate(
        self,
        topic: str,
        summaries: list[SourceSummary],
        sources: list[SourceDocument],
        plan: str = "",
        analysis: str = "",
    ) -> str:
        source_context = []
        for s in summaries:
            source_context.append(
                f"[{s.source_id}] {s.title}\nURL: {s.url}\nSummary: {s.summary}\n"
            )

        prompt = (
            "You are writing a research report.\n"
            "Create sections: Executive Summary, Key Findings, Market/Technical Analysis, Risks, Conclusion.\n"
            "Use citation markers like [1], [2] in the report body.\n"
            f"Research topic: {topic}\n\n"
            f"Planner notes:\n{plan}\n\n"
            f"Analyst synthesis:\n{analysis}\n\n"
            "Source notes:\n"
            + "\n".join(source_context)
        )

        body = self.client.generate(prompt=prompt, temperature=0.2)

        references = ["\n## References"]
        for i, src in enumerate(sources, start=1):
            references.append(f"{i}. {src.title} - {src.url}")

        return f"# Research Report: {topic}\n\n{body}\n\n" + "\n".join(references) + "\n"
