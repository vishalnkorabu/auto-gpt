from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Settings:
    openai_api_key: str
    openai_model: str
    tavily_api_key: str | None
    serpapi_api_key: str | None
    max_web_results: int
    max_paper_results: int


def load_settings() -> Settings:
    load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY is required.")

    return Settings(
        openai_api_key=openai_api_key,
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip(),
        tavily_api_key=os.getenv("TAVILY_API_KEY", "").strip() or None,
        serpapi_api_key=os.getenv("SERPAPI_API_KEY", "").strip() or None,
        max_web_results=int(os.getenv("MAX_WEB_RESULTS", "6")),
        max_paper_results=int(os.getenv("MAX_PAPER_RESULTS", "4")),
    )
