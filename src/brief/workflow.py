from typing import Literal

from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.types import Command, interrupt
from pydantic import BaseModel, model_validator

from brief.agent import build_agent

MAX_REVISIONS=2

class Review(BaseModel):
    """What the human sends back form the review phase"""

    action: Literal["approve", "revise", "cancel"]
    feedback: str | None = None

    @model_validator(mode="after")
    def _revise_needs_feedback(self):
        if self.action == "revise" and not (self.feedback or "").strip():
            raise ValueError("action 'revise' needs feedback")
        return self
    
class State(MessagesState):
    revisions: int
    status: str

def _text(message) -> str:
    content = message.content
    if isinstance(content, str):
        return content

    return "".join(b.get("text", "") for b in content if isinstance(b, dict))

def human_review(state: State) -> Command[Literal["research", "finalize", "__end__"]]:
    revisions = state.get("revisions", 0)
    decision = interrupt(
        {
            "type": "review",
            "draft": _text(state["messages"][-1]),
            "revisions": revisions,
            "max_revisions": MAX_REVISIONS,
        },
        response_schema=Review,
    )

    if decision.action == "approve":
        return Command(goto="finalize")

    if decision.action == "revise" and revisions < MAX_REVISIONS:
        return Command(
            goto="research",
            update={
                "messages": [{"role": "user", "content": f"Revise: {decision.feedback}"}],
                "revisions": revisions + 1,
            },
        )

    status = "cancelled" if decision.action=="cancel" else "revision_limit"
    return Command(goto=END, update={"status": status})

def finalize(state: State):
    return {"status": "approved"}

def build_workflow(*, checkpointer=None):
    graph = StateGraph(State)
    graph.add_node("research", build_agent())
    graph.add_node("human_review", human_review)
    graph.add_node("finalize", finalize)
    graph.add_edge(START, "research")
    graph.add_edge("research", "human_review")
    graph.add_edge("finalize", END)
    return graph.compile(checkpointer=checkpointer)

workflow = build_workflow()