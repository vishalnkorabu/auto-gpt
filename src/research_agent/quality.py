from __future__ import annotations

from urllib.parse import urlparse

from .models import SourceDocument


LOW_QUALITY_DOMAINS = {
    "linkedin.com",
    "facebook.com",
    "instagram.com",
    "x.com",
    "twitter.com",
    "pinterest.com",
}

LOW_SIGNAL_PATTERNS = (
    "sign in to view more content",
    "agree & join linkedin",
    "subscribe",
    "related articles",
    "contact us",
    "cookie policy",
    "user agreement",
    "all rights reserved",
)


def filter_high_quality_sources(sources: list[SourceDocument]) -> list[SourceDocument]:
    filtered: list[SourceDocument] = []
    for source in sources:
        if _is_high_quality(source):
            filtered.append(source)
    return filtered


def _is_high_quality(source: SourceDocument) -> bool:
    domain = _normalized_domain(source.url)
    if not domain:
        return False
    if any(domain == blocked or domain.endswith(f".{blocked}") for blocked in LOW_QUALITY_DOMAINS):
        return False

    content = (source.content or "").strip().lower()
    snippet = (source.snippet or "").strip().lower()

    if not content and not snippet:
        return False

    text_for_checks = f"{snippet}\n{content[:2000]}"
    if any(pattern in text_for_checks for pattern in LOW_SIGNAL_PATTERNS):
        return False

    # Avoid near-empty pages and navigation-only pages.
    word_count = len(content.split())
    if word_count < 80 and len(snippet.split()) < 20:
        return False

    return True


def _normalized_domain(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    host = parsed.netloc.lower().strip()
    if host.startswith("www."):
        host = host[4:]
    return host
