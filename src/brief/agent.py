import os
from dotenv import load_dotenv

load_dotenv()
from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model
from tavily import TavilyClient

client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def search_web(query: str, max_results: int = 5) -> str:
    """Search the web for upto date information.
    Return a numbered list of results with title, url, and a short summary.

    Args:
        query: The query to search the web for.
        num_results: The number of results to return.
    Returns:
        A string with a numbered list of results with title, url, and a short summary.

    Example:
    1. Title: "Apple Benefits for Farmers", URL: "https://www.example.com/apple-benefits-for-farmers", Summary: "Apple benefits for farmers include increased productivity, improved soil health, and reduced pest pressure."
    """
    response = client.search(query=query, max_results=max_results)
    results = response.get("results", [])
    if not results:
        return "No results found"

    result_str = ""
    for i, result in enumerate(results):
        result_str += f"{i+1}. Title: {result['title']}, URL: {result['url']}, Summary: {result.get('content', '')[:300]}\n"
    return result_str


MAX_PAGE_CHARS = 8000


def fetch_page_content(url: str) -> str:
    """Read the full copntext of the web page. Use it after search_web tool, on the 2-3 relevant urls,
    to get the details before answering.

    Args:
        url: the full url to read, taken from search_web tool.
    """

    try:
        response = (client.extract(urls=[url]))
    except Exception as e:
        return f"Error fetching {url}: {e}"

    results = response.get("results", [])
    if not results:
        return f"Error could not read the url: {url}"

    txt = (results[0].get("raw_content") or "").strip()
    if len(txt) > MAX_PAGE_CHARS:
        txt = txt[:MAX_PAGE_CHARS] + "\n\n[...truncated]"

    return f"Source: {url} \n \n {txt}"


# def answer_question(query: str) -> str:
#     """Answer a question directly"""
#     return "This is a test answer"

agent = create_deep_agent(
    model=init_chat_model(
        model="gpt-4o-mini",
        api_key=os.getenv("OPENAI_API_KEY"),
        max_retries=15,
        timeout=120,
    ),
    tools=[search_web, fetch_page_content],
    system_prompt=(
        "You are a research assistant. "
        # "Use search_web to find sources, then use fetch_page_content to read the 2-3 most relevant ones " It does perform the same without this also.
        "Base your answer only on what you read, and cite the URL of the "
        "source for each point."
    ),
)

if __name__ == "__main__":
    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "what enables a farmer to do farming of applesand answer in 3 bullets.",
                }
            ]
        }
    )
    # print(result["messages"][-1].content)
    for m in result["messages"]:
        m.pretty_print()
