"""Builds the agent. `agent` is also the graph LangGraph Studio loads (see langgraph.json)."""

import os

from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model

from brief.prompts import SYSTEM_PROMPT
from brief.tools import RESEARCH_TOOLS


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
    )


agent = build_agent()
