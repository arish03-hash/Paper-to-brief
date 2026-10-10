# Paper-to-Brief

A deep research agent: give it a question, it plans, researches sub-questions with subagents, critiques its own draft, and writes a cited markdown brief.

Phase 1: LangChain Deep Agents. Phase 2: Pydantic AI for validated structured outputs.

## Prerequisites

- Python 3.13
- [uv](https://docs.astral.sh/uv/) for dependencies and the virtual environment
- API keys:
  - **OpenAI** (model) - https://platform.openai.com
  - **Tavily** (web search) - https://tavily.com
  - **LangSmith** (tracing, optional) - https://smith.langchain.com
  - **Google Gemini** (optional, only if you switch the model to Gemini) - https://aistudio.google.com

## Setup

```powershell
# 1. Clone and enter the project
git clone https://github.com/arish03-hash/Paper-to-brief.git
cd Paper-to-brief

# 2. Install everything from pyproject.toml / uv.lock
uv sync
```

### Packages used (and why)

If you are starting from scratch instead of cloning, these are the `uv add` commands used so far:

```powershell
uv add deepagents langchain        # deep agent harness + LangChain core
uv add langchain-openai            # OpenAI models (gpt-4o-mini) via init_chat_model
uv add python-dotenv               # load API keys from .env
uv add tavily-python               # web search (search_web tool)
uv add "langgraph-cli[inmem]"      # `langgraph dev` + LangGraph Studio
uv add colorama                    # required on Windows for langgraph dev's coloured logs
uv add langchain-google-genai      # optional: Gemini models ("google_genai:<model>")
```

> Do **not** add `google-generativeai` (the old Gemini SDK). It conflicts with `langgraph-cli[inmem]`. Use `langchain-google-genai` instead.

## Environment variables

Copy `.env.example` to `.env` and fill in:

```
OPENAI_API_KEY=
TAVILY_API_KEY=
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=paper-to-brief
# Only if using Gemini:
# GOOGLE_API_KEY=
# Only if your LangSmith account is on the EU region:
# LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com
```

## Project structure

```
src/brief/
  __init__.py   loads .env
  tools.py      search_web, fetch_page (Tavily)
  prompts.py    system prompt
  agent.py      builds the deep agent (`agent` is the graph Studio loads)
run.py          CLI: run one question or all eval questions, save stats
evals/
  questions.txt fixed test questions, same for every milestone
  results.csv   one row per run: time, tool calls, tokens, quality score
runs/           per-run output: question.md, answer.md, stats.json (git-ignored)
langgraph.json  LangGraph Studio config
```

## Running

**One question** (saves the answer and stats to `runs/`):

```powershell
uv run python run.py "What is the Model Context Protocol?"
uv run python run.py "What is the Model Context Protocol?" --verbose   # also print every tool call
```

**All eval questions** (adds one row per question to `evals/results.csv`):

```powershell
uv run python run.py --evals --milestone m0
```

Then open `evals/results.csv`, read each answer in `runs/`, and fill in the `quality_1_to_5` column.

**In LangGraph Studio** (visual, step-by-step):

```powershell
uv run langgraph dev
```

Then open the Studio URL printed in the terminal, select the `brief` graph, add a human message and submit. The graph is configured in `langgraph.json`.

**Traces:** every run (terminal or Studio) appears in LangSmith under the `paper-to-brief` project.

## Milestones

| Milestone | What changes | Status |
|---|---|---|
| m0 | Baseline: `search_web` + `fetch_page`, no planning or files | done |
| m1 | Planning (`write_todos`) + notes saved to files | next |
| m2 | `researcher` subagent per sub-question | |
| m3 | `critic` subagent reviews the draft | |

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'tavily'` | `uv add tavily-python` |
| `langgraph dev` fails with `requires the colorama package` | `uv add colorama` (or set `LOG_COLOR=false` in `.env`) |
| `KeyError: 'summary'` in `search_web` | Tavily's field is `content`, not `summary` |
| OpenAI `429 ... no credits remaining` | Add credit to your OpenAI account |
| `ModuleNotFoundError: No module named 'brief'` | Run `uv sync` once (installs the `brief` package) |
| Git warns `CRLF will be replaced by LF` | Harmless. Set Cursor's `Files: Eol` to `\n` to silence it |
