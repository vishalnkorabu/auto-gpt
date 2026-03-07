from __future__ import annotations

from .llm import LLMClient
from .models import SourceDocument, SourceSummary


class LLMSummarizer:
    def __init__(self, api_key: str, model: str, base_url: str | None = None) -> None:
        self.client = LLMClient(api_key=api_key, model=model, base_url=base_url)

    def summarize_source(self, source_id: int, doc: SourceDocument) -> SourceSummary:
        prompt = (
            "Summarize the source in 4-6 lines and extract 3 key points.\n"
            f"Title: {doc.title}\nURL: {doc.url}\n"
            f"Content:\n{doc.content[:6000]}"
        )
        text = self.client.generate(prompt=prompt, temperature=0.2)

        points = []
        for line in text.splitlines():
            line = line.strip("-* ").strip()
            if line:
                points.append(line)
            if len(points) >= 3:
                break

        return SourceSummary(
            source_id=source_id,
            title=doc.title,
            url=doc.url,
            summary=text,
            key_points=points,
        )
