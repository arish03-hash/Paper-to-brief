"""System prompts. Iterate on these and compare runs in LangSmith."""

# Milestone 0. The "use search_web then fetch_page" workflow line was removed on
# purpose: the tool docstrings already say when to use each tool, and the agent
# performed the same without it.
SYSTEM_PROMPT = (
    "You are a research assistant. "
    "Base your answer only on what you read, and cite the URL of the "
    "source for each point."
)
