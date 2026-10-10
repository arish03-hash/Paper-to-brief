"""Paper-to-Brief: a deep research agent.

Loading .env here means every module in the package (tools, agent, run.py)
sees the API keys, however the package is imported.
"""

from dotenv import load_dotenv

load_dotenv()
