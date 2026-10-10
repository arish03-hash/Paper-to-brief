"""Builds the agent. `agent` is also the graph LangGraph Studio loads (see langgraph.json)."""

import os
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain.agents.middleware import TodoListMiddleware
from langchain.chat_models import init_chat_model

from brief.prompts import CRITIC_PROMPT, RESEARCHER_PROMPT, SYSTEM_PROMPT
from brief.tools import RESEARCH_TOOLS

NOTES_DIR = Path("runs/notes")

# Models: the main agent (plans, drafts, applies fixes) and the critic need careful
# instruction-following, so they use gpt-4.1-mini. Researchers only search and
# summarise pages, so they stay on the cheaper gpt-4o-mini.
MAIN_MODEL = "gpt-4.1-mini"
RESEARCHER_MODEL = "openai:gpt-4o-mini"
CRITIC_MODEL = "openai:gpt-4.1-mini"

# M2: web research happens inside this subagent. Its fetched pages stay in its own
# context; the main agent only receives the short report it returns.
RESEARCHER = {
    "name": "researcher",
    "description": (
        "Researches ONE sub-question on the web (search + read pages), saves notes "
        "to the findings file you name, and returns a short cited summary. "
        "Use one researcher per sub-question."
    ),
    "model": RESEARCHER_MODEL,
    "system_prompt": RESEARCHER_PROMPT,
    "tools": RESEARCH_TOOLS,
}

# M3: reviews the draft against the notes. No web tools: it checks the draft against
# what the researchers actually read. deepagents gives it the file tools automatically.
CRITIC = {
    "name": "critic",
    "description": (
        "Reviews a draft answer against the research notes in /findings/ and reports "
        "unsupported claims, wrong citations, duplicates, weak sources and missing parts. "
        "Call it once, after the draft is saved."
    ),
    "model": CRITIC_MODEL,
    "system_prompt": CRITIC_PROMPT,
    "tools": [],
}


def build_agent():
    model = init_chat_model(
        model=MAIN_MODEL,
        api_key=os.getenv("OPENAI_API_KEY"),
        max_retries=15,
        timeout=120,
    )
    return create_deep_agent(
        model=model,
        tools=[],  # main agent has no web tools: it must delegate to the researcher
        system_prompt=SYSTEM_PROMPT,
        subagents=[RESEARCHER, CRITIC],
        middleware=[TodoListMiddleware()],
        backend=FilesystemBackend(root_dir=NOTES_DIR, virtual_mode=True),
    )


agent = build_agent()
