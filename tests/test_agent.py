"""Unit tests for the agent's deterministic logic.

The LLM and network are stubbed so the tests are fast, offline, and reliable.
Run with: ``pytest``
"""

from __future__ import annotations

import research_agent.agent as agent_mod
from research_agent.agent import Report, ResearchAgent, Source, _parse_query_list
from research_agent.tools import SearchResult


class FakeLLM:
    """Returns canned responses based on what the prompt is asking for."""

    def __init__(self, plan: str = "", synthesis: str = "") -> None:
        self._plan = plan
        self._synthesis = synthesis

    def generate(self, prompt: str) -> str:
        return self._plan if "research planner" in prompt else self._synthesis


def test_parse_query_list_handles_json():
    assert _parse_query_list('["a", "b", "c"]') == ["a", "b", "c"]


def test_parse_query_list_handles_messy_output():
    raw = "Sure!\n- first query\n- second query\n"
    assert _parse_query_list(raw) == ["first query", "second query"]


def test_plan_caps_to_max_queries():
    agent = ResearchAgent(FakeLLM(plan='["q1", "q2", "q3", "q4", "q5"]'), max_queries=3)
    assert agent.plan("anything") == ["q1", "q2", "q3"]


def test_run_produces_cited_report(monkeypatch):
    # Stub the network layer used inside agent.gather().
    monkeypatch.setattr(
        agent_mod, "web_search",
        lambda query, n: [SearchResult("Example", "https://example.com", "snippet")],
    )
    monkeypatch.setattr(agent_mod, "fetch_text", lambda url, **kw: "Relevant page text.")

    agent = ResearchAgent(FakeLLM(plan='["one query"]', synthesis="Water is wet [1]."))
    report = agent.run("Is water wet?")

    assert isinstance(report, Report)
    assert report.answer == "Water is wet [1]."
    assert len(report.sources) == 1
    assert report.sources[0].url == "https://example.com"
    assert "[Example](https://example.com)" in report.to_markdown()


def test_gather_deduplicates_urls(monkeypatch):
    monkeypatch.setattr(
        agent_mod, "web_search",
        lambda query, n: [SearchResult("Dup", "https://dup.com", "s")],
    )
    monkeypatch.setattr(agent_mod, "fetch_text", lambda url, **kw: "text")

    sources = ResearchAgent(FakeLLM()).gather(["query a", "query b"])
    assert len(sources) == 1
    assert isinstance(sources[0], Source)
