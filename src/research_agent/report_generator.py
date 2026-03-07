from __future__ import annotations

from openai import OpenAI

from .models import SourceDocument, SourceSummary


class ReportGenerator:
    def __init__(self, api_key: str, model: str) -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate(self, topic: str, summaries: list[SourceSummary], sources: list[SourceDocument]) -> str:
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
            "Source notes:\n"
            + "\n".join(source_context)
        )

        response = self.client.responses.create(
            model=self.model,
            input=prompt,
            temperature=0.2,
        )
        body = response.output_text.strip()

        references = ["\n## References"]
        for i, src in enumerate(sources, start=1):
            references.append(f"{i}. {src.title} - {src.url}")

        return f"# Research Report: {topic}\n\n{body}\n\n" + "\n".join(references) + "\n"
