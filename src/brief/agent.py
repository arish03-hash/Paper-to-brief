"""Builds the agent. `agent` is also the graph LangGraph Studio loads (see langgraph.json)."""

import os
from pathlib import Path

from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model
from deepagents.backends import FilesystemBackend
from langchain.agents.middleware import TodoListMiddleware

from brief.prompts import SYSTEM_PROMPT
from brief.tools import RESEARCH_TOOLS

NOTES_DIR = Path("runs/notes")

def build_agent():
    model = init_chat_model(
        model="gpt-4o-mini",
        api_key=os.getenv("OPENAI_API_KEY"),
        max_retries=15,
        timeout=120,
    )
    return create_deep_agent(
        model=model,
        tools=RESEARCH_TOOLS,
        system_prompt=SYSTEM_PROMPT,
        middleware=[TodoListMiddleware()],
        # middleware=[
        #     ModelCallLimitMiddleware(run_limit = 50),
        #     ToolCallLimitMiddleware(run_limit = 50),
        # ],
        backend = FilesystemBackend(root_dir = NOTES_DIR, virtual_mode = True),
    )


agent = build_agent()
