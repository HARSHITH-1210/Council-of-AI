"""Runs the LangGraph council and streams its progress into the Streamlit UI."""

import asyncio
from typing import Any

from backend.config import CHAIRMAN_MODEL
from backend.graph import council_graph

from .components import short_name


def _log_progress(node: str, update: dict[str, Any], status) -> None:
    """Turn one graph node update into a line in the st.status box."""
    for failed in update.get("failed_models", []):
        status.write(f"⚠️ {failed} failed")

    if node == "council_member" and update.get("stage1"):
        status.write(f"✅ Stage 1 · **{short_name(update['stage1'][0]['model'])}** answered")
    elif node == "prepare_review" and update.get("label_to_model"):
        status.update(label="Stage 2 · Council members are reviewing each other…")
        status.write(f"🕵️ Anonymized {len(update['label_to_model'])} responses for peer review")
    elif node == "reviewer" and update.get("stage2"):
        status.write(f"✅ Stage 2 · **{short_name(update['stage2'][0]['model'])}** submitted rankings")
    elif node == "aggregate":
        status.update(label=f"Stage 3 · Chairman {short_name(CHAIRMAN_MODEL)} is synthesizing…")
    elif node == "chairman":
        status.write("✅ Stage 3 · Final answer ready")


async def _stream_council(inputs: dict[str, Any], status) -> dict[str, Any]:
    final_state: dict[str, Any] = {}
    async for mode, chunk in council_graph.astream(inputs, stream_mode=["updates", "values"]):
        if mode == "values":
            final_state = chunk
        else:
            for node, update in chunk.items():
                _log_progress(node, update or {}, status)

    return final_state


def run_council(user_query: str, *, generate_title: bool, status) -> dict[str, Any]:
    """
    Run the council graph to completion, logging progress into `status`.

    Returns:
        The final graph state (stage1, stage2, stage3, label_to_model, ...)
    """
    inputs = {"user_query": user_query, "generate_title": generate_title}
    return asyncio.run(_stream_council(inputs, status))
