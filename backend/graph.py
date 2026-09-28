"""LangGraph workflow for the 3-stage LLM Council.

    START ──Send×N──▶ council_member ──▶ prepare_review ──Send×N──▶ reviewer ──▶ aggregate ──▶ chairman ──▶ END
      │                                        │
      └──Send──▶ title ──▶ END                 └──(no responses)──▶ no_responses ──▶ END

Each council model runs as its own `council_member` / `reviewer` task, so the
models are queried in parallel and progress can be streamed per model.
"""

import operator
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from .config import CHAIRMAN_MODEL, COUNCIL_MODELS, TITLE_MODEL, TITLE_TIMEOUT
from .llm import query_model
from .prompts import build_chairman_prompt, build_ranking_prompt, build_title_prompt, clean_title
from .rankings import aggregate_rankings, build_label_to_model, parse_ranking


def _merge_in_council_order(left: list[dict], right: list[dict]) -> list[dict]:
    """Reducer: combine parallel results, keeping the COUNCIL_MODELS order."""
    order = {model: i for i, model in enumerate(COUNCIL_MODELS)}
    return sorted(left + right, key=lambda r: order.get(r["model"], len(order)))


class CouncilState(TypedDict, total=False):
    """Shared state for one run of the council."""
    # Inputs
    user_query: str
    generate_title: bool
    # Outputs
    title: str
    stage1: Annotated[list[dict[str, Any]], _merge_in_council_order]
    stage2: Annotated[list[dict[str, Any]], _merge_in_council_order]
    stage3: dict[str, Any]
    label_to_model: dict[str, str]
    aggregate_rankings: list[dict[str, Any]]
    failed_models: Annotated[list[str], operator.add]
    # Internal
    ranking_prompt: str


class MemberTask(TypedDict):
    """Payload for a single council_member / reviewer task."""
    model: str
    prompt: str


# --- Routing ---------------------------------------------------------------

def dispatch_council(state: CouncilState) -> list[Send]:
    """Fan out Stage 1 to every council model (plus title generation)."""
    sends = [
        Send("council_member", MemberTask(model=model, prompt=state["user_query"]))
        for model in COUNCIL_MODELS
    ]
    if state.get("generate_title"):
        sends.append(Send("title", state))
    return sends


def dispatch_reviewers(state: CouncilState) -> list[Send] | str:
    """Fan out Stage 2 to every council model, or bail out if Stage 1 was empty."""
    if not state.get("stage1"):
        return "no_responses"
    return [
        Send("reviewer", MemberTask(model=model, prompt=state["ranking_prompt"]))
        for model in COUNCIL_MODELS
    ]


# --- Nodes -----------------------------------------------------------------

async def title(state: CouncilState) -> dict:
    """Generate a short conversation title."""
    text = await query_model(
        TITLE_MODEL,
        build_title_prompt(state["user_query"]),
        timeout=TITLE_TIMEOUT,
    )
    return {"title": clean_title(text or "")}


async def council_member(task: MemberTask) -> dict:
    """Stage 1: one council model answers the user's question."""
    text = await query_model(task["model"], task["prompt"])
    if text is None:
        return {"failed_models": [f"{task['model']} (stage 1)"]}
    return {"stage1": [{"model": task["model"], "response": text}]}


def prepare_review(state: CouncilState) -> dict:
    """Anonymize Stage 1 responses and build the shared ranking prompt."""
    stage1 = state.get("stage1", [])
    if not stage1:
        return {}

    label_to_model = build_label_to_model(stage1)
    labeled_responses = {label: r["response"] for label, r in zip(label_to_model, stage1)}
    return {
        "label_to_model": label_to_model,
        "ranking_prompt": build_ranking_prompt(state["user_query"], labeled_responses),
    }


async def reviewer(task: MemberTask) -> dict:
    """Stage 2: one council model evaluates and ranks the anonymized responses."""
    text = await query_model(task["model"], task["prompt"])
    if text is None:
        return {"failed_models": [f"{task['model']} (stage 2)"]}
    return {"stage2": [{
        "model": task["model"],
        "ranking": text,
        "parsed_ranking": parse_ranking(text),
    }]}


def aggregate(state: CouncilState) -> dict:
    """Combine all peer rankings into an average position per model."""
    return {"aggregate_rankings": aggregate_rankings(
        state.get("stage2", []), state["label_to_model"]
    )}


async def chairman(state: CouncilState) -> dict:
    """Stage 3: the chairman synthesizes the final answer."""
    prompt = build_chairman_prompt(state["user_query"], state["stage1"], state.get("stage2", []))
    text = await query_model(CHAIRMAN_MODEL, prompt)
    return {"stage3": {
        "model": CHAIRMAN_MODEL,
        "response": text if text is not None else "Error: Unable to generate final synthesis.",
    }}


def no_responses(state: CouncilState) -> dict:
    """Terminal node used when every council model failed in Stage 1."""
    return {
        "stage3": {"model": "error", "response": "All models failed to respond. Please try again."},
        "label_to_model": {},
        "aggregate_rankings": [],
    }


# --- Graph -----------------------------------------------------------------

def build_council_graph():
    """Build and compile the council StateGraph."""
    builder = StateGraph(CouncilState)

    builder.add_node("title", title)
    builder.add_node("council_member", council_member)
    builder.add_node("prepare_review", prepare_review)
    builder.add_node("reviewer", reviewer)
    builder.add_node("aggregate", aggregate)
    builder.add_node("chairman", chairman)
    builder.add_node("no_responses", no_responses)

    builder.add_conditional_edges(START, dispatch_council, ["council_member", "title"])
    builder.add_edge("title", END)
    builder.add_edge("council_member", "prepare_review")
    builder.add_conditional_edges("prepare_review", dispatch_reviewers, ["reviewer", "no_responses"])
    builder.add_edge("reviewer", "aggregate")
    builder.add_edge("aggregate", "chairman")
    builder.add_edge("chairman", END)
    builder.add_edge("no_responses", END)

    return builder.compile()


council_graph = build_council_graph()
