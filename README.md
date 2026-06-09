# gemini-research-agent

A small, readable **autonomous research agent** built on Google Gemini. Give it a
question; it plans focused web searches, reads the results, and writes a clear
answer with inline citations back to the sources it actually used.

It's intentionally compact (~300 lines of core logic) so the agent loop is easy
to follow and extend — no heavyweight framework, just Python, the Gemini API,
and a web search tool.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-pytest-brightgreen)

## What it does

```
$ research-agent "What are the main differences between REST and GraphQL APIs?"

Researching: What are the main differences between REST and GraphQL APIs?

# What are the main differences between REST and GraphQL APIs?

REST and GraphQL differ most in how clients request data...
  - Data fetching: REST returns fixed shapes per endpoint; GraphQL lets the
    client ask for exactly the fields it needs [1][3].
  ...

## Sources
1. https://graphql.org/learn/
2. https://blog.postman.com/rest-vs-graphql/
3. https://aws.amazon.com/compare/the-difference-between-graphql-and-rest/
```

See [`examples/sample_report.md`](examples/sample_report.md) for full output.

## How it works

The agent runs a simple, transparent three-step loop:

```
question
   │
   ▼
┌─────────┐   LLM plans 3–4 focused
│  plan   │   sub-queries (JSON)
└────┬────┘
     ▼
┌─────────┐   DuckDuckGo search +
│ gather  │   polite page fetch, deduped
└────┬────┘
     ▼
┌─────────┐   LLM synthesizes a cited
│synthesize│  answer from ONLY those sources
└────┬────┘
     ▼
  Report (answer + sources)
```

Only the two genuinely language-shaped steps — **planning** and **synthesis** —
call the LLM. Searching, fetching, and de-duplication are plain deterministic
Python, which keeps cost down and behaviour easy to reason about. The synthesis
prompt instructs the model to cite inline and to use *only* the retrieved
sources, which keeps answers grounded instead of hallucinated.

## Install

```bash
git clone https://gitlab.com/broussardkobey67/gemini-research-agent.git
cd gemini-research-agent
pip install -r requirements.txt        # or: pip install -e .
```

Set a Gemini API key (free at [aistudio.google.com/apikey](https://aistudio.google.com/apikey)):

```bash
export GEMINI_API_KEY="your-key-here"
```

## Usage

```bash
# Print a report to the terminal
research-agent "How does HTTP/3 improve on HTTP/2?"

# Pick a stronger model and save to a file
research-agent "Compare Postgres and SQLite for a small SaaS" \
    --model gemini-2.5-pro -o report.md

# Or run as a module without installing
python -m research_agent "What is retrieval-augmented generation?"
```

Use it as a library:

```python
from research_agent import ResearchAgent, GeminiLLM

agent = ResearchAgent(GeminiLLM(model="gemini-2.0-flash"))
report = agent.run("What is the CAP theorem?")
print(report.answer)
for s in report.sources:
    print(s.index, s.url)
```

## Testing

The agent's logic is decoupled from the LLM and the network (both sit behind
small interfaces), so the suite runs fully offline:

```bash
pip install pytest
pytest
```

## Project structure

```
research_agent/
├── llm.py      # Gemini wrapper behind a 1-method protocol (swappable / fakeable)
├── tools.py    # web_search() + fetch_text() — no API key needed
├── agent.py    # plan → gather → synthesize loop and the Report model
└── cli.py      # argparse entry point
tests/
└── test_agent.py  # offline unit tests with a fake LLM + stubbed network
```

## Design notes

- **Swappable model.** Everything depends on a one-method `LLM` protocol, so
  pointing this at a different provider is a single new class.
- **Grounded by construction.** The model only ever sees retrieved text and is
  told to cite from it — there's no path for it to answer from memory alone.
- **Cheap by default.** `gemini-2.0-flash` handles planning and synthesis well;
  the model is called twice per question regardless of how many pages are read.

## License

MIT © Kobey Broussard
