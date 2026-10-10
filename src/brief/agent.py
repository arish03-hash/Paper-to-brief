"""Builds the agent. `agent` is also the graph LangGraph Studio loads (see langgraph.json)."""

import os
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain.agents.middleware import TodoListMiddleware
from langchain.chat_models import init_chat_model

from brief.prompts import RESEARCHER_PROMPT, SYSTEM_PROMPT
from brief.tools import RESEARCH_TOOLS

ROOT = Path(__file__).resolve().parents[2]  # project root, wherever you run from
NOTES_DIR = ROOT / "runs" / "notes"

# Milestone 2: web research happens inside this subagent. Its fetched pages stay in
# its own context; the main agent only receives the short report it returns.
RESEARCHER = {
    "name": "researcher",
    "description": (
        "Researches ONE sub-question on the web (search + read pages), saves notes "
        "to the findings file you name, and returns a short cited summary. "
        "Use one researcher per sub-question."
    ),
    "system_prompt": RESEARCHER_PROMPT,
    "tools": RESEARCH_TOOLS,
}

RESEARCHER = {
    "name": "researcher",
    "description": (
        "Researches ONE sub-question on the web (search + read pages), saves notes"
        "to the findings file you name, and returns a short cited summary."
        "Use one researcher per sub-question."
    ),
    "system_prompt": RESEARCHER_PROMPT,
    "tools": RESEARCH_TOOLS,
}

def build_agent():
    model = init_chat_model(
        model="gpt-4o-mini",
        api_key=os.getenv("OPENAI_API_KEY"),
        max_retries=15,
        timeout=120,
    )
    return create_deep_agent(
        model=model,
        tools=[],  # main agent has no web tools: it must delegate to the researcher
        system_prompt=SYSTEM_PROMPT,
        subagents=[RESEARCHER],
        middleware=[TodoListMiddleware()],
        backend=FilesystemBackend(root_dir=NOTES_DIR, virtual_mode=True),
    )


agent = build_agent()
