from __future__ import annotations

import argparse
from pathlib import Path

from .agent import ResearchAgent
from .config import load_settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Autonomous AI Research Agent")
    parser.add_argument("--query", required=True, help="Research query/topic")
    parser.add_argument("--output-dir", default="reports/latest", help="Output directory")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = load_settings()
    agent = ResearchAgent(settings)
    result = agent.run(query=args.query, output_dir=Path(args.output_dir))
    print(f"Report generated for topic: {result.topic}")
    print(f"Sources collected: {len(result.sources)}")
    print(f"Output directory: {Path(args.output_dir).resolve()}")


if __name__ == "__main__":
    main()
