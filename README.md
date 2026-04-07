# Autonomous AI Research Agent

Autonomous AI Research Agent that gathers information, analyzes sources, and generates structured research reports.

## What It Does

- Accepts a query like: `Impact of AI on healthcare startups`
- Searches the web and research papers
- Summarizes findings with an LLM
- Uses a multi-agent workflow (LangGraph): Planner -> Researcher -> Analyst -> Writer
- Stores sources and summaries
- Generates a structured report with citations
- Builds a FAISS index for source retrieval
- Provides a React chat UI for real-time query interaction
- Persists conversation history and reports in a local SQLite database

## Tech Stack

- Python
- Groq API (OpenAI-compatible)
- Django backend + Celery/Redis + SQLite + React (Vite) frontend
- LangChain + LangGraph + FAISS
- Web search via Tavily or SerpAPI
- Research paper search via Semantic Scholar

## Project Structure

```text
src/research_agent/
  agent.py             # Main orchestration
  cli.py               # CLI entrypoint
  config.py            # Env/settings loader
  models.py            # Dataclasses
  multi_agent.py       # LangGraph multi-agent pipeline
  search.py            # Web + paper search providers
  summarizer.py        # Source summarization with LLM
  report_generator.py  # Final report generation with citations
  vector_store.py      # FAISS indexing

src/research_agent_django/
  settings.py          # Django project settings
  urls.py              # Root URL config

src/research_agent_web/
  models.py            # SQLite-backed session/job/message tables
  views.py             # Django JSON API for sessions, jobs, history
  urls.py              # API routes
  tests.py             # Django tests for API and presentation basics

manage.py              # Django entrypoint
ROADMAP.md             # Phase-by-phase upgrade plan

frontend/
  src/App.jsx          # React chat interface
  src/styles.css       # UI styles
  vite.config.js       # Dev proxy to Django API
```

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
pip install -e .
```

3. Configure environment variables:

```bash
copy .env.example .env
```

Set at least:
- `GROQ_API_KEY`
- `TAVILY_API_KEY` or `SERPAPI_API_KEY`

For quick local validation without API keys or API calls, use `--dry-run`.

## Run

```bash
python -m research_agent.cli --query "Impact of AI on healthcare startups" --mode multi --output-dir reports/healthcare-ai
```

Dry run (no external calls):

```bash
python -m research_agent.cli --query "Impact of AI on healthcare startups" --mode multi --dry-run --output-dir reports/dry-run
```

## Run Chat UI (React)

Start backend:

```bash
python manage.py migrate
python manage.py runserver 8000
```

Start worker:

```bash
celery -A research_agent_django worker -l info -P solo
```

Redis is required for the worker queue. Default broker:

```bash
redis://127.0.0.1:6379/0
```

You can override this in `.env` with:

```bash
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0
RESEARCH_USE_CELERY=1
```

Local dev fallback:
- If `RESEARCH_USE_CELERY` is unset or `0`, jobs run in a local background thread.
- If `RESEARCH_USE_CELERY=1` but Redis/Celery publish fails, the app falls back to local execution automatically.

Start frontend (new terminal):

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` and send queries in the chat UI.

## Database Plan

The app now uses a local SQLite database (`db.sqlite3`) through Django ORM.

Tables implemented:
- `ConversationSession`: one saved chat thread, owned by a Django user
- `ConversationMessage`: every user/assistant message, including stored report payloads
- `ResearchJob`: one generation run tied to a session and its initiating user message
- `JobProgressEvent`: ordered progress messages used by the live generating UI
- `SavedReport`: persisted report records with confidence and source counts

This schema gives you:
- persistent chat history across app restarts
- per-user session isolation
- resumable session list in the UI
- traceable job progress for the loading state
- stored assistant outputs and source payloads for later review
- saved report metadata that can later power exports and analytics

The output directory will include:
- `report.md`
- `sources.json`
- `summaries.json`
- `plan.txt`
- `analysis.txt`
- `faiss_index/`

## Notes

- `--mode multi` is the default and runs the LangGraph multi-agent pipeline.
- `--mode single` runs the legacy single-pass workflow.
- `--dry-run` skips all external APIs and writes deterministic mock outputs for testing.
- LLM provider defaults to Groq (`LLM_PROVIDER=groq`), with optional OpenAI fallback.
- Set `MAX_PAPER_RESULTS=0` to disable Semantic Scholar paper search when rate-limited.
- Low-quality/gated sources (for example LinkedIn sign-in pages) are filtered before report generation.
- Django admin is available if you create a superuser: `python manage.py createsuperuser`
- Basic session/report/API tests are available via `python manage.py test`
- Jobs are now intended to run via Celery/Redis instead of in-process threads
- For local development, the app can still run without Redis by using the built-in fallback path
- You can still swap providers and extend orchestration behavior in `agent.py` and `multi_agent.py`.
