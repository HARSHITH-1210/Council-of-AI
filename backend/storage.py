"""JSON-file storage for conversations (one file per conversation in DATA_DIR)."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import DATA_DIR

DEFAULT_TITLE = "New Conversation"


def _path(conversation_id: str) -> Path:
    return DATA_DIR / f"{conversation_id}.json"


def _save(conversation: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _path(conversation["id"]).write_text(
        json.dumps(conversation, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def create_conversation() -> dict[str, Any]:
    """Create and save a new, empty conversation."""
    conversation = {
        "id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "title": DEFAULT_TITLE,
        "messages": [],
    }
    _save(conversation)
    return conversation


def get_conversation(conversation_id: str) -> dict[str, Any] | None:
    """Load a conversation, or None if it doesn't exist."""
    path = _path(conversation_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_conversations() -> list[dict[str, Any]]:
    """List conversation summaries (id, created_at, title), newest first."""
    if not DATA_DIR.exists():
        return []

    summaries = []
    for path in DATA_DIR.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        summaries.append({
            "id": data["id"],
            "created_at": data["created_at"],
            "title": data.get("title", DEFAULT_TITLE),
        })

    return sorted(summaries, key=lambda c: c["created_at"], reverse=True)


def _update(conversation_id: str, change) -> None:
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")
    change(conversation)
    _save(conversation)


def add_user_message(conversation_id: str, content: str) -> None:
    _update(conversation_id, lambda c: c["messages"].append(
        {"role": "user", "content": content}
    ))


def add_assistant_message(conversation_id: str, result: dict[str, Any]) -> None:
    """Save a council result (the final graph state) as an assistant message."""
    message = {
        "role": "assistant",
        "stage1": result.get("stage1", []),
        "stage2": result.get("stage2", []),
        "stage3": result.get("stage3", {}),
        "metadata": {
            "label_to_model": result.get("label_to_model", {}),
            "aggregate_rankings": result.get("aggregate_rankings", []),
            "failed_models": result.get("failed_models", []),
        },
    }
    _update(conversation_id, lambda c: c["messages"].append(message))


def update_title(conversation_id: str, title: str) -> None:
    _update(conversation_id, lambda c: c.update(title=title))


def delete_conversation(conversation_id: str) -> None:
    _path(conversation_id).unlink(missing_ok=True)
