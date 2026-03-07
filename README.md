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

## Tech Stack

- Python
- Groq API (OpenAI-compatible)
- FastAPI backend + React (Vite) frontend
- LangChain + LangGraph + FAISS
- Web search via Tavily or SerpAPI
- Research paper search via Semantic Scholar

## Project Structure

```text
src/research_agent/
  agent.py             # Main orchestration
  api_server.py        # FastAPI endpoint for chat UI
  cli.py               # CLI entrypoint
  config.py            # Env/settings loader
  models.py            # Dataclasses
  multi_agent.py       # LangGraph multi-agent pipeline
  search.py            # Web + paper search providers
  summarizer.py        # Source summarization with LLM
  report_generator.py  # Final report generation with citations
  vector_store.py      # FAISS indexing

frontend/
  src/App.jsx          # React chat interface
  src/styles.css       # UI styles
  vite.config.js       # Dev proxy to FastAPI
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
uvicorn research_agent.api_server:app --reload --port 8000
```

Start frontend (new terminal):

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` and send queries in the chat UI.

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
- You can still swap providers and extend orchestration behavior in `agent.py` and `multi_agent.py`.
