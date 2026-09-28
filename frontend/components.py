"""Streamlit components for rendering council messages."""

import re
from typing import Any

import streamlit as st

from backend.rankings import aggregate_rankings, build_label_to_model


def short_name(model: str) -> str:
    """'openai/gpt-5.1' -> 'gpt-5.1'."""
    return model.split("/")[-1]


def de_anonymize(text: str, label_to_model: dict[str, str]) -> str:
    """Replace 'Response X' labels with bold model names (display only)."""
    def replace(match: re.Match) -> str:
        model = label_to_model.get(match.group(0))
        return f"**{short_name(model)}**" if model else match.group(0)

    return re.sub(r"\bResponse [A-Z]\b", replace, text)


def render_stage1(stage1: list[dict[str, Any]]) -> None:
    with st.expander(f"Stage 1 · Individual responses ({len(stage1)})"):
        if not stage1:
            st.info("No council member responded.")
            return
        for tab, result in zip(st.tabs([short_name(r["model"]) for r in stage1]), stage1):
            with tab:
                st.caption(result["model"])
                st.markdown(result["response"])


def render_stage2(
    stage2: list[dict[str, Any]],
    label_to_model: dict[str, str],
    rankings: list[dict[str, Any]],
) -> None:
    with st.expander(f"Stage 2 · Peer rankings ({len(stage2)})"):
        if rankings:
            st.markdown("**Aggregate rankings** — average position across all peer evaluations (lower is better)")
            st.markdown(
                "| Rank | Model | Avg position | Votes |\n|---:|---|---:|---:|\n"
                + "\n".join(
                    f"| {i} | {short_name(r['model'])} | {r['average_rank']:.2f} | {r['rankings_count']} |"
                    for i, r in enumerate(rankings, start=1)
                )
            )

        if not stage2:
            st.info("No peer evaluations were returned.")
            return

        st.caption(
            "Each model evaluated all responses anonymized as Response A, B, C, etc. "
            "Model names are shown in **bold** below for readability only."
        )
        for tab, result in zip(st.tabs([short_name(r["model"]) for r in stage2]), stage2):
            with tab:
                st.caption(result["model"])
                st.markdown(de_anonymize(result["ranking"], label_to_model))
                if result.get("parsed_ranking"):
                    st.markdown("**Extracted ranking:**")
                    st.markdown("\n".join(
                        f"{i}. {short_name(label_to_model.get(label, label))}"
                        for i, label in enumerate(result["parsed_ranking"], start=1)
                    ))


def render_stage3(stage3: dict[str, Any]) -> None:
    st.markdown("##### Stage 3 · Final answer")
    st.caption(f"Chairman: {stage3.get('model', 'unknown')}")
    st.markdown(stage3.get("response", ""))


def render_assistant_message(message: dict[str, Any]) -> None:
    stage1 = message.get("stage1") or []
    stage2 = message.get("stage2") or []
    metadata = message.get("metadata") or {}

    # Older saved messages have no metadata; rebuild it from the stages
    label_to_model = metadata.get("label_to_model") or build_label_to_model(stage1)
    rankings = metadata.get("aggregate_rankings") or aggregate_rankings(stage2, label_to_model)

    if metadata.get("failed_models"):
        st.warning("Some council members failed and were skipped: " + ", ".join(metadata["failed_models"]))

    render_stage1(stage1)
    render_stage2(stage2, label_to_model, rankings)
    render_stage3(message.get("stage3") or {})


def render_message(message: dict[str, Any]) -> None:
    with st.chat_message(message["role"]):
        if message["role"] == "user":
            st.markdown(message["content"])
        else:
            render_assistant_message(message)
