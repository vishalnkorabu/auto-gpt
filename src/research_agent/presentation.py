from __future__ import annotations

import re

from .models import SourceDocument, SourceSummary


SECTION_HEADING_RE = re.compile(r"^(?:##\s+|\*\*)(.+?)(?:\*\*)?$", re.MULTILINE)
CITATION_RE = re.compile(r"\[(\d+)\]")
REFERENCE_HEADING_RE = re.compile(r"^##\s+References\s*$|^\*\*References\*\*\s*$", re.MULTILINE)


def build_presentable_report(
    report_markdown: str,
    sources: list[SourceDocument],
    summaries: list[SourceSummary],
) -> dict:
    source_items = _build_source_items(sources, summaries)
    sections = _parse_sections(report_markdown)
    cleaned_sections = [
        {
            "title": section["title"],
            "body": _strip_citations(section["body"]),
            "citations": sorted({citation for citation in section["citations"] if citation in source_items}),
        }
        for section in sections
        if section["title"].lower() != "references"
    ]
    response_text = _build_response_text(cleaned_sections, report_markdown)

    return {
        "headline": _extract_headline(report_markdown),
        "summary": _extract_section_text(cleaned_sections, "Executive Summary"),
        "response_text": response_text,
        "sections": cleaned_sections,
        "sources": [source_items[key] for key in sorted(source_items)],
        "stats": {
            "sources_count": len(sources),
            "citations_count": len(CITATION_RE.findall(report_markdown)),
            "sections_count": len(cleaned_sections),
        },
    }


def _build_source_items(
    sources: list[SourceDocument],
    summaries: list[SourceSummary],
) -> dict[int, dict]:
    summary_map = {summary.source_id: summary for summary in summaries}
    items: dict[int, dict] = {}
    for index, source in enumerate(sources, start=1):
        summary = summary_map.get(index)
        items[index] = {
            "id": index,
            "title": source.title,
            "url": source.url,
            "source_type": source.source_type,
            "snippet": source.snippet,
            "summary": summary.summary if summary else "",
            "key_points": summary.key_points if summary else [],
        }
    return items


def _parse_sections(report_markdown: str) -> list[dict]:
    matches = list(SECTION_HEADING_RE.finditer(report_markdown))
    if not matches:
        body = _strip_references(_remove_title(report_markdown.strip()))
        return [{"title": "Report", "body": body, "citations": _extract_citations(body)}]

    sections: list[dict] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(report_markdown)
        title = match.group(1).strip()
        body = report_markdown[start:end].strip()
        sections.append({"title": title, "body": body, "citations": _extract_citations(body)})
    return sections


def _extract_headline(report_markdown: str) -> str:
    for line in report_markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return "Research Report"


def _extract_section_text(sections: list[dict], section_title: str) -> str:
    for section in sections:
        if section["title"].lower() == section_title.lower():
            return section["body"]
    return sections[0]["body"] if sections else ""


def _extract_citations(text: str) -> list[int]:
    return [int(match) for match in CITATION_RE.findall(text)]


def _strip_citations(text: str) -> str:
    cleaned = CITATION_RE.sub("", text)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r" \.", ".", cleaned)
    return cleaned.strip()


def _strip_references(text: str) -> str:
    match = REFERENCE_HEADING_RE.search(text)
    if match:
        return text[: match.start()].strip()
    return text


def _remove_title(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].strip().startswith("# "):
        return "\n".join(lines[1:]).strip()
    return text


def _build_response_text(sections: list[dict], report_markdown: str) -> str:
    if sections:
        blocks = []
        for section in sections:
            body = section["body"].strip()
            if not body:
                continue
            if section["title"].lower() == "executive summary":
                blocks.append(body)
            else:
                blocks.append(f"{section['title']}\n{body}")
        return "\n\n".join(blocks).strip()

    fallback = _strip_citations(_strip_references(_remove_title(report_markdown)))
    return fallback.strip()
