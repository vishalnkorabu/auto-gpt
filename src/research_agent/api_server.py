from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .agent import ResearchAgent
from .config import load_settings


class ChatRequest(BaseModel):
    query: str = Field(min_length=3, max_length=500)
    mode: str = Field(default="multi", pattern="^(multi|single)$")
    dry_run: bool = False


class ChatResponse(BaseModel):
    query: str
    answer: str
    report_markdown: str
    sources_count: int
    output_dir: str


app = FastAPI(title="AI Research Agent API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    try:
        settings = load_settings(require_api_keys=not req.dry_run)
        agent = ResearchAgent(settings)
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("reports/api") / run_id
        result = agent.run(query=req.query, output_dir=output_dir, mode=req.mode, dry_run=req.dry_run)
        answer = _build_brief(result.markdown)
        return ChatResponse(
            query=req.query,
            answer=answer,
            report_markdown=result.markdown,
            sources_count=len(result.sources),
            output_dir=str(output_dir),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Run failed: {exc}") from exc


def _build_brief(report_markdown: str) -> str:
    lines = [line.strip() for line in report_markdown.splitlines() if line.strip()]
    if not lines:
        return "No report content produced."
    for i, line in enumerate(lines):
        if "Executive Summary" in line and i + 1 < len(lines):
            return lines[i + 1]
    return lines[0]
