"""Prompt templates for each stage of the council."""

from typing import Any


def build_ranking_prompt(user_query: str, labeled_responses: dict[str, str]) -> str:
    """
    Stage 2 prompt: ask a model to evaluate and rank anonymized responses.

    Args:
        user_query: The original user query
        labeled_responses: {"Response A": "<text>", ...}
    """
    responses_text = "\n\n".join(
        f"{label}:\n{text}" for label, text in labeled_responses.items()
    )

    return f"""You are evaluating different responses to the following question:

Question: {user_query}

Here are the responses from different models (anonymized):

{responses_text}

Your task:
1. First, evaluate each response individually. For each response, explain what it does well and what it does poorly.
2. Then, at the very end of your response, provide a final ranking.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")
- Do not add any other text or explanations in the ranking section

Example of the correct format for your ENTIRE response:

Response A provides good detail on X but misses Y...
Response B is accurate but lacks depth on Z...
Response C offers the most comprehensive answer...

FINAL RANKING:
1. Response C
2. Response A
3. Response B

Now provide your evaluation and ranking:"""


def build_chairman_prompt(
    user_query: str,
    stage1: list[dict[str, Any]],
    stage2: list[dict[str, Any]],
) -> str:
    """Stage 3 prompt: the chairman synthesizes all responses and rankings."""
    stage1_text = "\n\n".join(
        f"Model: {r['model']}\nResponse: {r['response']}" for r in stage1
    )
    stage2_text = "\n\n".join(
        f"Model: {r['model']}\nRanking: {r['ranking']}" for r in stage2
    )

    return f"""You are the Chairman of an LLM Council. Multiple AI models have provided responses to a user's question, and then ranked each other's responses.

Original Question: {user_query}

STAGE 1 - Individual Responses:
{stage1_text}

STAGE 2 - Peer Rankings:
{stage2_text}

Your task as Chairman is to synthesize all of this information into a single, comprehensive, accurate answer to the user's original question. Consider:
- The individual responses and their insights
- The peer rankings and what they reveal about response quality
- Any patterns of agreement or disagreement

Provide a clear, well-reasoned final answer that represents the council's collective wisdom:"""


def build_title_prompt(user_query: str) -> str:
    """Prompt for a short conversation title."""
    return f"""Generate a very short title (3-5 words maximum) that summarizes the following question.
The title should be concise and descriptive. Do not use quotes or punctuation in the title.

Question: {user_query}

Title:"""


def clean_title(raw_title: str) -> str:
    """Strip quotes and truncate a generated title."""
    title = raw_title.strip().strip('"\'')
    if len(title) > 50:
        title = title[:47] + "..."
    return title or "New Conversation"
