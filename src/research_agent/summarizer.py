from __future__ import annotations

import json

from .llm import LLMClient
from .models import SourceDocument, SourceSummary


class LLMSummarizer:
    def __init__(self, api_key: str, model: str, base_url: str | None = None) -> None:
        self.client = LLMClient(api_key=api_key, model=model, base_url=base_url)

    def summarize_source(self, source_id: int, doc: SourceDocument) -> SourceSummary:
        prompt = (
            "Summarize the source and extract key points.\n"
            'Return strict JSON with keys: "summary" (string), "key_points" (array of 3 short strings).\n'
            f"Title: {doc.title}\nURL: {doc.url}\n"
            f"Content:\n{doc.content[:6000]}"
        )
        text = self.client.generate(prompt=prompt, temperature=0.2)
        parsed = _safe_parse_json(text)
        summary = ""
        points: list[str] = []

        if isinstance(parsed, dict):
            summary = str(parsed.get("summary", "")).strip()
            raw_points = parsed.get("key_points", [])
            if isinstance(raw_points, list):
                points = [str(p).strip() for p in raw_points if str(p).strip()]

        if not summary:
            summary = _clean_summary(text)
        if len(points) < 3:
            points = _extract_points_from_text(text)

        points = points[:3]
        while len(points) < 3:
            points.append("Additional supporting point not explicitly provided.")

        return SourceSummary(
            source_id=source_id,
            title=doc.title,
            url=doc.url,
            summary=summary,
            key_points=points,
        )


def _safe_parse_json(text: str) -> dict | None:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        parsed = json.loads(text[start : end + 1])
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        return None
    return None


def _clean_summary(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        cleaned = line.strip()
        lower = cleaned.lower()
        if not cleaned:
            continue
        if lower.startswith("here is a summary"):
            continue
        if lower.startswith("key points"):
            continue
        if lower.startswith("three key points"):
            continue
        lines.append(cleaned)
    return "\n".join(lines[:6]).strip() or text.strip()


def _extract_points_from_text(text: str) -> list[str]:
    points: list[str] = []
    for line in text.splitlines():
        cleaned = line.strip(" -*0123456789.").strip()
        lower = cleaned.lower()
        if not cleaned:
            continue
        if lower.startswith("here is"):
            continue
        if lower.startswith("key points"):
            continue
        if lower.startswith("three key points"):
            continue
        if len(cleaned.split()) < 4:
            continue
        points.append(cleaned)
        if len(points) == 3:
            break
    return points
