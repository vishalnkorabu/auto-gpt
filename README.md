# Autonomous AI Research Agent

Autonomous AI Research Agent that gathers information, analyzes sources, and generates structured research reports.

## What It Does

- Accepts a query like: `Impact of AI on healthcare startups`
- Searches the web and research papers
- Summarizes findings with an LLM
- Stores sources and summaries
- Generates a structured report with citations
- Builds a FAISS index for source retrieval

## Tech Stack

- Python
- OpenAI API
- LangChain + FAISS
- Web search via Tavily or SerpAPI
- Research paper search via Semantic Scholar

## Project Structure

```text
src/research_agent/
  agent.py             # Main orchestration
  cli.py               # CLI entrypoint
  config.py            # Env/settings loader
  models.py            # Dataclasses
  search.py            # Web + paper search providers
  summarizer.py        # Source summarization with OpenAI
  report_generator.py  # Final report generation with citations
  vector_store.py      # FAISS indexing
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
- `OPENAI_API_KEY`
- `TAVILY_API_KEY` or `SERPAPI_API_KEY`

## Run

```bash
python -m research_agent.cli --query "Impact of AI on healthcare startups" --output-dir reports/healthcare-ai
```

The output directory will include:
- `report.md`
- `sources.json`
- `summaries.json`
- `faiss_index/`

## Notes

- This is a baseline scaffold for autonomous deep research workflows.
- You can swap providers or add multi-agent planning (CrewAI/LangGraph) in `agent.py`.
