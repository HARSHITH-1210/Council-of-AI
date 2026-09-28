# LLM Council

Instead of asking one LLM, ask a **council** of them. Your question goes to several models (GPT, Gemini, Claude, Grok, … via [OpenRouter](https://openrouter.ai/)), they review each other's answers anonymously, and a Chairman model writes the final response.

- **Backend:** [LangGraph](https://langchain-ai.github.io/langgraph/) workflow
- **Frontend:** [Streamlit](https://streamlit.io/) chat app

Based on [karpathy/llm-council](https://github.com/karpathy/llm-council).

## How it works

1. **Stage 1: First opinions.** Every council model answers the question in parallel. Each answer is viewable in its own tab.
2. **Stage 2: Peer review.** Answers are anonymized as *Response A, B, C…* so models can't play favorites. Each model evaluates and ranks them; the rankings are combined into an aggregate score.
3. **Stage 3: Final answer.** The Chairman reads all answers and rankings and synthesizes one final response.

The LangGraph workflow (`backend/graph.py`):

```
START ──Send×N──▶ council_member ──▶ prepare_review ──Send×N──▶ reviewer ──▶ aggregate ──▶ chairman ──▶ END
  │                                        │
  └──Send──▶ title ──▶ END                 └──(all models failed)──▶ no_responses ──▶ END
```

## Setup

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

Create a `.env` file in the project root:

```bash
OPENROUTER_API_KEY=sk-or-v1-...
```

Get a key at [openrouter.ai](https://openrouter.ai/) and add credits.

## Run

```bash
uv run streamlit run app.py
```

Then open http://localhost:8501.

## Configure the council

Edit `backend/config.py`:

```python
COUNCIL_MODELS = [
    "openai/gpt-5.1",
    "google/gemini-3-pro-preview",
    "anthropic/claude-sonnet-4.5",
    "x-ai/grok-4",
]
CHAIRMAN_MODEL = "google/gemini-3-pro-preview"
```

Any [OpenRouter model ID](https://openrouter.ai/models) works. IDs ending in `:free` cost nothing.

## Project structure

```
app.py                  Streamlit entrypoint (page layout, sidebar, chat input)
frontend/
  components.py         Rendering of Stage 1 / 2 / 3 results
  runner.py             Runs the graph and streams progress into the UI
backend/
  graph.py              LangGraph workflow (nodes, edges, state)
  prompts.py            Prompt templates for each stage
  rankings.py           Anonymization, ranking parsing, aggregate scores
  llm.py                OpenRouter client
  storage.py            Conversations saved as JSON in data/conversations/
  config.py             Models, API key, settings
```
