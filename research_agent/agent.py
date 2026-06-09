"""The research agent: plan -> search -> read -> synthesize, with citations.

The control loop is deliberately small and readable. An LLM is used for the two
genuinely language-shaped steps (planning sub-queries and writing the final
cited report); everything in between is plain, deterministic Python.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .llm import LLM
from .tools import fetch_text, web_search


@dataclass
class Source:
    index: int
    title: str
    url: str
    excerpt: str


@dataclass
class Report:
    question: str
    answer: str
    sources: list[Source] = field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [f"# {self.question}", "", self.answer, "", "## Sources", ""]
        for s in self.sources:
            lines.append(f"{s.index}. [{s.title}]({s.url})")
        return "\n".join(lines)


_PLAN_PROMPT = """You are a research planner. Break the user's question into {n} \
focused web-search queries that together cover the question well. Prefer \
specific, varied angles over near-duplicates.

Question: {question}

Return ONLY a JSON array of query strings, nothing else."""

_SYNTH_PROMPT = """You are a careful research analyst. Using ONLY the numbered \
sources below, write a clear, well-structured answer to the question. Cite \
claims inline with [n] matching the source numbers. If the sources disagree or \
are insufficient, say so plainly. Do not invent facts or citations.

Question: {question}

Sources:
{sources}

Write the answer in Markdown."""


class ResearchAgent:
    def __init__(self, llm: LLM, *, max_queries: int = 4, results_per_query: int = 4) -> None:
        self._llm = llm
        self._max_queries = max_queries
        self._results_per_query = results_per_query

    # -- step 1: planning -------------------------------------------------
    def plan(self, question: str) -> list[str]:
        raw = self._llm.generate(_PLAN_PROMPT.format(n=self._max_queries, question=question))
        queries = _parse_query_list(raw)
        return queries[: self._max_queries] or [question]

    # -- step 2: gathering ------------------------------------------------
    def gather(self, queries: list[str]) -> list[Source]:
        seen: set[str] = set()
        sources: list[Source] = []
        for query in queries:
            for hit in web_search(query, self._results_per_query):
                if hit.url in seen:
                    continue
                seen.add(hit.url)
                excerpt = fetch_text(hit.url) or hit.snippet
                if not excerpt:
                    continue
                sources.append(
                    Source(
                        index=len(sources) + 1,
                        title=hit.title or hit.url,
                        url=hit.url,
                        excerpt=excerpt,
                    )
                )
        return sources

    # -- step 3: synthesis ------------------------------------------------
    def synthesize(self, question: str, sources: list[Source]) -> str:
        if not sources:
            return "I couldn't find sufficient sources to answer this question."
        blocks = "\n\n".join(
            f"[{s.index}] {s.title} ({s.url})\n{s.excerpt}" for s in sources
        )
        return self._llm.generate(_SYNTH_PROMPT.format(question=question, sources=blocks))

    # -- orchestration ----------------------------------------------------
    def run(self, question: str) -> Report:
        queries = self.plan(question)
        sources = self.gather(queries)
        answer = self.synthesize(question, sources)
        return Report(question=question, answer=answer, sources=sources)


_LIST_ITEM = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+(.*)")


def _parse_query_list(raw: str) -> list[str]:
    """Best-effort extraction of a list of queries from an LLM response.

    Prefers a JSON array; falls back to bulleted/numbered list items; and only
    if neither is present treats every non-empty line as a query.
    """
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            return [str(q).strip() for q in data if str(q).strip()]
        except json.JSONDecodeError:
            pass

    # Prefer explicit list markers so conversational preamble ("Sure!") is
    # ignored when the model bullets its queries.
    bullets = [m.group(1).strip() for ln in raw.splitlines() if (m := _LIST_ITEM.match(ln))]
    if bullets:
        return bullets

    return [ln.strip() for ln in raw.splitlines() if ln.strip()]
