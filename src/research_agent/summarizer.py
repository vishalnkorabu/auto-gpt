from __future__ import annotations

from openai import OpenAI

from .models import SourceDocument, SourceSummary


class LLMSummarizer:
    def __init__(self, api_key: str, model: str) -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def summarize_source(self, source_id: int, doc: SourceDocument) -> SourceSummary:
        prompt = (
            "Summarize the source in 4-6 lines and extract 3 key points.\n"
            f"Title: {doc.title}\nURL: {doc.url}\n"
            f"Content:\n{doc.content[:6000]}"
        )
        response = self.client.responses.create(
            model=self.model,
            input=prompt,
            temperature=0.2,
        )
        text = response.output_text.strip()

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
