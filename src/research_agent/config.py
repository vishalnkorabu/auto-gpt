from __future__ import annotations

import os
from dataclasses import replace
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Settings:
    llm_provider: str
    llm_api_key: str
    llm_model: str
    llm_base_url: str | None
    tavily_api_key: str | None
    serpapi_api_key: str | None
    embedding_model: str
    max_web_results: int
    max_paper_results: int
    max_planned_queries: int


RESEARCH_DEPTH_PRESETS = {
    "quick": {"max_web_results": 3, "max_paper_results": 1, "max_planned_queries": 2},
    "standard": {},
    "deep": {"max_web_results": 9, "max_paper_results": 6, "max_planned_queries": 6},
}


def load_settings(require_api_keys: bool = True) -> Settings:
    load_dotenv()
    llm_provider = os.getenv("LLM_PROVIDER", "groq").strip().lower()
    groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()

    if llm_provider == "groq":
        llm_api_key = groq_api_key
        llm_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
        llm_base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").strip()
        if require_api_keys and not llm_api_key:
            raise ValueError("GROQ_API_KEY is required when LLM_PROVIDER=groq.")
    elif llm_provider == "openai":
        llm_api_key = openai_api_key
        llm_model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()
        llm_base_url = os.getenv("OPENAI_BASE_URL", "").strip() or None
        if require_api_keys and not llm_api_key:
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai.")
    else:
        raise ValueError("LLM_PROVIDER must be one of: groq, openai.")

    return Settings(
        llm_provider=llm_provider,
        llm_api_key=llm_api_key,
        llm_model=llm_model,
        llm_base_url=llm_base_url,
        tavily_api_key=os.getenv("TAVILY_API_KEY", "").strip() or None,
        serpapi_api_key=os.getenv("SERPAPI_API_KEY", "").strip() or None,
        embedding_model=os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2").strip(),
        max_web_results=int(os.getenv("MAX_WEB_RESULTS", "6")),
        max_paper_results=int(os.getenv("MAX_PAPER_RESULTS", "4")),
        max_planned_queries=int(os.getenv("MAX_PLANNED_QUERIES", "4")),
    )


def apply_research_depth(settings: Settings, depth: str) -> Settings:
    normalized = (depth or "standard").strip().lower()
    overrides = RESEARCH_DEPTH_PRESETS.get(normalized)
    if overrides is None:
        raise ValueError("research_depth must be one of: quick, standard, deep.")
    if not overrides:
        return settings
    return replace(settings, **overrides)
