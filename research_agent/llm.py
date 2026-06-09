"""Thin, testable wrapper around the Google Gemini API.

The rest of the codebase depends only on the small ``LLM`` protocol defined
here, which keeps the agent logic decoupled from the SDK and makes it trivial
to inject a fake model in tests.
"""

from __future__ import annotations

import os
from typing import Protocol


class LLM(Protocol):
    """Minimal interface the agent needs from a language model."""

    def generate(self, prompt: str) -> str:  # pragma: no cover - protocol
        ...


class GeminiLLM:
    """Production implementation backed by ``google-genai``.

    Args:
        model: A Gemini model id. ``gemini-2.0-flash`` is fast and cheap and
            is plenty for planning/synthesis; bump to ``gemini-2.5-pro`` for
            harder questions.
        api_key: Defaults to the ``GEMINI_API_KEY`` (or ``GOOGLE_API_KEY``)
            environment variable.
    """

    def __init__(self, model: str = "gemini-2.0-flash", api_key: str | None = None) -> None:
        key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key:
            raise RuntimeError(
                "No API key found. Set GEMINI_API_KEY (get one free at "
                "https://aistudio.google.com/apikey)."
            )
        # Imported lazily so the package can be imported (and tested) without
        # the SDK installed.
        from google import genai  # type: ignore

        self._client = genai.Client(api_key=key)
        self._model = model

    def generate(self, prompt: str) -> str:
        resp = self._client.models.generate_content(model=self._model, contents=prompt)
        return (resp.text or "").strip()
