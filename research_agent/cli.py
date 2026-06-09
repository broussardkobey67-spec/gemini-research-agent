"""Command-line entry point.

Usage:
    python -m research_agent "your question" [--model gemini-2.5-pro] [-o report.md]
"""

from __future__ import annotations

import argparse
import sys

from .agent import ResearchAgent
from .llm import GeminiLLM


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="research_agent",
        description="Autonomous web research agent powered by Google Gemini.",
    )
    parser.add_argument("question", help="The question to research.")
    parser.add_argument("--model", default="gemini-2.0-flash", help="Gemini model id.")
    parser.add_argument("--max-queries", type=int, default=4, help="Sub-queries to plan.")
    parser.add_argument("-o", "--output", help="Write the report to this file.")
    args = parser.parse_args(argv)

    try:
        llm = GeminiLLM(model=args.model)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    agent = ResearchAgent(llm, max_queries=args.max_queries)

    print(f"Researching: {args.question}\n", file=sys.stderr)
    report = agent.run(args.question)
    markdown = report.to_markdown()

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(markdown)
        print(f"Wrote report to {args.output} ({len(report.sources)} sources).", file=sys.stderr)
    else:
        print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
