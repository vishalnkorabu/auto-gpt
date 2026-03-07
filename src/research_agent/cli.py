from __future__ import annotations

import argparse
from pathlib import Path

from .agent import ResearchAgent
from .config import load_settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Autonomous AI Research Agent")
    parser.add_argument("--query", required=True, help="Research query/topic")
    parser.add_argument("--output-dir", default="reports/latest", help="Output directory")
    parser.add_argument(
        "--mode",
        default="multi",
        choices=["multi", "single"],
        help="Run multi-agent LangGraph workflow (multi) or legacy single flow (single)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without external API calls and generate deterministic mock outputs",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = load_settings(require_api_keys=not args.dry_run)
    agent = ResearchAgent(settings)
    result = agent.run(query=args.query, output_dir=Path(args.output_dir), mode=args.mode, dry_run=args.dry_run)
    print(f"Report generated for topic: {result.topic}")
    print(f"Sources collected: {len(result.sources)}")
    print(f"Execution mode: {args.mode}")
    print(f"Dry run: {args.dry_run}")
    print(f"Output directory: {Path(args.output_dir).resolve()}")


if __name__ == "__main__":
    main()
