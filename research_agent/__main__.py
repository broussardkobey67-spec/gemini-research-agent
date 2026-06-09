"""Enables ``python -m research_agent "your question"``."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
