from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class SourceDocument:
    title: str
    url: str
    snippet: str
    content: str
    source_type: str  # web | paper


@dataclass
class SourceSummary:
    source_id: int
    title: str
    url: str
    summary: str
    key_points: list[str] = field(default_factory=list)


@dataclass
class ResearchReport:
    topic: str
    markdown: str
    sources: list[SourceDocument]
    summaries: list[SourceSummary]


ProgressCallback = Callable[[str], None]
