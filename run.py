"""Run the agent on one question, or on every question in evals/questions.txt.

Each run is saved to runs/<timestamp>_<slug>/ (question, answer, stats), and a
summary row is appended to evals/results.csv so milestones can be compared.

Usage:
    uv run python run.py "Your question here"
    uv run python run.py --evals                 # all questions in evals/questions.txt
    uv run python run.py --evals --milestone m1  # label the rows for a later milestone
    uv run python run.py "question" --verbose    # also print every message and tool call
"""

import argparse
import csv
import json
import re
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from langchain_core.callbacks import BaseCallbackHandler, UsageMetadataCallbackHandler

from brief.agent import build_agent

ROOT = Path(__file__).parent
RUNS_DIR = ROOT / "runs"
QUESTIONS_FILE = ROOT / "evals" / "questions.txt"
RESULTS_FILE = ROOT / "evals" / "results.csv"

CSV_COLUMNS = [
    "timestamp", "milestone", "question", "seconds",
    "tool_calls", "tool_calls_by_name",
    "input_tokens", "output_tokens", "total_tokens",
    "run_dir", "quality_1_to_5",
]


def _read_approval() -> str:
    while True:
        choice = input("Approve or reject? [a/r]: ").strip().lower()
        if choice in ["a", "r"]:
            return choice
        print("Enter a to approve or r to reject")

def _read_feedback() -> str:
    while True:
        feedback = input("Reason or requested change: ").strip()
        if feedback:
            return feedback
        print("Please provide a feedback")

def _text(message) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    # Some models return a list of content blocks.
    return "".join(b.get("text", "") for b in content if isinstance(b, dict))

def _read_answer(payload: dict) -> str:
    print(f"\nThe agent asks: {payload['question']}")
    for i, option in enumerate(payload.get("options") or [], 1):
        print(f" {i}. {option}")

    while True:
        answer= input("Your answer: ").strip()
        if answer:
            return answer
        print("Please type an answer")

def _slug(text: str, length: int = 40) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:length]


class ToolCallCounter(BaseCallbackHandler):
    """Counts every tool call in a run, including calls made inside subagents."""

    def __init__(self):
        self.counts = Counter()

    def on_tool_start(self, serialized, input_str, **kwargs):
        name = (serialized or {}).get("name") or kwargs.get("name") or "unknown"
        self.counts[name] += 1
        if name == "task":
            sub=(kwargs.get("inputs") or {}).get("subagent_type", "?")
            print(f"[subagent started: {sub}]")


def run_question(question: str, milestone: str, verbose: bool = False) -> dict:
    print(f"\n=== {question}")
    # Callbacks see every model and tool call, subagents included. Counting from
    # result["messages"] would miss subagent work, which never enters that list.
    tool_counter = ToolCallCounter()
    usage = UsageMetadataCallbackHandler()

    agent = build_agent(checkpointer = InMemorySaver())
    config = {
        "configurable": {"thread_id": str(uuid4())},
        "callbacks": [tool_counter, usage],
    }

    start = time.perf_counter()
    result = agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
        config=config,
    )

    while result.get("__interrupt__"):
        responses = {}

        for pending in result["__interrupt__"]:
            payload = pending.value

            if isinstance(payload, dict) and payload.get("type")=="ask_user":
                responses[pending.id] = _read_answer(payload)
                continue

            if (
                not isinstance(payload, dict)
                or "action_requests" not in payload
            ):
                raise ValueError("unexpected approval interrupt payload")

            decisions = []

            for action in payload["action_requests"]:
                print(f"\nTool awaiting approval: {action['name']}")
                print(json.dumps(action["args"], indent=2))

                if _read_approval() == "a":
                    decisions.append({"type": "approve"})
                else:
                    feedback = _read_feedback()
                    decisions.append({
                        "type": "reject",
                        "message": (
                            "This tool call was not expected. "
                            f"Human feedback: {feedback}"
                        ),
                    })

            responses[pending.id] = {"decisions": decisions}

        result = agent.invoke(
            Command(resume=responses),
            config=config,
        )
        
    seconds = round(time.perf_counter() - start, 1)

    messages = result["messages"]
    if verbose:
        # Main agent only. Subagent steps are visible in LangSmith.
        for m in messages:
            m.pretty_print()

    tool_calls = tool_counter.counts
    input_tokens = sum(u.get("input_tokens", 0) for u in usage.usage_metadata.values())
    output_tokens = sum(u.get("output_tokens", 0) for u in usage.usage_metadata.values())

    answer = _text(messages[-1])
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = RUNS_DIR / f"{timestamp}_{_slug(question)}"
    run_dir.mkdir(parents=True, exist_ok=True)

    stats = {
        "timestamp": timestamp,
        "milestone": milestone,
        "question": question,
        "seconds": seconds,
        "tool_calls": sum(tool_calls.values()),
        "tool_calls_by_name": dict(tool_calls),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "run_dir": str(run_dir.relative_to(ROOT)),
    }
    (run_dir / "question.md").write_text(question, encoding="utf-8")
    (run_dir / "answer.md").write_text(answer, encoding="utf-8")
    (run_dir / "stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")

    if not verbose:  # verbose already printed it as the last message
        print(answer)
    print(
        f"\n--- {seconds}s | {stats['tool_calls']} tool calls {dict(tool_calls)} | "
        f"{stats['total_tokens']} tokens | saved to {stats['run_dir']}"
    )
    return stats


def append_results(rows: list[dict]) -> None:
    is_new = not RESULTS_FILE.exists()
    with RESULTS_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        if is_new:
            writer.writeheader()
        for row in rows:
            writer.writerow({
                **row,
                "tool_calls_by_name": json.dumps(row["tool_calls_by_name"]),
                "quality_1_to_5": "",  # fill in by hand after reading the answer
            })


def load_questions() -> list[str]:
    lines = QUESTIONS_FILE.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Paper-to-Brief agent.")
    parser.add_argument("question", nargs="?", help="A single question to research.")
    parser.add_argument("--evals", action="store_true", help="Run every question in evals/questions.txt.")
    parser.add_argument("--milestone", default="m0", help="Label for results.csv (default: m0).")
    parser.add_argument("--verbose", action="store_true", help="Print every message and tool call.")
    args = parser.parse_args()

    if args.evals:
        questions = load_questions()
    elif args.question:
        questions = [args.question]
    else:
        parser.error('give a question, e.g. run.py "What is MCP?", or use --evals')

    rows = [run_question(q, args.milestone, args.verbose) for q in questions]
    append_results(rows)
    print(f"\nAppended {len(rows)} row(s) to {RESULTS_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
