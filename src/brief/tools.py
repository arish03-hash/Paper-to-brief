"""Tools the agent can call: web search and page reading (both via Tavily)."""

import os

from tavily import TavilyClient
from langgraph.types import interrupt

MAX_PAGE_CHARS = 8000
SNIPPET_CHARS = 300

client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

def ask_user(question: str, options: list[str] | None = None) -> str:
    """Ask the human one short question and wait for the answer. Use it only if you are unsure about the question i.e. quesiton is ambiguous or ot ask which kinsd of sources to prioritise.

    Args: 
        question: The question to show the human.
        option: A list of options of suggested answers to show the human.
    """
    answer = interrupt({"type": "ask_user", "question": question, "options": options or []})

    return f"The user answered: {answer}"


LEAD_TOOLS = [ask_user]

def search_web(query: str, max_results: int = 5) -> str:
    """Search the web for up-to-date information.

    Args:
        query: A focused search query, a few keywords works best.
        max_results: Number of results to return (1-8).

    Returns:
        A numbered list of results, each with title, URL and a short summary.
    """
    response = client.search(query=query, max_results=max_results)
    results = response.get("results", [])
    if not results:
        return f"No results found for: {query}"

    result_str = ""
    for i, result in enumerate(results, 1):
        summary = (result.get("content") or "")[:SNIPPET_CHARS]
        result_str += f"{i}. Title: {result['title']}, URL: {result['url']}, Summary: {summary}\n"
    return result_str


def fetch_page(url: str) -> str:
    """Read the full text of a web page. Use it after search_web, on the 2-3 most
    relevant URLs, to get the details before answering.

    Args:
        url: The full URL to read, taken from a search_web result.
    """
    try:
        response = client.extract(urls=[url])
    except Exception as e:
        return f"Error fetching {url}: {e}"

    results = response.get("results", [])
    if not results:
        return f"Error: could not read the URL: {url}"

    txt = (results[0].get("raw_content") or "").strip()
    if len(txt) > MAX_PAGE_CHARS:
        txt = txt[:MAX_PAGE_CHARS] + "\n\n[...truncated]"

    return f"Source: {url}\n\n{txt}"


RESEARCH_TOOLS = [search_web, fetch_page]
