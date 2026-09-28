# CLAUDE.md - Technical Notes for LLM Council

LLM Council is a 3-stage deliberation system where multiple LLMs collaboratively answer user questions. The key idea is anonymized peer review in Stage 2, preventing models from playing favorites.

- **Backend:** LangGraph `StateGraph` in `backend/`
- **Frontend:** Streamlit, `app.py` + `frontend/`. The graph is invoked in-process; there is no HTTP API.

Run: `uv run streamlit run app.py` (http://localhost:8501).

## Backend (`backend/`)

- **`config.py`**: `COUNCIL_MODELS`, `CHAIRMAN_MODEL`, `TITLE_MODEL`, timeouts, `OPENROUTER_API_KEY` from `.env`, and `DATA_DIR` (absolute, anchored to the project root).
- **`llm.py`**: `query_model(model, prompt, *, timeout) -> str | None`. Returns None on failure (logged), which enables graceful degradation.
- **`prompts.py`**: pure prompt builders plus `clean_title`.
- **`rankings.py`**: `build_label_to_model`, `parse_ranking` (FINAL RANKING numbered list, falling back to any "Response X" in order), `aggregate_rankings` (average position, lower is better).
- **`storage.py`**: one JSON file per conversation. Assistant messages are stored as `{role, stage1, stage2, stage3, metadata}`, where metadata is `{label_to_model, aggregate_rankings, failed_models}`.
- **`graph.py`**:
  ```
  START ──Send×N──▶ council_member ──▶ prepare_review ──Send×N──▶ reviewer ──▶ aggregate ──▶ chairman ──▶ END
    └──Send──▶ title ──▶ END                   └──(no stage1)──▶ no_responses ──▶ END
  ```
  - `stage1`/`stage2` use a reducer that merges parallel results in `COUNCIL_MODELS` order. `failed_models` uses `operator.add`.
  - `council_member`/`reviewer` receive only a `MemberTask` `{model, prompt}` via `Send`, not the full state.
  - `prepare_review` is the Stage 1 join point: it assigns anonymous labels and builds one shared ranking prompt.
  - Stateless per run (no checkpointer). Only the current message is sent to the council, not the conversation history.

## Frontend

- **`app.py`**: sidebar (new/select conversations, council config), conversation view, delete button, chat input.
- **`frontend/runner.py`**: `run_council()` does `asyncio.run(council_graph.astream(..., stream_mode=["updates", "values"]))`. Updates are logged into `st.status`, and the last "values" chunk is the final state.
- **`frontend/components.py`**: Stage 1/2 are expanders with one tab per model. Stage 2 shows the raw evaluation with labels de-anonymized to **bold** model names (display only), the extracted ranking so parsing can be verified, and an aggregate table. Old messages without metadata are rebuilt from the stages.

## Gotchas

- Run Streamlit from the project root so `backend` and `frontend` are importable. Standalone scripts need `PYTHONPATH=.`.
- Backend modules use relative imports (`from .config import ...`).
- If models don't follow the ranking format, the fallback regex picks up any "Response X" mentions in order.
