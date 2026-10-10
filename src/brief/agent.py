import os
from dotenv import load_dotenv
load_dotenv()
from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model

def search_web(query: str) -> str:
    """Search the web for information"""
    return "This is a test search result"

def answer_question(query: str) -> str:
    """Answer a question directly"""
    return "This is a test answer"

agent = create_deep_agent(
    model=init_chat_model(
        model="gpt-4o-mini",
        api_key=os.getenv("OPENAI_API_KEY"),
        max_retries = 15,
        timeout = 120,
    ),
    tools = [search_web, answer_question],
)

if __name__ == "__main__":
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "Use the search_web tool to find what apples enable a farmer to do and answer in 3 bullets."}]}
    )
    # print(result["messages"][-1].content)
    for m in result["messages"]:
        m.pretty_print()