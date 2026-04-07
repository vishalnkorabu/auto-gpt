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

HIGH_TRUST_DOMAINS = {
    "nature.com",
    "nejm.org",
    "thelancet.com",
    "jamanetwork.com",
    "nih.gov",
    "fda.gov",
    "who.int",
    "sciencedirect.com",
    "stanford.edu",
    "harvard.edu",
    "mit.edu",
    "pubmed.ncbi.nlm.nih.gov",
    "semanticscholar.org",
}


def filter_high_quality_sources(sources: list[SourceDocument]) -> list[SourceDocument]:
    filtered: list[SourceDocument] = []
    for source in sources:
        if _is_high_quality(source):
            filtered.append(source)
    return filtered


def score_source_credibility(source: SourceDocument) -> float:
    domain = _normalized_domain(source.url)
    if not domain:
        return 0.15

    score = 0.45
    if any(domain == trusted or domain.endswith(f".{trusted}") for trusted in HIGH_TRUST_DOMAINS):
        score += 0.35
    if source.source_type == "paper":
        score += 0.15

    content_length = len((source.content or "").split())
    if content_length > 500:
        score += 0.08
    elif content_length > 150:
        score += 0.04

    if _is_high_quality(source):
        score += 0.07
    else:
        score -= 0.2

    return round(max(0.0, min(score, 1.0)), 2)


def score_report_confidence(sources: list[SourceDocument], citations_count: int) -> float:
    if not sources:
        return 0.0

    credibility_scores = [score_source_credibility(source) for source in sources]
    source_score = sum(credibility_scores) / len(credibility_scores)
    citation_score = min(citations_count / max(len(sources), 1), 3) / 3
    diversity_bonus = 0.08 if len({source.source_type for source in sources}) > 1 else 0.0
    confidence = (source_score * 0.72) + (citation_score * 0.2) + diversity_bonus
    return round(max(0.0, min(confidence, 1.0)), 2)


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
