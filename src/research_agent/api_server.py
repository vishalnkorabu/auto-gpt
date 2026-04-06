from __future__ import annotations

from datetime import datetime
from pathlib import Path
from threading import Lock, Thread
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .agent import ResearchAgent
from .config import load_settings
from .presentation import build_presentable_report


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
    report: dict


class JobStartResponse(BaseModel):
    job_id: str


class JobStatusResponse(BaseModel):
    job_id: str
    state: str
    progress_messages: list[str]
    result: ChatResponse | None = None
    error: str | None = None


app = FastAPI(title="AI Research Agent API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_jobs: dict[str, dict] = {}
_jobs_lock = Lock()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat/start", response_model=JobStartResponse)
def start_chat(req: ChatRequest) -> JobStartResponse:
    job_id = uuid4().hex
    with _jobs_lock:
        _jobs[job_id] = {
            "state": "queued",
            "progress_messages": ["Queued research job."],
            "result": None,
            "error": None,
        }

    thread = Thread(target=_run_job, args=(job_id, req), daemon=True)
    thread.start()
    return JobStartResponse(job_id=job_id)


@app.get("/api/chat/status/{job_id}", response_model=JobStatusResponse)
def chat_status(job_id: str) -> JobStatusResponse:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found.")
        return JobStatusResponse(
            job_id=job_id,
            state=job["state"],
            progress_messages=list(job["progress_messages"]),
            result=job["result"],
            error=job["error"],
        )


def _run_job(job_id: str, req: ChatRequest) -> None:
    def emit(message: str) -> None:
        with _jobs_lock:
            job = _jobs.get(job_id)
            if job is None:
                return
            if not job["progress_messages"] or job["progress_messages"][-1] != message:
                job["progress_messages"].append(message)

    with _jobs_lock:
        _jobs[job_id]["state"] = "running"

    try:
        settings = load_settings(require_api_keys=not req.dry_run)
        agent = ResearchAgent(settings)
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("reports/api") / run_id
        result = agent.run(
            query=req.query,
            output_dir=output_dir,
            mode=req.mode,
            dry_run=req.dry_run,
            progress_callback=emit,
        )
        answer = _build_brief(result.markdown)
        report = build_presentable_report(result.markdown, result.sources, result.summaries)
        response = ChatResponse(
            query=req.query,
            answer=answer,
            report_markdown=result.markdown,
            sources_count=len(result.sources),
            output_dir=str(output_dir),
            report=report,
        )
        with _jobs_lock:
            _jobs[job_id]["state"] = "completed"
            _jobs[job_id]["result"] = response
    except Exception as exc:
        with _jobs_lock:
            _jobs[job_id]["state"] = "failed"
            _jobs[job_id]["error"] = f"Run failed: {exc}"


def _build_brief(report_markdown: str) -> str:
    lines = [line.strip() for line in report_markdown.splitlines() if line.strip()]
    if not lines:
        return "No report content produced."
    for i, line in enumerate(lines):
        if "Executive Summary" in line and i + 1 < len(lines):
            return lines[i + 1]
    return lines[0]
