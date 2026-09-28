"""LLM Council — Streamlit entrypoint.

Run from the project root:
    uv run streamlit run app.py
"""

import streamlit as st

from backend import storage
from backend.config import CHAIRMAN_MODEL, COUNCIL_MODELS, OPENROUTER_API_KEY
from frontend.components import render_message
from frontend.runner import run_council

st.set_page_config(page_title="LLM Council", page_icon="🏛️", layout="wide")

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None


def select_conversation(conversation_id: str | None) -> None:
    st.session_state.conversation_id = conversation_id


# --- Sidebar ---------------------------------------------------------------

with st.sidebar:
    st.title("🏛️ LLM Council")
    st.button("＋ New conversation", on_click=select_conversation, args=(None,), width="stretch")

    st.divider()
    for conv in storage.list_conversations():
        is_current = conv["id"] == st.session_state.conversation_id
        st.button(
            conv["title"],
            key=f"conv_{conv['id']}",
            type="primary" if is_current else "secondary",
            on_click=select_conversation,
            args=(conv["id"],),
            width="stretch",
        )

    st.divider()
    with st.expander("Council configuration"):
        st.markdown("**Members**\n" + "\n".join(f"- {m}" for m in COUNCIL_MODELS))
        st.markdown(f"**Chairman**\n- {CHAIRMAN_MODEL}")

# --- Main ------------------------------------------------------------------

if not OPENROUTER_API_KEY:
    st.error("`OPENROUTER_API_KEY` is not set. Add it to a `.env` file in the project root.")
    st.stop()

conversation = (
    storage.get_conversation(st.session_state.conversation_id)
    if st.session_state.conversation_id else None
)

if conversation is None:
    st.header("Ask the council")
    st.caption(
        "Your question goes to every council member, they anonymously rank each "
        "other's answers, and the chairman synthesizes a final response."
    )
else:
    header, delete = st.columns([6, 1], vertical_alignment="bottom")
    header.header(conversation["title"])
    if delete.button("🗑️ Delete", width="stretch"):
        storage.delete_conversation(conversation["id"])
        select_conversation(None)
        st.rerun()

    for message in conversation["messages"]:
        render_message(message)

if prompt := st.chat_input("Ask the council…"):
    if conversation is None:
        conversation = storage.create_conversation()
        select_conversation(conversation["id"])

    is_first_message = not conversation["messages"]
    storage.add_user_message(conversation["id"], prompt)
    render_message({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        with st.status("Stage 1 · Collecting responses from the council…", expanded=True) as status:
            result = run_council(prompt, generate_title=is_first_message, status=status)
            status.update(label="Council has concluded", state="complete", expanded=False)

    storage.add_assistant_message(conversation["id"], result)
    if result.get("title"):
        storage.update_title(conversation["id"], result["title"])
    st.rerun()
