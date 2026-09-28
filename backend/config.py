"""Configuration for the LLM Council."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# OpenRouter API
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Council members - list of OpenRouter model identifiers
COUNCIL_MODELS = [
    "openai/gpt-5.1",
    "google/gemini-3-pro-preview",
    "anthropic/claude-sonnet-4.5",
    "x-ai/grok-4",
]

# Chairman model - synthesizes the final response
CHAIRMAN_MODEL = "google/gemini-3-pro-preview"

# Fast, cheap model used to generate conversation titles
TITLE_MODEL = "google/gemini-2.5-flash"

# Request timeouts (seconds)
MODEL_TIMEOUT = 120.0
TITLE_TIMEOUT = 30.0

# Conversation storage, anchored to the project root so the working directory doesn't matter
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "conversations"
